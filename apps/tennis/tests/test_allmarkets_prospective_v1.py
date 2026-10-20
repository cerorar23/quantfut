"""Synthetic pre-match records and independent result fixtures; no live requests."""
from pathlib import Path
from types import SimpleNamespace
import json
import pytest
from tennis_engine.scoring import Rules
from tennis_markets_v2.catalog import MarketEngine, KINDS
from tennis_allmarkets_v1.contracts import contracts, forecast_board, outcome, validate_mass
from tennis_allmarkets_v1 import prospective as m


@pytest.fixture
def study(tmp_path, monkeypatch):
    clock=['2026-10-19T18:00:00Z']
    monkeypatch.setattr(m,'now',lambda:clock[0])
    source=tmp_path/'source.pdf';source.write_bytes(b'official fixture source')
    calendar=tmp_path/'calendar.json';calendar.write_text('{}')
    review=tmp_path/'review.json';review.write_text('[]')
    quarantine=tmp_path/'identities.json'
    m.write_new(quarantine,{'circuits':{c:{'excluded_ids':[]} for c in ('ATP','WTA')}})
    qpath=tmp_path/'quality.json';qpath.write_text('{}')
    q=dict(created_at='2026-10-19T16:00:00Z',evaluation_start='2026-10-20T00:00:00Z',
        evaluation_end='2027-07-01T00:00:00Z',artifacts={},data_root=str(tmp_path),identity_review_path=str(quarantine))
    monkeypatch.setattr(m,'load_quality',lambda _:q)
    monkeypatch.setattr(m,'ServeModel',lambda *a,**kw:SimpleNamespace(names={'A':'Alice Example','B':'Bea Example'},
        predict=lambda *a,**kw:dict(p=.62,q=.62,unknown_effects=0)))
    event=dict(id='api_tennis:1',sport_key='tennis_atp_api_1',home_team='Alice Example',away_team='Bea Example',commence_time='2026-10-20T12:00:00Z')
    fixture=dict(event_id=event['id'],sport_key=event['sport_key'],status='scheduled',actual_start=None,
        participants=['Alice Example','Bea Example'],participants_verified=True,provider_time_reconciled=True,
        provider_commence_time=event['commence_time'],source_kind='official_order_of_play',
        official_not_before=event['commence_time'],observed_at='2026-10-19T17:58:00Z',source_url='https://protennislive.com/op.pdf',
        source_path=str(source),source_sha256=m.digest(source),evidence='reviewed exact singles pair',
        calendar_source_path=str(calendar),calendar_source_sha256=m.digest(calendar),calendar_received_at='2026-10-19T17:58:00Z',
        review_path=str(review),review_sha256=m.digest(review))
    parent=dict(event=event,circuit='ATP',player_ids=['A','B'],competition_id='ATP:1:2026',
        sealed_at='2026-10-19T17:59:00Z',variants={'model_probability':.5},artifacts={},protocol_sha256=m.digest(qpath),
        fixture_receipt=fixture,tournament_metadata=dict(metadata_verified=True,surface='Hard',best_of=3,deciding_tiebreak=7,
            source_url=fixture['source_url'],valid_from='2026-10-20',valid_to='2026-10-20'))
    parents=tmp_path/'parents';parentpath=parents/('x'*64+'.json')
    m.write_new(parentpath,dict(parent,payload_sha256=m.checksum(parent)))
    protocol=tmp_path/'protocol.json';m.freeze(protocol,qpath)
    preds=tmp_path/'predictions';preds.mkdir()
    results=tmp_path/'results.json';m.write_new(results,[])
    return SimpleNamespace(clock=clock,protocol=protocol,parent=parentpath,parents=parents,predictions=preds,results=results,root=tmp_path)


def make_result(s, **changes):
    source=s.root/'result_source.json';source.write_text('official completed score')
    r=dict(event_id='api_tennis:1',sport_key='tennis_atp_api_1',home_team='Alice Example',away_team='Bea Example',
        status='completed',actual_start='2026-10-20T12:03:00Z',actual_end='2026-10-20T14:00:00Z',
        received_at='2026-10-20T14:01:00Z',best_of=3,completed_sets=2,score_A_B='6-4 6-4',official_winner='Alice Example',
        source_path=str(source),source_sha256=m.digest(source))
    r.update(changes)
    s.results.write_text(json.dumps([r]))
    s.clock[0]='2026-10-20T14:02:00Z'
    return r


