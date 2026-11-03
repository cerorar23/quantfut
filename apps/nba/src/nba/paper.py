"""Immutable pregame shadow cohorts and later official descriptive scoring."""
from collections import Counter, defaultdict
from datetime import UTC, datetime
import gzip
import json
from pathlib import Path
import re
import shutil

import httpx

from .audit import Ledger, digest, write_json
from .context import utc, name_key
from .fullgame_rebounds import distribution
from .model import contract_probabilities, scores
from .odds_capture import prop_pairs
from .prop_feed import attach_official_identities, capture_props
from .startup import preceding_season
from .prospective_context import injury_observations

PROTOCOL = Path(__file__).with_name('paper_protocol.json')
COUNTS = {'player_points': 'points', 'player_rebounds': 'rebounds', 'player_assists': 'assists'}


def now_utc():
    return datetime.now(UTC)


def load_history(labels_path, boxes_path):
    """Join verified fullgame exposures to corrected PTS/REB/AST labels."""
    labels = {}
    with gzip.open(labels_path, 'rt', encoding='utf8') as stream:
        for row in map(json.loads, stream):
            key = row['game_id'],row['player_id']
            if key in labels:
                raise ValueError('duplicate history label')
            labels[key] = row
    rows, seen = [], set()
    with gzip.open(boxes_path, 'rt', encoding='utf8') as stream:
        for box in map(json.loads, stream):
            key = box['game_id'], box['player_id']
            if key not in labels:
                continue
            label = labels[key]
            # Some corrected archive rows omit the serialized namespace. The
            # previously verified fullgame label supplies it only after this
            # exact game/player/date/season/team join, never by name guessing.
            if (key in seen or label['id_namespace']!='nba' or box.get('id_namespace','nba')!='nba'
                    or any(label[k] != box[k] for k in ('date', 'season', 'team_id', 'participated'))):
                raise ValueError('conflicting history identity')
            seen.add(key)
            if label['season_type'] != 'regular' or label['target_overtime'] != 'included' or label['rebounds'] != box['rebounds']:
                raise ValueError('wrong history scope')
            if abs(label['fullgame_minutes'] - (box['minutes'] or 0)) > 1e-8:
                raise ValueError('conflicting history exposure')
            for stat in COUNTS.values():
                if type(box[stat]) is not int or box[stat] < 0:
                    raise ValueError('invalid history count')
            rows.append(dict(label, points=box['points'], assists=box['assists']))
    if seen != set(labels):
        raise ValueError('missing verified history boxes')
    return rows


def predict(history, player_id, market, seal, protocol):
    season = protocol['season']
    prior = preceding_season(season)
    cutoff = seal.date().isoformat()
    past = sorted((r for r in history if r['player_id'] == player_id and r['date'] < cutoff
        and r['season'] in (prior, season) and r['season_type'] == 'regular'
        and r['participated'] and r['fullgame_minutes'] > 0), key=lambda r:(r['date'], r['game_id']))[-protocol['history_window']:]
    if len(past) < protocol['minimum_appearances']:
        raise ValueError('insufficient_prior_history')
    stat = COUNTS[market]
    feature = dict(date=cutoff, history_max_date=max(r['date'] for r in past),
        history_game_ids=[r['game_id'] for r in past], history_count=len(past),
        history_seasons=sorted({r['season'] for r in past}), history_OT_games=sum(r['overtime_periods'] > 0 for r in past),
        minute_samples=[r['fullgame_minutes'] for r in past],
        rate_alpha=protocol['prior_minutes']*protocol['prior_rates'][market]+sum(r[stat] for r in past),
        rate_beta=protocol['prior_minutes']+sum(r['fullgame_minutes'] for r in past),
        baseline_count_mean=sum(r[stat] for r in past[-protocol['baseline_window']:])/len(past[-protocol['baseline_window']:]),
        distribution_overtime='included', historical_receipt_known=False)
    candidate = distribution(feature, protocol)
    baseline = distribution(feature, protocol, 'fullgame_recent_poisson')
    return dict(feature=feature, candidate=candidate, baseline=baseline,
        projected_minutes=sum(feature['minute_samples'])/len(past),
        candidate_mean=sum(i*p for i,p in enumerate(candidate['pmf'])),
        baseline_mean=feature['baseline_count_mean'], status='exploratory_conditional_forecast')


