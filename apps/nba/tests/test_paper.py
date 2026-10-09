from copy import deepcopy
from datetime import UTC, datetime, timedelta
import gzip
import json
import sqlite3

import httpx
import pytest

from nba import paper, odds_capture
from nba.audit import digest, write_json
from nba.prop_feed import capture_props

NOW = datetime.now(UTC)
TIP = NOW+timedelta(hours=2)
EVENT = 'a'*32
PROTOCOL = json.loads(paper.PROTOCOL.read_bytes())


def histories():
    return [dict(game_id=f'00225000{i:02d}',player_id=1,team_id=10,id_namespace='nba',season='2025-26',
        season_type='regular',date=f'2026-04-{i+1:02d}',participated=True,fullgame_minutes=52. if i==0 else 30.,
        overtime_periods=1 if i==0 else 0,target_overtime='included',rebounds=6,points=20,assists=5) for i in range(20)]


@pytest.fixture
def cohort(tmp_path,monkeypatch):
    monkeypatch.setattr(paper,'now_utc',lambda:NOW)
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW
    monkeypatch.setattr(odds_capture,'datetime',FrozenDatetime)
    event = dict(id=EVENT,sport_key='basketball_nba',home_team='Test Home',away_team='Test Away',commence_time=TIP.isoformat())
    def respond(request):
        path = request.url.path
        cost = 0
        if path.endswith('/sports'): body = []
        elif path.endswith('/events'): body = [event]
        elif path.endswith('/markets'):
            cost=1;body=dict(event,bookmakers=[])
        else:
            cost=3;body=dict(event,bookmakers=[dict(key=book,markets=[dict(key=market,
                last_update=(NOW-timedelta(seconds=5)).isoformat(),outcomes=[dict(name=side,description='Test Player',point=3.5,price=1.9)
                for side in ('Over','Under')]) for market in paper.COUNTS]) for book in ('sportsbet','fanduel')])
        return httpx.Response(200,json=body,headers={'x-requests-last':str(cost),'x-requests-used':'100','x-requests-remaining':'10000'})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        capture_props(tmp_path/'feed','test',4,maximum_events=1,regular_only=True,client=client,clock=lambda:NOW)
    proof = dict(name='Test Player',nba_player_id=1,official_profile_identity_verified=True,
        first_received_at_utc=(NOW-timedelta(hours=1)).isoformat(),source_sha256='a'*64)
    write_json(tmp_path/'identity.json',[proof])
    labels=histories()
    for name,rows in [('labels',labels),('boxes',[dict(r,minutes=r['fullgame_minutes']) for r in labels])]:
        with gzip.open(tmp_path/(name+'.gz'),'wt',encoding='utf8') as stream:
            for row in rows: stream.write(json.dumps(row)+'\n')
    return tmp_path


def register(root):
    return paper.register(root/'feed',root/'identity.json',root/'labels.gz',root/'boxes.gz',root/'run')


def official(root,*,played='1',status=3):
    def team(name,players):return dict(teamCity='Test',teamName=name,players=players)
    player=dict(personId=1,played=played,statistics=dict(points=20,reboundsTotal=6,assists=5))
    game=dict(gameId='0022600001',gameTimeUTC=TIP.isoformat(),gameStatus=status,
        homeTeam=team('Home',[player]),awayTeam=team('Away',[]))
    folder=root/'official';folder.mkdir()
    write_json(folder/'boxscore.json',dict(game=game))
    write_json(folder/'receipt.json',dict(game_id=game['gameId'],http_status=200,
        url='https://cdn.nba.com/static/json/liveData/boxscore/boxscore_0022600001.json',raw_file='boxscore.json',
        raw_sha256=digest(folder/'boxscore.json'),first_received_at_utc=(TIP+timedelta(hours=3)).isoformat()))
    return folder/'receipt.json'


def test_causal_fullgame_opening_prior_and_generic_markets():
    history=histories()
    for market in paper.COUNTS:
        result=paper.predict(history,1,market,NOW,PROTOCOL)
        assert result['feature']['minute_samples'][0]==52 and result['feature']['history_count']==20
        assert result['feature']['history_seasons']==['2025-26']
        future=dict(history[-1],date=NOW.date().isoformat(),points=1000,rebounds=1000,assists=1000)
        assert paper.predict(history+[future],1,market,NOW,PROTOCOL)==result
        assert sum(result['candidate']['pmf'])==pytest.approx(1)
    with pytest.raises(ValueError,match='insufficient'):
        paper.predict(history[:9],1,'player_points',NOW,PROTOCOL)


