"""Statistics-only exploratory NBA models. Original paper registrations are separate."""
from collections import Counter, defaultdict, deque
from datetime import UTC, date, datetime
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logit
from scipy.stats import nbinom, norm, poisson

from .audit import digest, write_json

STATS = ('points', 'rebounds', 'assists', 'threes', 'steals', 'blocks')
LABELS = dict(player_points='Puntos de jugador', player_rebounds='Rebotes',
              player_assists='Asistencias', player_threes='Triples',
              player_steals='Robos', player_blocks='Tapones', winner='Ganador',
              team_points='Puntos de equipo', game_total='Total del partido')


def read_rows(path):
    with gzip.open(path, 'rt', encoding='utf8') as stream:
        return [json.loads(line) for line in stream]


def archive_file(manifest, name, sources):
    entries = json.loads(Path(manifest).read_bytes())['files']
    entry, = [e for e in entries if Path(e['name']).name == name]
    path = Path(manifest).parent / name
    if digest(path) != entry['sha256'] or path.stat().st_size != entry['bytes']:
        raise ValueError('archive integrity mismatch')
    sources.append(dict(path=path.as_posix(), sha256=entry['sha256']))
    return path


def recover(dataset, raw_root, output):
    """Extend accepted IDs by exact counts; disagreement quarantines the whole game."""
    import pyarrow.parquet as pq
    accepted = read_rows(dataset)
    sources = [dict(path=str(dataset), sha256=digest(dataset))]
    original = Path(raw_root) / 'github/9252ea665d8ea68ad20aa3209a6546381066fd98/manifest.json'
    release = Path(raw_root) / 'github/sportsdataverse__sportsdataverse-data/release_97519777/manifest.json'
    candidates, teams = defaultdict(list), {}
    for year in range(2022, 2027):
        for manifest, name, snake in [(original, f'playerlog_{year}.parquet', False),
                                      (release, f'player_boxscores_{year}.parquet', True)]:
            for r in pq.read_table(archive_file(manifest, name, sources)).to_pylist():
                columns = ('game_id', 'person_id', 'team_id', 'points', 'rebounds_total', 'assists',
                           'three_pointers_made', 'steals', 'blocks') if snake else (
                               'gameId', 'personId', 'teamId', 'points', 'reboundsTotal', 'assists',
                               'threePointersMade', 'steals', 'blocks')
                values = tuple(r.get(k) for k in columns)
                candidates[values[:3]].append(values[3:])
        for r in pq.read_table(archive_file(original, f'gamelog_{year}.parquet', sources)).to_pylist():
            if not str(r['game_id']).startswith('002'):
                continue
            key = r['game_id'], r['team_id']
            t = dict(game_id=r['game_id'], date=r['game_date'][:10], season=r['season_year'],
                     team_id=r['team_id'], name=r['team_name'], matchup=r['matchup'],
                     home=' vs. ' in r['matchup'], points=r['pts'], threes=r['fg3m'],
                     steals=r['stl'], blocks=r['blk'])
            if (' vs. ' not in r['matchup'] and ' @ ' not in r['matchup']) or (
                    key in teams and teams[key] != t):
                raise ValueError('team reference conflict')
            teams[key] = t
    rows, bad, issues = [], set(), Counter()
    for r in accepted:
        if r.get('id_namespace') != 'nba':
            raise ValueError('NBA ID namespace required')
        if r['season_type'] != 'regular':
            continue
        key = r['game_id'], r['player_id'], r['team_id']
        matches = {v for v in candidates[key] if v[:3] == tuple(r[s] for s in STATS[:3])
                   and all(type(x) is int and x >= 0 for x in v)}
        if len(matches) != 1:
            bad.add(r['game_id']); issues['missing_or_conflicting_extra_counts'] += 1
            continue
        counts, = matches
        row = dict(r, **dict(zip(STATS, counts)))
        if not row['participated'] and any(counts):
            bad.add(r['game_id']); issues['DNP_nonzero'] += 1
        rows.append(row)
    groups = defaultdict(list)
    for r in rows:
        groups[r['game_id']].append(r)
    games = []
    for gid, players in groups.items():
        ids = sorted({r['team_id'] for r in players})
        refs = [teams.get((gid, i)) for i in ids]
        if gid in bad or len(ids) != 2 or any(t is None for t in refs):
            bad.add(gid); issues['incomplete_game'] += 1; continue
        if sum(t['home'] for t in refs) != 1:
            bad.add(gid); issues['home_away'] += 1; continue
        for t in refs:
            own = [r for r in players if r['team_id'] == t['team_id']]
            if any(r['date'] != t['date'] or r['season'] != t['season'] for r in own) or any(
                    sum(r[s] for r in own) != t[s] for s in ('points', 'threes', 'steals', 'blocks')):
                bad.add(gid); issues['team_count_reconciliation'] += 1
        if gid not in bad:
            home, = [t for t in refs if t['home']]
            away, = [t for t in refs if not t['home']]
            if home['points'] == away['points']:
                bad.add(gid); issues['tied_final'] += 1; continue
            games.append(dict(game_id=gid, date=home['date'], season=home['season'], home=home, away=away))
    rows = sorted((r for r in rows if r['game_id'] not in bad), key=lambda r: (r['date'], r['game_id'], r['player_id']))
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    path = output / 'players.jsonl.gz'
    with path.open('wb') as file:
        with gzip.GzipFile(filename='', fileobj=file, mode='wb', mtime=0) as stream:
            for row in rows:
                stream.write((json.dumps(row, sort_keys=True) + '\n').encode())
    write_json(output / 'games.json', sorted(games, key=lambda g: (g['date'], g['game_id'])))
    report = dict(accepted_rows=len(accepted), extended_rows=len(rows), regular_games=len(games),
                  quarantined_games=len(bad), issues=dict(issues), sources=sources,
                  first_date=rows[0]['date'], last_date=rows[-1]['date'],
                  exact_ids_and_counts_join=True, original_pregame_receipt_known=False)
    write_json(output / 'coverage.json', report)
    return report


