from copy import deepcopy
from datetime import timedelta
import json

import numpy as np
import pytest

from nba import multimarket as m
from nba import multimarket_dashboard as web
from nba.audit import digest, write_json


@pytest.fixture
def protocol():
    return dict(train_end='2022-07-01',validation_end='2023-07-01',history_max_days=370,
        history_window=20,min_history=10,prior_minutes=90,empirical_weight=.25,
        player_prior_rates={s:.2 for s in m.STATS},elo_home=65,elo_k=20,
        elo_season_regression=.25,confidence_bootstrap=40,seed=1)


def row(day, value=3):
    return dict(date=day,player_id=1,team_id=10,minutes=30,participated=True,game_id=day,
                **{s:value for s in m.STATS})


def test_same_day_targets_and_future_never_enter_player_features(protocol):
    history=[row(f'2022-07-{i:02d}',2) for i in range(1,12)]
    target=row('2022-07-12',1000);duplicate=dict(target,game_id='same-day-other',points=2000)
    before,_,_=m.player_samples(history+[target,duplicate],protocol)
    after,_,_=m.player_samples(history+[dict(target,points=4000),duplicate,row('2022-07-13',9000)],protocol)
    left=[r for r in before['player_points'] if r['date']=='2022-07-12']
    right=[r for r in after['player_points'] if r['date']=='2022-07-12']
    assert len(left)==len(right)==2
    for a,b in zip(left,right):
        assert a['estimate']==b['estimate'] and a['probability']==b['probability']
        assert a['last_feature_date']<'2022-07-12'


@pytest.mark.parametrize('stat',m.STATS)
def test_count_distribution_mass_tail_and_threshold_match(protocol,stat):
    hist=[row(f'2022-07-{i:02d}',0 if i%2 else 7) for i in range(1,21)]
    par=m.player_parameters(hist,stat,protocol);pmf=m.player_distribution(par,protocol)
    assert sum(pmf)==pytest.approx(1,abs=1e-12) and min(pmf)>=0
    assert sum(pmf[4:])==pytest.approx(m.player_over(par,3.5,protocol),abs=1e-10)
    assert m.player_over(par,.5,protocol)>m.player_over(par,6.5,protocol)


def test_DNP_is_excluded_from_conditional_history_and_never_zero_result(protocol):
    rows=[row(f'2022-07-{i:02d}') for i in range(1,12)]
    rows.append(dict(row('2022-07-12',0),participated=False,minutes=0))
    samples,skipped,hist=m.player_samples(rows,protocol)
    assert skipped['conditional_DNP_excluded']==1 and len(hist[1])==11
    assert all(r['date']!='2022-07-12' for r in samples['player_blocks'])


def test_calibration_ignores_evaluation_outcomes(protocol):
    rows=[dict(date='2022-10-01',probability=.3 if i%2 else .8,y=i%3==0) for i in range(120)]
    fitted=m.fit_calibration(rows+[dict(date='2024-01-01',probability=.999,y=0)],protocol)
    changed=m.fit_calibration(rows+[dict(date='2024-01-01',probability=.001,y=1)],protocol)
    assert fitted==changed and fitted['last_date']<'2023-07-01'
    for p in (0,1): assert 0<m.apply_calibration(p,dict(slope=3,bias=2))<1


def final_game():
    def team(tid,pid,points):
        stats=dict(points=points,reboundsTotal=6,assists=4,threePointersMade=2,steals=1,blocks=0)
        return dict(teamId=tid,statistics=stats,players=[dict(personId=pid,played='1',statistics=stats)])
    return dict(gameId='0022600001',gameStatus=3,gameTimeUTC='2026-10-20T19:00:00+00:00',
                homeTeam=team(10,1,101),awayTeam=team(20,2,99))


def mapping():
    return dict(nba_game_id='0022600001',tipoff_utc='2026-10-20T19:00:00+00:00',home_nba_team_id=10,away_nba_team_id=20)


