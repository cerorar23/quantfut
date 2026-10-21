"""No live requests: result identities, source binding, clocks and scores."""
from copy import deepcopy
from pathlib import Path
import json
import pytest
from tennis_evidence_v1.results import score_text, timestamp_proof, provider_result
from tennis_evidence_v1.historical import categorical_metrics
from tennis_engine.paper_validation import digest


@pytest.mark.parametrize('a,b,expected', [('6.4','7.7','6-7(4)'),('7.10','6.8','7-6(8)'),('6','4','6-4')])
def test_api_scores_are_strings_not_float_games(a,b,expected):
    assert score_text([dict(score_set='1',score_first=a,score_second=b)])==(expected,1)


@pytest.mark.parametrize('scores',[
    [dict(score_set='2',score_first='6',score_second='4')],
    [dict(score_set='1',score_first='7.4',score_second='6.7')],
    [dict(score_set='1',score_first='6.4',score_second='7')],
    [dict(score_set='1',score_first='6.4',score_second='4.2')],
    [dict(score_set='1',score_first='3',score_second='2'),dict(score_set='2',score_first='6',score_second='4')],
])
def test_invalid_partial_or_inconsistent_set_encodings_are_rejected(scores):
    with pytest.raises(ValueError):score_text(scores)


@pytest.fixture
def evidence(tmp_path):
    source=tmp_path/'result.json';source.write_text('{}')
    time_source=tmp_path/'times.json'
    time_source.write_text(json.dumps({'event':{'start':'2026-10-20T12:03:00Z','end':'2026-10-20T14:00:00Z','home':'Alice Example','away':'Bea Example'}}))
    parent=dict(event=dict(id='api_tennis:1',sport_key='tennis_atp_api_1',home_team='Alice Example',away_team='Bea Example'),
        tournament_metadata=dict(best_of=3),circuit='ATP',sealed_at='2026-10-19T18:00:00Z',
        fixture_receipt=dict(official_not_before='2026-10-20T12:00:00Z'))
    raw=dict(event_key=1,first_player_key=100,second_player_key=200,tournament_key=1,tournament_season='2026',
        event_status='Finished',event_type_type='Atp Singles',event_winner='First Player',event_final_result='2 - 0',
        scores=[dict(score_set='1',score_first='6',score_second='4'),dict(score_set='2',score_first='7.7',score_second='6.4')])
    receipt=dict(source_path=str(source),sha256=digest(source),received_at='2026-10-20T14:05:00Z')
    proof=dict(event_id='api_tennis:1',semantics='physical_court_start_end',reviewed=True,reviewed_by='synthetic-test',
        source_url='https://www.atptour.com/physical-times.json',source_path=str(time_source),source_sha256=digest(time_source),
        participants=['Alice Example','Bea Example'],
        field_paths=dict(actual_start=['event','start'],actual_end=['event','end'],home_team=['event','home'],away_team=['event','away']),
        actual_start='2026-10-20T12:03:00Z',actual_end='2026-10-20T14:00:00Z',received_at='2026-10-20T14:02:00Z')
    return parent,raw,receipt,proof,'2026-10-20T14:10:00Z'


def test_completed_result_binds_provider_ids_and_physical_source(evidence):
    parent,raw,receipt,proof,at=evidence
    result=provider_result(parent,raw,receipt,raw,proof,at)
    assert result['score_A_B']=='6-4 7-6(4)'
    assert result['official_winner']=='Alice Example'
    assert result['actual_start']==proof['actual_start']
    assert result['physical_times_are_scheduled_estimates'] is False


def test_no_physical_time_proof_never_imputes_scheduled_time(evidence):
    parent,raw,receipt,proof,at=evidence
    raw['event_date']='2026-10-20';raw['event_time']='12:00'
    with pytest.raises(ValueError,match='still missing'):provider_result(parent,raw,receipt,raw,None,at)


@pytest.mark.parametrize('field,value', [('first_player_key',200),('second_player_key',100),('tournament_key',2),('tournament_season','2025')])
def test_identity_orientation_and_edition_cannot_silently_change(evidence,field,value):
    parent,raw,receipt,proof,at=evidence;altered=deepcopy(raw);altered[field]=value
    with pytest.raises(ValueError,match='changed'):provider_result(parent,altered,receipt,raw,proof,at)


def test_final_sets_must_agree_with_individual_scores(evidence):
    parent,raw,receipt,proof,at=evidence;raw['event_final_result']='0 - 2'
    with pytest.raises(ValueError,match='Final sets'):provider_result(parent,raw,receipt,raw,proof,at)


@pytest.mark.parametrize('change',['unreviewed','wrong_value','modified_source','timezone_missing','end_after_receipt'])
def test_timestamp_values_are_not_merely_trusted_booleans(evidence,change):
    parent,raw,receipt,proof,at=evidence
    if change=='unreviewed':proof['reviewed']=False
    if change=='wrong_value':proof['actual_start']='2026-10-20T12:01:00Z'
    if change=='modified_source':Path(proof['source_path']).write_text('{}')
    if change=='timezone_missing':
        p=Path(proof['source_path']);v=json.loads(p.read_text());v['event']['start']='2026-10-20T12:03:00';p.write_text(json.dumps(v));proof['source_sha256']=digest(p)
    if change=='end_after_receipt':proof['received_at']='2026-10-20T13:00:00Z'
    with pytest.raises(ValueError):timestamp_proof(proof,parent['event']['id'],at)


def test_walkover_does_not_invent_match_times(evidence):
    parent,raw,receipt,proof,at=evidence;raw['event_status']='Walk Over'
    result=provider_result(parent,raw,receipt,raw,None,at)
    assert result['actual_start'] is None and result['actual_end'] is None and result['completed_sets']==0


