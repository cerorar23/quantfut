import copy
import json
import numpy as np
import pytest
from nba.rebound_distributions import (rebound_labels,rate_features,fit_dispersion,family_distribution,
    categories,count_scores,choose_family,FAMILIES)

P=dict(train_season='2021-22',fit_cutoff='2022-07-01',rate_history_window=20,minimum_rate_appearances=2,
    baseline_window=2,rate_prior_minutes=30,rate_prior_rebounds_per_minute=.18,maximum_dispersion=2,
    tail_probability=1e-12,tail_tolerance=1e-10,minimum_support=80,maximum_support=4096,
    seed=20261007,log_probability_floor=1e-300,diagnostic_lines=[4.5,7.5,10.5],bootstrap_replicates=10,
    candidate_priority=['minutes_poisson','gamma_poisson','negative_binomial'],selection_minimum_difference=1e-12)

def row(gid,day,reb=4,minutes=20,ot=0,season='2021-22'):
    return dict(game_id=gid,player_id=1,date=day,season=season,season_type='regular',id_namespace='nba',
        team_id=10,regulation_minutes=minutes,overtime_periods=ot,rebounds=reb)

def minute(gid,day,season='2021-22'):
    return dict(game_id=gid,player_id=1,date=day,season=season,history_max_date='2021-10-01',
        history_game_ids=['1','2'],candidate_samples=[10,20,30],baseline_mean=20)

def feature(day='2023-01-01'):
    return dict(game_id='x',player_id=1,date=day,season='2022-23',rate_alpha=12,rate_beta=60,rate_mean=.2,
        baseline_count_mean=4,minute_samples=[20],rate_history_max_date='2021-12-31',minute_history_max_date='2021-12-31')

def params(phi=.1):
    return dict(fit_cutoff='2022-07-01',fitting_max_date='2022-04-10',dispersion=phi,shape=1/phi if phi else None)

def test_rate_history_excludes_overtime_same_day_and_future():
    rows=[row('1','2021-10-02'),row('2','2021-10-03',6),row('ot','2021-10-04',40,ot=1),
        row('3','2021-10-05',5),row('4','2021-10-05',8),row('5','2021-10-06',9)]
    minutes=[minute(r['game_id'],r['date']) for r in rows]
    features,_,_=rate_features(rows,minutes,P)
    assert features[0]['rate_history_game_ids']==features[1]['rate_history_game_ids']==['1','2']
    assert features[0]['rate_alpha']==pytest.approx(15.4)
    changed=copy.deepcopy(rows);changed[3]['rebounds']=100;changed[-1]['rebounds']=101
    second,_,_=rate_features(changed,minutes,P)
    assert features[:2]==second[:2] and 'actual_rebounds' not in features[0]

@pytest.mark.parametrize('kind',['duplicate','namespace','count','minute_future','season','minute_identity'])
def test_rate_rejects_identity_and_temporal_corruption(kind):
    rows=[row('1','2021-10-02'),row('2','2021-10-03'),row('3','2021-10-04')]
    minutes=[minute('3','2021-10-04')]
    if kind=='duplicate':rows.append(copy.deepcopy(rows[0]))
    if kind=='namespace':rows[0]['id_namespace']='espn'
    if kind=='count':rows[0]['rebounds']=2.5
    if kind=='minute_future':minutes[0]['history_max_date']='2021-10-04'
    if kind=='season':minutes[0]['season']='2022-23'
    if kind=='minute_identity':minutes[0]['date']='2021-10-05'
    with pytest.raises(ValueError):rate_features(rows,minutes,P)

def test_zero_or_overtime_labels_are_retained_but_excluded_from_target():
    rows=[row('1','2021-10-02'),row('2','2021-10-03'),row('ot','2021-10-04',ot=1),row('zero','2021-10-05',minutes=0)]
    _,_,skips=rate_features(rows,[],P)
    assert skips['overtime_game_label_excluded']==1 and skips['zero_regulation_exposure']==1

@pytest.mark.parametrize('kind',['duplicate','namespace','stats','missing'])
def test_rebound_label_join_rejects_mismatches(kind):
    labels=[row('1','2021-10-02')];boxes=copy.deepcopy(labels)
    if kind=='duplicate':boxes.append(copy.deepcopy(boxes[0]))
    if kind=='namespace':boxes[0]['id_namespace']='espn'
    if kind=='stats':boxes[0]['rebounds']=float('nan')
    if kind=='missing':boxes=[]
    with pytest.raises(ValueError):rebound_labels(labels,boxes)