def test_extra_stats_and_team_markets_use_reconciled_official_scores():
    forecasts=[dict(player_id=1,team_id=10,market='player_threes'),dict(player_id='winner',market='winner'),
               dict(player_id=10,team_id=10,market='team_points'),dict(player_id='total',market='game_total')]
    result=web.score_game(final_game(),forecasts,mapping())
    assert [result[(f['player_id'],f['market'])]['actual'] for f in forecasts]==[2,1,101,200]
    bad=final_game();bad['homeTeam']['statistics']=dict(bad['homeTeam']['statistics'],threePointersMade=99)
    failed=web.score_game(bad,forecasts,mapping())
    assert failed[(1,'player_threes')]['status']=='validation_hold'
    assert failed[('total','game_total')]['actual']==200


@pytest.mark.parametrize('mutation',['missing','wrong_team','missing_stat','nonparticipant'])
def test_missing_extra_stat_or_player_is_never_scored_as_zero(mutation):
    game=final_game();forecasts=[dict(player_id=1,team_id=10,market='player_blocks')]
    if mutation=='missing': forecasts[0]['player_id']=99
    elif mutation=='wrong_team': forecasts[0]['team_id']=20
    elif mutation=='missing_stat': game['homeTeam']['players'][0]['statistics'].pop('blocks')
    else: game['homeTeam']['players'][0]['played']='0';game['homeTeam']['players'].append(
        dict(personId=3,played='1',statistics=deepcopy(game['homeTeam']['statistics'])))
    result=web.score_game(game,forecasts,mapping())[(forecasts[0]['player_id'],'player_blocks')]
    assert result['actual'] is None and result['status']==('dnp' if mutation=='nonparticipant' else 'validation_hold')


def test_correlated_team_residuals_change_total_uncertainty(protocol):
    # Synthetic scores with shared pace shocks: total variance must include covariance.
    games=[]
    from datetime import date
    start=date(2021,10,1)
    for i in range(220):
        day=(start+timedelta(days=i)).isoformat();shock=[-10,3,7,-2,9][i%5]
        games.append(dict(game_id=str(i),date=day,season='2021-22',
            home=dict(team_id=10,points=110+shock+(i%3)),away=dict(team_id=20,points=104+shock)))
    _,league,hist,ratings=m.team_samples(games,protocol)
    cov=np.asarray(league['covariance'])
    assert cov[0,1]>0 and cov.sum()>cov.trace()
    future=dict(date='2022-06-01',home=dict(team_id=10,points=9999),away=dict(team_id=20,points=0))
    f=m.team_features(future,hist,ratings,league,protocol)
    future['home']['points']=0;future['away']['points']=9999
    assert f==m.team_features(future,hist,ratings,league,protocol)


def test_frozen_bundle_tampering_is_rejected(tmp_path):
    write_json(tmp_path/'bundle.json',dict(forecasts=[]))
    write_json(tmp_path/'bundle.seal.json',dict(sha256=digest(tmp_path/'bundle.json')))
    instance=web.MultiDashboard.__new__(web.MultiDashboard);instance.folder=tmp_path;instance.seal=digest(tmp_path/'bundle.seal.json')
    assert instance.load()['forecasts']==[]
    write_json(tmp_path/'bundle.json',dict(forecasts=['changed']))
    with pytest.raises(ValueError,match='bundle changed'):instance.load()


@pytest.mark.parametrize('tipoff,expected',[
    ('2026-10-21T00:00:00+00:00','2026-27'),('2026-12-31T23:00:00+00:00','2026-27'),
    ('2027-01-15T01:00:00+00:00','2026-27'),('2027-04-12T00:00:00+00:00','2026-27'),
    ('2027-10-19T23:30:00+00:00','2027-28'),('2008-11-01T00:00:00+00:00','2008-09')])
def test_season_label_follows_nba_season_not_calendar_year(tipoff,expected):
    assert m.season_label(tipoff)==expected
