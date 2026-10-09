"""Exploratory full-game counts: past overtime retained, target overtime unused."""
from collections import Counter,defaultdict
from datetime import date
from itertools import groupby
import math
import numpy as np
from scipy.stats import nbinom,poisson


def fullgame_labels(minute_labels,boxes):
    official={(r['game_id'],r['player_id']):r for r in boxes if r['season_type']=='regular'}
    if len(official)!=sum(r['season_type']=='regular' for r in boxes):raise ValueError('duplicate official label')
    rows=[];seen=set()
    for label in minute_labels:
        key=(label['game_id'],label['player_id'])
        if key in seen or key not in official:raise ValueError('missing or duplicate fullgame identity')
        seen.add(key);box=official[key]
        for name in ['date','season','team_id','id_namespace']:
            if label[name]!=box[name]:raise ValueError('fullgame identity mismatch')
        ot=label['overtime_periods'];minutes=box['minutes'];count=box['rebounds']
        if type(ot) is not int or ot<0:raise ValueError('invalid overtime periods')
        if type(count) is not int or count<0:raise ValueError('invalid fullgame count')
        if minutes is None:
            if box['participated']:raise ValueError('missing participant exposure')
            minutes=0.
        if isinstance(minutes,bool) or not math.isfinite(minutes) or not 0<=minutes<=48+5*ot+1/60:
            raise ValueError('invalid fullgame minutes')
        if abs(minutes-(label['box_minutes'] or 0))>1e-8:raise ValueError('exposure source mismatch')
        rows.append(dict(**{k:box[k] for k in ['game_id','player_id','team_id','id_namespace','date','season','season_type']},
            fullgame_minutes=float(minutes),rebounds=count,overtime_periods=ot,participated=box['participated'],
            target_overtime='included',label_only=True,original_historical_receipt_known=False))
    if seen!=set(official):raise ValueError('fullgame roster coverage differs')
    return rows


def features(rows,protocol):
    seen=set();game_metadata={}
    for row in rows:
        date.fromisoformat(row['date']);key=(row['game_id'],row['player_id'])
        if key in seen or row['id_namespace']!='nba' or row['season_type']!='regular':raise ValueError('invalid fullgame identity')
        seen.add(key);metadata=(row['date'],row['season'],row['overtime_periods'])
        if row['game_id'] in game_metadata and game_metadata[row['game_id']]!=metadata:raise ValueError('conflicting game clock')
        game_metadata[row['game_id']]=metadata
        if type(row['overtime_periods']) is not int or row['overtime_periods']<0:raise ValueError('invalid fullgame clock')
        if (type(row['rebounds']) is not int or row['rebounds']<0 or type(row['participated']) is not bool
                or isinstance(row['fullgame_minutes'],bool) or not math.isfinite(row['fullgame_minutes'])
                or not 0<=row['fullgame_minutes']<=48+5*row['overtime_periods']+1/60):raise ValueError('invalid fullgame outcome')
    history=defaultdict(list);forecasts=[];outcomes=[];skips=Counter()
    for day,group in groupby(sorted(rows,key=lambda r:(r['date'],r['game_id'],r['player_id'])),key=lambda r:r['date']):
        today=list(group)
        for row in today:
            # This is an explicit retrospective participation cohort, never a pregame eligibility rule.
            if not row['participated'] or row['fullgame_minutes']<=0:
                skips['observed_nonpositive_participation']+=1;continue
            past=[r for r in history[row['player_id'],row['season']] if r['date']<day and r['participated'] and r['fullgame_minutes']>0][-protocol['history_window']:]
            if len(past)<protocol['minimum_appearances']:skips['insufficient_prior_fullgame_history']+=1;continue
            alpha=protocol['prior_minutes']*protocol['prior_rate']+sum(r['rebounds'] for r in past)
            beta=protocol['prior_minutes']+sum(r['fullgame_minutes'] for r in past)
            identity={k:row[k] for k in ['game_id','player_id','date','season']}
            forecasts.append(dict(**identity,rate_alpha=alpha,rate_beta=beta,
                minute_samples=[r['fullgame_minutes'] for r in past],baseline_count_mean=float(np.mean([r['rebounds'] for r in past[-protocol['baseline_window']:]])),
                history_game_ids=[r['game_id'] for r in past],history_max_date=max(r['date'] for r in past),
                history_count=len(past),history_OT_games=sum(r['overtime_periods']>0 for r in past),
                distribution_overtime='included',conditional_on_participation=True,retrospective_cohort=True,
                availability_known=False,void_probability=None,actionable=False))
            outcomes.append(dict(**identity,team_id=row['team_id'],actual_rebounds=row['rebounds'],
                actual_fullgame_minutes=row['fullgame_minutes'],actual_overtime_periods=row['overtime_periods']))
        # Every target-date forecast completes before any same-date outcomes enter history.
        for row in today:history[row['player_id'],row['season']].append(row)
    return forecasts,outcomes,dict(skips)


def distribution(feature,protocol,family='fullgame_gamma_poisson'):
    if feature['history_max_date']>=feature['date'] or feature.get('distribution_overtime')!='included':raise ValueError('future history or wrong target')
    minutes=np.asarray(feature['minute_samples'],dtype=float)
    if minutes.ndim!=1 or not minutes.size or not np.isfinite(minutes).all() or (minutes<=0).any():raise ValueError('invalid historical fullgame exposure')
    alpha,beta=feature['rate_alpha'],feature['rate_beta']
    if not all(math.isfinite(v) and v>0 for v in [alpha,beta]):raise ValueError('invalid rate posterior')
    if family=='fullgame_gamma_poisson':
        success=beta/(beta+minutes);quantiles=nbinom.ppf(1-protocol['tail_probability'],alpha,success)
    elif family=='fullgame_recent_poisson':
        mean=feature['baseline_count_mean']
        if not math.isfinite(mean) or mean<0:raise ValueError('invalid baseline mean')
        quantiles=np.atleast_1d(poisson.ppf(1-protocol['tail_probability'],mean))
    else:raise ValueError('unsupported fullgame family')
    if not np.isfinite(quantiles).all():raise ValueError('unbounded numerical count support')
    maximum=int(max(protocol['minimum_support'],quantiles.max()))
    if maximum>protocol['maximum_support']:raise ValueError('fullgame count support budget exceeded')
    grid=np.arange(maximum+1)
    if family=='fullgame_gamma_poisson':
        probabilities=nbinom.pmf(grid[:,None],alpha,success[None,:]).mean(axis=1)
        tail=float(nbinom.sf(maximum,alpha,success).mean())
    else:probabilities=poisson.pmf(grid,mean);tail=float(poisson.sf(maximum,mean))
    if not np.isfinite(probabilities).all() or tail>protocol['tail_tolerance'] or abs(probabilities.sum()-1)>protocol['tail_tolerance']:
        raise ValueError('invalid fullgame count probabilities')
    probabilities/=probabilities.sum()
    return dict(pmf=probabilities.tolist(),family=family,omitted_tail_mass=tail,distribution_overtime='included',
        conditional_on_participation=True,void_probability=None,actionable=False,
        minute_model='Empirical past positive fullgame exposures; OT implicit, no explicit OT duration/rotation forecast')