def test_poisson_and_mixture_moments_known_values():
    f=feature();out=family_distribution(f,params(),P,'minutes_poisson')
    p=np.array(out['pmf']);k=np.arange(len(p))
    assert p.sum()==pytest.approx(1,abs=1e-12) and np.dot(k,p)==pytest.approx(4)
    assert np.dot((k-4)**2,p)==pytest.approx(4)
    mixed=family_distribution(dict(f,minute_samples=[0,40]),params(),P,'minutes_poisson')
    q=np.array(mixed['pmf']);assert np.dot(k,q)==pytest.approx(4)
    assert np.dot((k-4)**2,q)==pytest.approx(20)

@pytest.mark.parametrize('family',['gamma_poisson','negative_binomial'])
def test_negative_binomial_moments_and_tail(family):
    out=family_distribution(feature(),params(),P,family);p=np.array(out['pmf']);k=np.arange(len(p))
    shape=12 if family=='gamma_poisson' else 10
    assert np.dot(k,p)==pytest.approx(4,rel=1e-10)
    assert np.dot((k-4)**2,p)==pytest.approx(4+16/shape,rel=1e-9)
    assert out['omitted_tail_mass']<=1e-10

def test_zero_dispersion_is_exact_poisson_limit():
    a=family_distribution(feature(),params(0),P,'negative_binomial')
    b=family_distribution(feature(),params(0),P,'minutes_poisson')
    assert a['pmf']==b['pmf']

@pytest.mark.parametrize('family',FAMILIES)
def test_fitted_parameters_cannot_be_applied_before_cut(family):
    with pytest.raises(ValueError):family_distribution(feature('2022-01-01'),params(),P,family)

def test_dispersion_fitting_rejects_validation_or_future_labels():
    f=feature('2022-01-01');f['season']='2021-22'
    y=dict(game_id='x',player_id=1,date=f['date'],season='2021-22',actual_rebounds=20)
    fit=fit_dispersion([f],[y],P);assert fit['training_cases']==1 and fit['dispersion']>0
    for changes in [dict(season='2022-23'),dict(date='2023-01-01'),dict(rate_history_max_date='2022-01-01')]:
        bad=dict(f,**changes)
        with pytest.raises(ValueError):fit_dispersion([bad],[y],P)

def test_fitted_numpy_moments_are_serializable_without_nonfinite_values():
    f=feature('2022-01-01');f['season']='2021-22'
    y=dict(game_id='x',player_id=1,date=f['date'],season='2021-22',actual_rebounds=20)
    fit=fit_dispersion([f],[y],P)
    assert type(fit['dispersion_clamped']) is bool
    assert json.loads(json.dumps(fit,allow_nan=False))==fit

def test_discrete_crps_point_mass_and_atom_coverage():
    p=[0,0,1,0,0,0];s=count_scores(p,5,'x',P)
    assert s['crps']==3 and s['mae']==3 and s['nll_probability_clipped']
    perfect=count_scores(p,2,'x',P)
    assert perfect['crps']==0 and perfect['central_interval_mass']==1 and perfect['coverage_minus_mass']==0

def test_categories_push_monotonicity_and_void_unknown():
    p=family_distribution(feature(),params(),P,'gamma_poisson')['pmf']
    integer=categories(p,4);half=categories(p,4.5)
    assert integer['push']==pytest.approx(p[4]) and half['push']==0
    assert integer['under']+integer['push']+integer['over']==pytest.approx(1)
    assert categories(p,3)['over']>=categories(p,4)['over']>=categories(p,5)['over']
    assert integer['void_probability'] is None and not integer['actual_contract_verified']

def test_randomized_pit_is_reproducible_and_inside_outcome_atom():
    p=family_distribution(feature(),params(),P,'gamma_poisson')['pmf']
    a=count_scores(p,4,'case',P);b=count_scores(p,4,'case',P)
    assert a==b and sum(p[:4])<=a['randomized_pit']<=sum(p[:5])

def test_selection_retains_baseline_on_failure_and_uses_fixed_tie_priority():
    validation=dict(rows=10,models={f:dict(crps=1) for f in FAMILIES})
    assert choose_family(validation,P)['selected_family']=='baseline'
    for f in FAMILIES[1:]:validation['models'][f]['crps']=.9
    assert choose_family(validation,P)['selected_family']=='minutes_poisson'

@pytest.mark.parametrize('kind',['negative','unnormalized','nonfinite','line','outcome'])
def test_invalid_count_probabilities_and_labels_rejected(kind):
    p=[.5,.5]
    if kind=='negative':p=[-.1,1.1]
    if kind=='unnormalized':p=[.2,.2]
    if kind=='nonfinite':p=[float('nan'),.5]
    with pytest.raises(ValueError):
        if kind=='line':categories(p,-1)
        else:count_scores(p,2 if kind=='outcome' else 1,'x',P)