def verify_quotes(feed):
    """Replay prices from raw bytes, rejecting mutated exports or future receipts."""
    feed = Path(feed)
    receipts = json.loads((feed/'raw/manifest.json').read_bytes())['files']
    accepted = {}
    for receipt in receipts:
        if not receipt['name'].startswith('props_') or receipt['http_status'] != 200:
            continue
        path = feed/'raw'/receipt['name']
        if digest(path) != receipt['sha256']:
            raise ValueError('price raw hash mismatch')
        body = json.loads(path.read_bytes())
        rows, _ = prop_pairs(body, receipt, dict(odds_api_event_id=body['id'], home_team=body['home_team'],
            away_team=body['away_team'], scheduled_utc=body['commence_time']), receipt['first_received_at_utc'], historical=False)
        for row in rows:
            key = (row['event_id'],row['book'],row['market'],row['provider_player_name'],row['line'],row['raw_sha256'])
            accepted[key] = (row, body)
    pairs = json.loads((feed/'pairs.json').read_bytes())
    seen = set()
    for pair in pairs:
        key = (pair['event_id'],pair['book'],pair['market'],pair['provider_player_name'],pair['line'],pair['raw_sha256'])
        if key in seen or key not in accepted:
            raise ValueError('duplicate or unproven exported quote')
        seen.add(key)
        row, body = accepted[key]
        for name in ('over_decimal','under_decimal','first_received_at_utc','source_updated_at_utc'):
            if pair[name] != row[name]:
                raise ValueError('mutated exported price or clock')
        if any(pair[name] != body[field] for name,field in [('tipoff_utc','commence_time'),('sport_key','sport_key'),('home_team','home_team'),('away_team','away_team')]):
            raise ValueError('mutated exported event')
    return pairs