def test_single_unit_per_player_market_immutable_and_unknown_availability(cohort):
    result=register(cohort)
    assert result['forecasts']==3 and result['quotes']==6 and result['hypothetical_entries']==3
    forecasts=paper.verify_registration(cohort/'run')
    assert all(f['reference_quote']['book']=='sportsbet' and not f['final_availability_known'] for f in forecasts)
    assert all(not f['operational_actionable'] for f in forecasts)
    with sqlite3.connect(cohort/'run/journal.sqlite') as db:
        with pytest.raises(sqlite3.IntegrityError):db.execute('DELETE FROM events')
    with pytest.raises(ValueError,match='new registration'):register(cohort)


def test_stale_preferred_quote_abstains_without_book_shopping(cohort,monkeypatch):
    monkeypatch.setattr(paper,'now_utc',lambda:NOW+timedelta(seconds=61))
    assert register(cohort)['hypothetical_entries']==0
    assert all(f['hypothetical_entry']['reason']=='stale_quote' for f in paper.verify_registration(cohort/'run'))


def test_received_injury_candidate_blocks_paper_entry_without_inventing_final_availability(cohort):
    raw=cohort/'injuries.json'
    write_json(raw,dict(injuries=[dict(id=10,injuries=[dict(athlete=dict(id='99',displayName='Test Player'),status='Out')])]))
    receipt=cohort/'injury_receipt.json'
    write_json(receipt,dict(url='https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries',http_status=200,
        raw_file=raw.as_posix(),raw_sha256=digest(raw),first_received_at_utc=NOW.isoformat()))
    result=paper.register(cohort/'feed',cohort/'identity.json',cohort/'labels.gz',cohort/'boxes.gz',cohort/'run',injury_receipt=receipt)
    assert result['forecasts']==3 and result['hypothetical_entries']==0
    assert all(f['hypothetical_entry']['reason']=='listed_in_injury_context' and not f['final_availability_known']
        for f in paper.verify_registration(cohort/'run'))


def test_started_events_never_registered(cohort,monkeypatch):
    monkeypatch.setattr(paper,'now_utc',lambda:TIP)
    result=register(cohort)
    assert result['forecasts']==0 and result['exclusions']==6


@pytest.mark.parametrize('kind',['price','clock','raw','duplicate'])
def test_reject_mutated_quotes(cohort,kind):
    path=cohort/'feed/pairs.json';pairs=json.loads(path.read_bytes())
    if kind=='price':pairs[0]['over_decimal']=9.
    elif kind=='clock':pairs[0]['source_updated_at_utc']=TIP.isoformat()
    elif kind=='duplicate':pairs.append(deepcopy(pairs[0]))
    else:
        manifest=json.loads((cohort/'feed/raw/manifest.json').read_bytes())
        name=next(r['name'] for r in manifest['files'] if r['name'].startswith('props_'))
        (cohort/'feed/raw'/name).write_text('{}')
    write_json(path,pairs)
    with pytest.raises(ValueError):register(cohort)


def test_sealed_prediction_cannot_be_replaced(cohort):
    register(cohort)
    path=cohort/'run/forecasts.json';rows=json.loads(path.read_bytes());rows[0]['candidate_mean']=99.
    write_json(path,rows)
    with pytest.raises(ValueError,match='sealed'):paper.verify_registration(cohort/'run')


def test_corrected_archive_missing_namespace_requires_verified_label_join(cohort):
    path=cohort/'boxes.gz'
    with gzip.open(path,'rt',encoding='utf8') as stream:rows=list(map(json.loads,stream))
    for row in rows:row.pop('id_namespace')
    with gzip.open(path,'wt',encoding='utf8') as stream:
        for row in rows:stream.write(json.dumps(row)+'\n')
    assert len(paper.load_history(cohort/'labels.gz',path))==20
    rows[0]['team_id']=999
    with gzip.open(path,'wt',encoding='utf8') as stream:
        for row in rows:stream.write(json.dumps(row)+'\n')
    with pytest.raises(ValueError,match='identity'):paper.load_history(cohort/'labels.gz',path)


def test_one_operation_pilot_preflights_before_any_paid_request(cohort):
    manifest=json.loads((cohort/'feed/raw/manifest.json').read_bytes())
    calls=[]
    def respond(request):
        calls.append(request.url.path)
        if request.url.path.endswith('/sports'):name='account.json';cost=0
        elif request.url.path.endswith('/events'):name='basketball_nba_events.json';cost=0
        elif request.url.path.endswith('/markets'):name='markets_'+EVENT+'.json';cost=1
        else:name='props_'+EVENT+'.json';cost=3
        return httpx.Response(200,content=(cohort/'feed/raw'/name).read_bytes(),headers={
            'x-requests-last':str(cost),'x-requests-used':'100','x-requests-remaining':'10000'})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result=paper.run_pilot(cohort/'pilot','test',4,cohort/'identity.json',cohort/'labels.gz',cohort/'boxes.gz',maximum_events=1,client=client)
        assert result['feed']['credits_consumed']==4 and result['registration']['forecasts']==3 and len(calls)==4
        with gzip.open(cohort/'boxes.gz','wt',encoding='utf8') as stream:stream.write('')
        with pytest.raises(ValueError,match='missing verified'):
            paper.run_pilot(cohort/'invalid','test',4,cohort/'identity.json',cohort/'labels.gz',cohort/'boxes.gz',client=client)
        assert len(calls)==4 and not (cohort/'invalid').exists()