def test_categorical_ece_includes_confidences_below_fifty_percent():
    vector={'a':.4,'b':.35,'c':.25}
    result=categorical_metrics(['a','b'],[vector,vector],['one','two'])
    assert result['n']==2 and result['top_choice_accuracy']==.5
    assert result['calibration'][4]['n']==2
    assert result['top_choice_ece']==pytest.approx(.1)
    assert result['vector_log_loss']>0


def test_invalid_categorical_vector_rejected():
    with pytest.raises(ValueError):categorical_metrics(['a'],[{'a':.8,'b':.5}],['one'])


def test_high_accuracy_does_not_hide_imbalanced_observed_class_counts():
    result=categorical_metrics(['a']*9+['b'],[{'a':.9,'b':.1}]*10,['one']*5+['two']*5)
    assert result['top_choice_accuracy']==result['largest_observed_class_fraction']==.9
    assert result['class_balance_is_ex_post_diagnostic_not_a_fitted_benchmark']


def test_timestamp_source_cannot_belong_to_different_pair(evidence):
    parent,raw,receipt,proof,at=evidence
    proof['participants']=['Different Person','Bea Example']
    with pytest.raises(ValueError,match='participants'):provider_result(parent,raw,receipt,raw,proof,at)


@pytest.fixture
def bridge(evidence,tmp_path,monkeypatch):
    from tennis_evidence_v1 import results as m
    parent,raw,receipt,proof,at=evidence
    q=tmp_path/'quality.json';q.write_text('{}');mp=tmp_path/'markets'/'protocol.json';mp.parent.mkdir();mp.write_text('{}')
    parent.update(artifacts={},protocol_sha256=digest(q))
    original=deepcopy(raw);original['event_status']='1'
    calendar=tmp_path/'original_calendar.json';calendar.write_text(json.dumps(dict(result=[original])))
    parent['event']['commence_time']='2026-10-20T12:00:00Z'
    parent['fixture_receipt'].update(calendar_source_path=str(calendar),calendar_source_sha256=digest(calendar))
    m.write_new(tmp_path/'future_predictions'/'parent.json',dict(parent,payload_sha256=m.checksum(parent)))
    capture=tmp_path/'capture';(capture/'originals'/'one').mkdir(parents=True)
    source=capture/'originals'/'one'/'response.json';source.write_text(json.dumps(dict(success=1,result=[raw])))
    receipt.update(source_path=str(source),sha256=digest(source),http_status=200,method='get_fixtures')
    m.write_new(source.parent/'receipt.json',receipt)
    times=tmp_path/'time_reviews';times.mkdir()
    monkeypatch.setattr(m,'now',lambda:at)
    monkeypatch.setattr(m,'load',lambda _:dict(artifacts={},evaluation_start='2026-10-20T00:00:00Z',evaluation_end='2027-07-01T00:00:00Z'))
    monkeypatch.setattr(m,'load_markets',lambda _: {})
    monkeypatch.setattr(m,'evaluate_future',lambda *a:dict(accepted=len(m.read(a[2]))))
    monkeypatch.setattr(m,'evaluate_markets',lambda *a:dict(accepted=len(m.read(a[2]))))
    return m,q,mp,capture,times,proof,source,receipt,tmp_path


def test_reconciliation_records_missing_time_candidate_without_counting_it(bridge):
    m,q,mp,capture,times,proof,source,receipt,root=bridge
    report=m.reconcile(q,mp,capture,times,root/'run')
    assert report['registered_events']==1 and report['admissible_results']==0
    assert report['matched_terminal_events']==1
    assert 'Physical start/end evidence still missing' in report['pending_reasons']
    assert len(m.read(root/'run'/'terminal_candidates.json'))==1


def test_reconciliation_feeds_both_evaluators_when_source_proof_is_complete(bridge):
    m,q,mp,capture,times,proof,source,receipt,root=bridge
    m.write_new(times/'proof.json',proof)
    report=m.reconcile(q,mp,capture,times,root/'run')
    assert report['admissible_results']==1 and not report['pending']
    assert m.read(root/'run'/'winner_evaluation.json')['accepted']==1
    assert m.read(root/'run'/'markets_evaluation.json')['accepted']==1
    with pytest.raises(FileExistsError):m.reconcile(q,mp,capture,times,root/'run')


def test_conflicting_terminal_sources_are_not_resolved_by_latest_or_favourable_score(bridge):
    m,q,mp,capture,times,proof,source,receipt,root=bridge
    other=capture/'originals'/'two';other.mkdir()
    raw=m.read(source);raw['result'][0]['event_winner']='Second Player'
    target=other/'response.json';target.write_text(json.dumps(raw))
    receipt.update(source_path=str(target),sha256=digest(target),received_at='2026-10-20T14:06:00Z')
    m.write_new(other/'receipt.json',receipt)
    report=m.reconcile(q,mp,capture,times,root/'run')
    assert report['admissible_results']==0
    assert report['pending_reasons']=={'conflicting_terminal_sources_need_review':1}


def test_duplicate_events_in_one_provider_batch_invalidate_entire_batch(bridge):
    m,q,mp,capture,times,proof,source,receipt,root=bridge
    body=m.read(source);body['result']*=2;source.write_text(json.dumps(body))
    receipt['sha256']=digest(source);(source.parent/'receipt.json').write_text(json.dumps(receipt))
    report=m.reconcile(q,mp,capture,times,root/'run')
    assert report['matched_terminal_events']==0 and report['source_errors']