def register(feed, identity_path, labels_path, boxes_path, output, protocol_path=PROTOCOL, injury_receipt=None):
    root = Path(output)
    if root.exists():
        raise ValueError('new registration directory required')
    protocol = json.loads(Path(protocol_path).read_bytes())
    if protocol != json.loads(PROTOCOL.read_bytes()):
        raise ValueError('unsupported shadow protocol version')
    history = load_history(labels_path, boxes_path)
    pairs = verify_quotes(feed)
    started = now_utc()
    injury_rows = []
    injury_paths = []
    if injury_receipt:
        receipt = json.loads(Path(injury_receipt).read_bytes())
        injury_raw = Path(receipt['raw_file'])
        if (receipt['url']!='https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries'
                or receipt['http_status']!=200 or digest(injury_raw)!=receipt['raw_sha256']
                or utc(receipt['first_received_at_utc'])>started):
            raise ValueError('unproven injury context receipt')
        injury_rows = injury_observations(json.loads(injury_raw.read_bytes()),receipt['first_received_at_utc'])
        injury_paths = [Path(injury_receipt),injury_raw]
    identities = json.loads(Path(identity_path).read_bytes())
    pairs = attach_official_identities(pairs, identities, started.isoformat())
    root.mkdir(parents=True)
    shutil.copyfile(protocol_path, root/'protocol.json')
    input_paths = [Path(feed)/'pairs.json',Path(feed)/'raw/manifest.json',Path(identity_path),Path(labels_path),Path(boxes_path),*injury_paths]
    input_hashes = {p.as_posix():digest(p) for p in input_paths}
    snapshot = root/'model';snapshot.mkdir()
    for source in (Path(__file__), Path(__file__).with_name('fullgame_rebounds.py'),Path(__file__).with_name('model.py')):
        shutil.copyfile(source,snapshot/source.name)
    ledger = Ledger(root/'journal.sqlite')
    ledger.append('protocol_before_predictions',dict(protocol_sha256=digest(root/'protocol.json'),input_hashes=input_hashes,
        started_at_utc=started.isoformat(),model_hashes={p.name:digest(p) for p in snapshot.iterdir()},external_anchor=False))
    groups, exclusions = defaultdict(list), []
    for pair in pairs:
        if pair['sport_key'] != 'basketball_nba' or not pair['identity_verified']:
            exclusions.append(dict(event_id=pair['event_id'],name=pair['provider_player_name'],reason='regular_scope_or_identity'));continue
        if utc(pair['first_received_at_utc']) > started or utc(pair['tipoff_utc']) <= started:
            exclusions.append(dict(event_id=pair['event_id'],name=pair['provider_player_name'],reason='not_received_pregame'));continue
        groups[pair['event_id'],pair['nba_player_id'],pair['market']].append(pair)
    forecasts = []
    for (event,player,market), quotes in sorted(groups.items()):
        try:
            prediction = predict(history, player, market, started, protocol)
        except ValueError as error:
            exclusions.append(dict(event_id=event,player_id=player,market=market,reason=str(error)));continue
        sealed = now_utc()
        if any(sealed >= utc(q['tipoff_utc']) for q in quotes):
            exclusions.append(dict(event_id=event,player_id=player,market=market,reason='started_before_seal'));continue
        quotes = sorted(quotes,key=lambda q:(protocol['book_priority'].index(q['book']),q['line']))
        reference = quotes[0]
        probs = contract_probabilities(prediction['candidate']['pmf'],reference['line'])
        baseline_probs = contract_probabilities(prediction['baseline']['pmf'],reference['line'])
        evs = {side:probs[side]*(reference[side+'_decimal']-1)-probs['under' if side=='over' else 'over'] for side in ('over','under')}
        side = max(evs,key=evs.get)
        age = max((sealed-utc(reference[k])).total_seconds() for k in ('first_received_at_utc','source_updated_at_utc'))
        injury_candidates = [dict(row,identity_match='exact_name_candidate_only; NBA crosswalk unverified')
            for row in injury_rows if name_key(row['name'])==name_key(reference['provider_player_name'])]
        eligible = 0 <= age <= protocol['freshness_seconds'] and evs[side] >= protocol['minimum_hypothetical_ev'] and not injury_candidates
        forecast = dict(event_id=event,player_id=player,market=market,name=reference['provider_player_name'],
            tipoff_utc=reference['tipoff_utc'],home_team=reference['home_team'],away_team=reference['away_team'],
            sealed_at_utc=sealed.isoformat(),quote_count=len(quotes),quotes=quotes,reference_quote=reference,
            probabilities=probs,baseline_probabilities=baseline_probs,reference_age_at_seal_seconds=age,
            hypothetical_entry=dict(selected=eligible,side=side,decimal=reference[side+'_decimal'],ev=evs[side],
                units=1 if eligible else 0,reason='conditional_paper_only' if eligible else 'stale_quote' if age>protocol['freshness_seconds'] else 'listed_in_injury_context' if injury_candidates else 'below_fixed_EV',
                settlement_contract='hypothetical_fullgame_participation_DNPvoid',real_account_rules_verified=False),
            final_availability_known=False,injury_adjustment_applied=False,context_reason='final event availability unknown; old history may not reflect current injury or rotation',
            injury_context_candidates=injury_candidates,injury_context_received=bool(injury_receipt),
            operational_actionable=False,clv=None,**prediction)
        ledger.append('pregame_forecast',forecast)
        forecasts.append(forecast)
    ledger.append('exclusions',dict(rows=exclusions))
    write_json(root/'forecasts.json',forecasts)
    write_json(root/'exclusions.json',exclusions)
    result = dict(mode='exploratory_conditional_shadow_pilot',registered_at_utc=started.isoformat(),
        forecasts=len(forecasts),events=len({f['event_id'] for f in forecasts}),players=len({f['player_id'] for f in forecasts}),
        forecasts_by_market=dict(Counter(f['market'] for f in forecasts)),quotes=sum(f['quote_count'] for f in forecasts),
        hypothetical_entries=sum(f['hypothetical_entry']['selected'] for f in forecasts),exclusions=len(exclusions),
        result_status='pending_official_final_results',operational_bets=0,production_ready=False,confirmatory_F7_started=False,
        ledger=ledger.verify(),input_hashes=input_hashes,external_anchor=False)
    write_json(root/'result.json',result)
    write_json(root/'seal.json',dict(files={p.relative_to(root).as_posix():digest(p) for p in root.rglob('*') if p.is_file()},
        created_at_utc=now_utc().isoformat(),external_anchor=False))
    return result