@pytest.mark.parametrize('played',['0','1'])
def test_official_result_scores_once_per_unit_with_DNP_separate(cohort,monkeypatch,played):
    register(cohort);receipt=official(cohort,played=played)
    monkeypatch.setattr(paper,'now_utc',lambda:TIP+timedelta(hours=4))
    result=paper.score_result(cohort/'run',EVENT,receipt,cohort/'scores')
    assert result['conditional_observations']==(3 if played=='1' else 0)
    assert result['DNP_observations']==(3 if played=='0' else 0)
    if played=='0':assert result['hypothetical_profit']==0 and result['by_market']=={}
    else:
        assert all(r['n']==1 for r in result['by_market'].values())
        assert result['hypothetical_profit']==pytest.approx(2.7)
    assert result['clv'] is None and not result['production_ready']


@pytest.mark.parametrize('mutation',['nonfinal','wrong_event','missing_player','future_receipt','changed_raw'])
def test_official_result_identity_finality_and_receipt_guards(cohort,monkeypatch,mutation):
    register(cohort);receipt_path=official(cohort)
    monkeypatch.setattr(paper,'now_utc',lambda:TIP+timedelta(hours=4))
    raw=receipt_path.parent/'boxscore.json';body=json.loads(raw.read_bytes());receipt=json.loads(receipt_path.read_bytes())
    if mutation=='nonfinal':body['game']['gameStatus']=2
    elif mutation=='wrong_event':body['game']['gameTimeUTC']=(TIP+timedelta(minutes=1)).isoformat()
    elif mutation=='missing_player':body['game']['homeTeam']['players']=[]
    elif mutation=='future_receipt':receipt['first_received_at_utc']=(TIP+timedelta(hours=5)).isoformat()
    else:body['game']['homeTeam']['players'][0]['statistics']['points']=99
    write_json(raw,body)
    if mutation!='changed_raw':receipt['raw_sha256']=digest(raw)
    write_json(receipt_path,receipt)
    with pytest.raises(ValueError):paper.score_result(cohort/'run',EVENT,receipt_path,cohort/'scores')


@pytest.mark.parametrize('mutation',['normal','nonfinal','wrong_counts','unknown_minutes','wrong_url'])
def test_official_web_fallback_keeps_participation_and_finality_checks(mutation):
    player=dict(personId=1,statistics=dict(minutes='30:00',points=20,reboundsTotal=6,assists=5),comment='')
    home=dict(players=[player],inactives=[dict(personId=2)],statistics=dict(points=20,reboundsTotal=6,assists=5))
    away=dict(players=[],inactives=[],statistics=dict(points=0,reboundsTotal=0,assists=0))
    game=dict(gameId='0022600001',gameStatus=3,homeTeam=home,awayTeam=away)
    receipt=dict(game_id=game['gameId'],url='https://www.nba.com/game/bos-vs-det-0022600001/box-score',raw_file='boxscore.html')
    if mutation=='nonfinal':game['gameStatus']=2
    elif mutation=='wrong_counts':home['statistics']['points']=21
    elif mutation=='unknown_minutes':player['statistics']['minutes']=''
    elif mutation=='wrong_url':receipt['url']='https://example.com/result'
    raw=('<script id="__NEXT_DATA__">'+json.dumps(dict(props=dict(pageProps=dict(game=game))))+'</script>').encode()
    if mutation=='normal':
        parsed=paper.official_game(raw,receipt)
        assert parsed['homeTeam']['players'][0]['played']=='1'
        assert parsed['homeTeam']['players'][1]['played']=='0'
    else:
        with pytest.raises(ValueError):paper.official_game(raw,receipt)


def test_descriptive_summary_rejects_duplicate_units_and_modified_results(cohort,monkeypatch):
    register(cohort);receipt=official(cohort)
    monkeypatch.setattr(paper,'now_utc',lambda:TIP+timedelta(hours=4))
    paper.score_result(cohort/'run',EVENT,receipt,cohort/'scores')
    summary=paper.summarize_scores([cohort/'scores'],cohort/'summary')
    assert summary['units']==3 and summary['games']==1 and not summary['confirmatory_F7_started']
    with pytest.raises(ValueError,match='duplicate observation'):
        paper.summarize_scores([cohort/'scores',cohort/'scores'],cohort/'duplicate')
    (cohort/'scores/outcomes.json').write_text('[]')
    with pytest.raises(ValueError,match='evaluation seal'):
        paper.summarize_scores([cohort/'scores'],cohort/'changed')