def eligible(history, cut, protocol):
    return [r for r in history if 0 < (date.fromisoformat(cut) - date.fromisoformat(r['date'])).days
            <= protocol['history_max_days']][-protocol['history_window']:]


def player_parameters(history, stat, protocol):
    minutes = np.asarray([r['minutes'] for r in history], dtype=float)
    counts = np.asarray([r[stat] for r in history], dtype=float)
    exposure = protocol['prior_minutes'] + minutes.sum()
    alpha = protocol['prior_minutes'] * protocol['player_prior_rates'][stat] + counts.sum()
    rate = alpha / exposure
    mean = float(rate * minutes.mean())
    # Gamma rate uncertainty and observed variation in playing time.
    variance = mean + float(alpha / exposure**2 * np.mean(minutes**2) + rate**2 * np.var(minutes))
    n = max(mean**2 / max(variance - mean, 1e-8), 1e-6)
    return dict(mean=mean, n=n, p=n/(n+mean), baseline=float(counts[-10:].mean()),
                sample=counts.tolist(), last_date=history[-1]['date'], history_n=len(history),
                projected_minutes=float(minutes.mean()))


def player_over(parameters, line, protocol):
    w = protocol['empirical_weight']
    empirical = np.mean(np.asarray(parameters['sample']) > line)
    return float((1-w)*nbinom.sf(np.floor(line), parameters['n'], parameters['p']) + w*empirical)


def player_distribution(parameters, protocol):
    w = protocol['empirical_weight']
    limit = max(int(nbinom.ppf(1-1e-12, parameters['n'], parameters['p'])),
                max(map(int, parameters['sample'])), 80)
    if limit > 4096:
        raise ValueError('count tail outside research support')
    k = np.arange(limit+1)
    pmf = (1-w)*nbinom.pmf(k, parameters['n'], parameters['p'])
    pmf += w*np.bincount(np.asarray(parameters['sample'], dtype=int), minlength=limit+1)/len(parameters['sample'])
    if 1-pmf.sum() > 1e-9:
        raise ValueError('truncated count mass')
    return (pmf/pmf.sum()).tolist()