def verify_registration(root):
    root = Path(root)
    seal = json.loads((root/'seal.json').read_bytes())
    for name, hashed in seal['files'].items():
        if digest(root/name) != hashed:
            raise ValueError('sealed registration changed')
    ledger = Ledger(root/'journal.sqlite')
    if ledger.verify() != json.loads((root/'result.json').read_bytes())['ledger']:
        raise ValueError('registration journal mismatch')
    return json.loads((root/'forecasts.json').read_bytes())


def run_pilot(output, key, cap, identity_path, labels_path, boxes_path, *, maximum_events=3, injury_receipt=None, client=None):
    """Validate the history before spending; capture and seal in one operation."""
    root=Path(output)
    if root.exists():
        raise ValueError('new pilot directory required')
    load_history(labels_path,boxes_path)
    json.loads(Path(identity_path).read_bytes())
    root.mkdir(parents=True)
    shutil.copyfile(PROTOCOL,root/'paper_protocol.json')
    ledger=Ledger(root/'execution.sqlite')
    ledger.append('protocol_before_paid_queries',dict(protocol_sha256=digest(root/'paper_protocol.json'),
        credit_cap=cap,maximum_regular_events=maximum_events,input_hashes={str(p):digest(p) for p in (identity_path,labels_path,boxes_path)},
        created_at_utc=now_utc().isoformat(),production_ready=False))
    feed=capture_props(root/'feed',key,cap,maximum_events=maximum_events,regular_only=True,client=client)
    registered=register(root/'feed',identity_path,labels_path,boxes_path,root/'registration',root/'paper_protocol.json',injury_receipt)
    result=dict(feed=feed,registration=registered,automatic_collection_installed=False,real_bets=0)
    ledger.append('pregame_registration',dict(seal_sha256=digest(root/'registration/seal.json'),**result))
    write_json(root/'execution.json',result)
    return result


def capture_official_result(game_id, destination, game_slug=None):
    """One free public NBA request; never retry or alter a prior receipt."""
    if not re.fullmatch(r'00[2456]\d{7}',game_id):
        raise ValueError('regular, play-in, playoff or Cup final NBA game ID required')
    root = Path(destination);root.mkdir(parents=True,exist_ok=False)
    url = f'https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{game_id}.json'
    if game_slug:
        if not re.fullmatch(r'[a-z]{2,3}-vs-[a-z]{2,3}-'+game_id,game_slug):
            raise ValueError('official game slug must contain the same NBA ID')
        url=f'https://www.nba.com/game/{game_slug}/box-score'
    requested = now_utc().isoformat()
    status,body,error=None,b'',None
    try:
        with httpx.Client(timeout=25,follow_redirects=False,headers={
                'User-Agent':'Mozilla/5.0 NBA research receipt capture','Accept':'application/json,text/html'}) as client:
            response = client.get(url)
            status,body=response.status_code,response.content
    except httpx.HTTPError as exc:
        error=type(exc).__name__
    name='boxscore.html' if game_slug else 'boxscore.json'
    path = root/name;path.write_bytes(body)
    receipt = dict(url=url,game_id=game_id,http_status=status,error=error,raw_sha256=digest(path),
        requested_at_utc=requested,first_received_at_utc=now_utc().isoformat(),raw_file=name)
    write_json(root/'receipt.json',receipt)
    return root/'receipt.json'


