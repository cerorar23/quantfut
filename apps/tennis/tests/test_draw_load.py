"""Synthetic checks of logical precedence and isolated train/test transforms."""
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
from tennis_engine.draw_load import (extract_draw_load,observed_counters,DrawLoadCorrection,
    CONTROL_FEATURES,LOAD_FEATURES,compare_draw_load)


def match(mid,round,winner,loser,score='6-4 6-4',points=120):
    return dict(match_id=mid,circuit='ATP',source_group='tour',tourney_id='2024-1',tourney_level='A',round=round,
        winner_id=winner,loser_id=loser,score=score,best_of=3,valid_serve_counts=True,w_svpt=points//2,l_svpt=points-points//2)


@pytest.fixture
def draw():
    history=pd.DataFrame([match('a1','R32','a','x','6-7(4) 7-6(4) 6-0',160),
        match('b1','R32','b','y'),match('target','R16','a','b'),match('future','QF','a','z')])
    target=pd.DataFrame([dict(match_id='target',player_a='a',player_b='b')])
    return history,target


def test_only_prior_rounds_and_point_denominators_count(draw):
    h,t=draw;load,r=extract_draw_load(h,t);row=load.iloc[0]
    assert row.load_points_difference==40 and row.load_games_difference==12
    assert row.load_sets_difference==1 and row.load_deciding_sets_difference==1
    assert row.a_prior_match_ids=='["a1"]' and row.b_prior_match_ids=='["b1"]'
    assert r['windows_3d_7d_available'] is False and row.clock_window_verified==False


def test_target_and_later_scores_or_counters_cannot_change_load(draw):
    h,t=draw;before,_=extract_draw_load(h,t)
    changed=h.copy();mask=changed.match_id.isin(['target','future'])
    changed.loc[mask,'score']='0-6 0-6';changed.loc[mask,['w_svpt','l_svpt']]=999
    after,_=extract_draw_load(changed,t)
    pd.testing.assert_frame_equal(before,after)


def test_unrelated_future_edition_does_not_change_load(draw):
    h,t=draw;before,_=extract_draw_load(h,t)
    future=match('other','R32','a','q');future['tourney_id']='2025-100'
    after,_=extract_draw_load(pd.concat([h,pd.DataFrame([future])],ignore_index=True),t)
    pd.testing.assert_frame_equal(before,after)


def test_missing_points_are_not_claimed_as_zero_workload(draw):
    h,t=draw;h.loc[h.match_id.eq('a1'),'valid_serve_counts']=False
    row=extract_draw_load(h,t)[0].iloc[0]
    assert row.a_points_known_subtotal==0 and row.a_points_missing==1
    assert row.observed_counters_complete==False and row.a_games_known_subtotal==32


def test_walkover_has_no_play_and_no_false_missing_counter(draw):
    h,t=draw;h.loc[h.match_id.eq('a1'),'score']='W/O'
    row=extract_draw_load(h,t)[0].iloc[0]
    assert row.a_walkovers==1 and row.a_played_matches==0
    assert row.a_points_known_subtotal==0 and row.a_points_missing==0
    assert row.both_have_prior_observed_play==False


def test_loss_followed_by_advancement_quarantines_history(draw):
    h,t=draw;h.loc[h.match_id.eq('a1'),['winner_id','loser_id']]=['x','a']
    row=extract_draw_load(h,t)[0].iloc[0]
    assert row.a_status=='draw_progression_conflict' and row.draw_load_supported==False


def test_duplicate_stage_and_round_robin_are_not_ordered(draw):
    h,t=draw;other=match('duplicate','R32','a','q')
    row=extract_draw_load(pd.concat([h,pd.DataFrame([other])],ignore_index=True),t)[0].iloc[0]
    assert row.draw_load_supported==False
    h.loc[h.match_id.eq('a1'),'round']='RR'
    row=extract_draw_load(h,t)[0].iloc[0]
    assert row.a_status=='unsupported_round_format'


def test_nonstandard_score_preserves_missing_games_not_guessed_points():
    row=SimpleNamespace(score='6-4 1-2 RET',best_of=3,valid_serve_counts=True,w_svpt=60,l_svpt=60)
    counts=observed_counters(row)
    assert counts==dict(points=120,games=None,sets=None,deciding_sets=None)


def test_team_knockout_rounds_are_not_an_individual_draw(draw):
    h,t=draw;h['tourney_id']='2024-W-FC-2024-FLS';h['tourney_level']='D'
    row=extract_draw_load(h,t)[0].iloc[0]
    assert row.draw_load_supported==False and row.a_status=='unsupported_round_format'


@pytest.fixture
def experiment():
    rng=np.random.default_rng(8);data=[];base=[];loads=[]
    for i in range(140):
        year=2024 if i<100 else 2025
        data.append(dict(match_id=str(i),player_a='a',player_b='b',y=i%2,circuit='ATP',
            partition='development_2024' if year==2024 else 'exploratory_2025',comparison_block_id=f'{year}-{i//10}',
            historical_reconstruction=True,genuine_asof_validation=False,completed_standard=True,
            edition_source_period_first=f'{year}-06-01',edition_source_period_last=f'{year}-06-07'))
        base.append(dict(match_id=str(i),player_a='a',player_b='b',y=i%2,baseline_probability=.45+.1*(i%2),
            origin=f'{year}-01-01',training_latest_period=f'{year-1}-11-20',pool_latest_period=f'{year-1}-11-19'))
        loads.append(dict(match_id=str(i),draw_load_supported=True,both_have_prior_observed_play=True,
            observed_counters_complete=True,**dict(zip(CONTROL_FEATURES+LOAD_FEATURES,rng.normal(size=10)))))
    return pd.DataFrame(data),pd.DataFrame(base),pd.DataFrame(loads)


def test_three_variants_share_one_cohort_and_test_cannot_change_fit(experiment):
    d,b,l=experiment;scored,first=compare_draw_load(d,b,l)
    changed=d.copy();changed.loc[100:,'y']=1-changed.loc[100:,'y']
    other=b.copy();other.loc[100:,'y']=changed.loc[100:,'y']
    changed_l=l.copy();changed_l.loc[100:,list(LOAD_FEATURES)]*=1000
    _,later=compare_draw_load(changed,other,changed_l)
    assert first['artifacts']==later['artifacts']
    assert len(scored)==40 and {x['n'] for x in first['metrics'].values()}=={40}
    expected=np.sqrt(np.mean(l.iloc[:100][list(CONTROL_FEATURES+LOAD_FEATURES)].to_numpy()**2,axis=0));expected[expected==0]=1
    np.testing.assert_allclose(first['artifacts']['load']['rms_train'],expected)


def test_fit_rejects_evaluation_and_player_swap_is_symmetric(experiment):
    d,b,l=experiment;frame=d.merge(b[['match_id','baseline_probability']],on='match_id').merge(l,on='match_id')
    with pytest.raises(ValueError,match='development'):DrawLoadCorrection(LOAD_FEATURES).fit(frame)
    training=frame.iloc[:100].copy();model=DrawLoadCorrection(LOAD_FEATURES);model.fit(training)
    swapped=training.copy();swapped[list(LOAD_FEATURES)]=-swapped[list(LOAD_FEATURES)];swapped['y']=1-swapped.y
    swapped['baseline_probability']=1-swapped.baseline_probability
    other=DrawLoadCorrection(LOAD_FEATURES);other.fit(swapped)
    np.testing.assert_allclose(model.predict(training),1-other.predict(swapped),atol=1e-10)


def test_foreign_load_ids_or_competition_split_are_rejected(experiment):
    d,b,l=experiment
    with pytest.raises(ValueError,match='identities'):compare_draw_load(d,b,l.iloc[:-1])
    d.loc[100,'comparison_block_id']=d.loc[0,'comparison_block_id']
    with pytest.raises(ValueError,match='Competition crosses'):compare_draw_load(d,b,l)
