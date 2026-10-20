from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math

import pytest

from tennis_engine.benchmark import (BenchmarkCase, BenchmarkResult, BenchmarkPrediction,
                                     BenchmarkEvaluator, probability_metrics)
from tennis_engine.recent_load import LoadObservation, RecentLoadExtractor, api_tennis_history
from tennis_engine.load_runner import LoadCorrection, LoadTrainingRow, ModelRunner, load_difference

DECISION = '2026-10-17T12:00:00Z'
START = '2026-10-18T12:00:00Z'


def observation(**kwargs):
    fields = dict(event_id='past', player_ids=('a','c'), ended_after='2026-10-16T10:00:00Z',
                  ended_by='2026-10-16T12:00:00Z', available_at='2026-10-16T13:00:00Z',
                  status='completed', points=140, games=24, sets=3, deciding_set=1, source_sha256='a'*64)
    fields.update(kwargs)
    return LoadObservation(**fields)


def extract(rows, player='a', **kwargs):
    return RecentLoadExtractor().transform(rows,player,DECISION,START,'target',**kwargs)


def case(i='x', **kwargs):
    fields=dict(case_id=i,event_id=i,player_a='a',player_b='b',decision_at=DECISION,scheduled_start=START)
    fields.update(kwargs)
    return BenchmarkCase(**fields)


def result(i='x', **kwargs):
    fields=dict(event_id=i,player_a='a',player_b='b',status='completed',y=1,
                actual_start='2026-10-18T12:10:00Z',ended_at='2026-10-18T14:00:00Z',available_at='2026-10-18T14:01:00Z')
    fields.update(kwargs)
    return BenchmarkResult(**fields)


def pred(i='x',p=.7,**kwargs):
    fields=dict(case_id=i,player_a='a',player_b='b',decision_at=DECISION,probability=p)
    fields.update(kwargs)
    return BenchmarkPrediction(**fields)


def test_strict_receipt_gate_prevents_backfilled_and_equal_time_leakage():
    good=observation()
    for when in [DECISION,'2026-10-18T00:00:00Z']:
        value=extract([good,observation(event_id='backfill',available_at=when)])
        assert value['features']['points_3d']['value']==140
        assert value['excluded']['not_known_before_decision']==1


def test_end_interval_boundary_is_ambiguous_and_unknown_is_not_zero():
    wide=observation(ended_after='2026-10-10T00:00:00Z')
    feature=extract([wide])['features']['points_3d']
    assert feature['value'] is None
    assert feature['ambiguous_boundary_matches']==1
    assert extract([])['features']['points_3d']['value'] is None
    assert extract([],history_complete=True)['features']['points_3d']['value']==0


def test_lower_boundary_included_and_upper_bound_at_decision_excluded():
    lower=observation(ended_after='2026-10-14T12:00:00Z',ended_by='2026-10-14T12:00:00Z')
    upper=observation(event_id='u',ended_after=DECISION,ended_by=DECISION,available_at=DECISION)
    assert extract([lower,upper])['features']['points_3d']['value']==140


def test_latest_available_revision_deduplicates_and_preserves_earlier_version():
    old=observation();new=replace(old,points=150,available_at='2026-10-16T14:00:00Z')
    future=replace(old,points=999,available_at='2026-10-18T00:00:00Z')
    assert extract([future,new,old,old])['features']['points_3d']['value']==150
    with pytest.raises(ValueError):extract([old,replace(old,points=145)])


def test_target_excluded_retirement_load_kept_and_walkover_not_counted():
    rows=[observation(status='retired'),observation(event_id='target',points=999),
          observation(event_id='wo',status='walkover',points=0)]
    assert extract(rows)['features']['points_3d']['value']==140


def test_missing_counter_preserved_and_player_identity_revision_resolved_first():
    assert extract([observation(points=None)])['features']['points_3d']['value'] is None
    rows=[observation(),observation(player_ids=('d','c'),available_at='2026-10-16T14:00:00Z')]
    assert extract(rows)['features']['points_3d']['observed_matches']==0


@pytest.mark.parametrize('kwargs',[{'points':-1},{'points':True},{'ended_by':'2026-10-19T00:00:00Z'},
                                  {'available_at':'2026-10-16T13:00:00'}, {'player_ids':('a','a')}])
def test_invalid_load_contracts_rejected(kwargs):
    with pytest.raises(ValueError):observation(**kwargs)


def test_metrics_analytical_values_endpoints_and_empty_cohort():
    s=probability_metrics([0,1],[.25,.75])
    assert s['brier']==pytest.approx(.0625)
    assert s['log_loss']==pytest.approx(-math.log(.75))
    assert s['ece']==pytest.approx(.25)
    assert len(s['calibration'])==10
    perfect=probability_metrics([0,1],[0.,1.])
    assert perfect['brier']==0 and perfect['calibration'][-1]['n']==1
    assert probability_metrics([],[])['log_loss'] is None


@pytest.mark.parametrize('p',[float('nan'),float('inf'),-.1,1.1,True])
def test_invalid_probabilities_rejected(p):
    with pytest.raises(ValueError):probability_metrics([1],[p])