def official_game(raw,receipt):
    """Two official transports, identical final-game identity and count checks."""
    gid=receipt['game_id'];url=receipt['url']
    if url==f'https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{gid}.json':
        if receipt['raw_file']!='boxscore.json':raise ValueError('unexpected result receipt path')
        return json.loads(raw)['game']
    if not re.fullmatch(r'https://www\.nba\.com/game/[a-z]{2,3}-vs-[a-z]{2,3}-'+gid+r'/box-score',url) or receipt['raw_file']!='boxscore.html':
        raise ValueError('official NBA result URL required')
    match=re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',raw.decode('utf8'),re.S)
    if not match:raise ValueError('missing official NBA web payload')
    game=json.loads(match[1])['props']['pageProps']['game']
    if game['gameId']!=gid or game['gameStatus']!=3:raise ValueError('final NBA web boxscore required')
    for side in ('homeTeam','awayTeam'):
        team=game[side]
        for player in team['players']:
            minutes=player['statistics']['minutes']
            if re.fullmatch(r'\d+:\d{2}(?:\.\d+)?',minutes or ''):
                whole,seconds=minutes.split(':');exposure=int(whole)+float(seconds)/60
                if float(seconds)>=60:raise ValueError('invalid official web minutes')
                player['played']='1' if exposure>0 else '0'
            elif not minutes and player.get('comment','').startswith(('DNP','DND')):
                player['played']='0'
            else:raise ValueError('unknown official web participation')
            if player['played']=='0' and any(player['statistics'][k]!=0 for k in ('points','reboundsTotal','assists')):
                raise ValueError('nonparticipant has nonzero counts')
        for inactive in team.get('inactives',[]):
            team['players'].append(dict(inactive,played='0',statistics={},explicit_official_inactive=True))
        for stat in ('points','reboundsTotal','assists'):
            counts=[p['statistics'][stat] for p in team['players'] if p['played']=='1']
            if any(type(v) is not int or v<0 for v in counts) or sum(counts)!=team['statistics'][stat]:
                raise ValueError('official web team/player counts do not reconcile')
    return game


def score_result(registration, event_id, receipt_path, output):
    """Descriptive scores on unique units; hypothetical profit is not book settlement."""
    forecasts = [f for f in verify_registration(registration) if f['event_id']==event_id]
    if not forecasts:
        raise ValueError('event not in registered cohort')
    receipt_path = Path(receipt_path)
    receipt = json.loads(receipt_path.read_bytes())
    gid = receipt['game_id']
    if not re.fullmatch(r'002\d{7}',gid) or receipt['http_status']!=200:
        raise ValueError('official regular NBA result receipt required')
    if receipt['raw_file'] not in ('boxscore.json','boxscore.html'):
        raise ValueError('unexpected result receipt path')
    path = receipt_path.parent/receipt['raw_file']
    if digest(path)!=receipt['raw_sha256'] or utc(receipt['first_received_at_utc'])>now_utc():
        raise ValueError('result raw hash or receipt clock mismatch')
    game = official_game(path.read_bytes(),receipt)
    if game['gameId']!=gid or game['gameStatus']!=3:
        raise ValueError('final NBA boxscore required')
    tip = utc(game['gameTimeUTC'])
    if utc(receipt['first_received_at_utc'])<=tip:
        raise ValueError('result received before game')
    def team_name(team):
        return team['teamCity']+' '+team['teamName']
    if any(utc(f['tipoff_utc'])!=tip or f['home_team']!=team_name(game['homeTeam']) or f['away_team']!=team_name(game['awayTeam'])
        or utc(f['sealed_at_utc'])>=tip for f in forecasts):
        raise ValueError('official event mapping mismatch')
    players = {}
    for team in (game['homeTeam'],game['awayTeam']):
        for player in team['players']:
            if player['personId'] in players:
                raise ValueError('duplicate official player')
            players[player['personId']] = player
    rows = []
    for f in forecasts:
        if f['player_id'] not in players:
            raise ValueError('missing official player; cannot assume DNP')
        player = players[f['player_id']]
        if player['played'] not in ('0','1'):
            raise ValueError('unknown participation')
        played = player['played']=='1'
        row = dict(event_id=event_id,nba_game_id=gid,player_id=f['player_id'],market=f['market'],played=played,
            sealed_at_utc=f['sealed_at_utc'],tipoff_utc=f['tipoff_utc'],predicted_over=f['probabilities']['over'],
            observation_unit='event/player/market',official_result_sha256=receipt['raw_sha256'],hypothetical_profit=0.,operational_settlement=False)
        if played:
            stat = {'player_rebounds':'reboundsTotal','player_points':'points','player_assists':'assists'}[f['market']]
            count = player['statistics'][stat]
            if type(count) is not int or count<0:
                raise ValueError('invalid official count')
            row.update(actual=count,candidate=scores(f['candidate']['pmf'],count),baseline=scores(f['baseline']['pmf'],count))
            line = f['reference_quote']['line']
            row['over_brier'] = (f['probabilities']['over']-int(count>line))**2
            row['baseline_over_brier'] = (f['baseline_probabilities']['over']-int(count>line))**2
            entry = f['hypothetical_entry']
            if entry['selected']:
                won = count>line if entry['side']=='over' else count<line
                row['hypothetical_profit'] = 0. if count==line else entry['decimal']-1 if won else -1.
            row['status'] = 'conditional_count_scored'
        else:
            row['status'] = 'DNP_excluded_from_conditional_count_scores_paper_void'
        rows.append(row)
    by_market = {}
    for market in COUNTS:
        selected = [r for r in rows if r['market']==market and r['played']]
        if selected:
            by_market[market] = dict(n=len(selected),**{family:{metric:sum(r[family][metric] for r in selected)/len(selected)
                for metric in ('crps','nll','mae','covered80')} for family in ('candidate','baseline')},
                over_brier=sum(r['over_brier'] for r in selected)/len(selected),
                baseline_over_brier=sum(r['baseline_over_brier'] for r in selected)/len(selected))
    result = dict(status='descriptive_official_result_evaluation',event_id=event_id,nba_game_id=gid,
        conditional_observations=sum(r['played'] for r in rows),DNP_observations=sum(not r['played'] for r in rows),
        by_market=by_market,hypothetical_units=sum(f['hypothetical_entry']['units'] for f in forecasts),
        hypothetical_profit=sum(r['hypothetical_profit'] for r in rows),clv=None,
        uncertainty='single-event dependent sample; no significance or promotion claim',production_ready=False,
        raw_sha256=receipt['raw_sha256'],receipt_sha256=digest(receipt_path),registration_seal_sha256=digest(Path(registration)/'seal.json'))
    root = Path(output);root.mkdir(parents=True,exist_ok=False)
    write_json(root/'outcomes.json',rows);write_json(root/'result.json',result)
    write_json(root/'seal.json',dict(files={p.name:digest(p) for p in (root/'outcomes.json',root/'result.json')},external_anchor=False))
    return result