@pytest.mark.parametrize('best_of',[3,5])
def test_board_covers_ten_families_and_score_is_single_vector(best_of):
    rows=forecast_board(MarketEngine(.64,.60,Rules(best_of)))
    assert {r['contract']['kind'] for r in rows}==KINDS
    vector=[r for r in rows if r['contract']['kind']=='correct_score']
    assert len(vector)==1
    assert len(vector[0]['probabilities'])==2*(best_of//2+1)
    assert len({m.key(r['contract']) for r in rows})==len(rows)
    for row in rows:validate_mass(row['probabilities'])


@pytest.mark.parametrize('contract,expected',[
    (dict(kind='set_winner',selection='A',set_number=3),'push'),
    (dict(kind='games_total',selection='over',line=20),'push'),
    (dict(kind='games_total',selection='over',line=19.5),'win'),
    (dict(kind='sets_handicap',selection='A',line=-1.5),'win'),
    (dict(kind='tiebreak',selection='yes'),'loss'),
    (dict(kind='correct_score',selection='vector'),'2-0'),
])
def test_observable_outcomes_without_inventing_odds(contract,expected):
    assert outcome(contract,dict(status='completed',score_A_B='6-4 6-4',best_of=3,completed_sets=2))==expected


def test_retirement_is_retained_outside_completed_probability_contract():
    assert outcome(dict(kind='winner',selection='A'),dict(status='retired'))=='outside_completed_contract'


def test_new_markets_have_new_timestamp_and_no_old_external_stamp(study):
    path=m.seal(study.protocol,study.parent,study.predictions)
    value=m.read(path)
    assert value['sealed_at']>value['parent_winner_sealed_at']
    assert not value['externally_timestamped']
    assert m.read(study.parent)['sealed_at']=='2026-10-19T17:59:00Z'
    with pytest.raises(FileExistsError):m.seal(study.protocol,study.parent,study.predictions)


def test_pending_events_are_reported_for_all_ten_families(study):
    m.seal(study.protocol,study.parent,study.predictions)
    report=m.evaluate(study.protocol,study.predictions,study.results)
    assert report['unique_events']==1
    assert set(report['market_families'])==KINDS
    assert all(g['evaluated']==0 and g['pending']==1 and g['coverage']==0 for g in report['groups'])
    assert not any(g['eligible_for_independent_review'] for g in report['groups'])


def test_completed_score_scores_once_per_exact_contract(study):
    m.seal(study.protocol,study.parent,study.predictions)
    make_result(study)
    report=m.evaluate(study.protocol,study.predictions,study.results)
    assert report['unique_events']==1 and not report['rejected_records']
    vector=[g for g in report['groups'] if g['contract']['kind']=='correct_score']
    assert len(vector)==1 and vector[0]['evaluated']==1
    assert vector[0]['proper_vector_log_loss']>0 and vector[0]['conditional_binary_metrics'] is None
    third=[g for g in report['groups'] if g['contract'].get('set_number')==3]
    assert all(g['pushes']==1 and g['conditional_binary_metrics'] is None for g in third)


@pytest.mark.parametrize('change', ['missing_time','wrong_identity','after_start','changed_source','duplicate'])
def test_invalid_result_evidence_never_scores(study,change):
    m.seal(study.protocol,study.parent,study.predictions)
    r=make_result(study)
    if change=='missing_time':r['actual_start']=None
    if change=='wrong_identity':r['home_team']='Another Player'
    if change=='after_start':r['actual_start']='2026-10-19T17:59:30Z'
    if change=='changed_source':Path(r['source_path']).write_text('altered')
    study.results.write_text(json.dumps([r,r] if change=='duplicate' else [r]))
    if change=='duplicate':
        with pytest.raises(ValueError,match='unique'):m.evaluate(study.protocol,study.predictions,study.results)
    else:
        report=m.evaluate(study.protocol,study.predictions,study.results)
        assert report['unique_events']==1 and report['rejected_results']
        assert all(g['registered']==1 and g['evaluated']==0 and g['coverage']==0 for g in report['groups'])


def test_four_hour_extension_never_bypasses_official_earliest(study):
    study.clock[0]='2026-10-19T21:59:00Z'
    with pytest.raises(ValueError,match='window'):m.seal(study.protocol,study.parent,study.predictions)
    study.clock[0]='2026-10-20T12:00:00Z'
    with pytest.raises(ValueError):m.seal(study.protocol,study.parent,study.predictions)


def test_record_tamper_and_board_truncation_rejected(study):
    path=m.seal(study.protocol,study.parent,study.predictions)
    v=m.read(path);v.pop('payload_sha256');v['rows'].pop()
    path.write_text(json.dumps(dict(v,payload_sha256=m.checksum(v))))
    report=m.evaluate(study.protocol,study.predictions,study.results)
    assert report['unique_events']==0 and report['rejected_records']


def test_frozen_study_code_hash_mismatch_is_rejected(study):
    p=m.read(study.protocol);p['code_sha256'][next(iter(p['code_sha256']))]='0'*64
    study.protocol.write_text(json.dumps(p))
    with pytest.raises(ValueError,match='code changed'):m.load(study.protocol)


def test_future_protocol_cannot_be_backdated(study):
    study.clock[0]='2026-10-20T00:00:00Z'
    with pytest.raises(ValueError,match='future interval'):m.freeze(study.root/'late_protocol.json',study.root/'quality.json')


@pytest.mark.parametrize('status',['retired','walkover'])
def test_noncompleted_events_stay_in_coverage_without_fabricated_losses(study,status):
    m.seal(study.protocol,study.parent,study.predictions)
    changes=dict(status=status,completed_sets=0)
    if status=='walkover':changes.update(actual_start=None,actual_end=None)
    make_result(study,**changes)
    report=m.evaluate(study.protocol,study.predictions,study.results)
    assert report['unique_events']==1 and not report['rejected_results']
    assert all(g['outside_completed_contract']==1 and g['evaluated']==0 and g['registered']==1 for g in report['groups'])


def test_locally_rehashed_probabilities_must_still_reproduce(study):
    path=m.seal(study.protocol,study.parent,study.predictions)
    v=m.read(path);v.pop('payload_sha256');v['rows'][0]['probabilities']=dict(win=.8,push=0,loss=.2)
    path.write_text(json.dumps(dict(v,payload_sha256=m.checksum(v))))
    report=m.evaluate(study.protocol,study.predictions,study.results)
    assert report['unique_events']==0 and 'reproduce' in report['rejected_records'][0]['reason']


def test_repeated_cycle_deduplicates_by_event_not_parent_filename(study):
    assert m.run_seals(study.protocol,study.parents,study.predictions)['statuses']=={'sealed':1}
    assert m.run_seals(study.protocol,study.parents,study.predictions)['statuses']=={'already_sealed':1}