def test_common_cohort_identical_and_all_statuses_preserved_in_coverage():
    cs=[case(str(i)) for i in range(4)]
    rs=[result('0'),result('1'),result('2',status='retired'),result('3',status='walkover',y=None)]
    variants={'base':[pred(str(i)) for i in range(4)],'load':[pred('1',.6)]}
    report=BenchmarkEvaluator().evaluate(cs,rs,variants,'2026-10-19T00:00:00Z')
    assert report['common_case_ids']==['1'] and report['coverage']==.25
    assert all(v['n']==1 for v in report['metrics'].values())
    assert report['result_statuses']['retired']==1 and report['n_eligible_completed']==2


def test_evaluation_rejects_prediction_duplicates_orientation_and_leaked_decision():
    evaluator=BenchmarkEvaluator()
    for predictions in [[pred(),pred()], [pred(player_a='b',player_b='a')]]:
        with pytest.raises(ValueError):evaluator.evaluate([case()],[result()],{'a':predictions},'2026-10-19T00:00:00Z')
    report=evaluator.evaluate([case()],[result(actual_start=DECISION)],{'a':[pred()]},'2026-10-19T00:00:00Z')
    assert report['n_common']==0 and report['excluded']['invalid_actual_chronology']==1


def test_future_labels_and_missing_actual_times_not_scored():
    for r in [result(available_at='2026-10-20T00:00:00Z'),result(actual_start=None)]:
        report=BenchmarkEvaluator().evaluate([case()],[r],{'a':[pred()]},'2026-10-19T00:00:00Z')
        assert report['metrics']['a']['n']==0


def test_archive_normalization_counts_points_without_inventing_end_time(tmp_path):
    payload={'success':1,'result':[{'event_type_type':'Atp Singles','event_status':'Finished',
        'event_key':42,'first_player_key':1,'second_player_key':2,'event_date':'2026-10-16','event_time':'12:00',
        'scores':[{'score_first':'7','score_second':'6'},{'score_first':'6','score_second':'4'}],
        'statistics':[{'player_key':p,'stat_period':'match','stat_name':'Service Points Won','stat_total':n}
                      for p,n in [(1,80),(2,75)]]}]}
    path=tmp_path/'raw.json';path.write_text(json.dumps(payload))
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    rows=api_tennis_history(path,'2026-10-16T18:00:00Z',digest)
    assert rows[0].points==155 and rows[0].games==23 and rows[0].sets==2
    assert rows[0].ended_after.startswith('0001')
    assert extract(rows,player='1')['features']['points_3d']['value'] is None
    with pytest.raises(ValueError):api_tennis_history(path,'2026-10-16T18:00:00Z','0'*64)


def training_rows():
    rows=[]
    for i in range(24):
        decision=datetime(2025,1,10,tzinfo=timezone.utc)+timedelta(days=i)
        d=decision.isoformat();start=(decision+timedelta(hours=1)).isoformat()
        c=case(str(i),decision_at=d,scheduled_start=start)
        r=result(str(i),y=i%2,actual_start=start,ended_at=(decision+timedelta(hours=3)).isoformat(),
                 available_at=(decision+timedelta(hours=4)).isoformat())
        h=observation(event_id='prior'+str(i),ended_after=(decision-timedelta(days=1)).isoformat(),
                      ended_by=(decision-timedelta(hours=23)).isoformat(),available_at=(decision-timedelta(hours=22)).isoformat(),points=100+i)
        rows.append(LoadTrainingRow(c,r,pred(str(i),p=.5,decision_at=d),(h,),True))
    return rows


def test_fit_and_run_real_residual_preserves_player_swap_symmetry():
    model=LoadCorrection();model.fit(training_rows(),'2025-02-10T00:00:00Z')
    runner=ModelRunner(lambda c:.7 if c.player_a=='a' else .3,model)
    out=runner.run([case('x'),case('y',player_a='b',player_b='a')],[observation()])
    predictions=out['variants']['current_plus_load']
    assert predictions[0].probability is not None
    assert predictions[0].probability+predictions[1].probability==pytest.approx(1)
    with pytest.raises(ValueError):model.fit(training_rows(),'2025-02-10T00:00:00Z')


def test_fit_refuses_future_labels_insufficient_rows_and_target_reuse():
    rows=training_rows()
    with pytest.raises(ValueError):LoadCorrection().fit(rows,'2025-01-10T00:00:00Z')
    with pytest.raises(ValueError):LoadCorrection().fit(rows[:2],'2025-02-10T00:00:00Z')
    fitted=LoadCorrection();fitted.fit(rows,'2025-02-10T00:00:00Z')
    with pytest.raises(ValueError):ModelRunner(lambda c:.5,fitted).run([case('0')],[observation()])


def test_untrained_candidate_explicitly_abstains_instead_of_copying_baseline():
    output=ModelRunner(lambda c:.7).run([case()],[observation()])
    assert output['variants']['current'][0].probability==.7
    p=output['variants']['current_plus_load'][0]
    assert p.probability is None and p.reason=='no_temporally_valid_training_sample'
