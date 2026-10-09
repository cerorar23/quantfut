import copy
import numpy as np
import pytest
from nba.fullgame_rebounds import features,distribution,fullgame_labels

PROTOCOL=dict(history_window=20,minimum_appearances=2,baseline_window=2,prior_minutes=30,prior_rate=.18,
    tail_probability=1e-12,tail_tolerance=1e-10,minimum_support=80,maximum_support=4096)
def rows():
    return [dict(game_id='g'+str(i),player_id=1,team_id=2,id_namespace='nba',season='2025-26',season_type='regular',date='2026-01-0'+str(i),
        rebounds=reb,fullgame_minutes=minutes,overtime_periods=ot,participated=True)
        for i,(reb,minutes,ot) in enumerate([(3,30,0),(8,51,1),(10,58,2),(4,35,0)],1)]

def test_fullgame_retains_overtime_targets_and_past_exposure():
    f,y,skips=features(rows(),PROTOCOL)
    assert len(f)==2 and [r['actual_overtime_periods'] for r in y]==[2,0]
    assert f[0]['minute_samples']==[30,51] and f[0]['history_OT_games']==1
    assert 'overtime_game_label_excluded' not in skips
    result=distribution(f[0],PROTOCOL)
    assert result['distribution_overtime']=='included' and result['void_probability'] is None
    assert abs(sum(result['pmf'])-1)<1e-10

def test_target_and_future_overtime_counts_cannot_change_own_forecast():
    original=rows();before=features(original,PROTOCOL)[0][0]
    changed=copy.deepcopy(original);changed[2].update(rebounds=99,fullgame_minutes=60,overtime_periods=3)
    changed[3].update(rebounds=89,fullgame_minutes=63,overtime_periods=3)
    assert features(changed,PROTOCOL)[0][0]==before

def test_same_day_outcomes_not_in_history():
    data=rows();data[2]['date']=data[1]['date']
    f,_,_=features(data,PROTOCOL)
    assert len(f)==1 and f[0]['date']=='2026-01-04' and f[0]['history_max_date']=='2026-01-02'

@pytest.mark.parametrize('mutation',[dict(fullgame_minutes=49,overtime_periods=0),dict(rebounds=-1),dict(overtime_periods=True),dict(fullgame_minutes=float('nan'))])
def test_impossible_clock_and_outcomes_rejected(mutation):
    data=rows();data[0].update(mutation)
    with pytest.raises(ValueError):features(data,PROTOCOL)

def test_future_cut_and_support_budget_rejected():
    f=features(rows(),PROTOCOL)[0][0]
    with pytest.raises(ValueError):distribution(dict(f,history_max_date=f['date']),PROTOCOL)
    with pytest.raises(ValueError):distribution(f,dict(PROTOCOL,maximum_support=1))

def test_zero_exposure_not_used_to_infer_pregame_dnp():
    data=rows();data[2].update(fullgame_minutes=0,participated=False)
    f,y,skips=features(data,PROTOCOL)
    assert len(f)==1 and y[0]['game_id']=='g4' and skips['observed_nonpositive_participation']==1
    assert f[0]['availability_known'] is False and f[0]['void_probability'] is None

def test_labels_use_official_fullgame_exposure_without_scaling():
    box=dict(game_id='g1',player_id=1,team_id=2,id_namespace='nba',season='2025-26',season_type='regular',date='2026-01-01',
        rebounds=10,minutes=53.,participated=True)
    label=dict(box,box_minutes=53.,overtime_periods=1,regulation_minutes=48.)
    result=fullgame_labels([label],[box])[0]
    assert result['fullgame_minutes']==53 and result['rebounds']==10
    with pytest.raises(ValueError):fullgame_labels([dict(label,team_id=3)],[box])