def player_samples(rows, protocol):
    histories, days, samples = defaultdict(lambda: deque(maxlen=20)), defaultdict(list), defaultdict(list)
    for r in rows:
        days[r['date']].append(r)
    skipped = Counter()
    for cut in sorted(days):
        for r in days[cut]:
            if cut < protocol['train_end']:
                continue
            hist = eligible(histories[r['player_id']], cut, protocol)
            if not r['participated'] or r['minutes'] <= 0:
                skipped['conditional_DNP_excluded'] += 1; continue
            if len(hist) < protocol['min_history']:
                skipped['insufficient_history'] += 1; continue
            minutes = np.asarray([h['minutes'] for h in hist],dtype=float)
            counts = np.asarray([[h[s] for s in STATS] for h in hist],dtype=float)
            exposure = protocol['prior_minutes']+minutes.sum()
            alpha = protocol['prior_minutes']*np.asarray([protocol['player_prior_rates'][s] for s in STATS])+counts.sum(axis=0)
            rate = alpha/exposure;mean=rate*minutes.mean()
            variance = mean+alpha/exposure**2*np.mean(minutes**2)+rate**2*np.var(minutes)
            n = np.maximum(mean**2/np.maximum(variance-mean,1e-8),1e-6)
            baseline = counts[-10:].mean(axis=0);lines=np.floor(baseline)+.5
            weight=protocol['empirical_weight']
            probabilities=(1-weight)*nbinom.sf(np.floor(lines),n,n/(n+mean))+weight*np.mean(counts>lines,axis=0)
            baseline_probabilities=poisson.sf(np.floor(lines),np.maximum(baseline,1e-8))
            estimates=(1-weight)*mean+weight*counts.mean(axis=0)
            for idx,stat in enumerate(STATS):
                line = float(lines[idx])
                samples['player_'+stat].append(dict(date=cut, game_id=r['game_id'], unit=r['player_id'],
                    actual=r[stat], line=line, y=int(r[stat] > line),
                    probability=float(probabilities[idx]), baseline_probability=float(baseline_probabilities[idx]),
                    estimate=float(estimates[idx]), baseline_estimate=float(baseline[idx]), last_feature_date=hist[-1]['date']))
        # Every forecast on this date precedes every outcome on this date.
        for r in days[cut]:
            if r['participated'] and r['minutes'] > 0:
                histories[r['player_id']].append(r)
    return dict(samples), dict(skipped), histories


def team_features(game, histories, ratings, league, protocol):
    cut = game['date']; home, away = game['home'], game['away']
    hh = eligible(histories[home['team_id']], cut, protocol)
    ah = eligible(histories[away['team_id']], cut, protocol)
    if min(len(hh), len(ah)) < protocol['min_history']:
        return None
    # Equal-weight recent offense and opponent defense; each enters before the game.
    hm = (np.mean([r['points'] for r in hh]) + np.mean([r['allowed'] for r in ah]))/2 + league['home_advantage']/2
    am = (np.mean([r['points'] for r in ah]) + np.mean([r['allowed'] for r in hh]))/2 - league['home_advantage']/2
    probability = 1/(1+10**(-(ratings[home['team_id']]-ratings[away['team_id']]+protocol['elo_home'])/400))
    return dict(home_mean=float(hm), away_mean=float(am), probability=float(probability),
                home_baseline=float(np.mean([r['points'] for r in hh[-10:]])),
                away_baseline=float(np.mean([r['points'] for r in ah[-10:]])),
                last_feature_date=max(hh[-1]['date'], ah[-1]['date']))