def summarize_scores(evaluations,output):
    """Combine completed events, rejecting duplicate units and modified evaluations."""
    rows=[]
    for folder in evaluations:
        root=Path(folder);seal=json.loads((root/'seal.json').read_bytes())
        for name in ('outcomes.json','result.json'):
            if digest(root/name)!=seal['files'][name]:raise ValueError('evaluation seal changed')
        rows.extend(json.loads((root/'outcomes.json').read_bytes()))
    seen=set()
    for row in rows:
        key=(row['event_id'],row['player_id'],row['market'])
        if key in seen:raise ValueError('duplicate observation unit; select one preregistered version per event/player/market')
        seen.add(key)
    metrics={}
    for market in COUNTS:
        completed=[r for r in rows if r['market']==market and r['played']]
        if completed:
            metrics[market]=dict(n=len(completed),**{family:{metric:sum(r[family][metric] for r in completed)/len(completed)
                for metric in ('crps','nll','mae','covered80')} for family in ('candidate','baseline')},
                over_brier=sum(r['over_brier'] for r in completed)/len(completed),
                baseline_over_brier=sum(r['baseline_over_brier'] for r in completed)/len(completed))
    result=dict(status='descriptive_shadow_summary',units=len(rows),conditional_units=sum(r['played'] for r in rows),
        DNP_units=sum(not r['played'] for r in rows),games=len({r['event_id'] for r in rows}),
        players=len({r['player_id'] for r in rows}),by_market=metrics,
        hypothetical_profit=sum(r['hypothetical_profit'] for r in rows),clv=None,confidence_intervals=None,
        uncertainty='Dependent observations; no confirmatory power/cluster protocol approved, no promotion or significant-effect claim',
        production_ready=False,confirmatory_F7_started=False,
        input_hashes={str(Path(p)/'seal.json'):digest(Path(p)/'seal.json') for p in evaluations})
    root=Path(output);root.mkdir(parents=True,exist_ok=False);write_json(root/'summary.json',result)
    return result