def team_samples(games, protocol):
    train = [g for g in games if g['date'] < protocol['train_end']]
    if len(train) < 100:
        raise ValueError('training team sample insufficient')
    league = dict(home_advantage=float(np.mean([g['home']['points']-g['away']['points'] for g in train])),
                  home_win=float(np.mean([g['home']['points']>g['away']['points'] for g in train])))
    histories, ratings = defaultdict(lambda: deque(maxlen=20)), defaultdict(lambda: 1500.)
    days = defaultdict(list); features = []; season = None
    for g in games: days[g['date']].append(g)
    for cut in sorted(days):
        current = days[cut][0]['season']
        if season is not None and season != current:
            for key in ratings:
                ratings[key] = 1500+(ratings[key]-1500)*(1-protocol['elo_season_regression'])
        season = current
        for g in days[cut]:
            f = team_features(g, histories, ratings, league, protocol)
            if f: features.append(dict(g, **f))
        for g in days[cut]:
            h, a = g['home'], g['away']; hid, aid = h['team_id'], a['team_id']
            p = 1/(1+10**(-(ratings[hid]-ratings[aid]+protocol['elo_home'])/400))
            delta = protocol['elo_k']*(int(h['points']>a['points'])-p)
            ratings[hid] += delta; ratings[aid] -= delta
            for own, other in [(h,a),(a,h)]:
                histories[own['team_id']].append(dict(date=cut, points=own['points'], allowed=other['points']))
    residuals = np.asarray([[g['home']['points']-g['home_mean'], g['away']['points']-g['away_mean']]
                            for g in features if g['date'] < protocol['train_end']])
    covariance = np.cov(residuals, rowvar=False)
    if not np.all(np.linalg.eigvalsh(covariance) > 0):
        raise ValueError('joint score covariance invalid')
    league['covariance'] = covariance.tolist()
    samples = defaultdict(list)
    for g in features:
        if g['date'] < protocol['train_end']: continue
        h, a = g['home'], g['away']; common = dict(date=g['date'], game_id=g['game_id'], last_feature_date=g['last_feature_date'])
        samples['winner'].append(dict(common, unit=h['team_id'], actual=int(h['points']>a['points']),
            y=int(h['points']>a['points']), line=.5, probability=g['probability'], baseline_probability=league['home_win'],
            estimate=g['probability'], baseline_estimate=league['home_win']))
        for side, idx in [('home',0),('away',1),('total',2)]:
            mean = g['home_mean']+g['away_mean'] if idx==2 else g[side+'_mean']
            baseline = g['home_baseline']+g['away_baseline'] if idx==2 else g[side+'_baseline']
            actual = h['points']+a['points'] if idx==2 else g[side]['points']
            variance = float(covariance.sum()) if idx==2 else float(covariance[idx,idx])
            line = float(np.floor(baseline)+.5)
            market = 'game_total' if idx==2 else 'team_points'
            samples[market].append(dict(common, unit='total' if idx==2 else g[side]['team_id'], actual=actual,
                y=int(actual>line), line=line, probability=float(norm.sf(line,mean,np.sqrt(variance))),
                baseline_probability=float(norm.sf(line,baseline,np.sqrt(variance))), estimate=mean, baseline_estimate=baseline))
    return dict(samples), league, histories, ratings


def apply_calibration(probability, calibration):
    p = np.clip(probability, 1e-6, 1-1e-6)
    return np.clip(expit(calibration['slope']*logit(p)+calibration['bias']), 1e-9, 1-1e-9)


def fit_calibration(rows, protocol, field='probability'):
    valid = [r for r in rows if protocol['train_end'] <= r['date'] < protocol['validation_end']]
    if len(valid) < 100: raise ValueError('validation sample insufficient')
    x = logit(np.clip([r[field] for r in valid], 1e-6, 1-1e-6)); y = np.asarray([r['y'] for r in valid])
    def objective(ab):
        z = ab[0]*x+ab[1]
        return float(np.mean(np.logaddexp(0,z)-y*z)+.001*((ab[0]-1)**2+ab[1]**2))
    result = minimize(objective,[1.,0.],bounds=[(.2,3.),(-2.,2.)],method='L-BFGS-B')
    if not result.success: raise ValueError('calibration optimization failed')
    return dict(slope=float(result.x[0]), bias=float(result.x[1]), observations=len(valid),
                first_date=valid[0]['date'], last_date=valid[-1]['date'])


def summarize(rows, calibration, protocol, baseline_calibration=None):
    test = [r for r in rows if r['date'] >= protocol['validation_end']]
    if not test: raise ValueError('evaluation sample missing')
    p = apply_calibration(np.asarray([r['probability'] for r in test]),calibration)
    b = apply_calibration(np.asarray([r['baseline_probability'] for r in test]),baseline_calibration or dict(slope=1,bias=0))
    y = np.asarray([r['y'] for r in test]); hit = (p>=.5)==y
    loss = (p-y)**2; base_loss = (b-y)**2
    clusters = defaultdict(list)
    for i,r in enumerate(test): clusters[r['game_id']].append(i)
    pairs = np.asarray([(float(np.sum(loss[v]-base_loss[v])),len(v)) for v in clusters.values()])
    rng = np.random.default_rng(protocol['seed']); boot=[]
    for _ in range(protocol['confidence_bootstrap']):
        selected = pairs[rng.integers(0,len(pairs),len(pairs))]
        boot.append(float(selected[:,0].sum()/selected[:,1].sum()))
    cuts=[]
    for threshold in (.7,.8):
        mask = np.maximum(p,1-p)>=threshold; n=int(mask.sum())
        cuts.append(dict(min_probability=threshold, selected=n, coverage=n/len(test),
                         accuracy=float(hit[mask].mean()) if n else None,
                         baseline_accuracy_same_units=float(((b[mask]>=.5)==y[mask]).mean()) if n else None,
                         mean_probability=float(np.maximum(p[mask],1-p[mask]).mean()) if n else None))
    bins=[]
    for low in np.arange(0,1,.1):
        mask=(p>=low)&(p<low+.1); n=int(mask.sum())
        bins.append(dict(low=float(low), count=n, probability=float(p[mask].mean()) if n else None,
                         observed=float(y[mask].mean()) if n else None))
    return dict(observations=len(test), games=len(clusters), first_date=test[0]['date'], last_date=test[-1]['date'],
        brier=float(loss.mean()), baseline_brier=float(base_loss.mean()),
        paired_brier_difference=float((loss-base_loss).mean()), paired_brier_difference_95_ci=np.quantile(boot,[.025,.975]).tolist(),
        logloss=float(np.mean(-y*np.log(p)-(1-y)*np.log1p(-p))),
        baseline_logloss=float(np.mean(-y*np.log(b)-(1-y)*np.log1p(-b))),
        accuracy=float(hit.mean()), baseline_accuracy=float(((b>=.5)==y).mean()),
        mae=float(np.mean([abs(r['actual']-r['estimate']) for r in test])),
        baseline_mae=float(np.mean([abs(r['actual']-r['baseline_estimate']) for r in test])),
        selections=cuts, calibration_bins=bins, calibrated_on_previous_season_only=True)


def evaluate(players, games, protocol, output):
    player, skipped, _ = player_samples(players, protocol)
    team, league, _, _ = team_samples(games, protocol)
    rows = dict(player, **team); calibrations={}; metrics={}
    for market, observations in rows.items():
        calibrations[market] = fit_calibration(observations, protocol)
        base_calibration=fit_calibration(observations,protocol,'baseline_probability')
        metrics[market] = summarize(observations, calibrations[market], protocol,base_calibration)
        metrics[market]['baseline_calibration']=base_calibration
    model=dict(version='nba-multimarket-research-1',protocol=protocol,calibrations=calibrations,league=league)
    report=dict(markets=metrics, skipped=skipped, retrospective_not_confirmatory=True,
                conditional_player_participation=True, bookmaker_features=False,
                ranking='No universal ranking: different targets, reference thresholds and selection coverage.',
                original_pregame_receipt_known=False)
    write_json(Path(output)/'model.json',model); write_json(Path(output)/'comparison.json',report)
    return model,report


def prospective(players, games, model, mappings, as_of):
    protocol=model['protocol']; cut=datetime.fromisoformat(as_of).date().isoformat()
    histories=defaultdict(list)
    for r in players:
        if r['participated'] and r['minutes']>0 and r['date']<cut:
            histories[r['player_id']].append(r)
    _, _, teams, ratings=team_samples([g for g in games if g['date']<cut],protocol)
    forecasts=[]
    def append(common,market,estimate,low,high,line,p,**extra):
        forecasts.append(dict(common,market=market,market_label=LABELS[market],estimate=float(estimate),
            range_low=float(low),range_high=float(high),line=float(line),probability_over=float(p),probability_under=float(1-p),
            sealed_at_utc=as_of,actionable=False,reference='Umbral estadístico; no es una línea de una casa',
            **extra))
    for m in mappings:
        if datetime.fromisoformat(as_of)>=datetime.fromisoformat(m['tipoff_utc']):
            raise ValueError('cannot seal after tipoff')
        common=dict(event_id=m['provider_event_id'],nba_game_id=m['nba_game_id'])
        for pid in m['players']:
            hist=eligible(histories[pid],cut,protocol)
            if len(hist)<protocol['min_history']: raise ValueError('prospective player history insufficient')
            if hist[-1]['team_id'] not in (m['home_nba_team_id'],m['away_nba_team_id']):
                raise ValueError('player team requires new roster proof')
            for stat in STATS:
                market='player_'+stat;par=player_parameters(hist,stat,protocol);pmf=player_distribution(par,protocol)
                cdf=np.cumsum(pmf);line=float(np.floor(par['baseline'])+.5)
                p=apply_calibration(player_over(par,line,protocol),model['calibrations'][market])
                append(common,market,np.dot(np.arange(len(pmf)),pmf),np.searchsorted(cdf,.1),np.searchsorted(cdf,.9),line,p,
                    player_id=pid,player=hist[-1]['name'],team_id=hist[-1]['team_id'],conditional_participation=True,
                    last_feature_date=hist[-1]['date'],history_games=len(hist),projected_minutes=par['projected_minutes'],
                    pmf=pmf,availability='unknown')
        game=dict(date=cut,home=dict(team_id=m['home_nba_team_id']),away=dict(team_id=m['away_nba_team_id']))
        # New season ratings regress once, even before any season game is observed.
        if games[-1]['season'] != str(datetime.fromisoformat(m['tipoff_utc']).year)+'-'+str((datetime.fromisoformat(m['tipoff_utc']).year+1)%100):
            adjusted=defaultdict(lambda:1500.,{k:1500+(v-1500)*(1-protocol['elo_season_regression']) for k,v in ratings.items()})
        else: adjusted=ratings
        f=team_features(game,teams,adjusted,model['league'],protocol)
        if f is None: raise ValueError('prospective team history insufficient')
        p=apply_calibration(f['probability'],model['calibrations']['winner'])
        append(common,'winner',p,0,1,.5,p,player_id='winner',player='Ganador: '+m['home_team'],
               home_team_id=m['home_nba_team_id'],last_feature_date=f['last_feature_date'],conditional_participation=False)
        cov=np.asarray(model['league']['covariance'])
        for side,idx in [('home',0),('away',1),('total',2)]:
            market='game_total' if idx==2 else 'team_points'
            mean=f['home_mean']+f['away_mean'] if idx==2 else f[side+'_mean']
            baseline=f['home_baseline']+f['away_baseline'] if idx==2 else f[side+'_baseline']
            sd=float(np.sqrt(cov.sum() if idx==2 else cov[idx,idx]));line=float(np.floor(baseline)+.5)
            p=apply_calibration(norm.sf(line,mean,sd),model['calibrations'][market])
            append(common,market,mean,max(0,norm.ppf(.1,mean,sd)),norm.ppf(.9,mean,sd),line,p,
                player_id='total' if idx==2 else m[side+'_nba_team_id'],player='Total del partido' if idx==2 else m[side+'_team'],
                team_id=None if idx==2 else m[side+'_nba_team_id'],last_feature_date=f['last_feature_date'],
                conditional_participation=False)
    return forecasts


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['recover','evaluate','forecast'])
    parser.add_argument('--output',required=True)
    parser.add_argument('--protocol',required=True)
    parser.add_argument('--data',required=True)
    parser.add_argument('--raw-root',default='apps/nba/.local/raw')
    parser.add_argument('--plan')
    args=parser.parse_args();out=Path(args.output);protocol=json.loads(Path(args.protocol).read_bytes())
    if args.command=='recover': result=recover(args.data,args.raw_root,out)
    elif args.command=='evaluate':
        model,result=evaluate(read_rows(Path(args.data)/'players.jsonl.gz'),json.loads((Path(args.data)/'games.json').read_bytes()),protocol,out)
        model['inputs']=dict(source_sha256=digest(__file__),protocol_sha256=digest(args.protocol),
            players_sha256=digest(Path(args.data)/'players.jsonl.gz'),games_sha256=digest(Path(args.data)/'games.json'))
        write_json(out/'model.json',model)
    else:
        players=read_rows(Path(args.data)/'players.jsonl.gz');games=json.loads((Path(args.data)/'games.json').read_bytes())
        model=json.loads((out/'model.json').read_bytes());plan=json.loads(Path(args.plan).read_bytes())
        expected=dict(source_sha256=digest(__file__),protocol_sha256=digest(args.protocol),
            players_sha256=digest(Path(args.data)/'players.jsonl.gz'),games_sha256=digest(Path(args.data)/'games.json'))
        if model['inputs']!=expected:raise ValueError('model inputs/source changed')
        now=datetime.now(UTC).isoformat();rows=prospective(players,games,model,plan['mappings'],now)
        bundle=dict(version='nba-multimarket-research-1',created_at_utc=now,model_sha256=digest(out/'model.json'),
                    protocol_sha256=digest(args.protocol),dataset_sha256=digest(Path(args.data)/'players.jsonl.gz'),
                    original_plan_sha256=digest(args.plan),forecasts=rows,
                    comparison=json.loads((out/'comparison.json').read_bytes()),original_pilot_unchanged=True)
        if (out/'bundle.json').exists(): raise ValueError('sealed bundle already exists')
        write_json(out/'bundle.json',bundle)
        write_json(out/'bundle.seal.json',dict(sha256=digest(out/'bundle.json'),created_at_utc=now,external_anchor=False))
        result=dict(forecasts=len(rows),markets=sorted({r['market'] for r in rows}),sealed_before_tipoff=True)
    print(json.dumps(result,allow_nan=False))


if __name__=='__main__': main()
