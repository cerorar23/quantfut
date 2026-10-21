"""Financial gates are tested with artificial records, never scored as evidence."""
import copy,json,hashlib
from pathlib import Path
import pytest
from tennis_engine.paper_validation import freeze_paper_policy,load_policy,assess_paper_event,seal_paper_order,evaluate_paper,canonical,quote_receipt_from_archive
from tennis_engine.shadow import write_immutable

DECISION='2026-10-20T08:01:00Z'

def file(tmp_path,name,data):
 p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data if isinstance(data,bytes) else json.dumps(data).encode());return p

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

@pytest.fixture
def setup(tmp_path):
 asset=file(tmp_path,'model.json',b'test fixture, not a production model')
 protocol=file(tmp_path,'model_protocol.json',dict(artifacts={str(asset):sha(asset)},required_artifact_hashes={'ATP':[sha(asset)],'WTA':[sha(asset)]}))
 policy_path=tmp_path/'policy.json';freeze_paper_policy(policy_path,protocol,'2026-10-20T00:00:00Z','2027-01-01T00:00:00Z',created_at='2026-10-19T00:00:00Z')
 event=dict(id='e1',sport_key='tennis_atp_test',home_team='A',away_team='B',commence_time='2026-10-20T10:00:00Z')
 evidence=file(tmp_path,'fixture.json',b'unit-test fixture source')
 fixture=dict(event_id='e1',status='scheduled',observed_at='2026-10-20T08:00:00Z',actual_start=None,
  participants_verified=True,provider_time_reconciled=True,source_url='https://www.atptour.com/schedule',evidence='test fixture',
  sport_key=event['sport_key'],participants=['A','B'],provider_commence_time=event['commence_time'],source_path=str(evidence),source_sha256=sha(evidence))
 row=dict(event=event,circuit='ATP',identities={'identities_verified':True},fixture_receipt=fixture,
  tournament_metadata=dict(surface='Hard',best_of=3,deciding_tiebreak=7,metadata_verified=True,source_url='https://www.atptour.com/rules',valid_from='2026-10-01',valid_to='2026-10-31'),
  prediction=dict(winner_A=.6,winner_B=.4,cutoff='2026-10-16'),artifact_sha256={str(asset):sha(asset)})
 payload=dict(observed_at='2026-10-20T08:00:00Z',prediction_sealed_at='2026-10-20T08:00:00Z',events=[row])
 record=write_immutable(tmp_path,payload)
 quote=make_quote(tmp_path,event,'entry','2026-10-20T08:00:01Z','2026-10-20T08:00:02Z','2026-10-20T08:00:00Z',2.2,1.8)
 return dict(root=tmp_path,asset=asset,policy_path=policy_path,policy=load_policy(policy_path),row=row,record=record,quote=quote,event=event)

def make_quote(root,event,name,requested,received,updated,a,b):
 body=copy.deepcopy(event);body['bookmakers']=[dict(key='pinnacle',last_update=updated,markets=[dict(key='h2h',outcomes=[dict(name='A',price=a),dict(name='B',price=b)])])]
 p=file(root,name+'/response.json',body)
 receipt=file(root,name+'/receipt.json',dict(path='sports/'+event['sport_key']+'/events/'+event['id']+'/odds',sha256=sha(p),requested_at=requested,received_at=received))
 return quote_receipt_from_archive(receipt)

def results(s,status='completed',sets=2,winner='A'):
 evidence=file(s['root'],'result_source.json',b'unit test result source')
 r=dict(event_id='e1',home_team='A',away_team='B',sport_key=s['event']['sport_key'],status=status,completed_sets=sets,official_winner=winner,
  actual_start='2026-10-20T10:00:00Z',actual_end='2026-10-20T11:00:00Z',received_at='2026-10-20T11:05:00Z',score_A_B='6-4 6-4',best_of=3,source_path=str(evidence),source_sha256=sha(evidence))
 return file(s['root'],'results.json',[r])

def seal(s):return seal_paper_order(s['root']/'orders',s['record'],'e1','A',s['quote'],s['policy_path'],decision_at=DECISION)

def test_unused_missing_climate_and_fatigue_do_not_block_frozen_baseline(setup):
 r=assess_paper_event(setup['row'],setup['quote'],DECISION,setup['policy'],'A')
 assert r['paper_eligible'] and not r['real_money_eligible'] and not r['actual_execution_verified']

@pytest.mark.parametrize('mutation',[lambda s:s['quote'].update(received_at='2026-10-20T08:02:00Z'),lambda s:s['row']['identities'].update(identities_verified=False),lambda s:s['row']['fixture_receipt'].update(status='playing'),lambda s:s['row']['prediction'].update(winner_A=.7),lambda s:s['row']['artifact_sha256'].clear()])
def test_technical_gates_reject_future_quotes_identity_started_match_and_model_mismatch(setup,mutation):
 mutation(setup);assert not assess_paper_event(setup['row'],setup['quote'],DECISION,setup['policy'],'A')['paper_eligible']

def test_changed_raw_odds_and_duplicate_orders_are_rejected(setup):
 seal(setup)
 with pytest.raises(FileExistsError):seal(setup)
 Path(setup['quote']['source_path']).write_bytes(b'{}')
 with pytest.raises(ValueError):seal(setup)

def test_empty_future_study_is_unavailable_not_zero_loss_or_profit(setup):
 p=file(setup['root'],'empty_results.json',[]);r=evaluate_paper(setup['policy_path'],setup['root']/'orders',p,as_of='2026-10-21T00:00:00Z')
 assert r['status']=='insufficient_prospective_financial_evidence' and r['by_circuit']['ATP']['net_paper_roi'] is None
 assert not r['production_approved']

def test_win_is_paper_only_and_missing_close_or_small_sample_cannot_approve(setup):
 seal(setup);r=evaluate_paper(setup['policy_path'],setup['root']/'orders',results(setup),as_of='2026-10-20T12:00:00Z')
 assert r['by_circuit']['ATP']['net_paper_roi']==pytest.approx(1.2)
 assert r['by_circuit']['ATP']['closing_coverage']==0 and not r['by_circuit']['ATP']['predeclared_evidence_gate']
 assert not r['actual_execution_verified'] and not r['production_approved']

@pytest.mark.parametrize('sets,profit,expected',[(0,0.,'void'),(1,1.2,'win')])
def test_retirements_are_retained_and_apply_verified_set_rule(setup,sets,profit,expected):
 seal(setup);r=evaluate_paper(setup['policy_path'],setup['root']/'orders',results(setup,'retired',sets),as_of='2026-10-20T12:00:00Z')
 assert r['rows'][0]['status']==expected and r['rows'][0]['net_profit']==pytest.approx(profit)
 assert r['by_circuit']['ATP']['settled']==1 and not r['by_circuit']['ATP']['retirements_excluded']

def test_result_with_unknown_winner_cannot_be_mapped_to_player_b(setup):
 seal(setup);r=evaluate_paper(setup['policy_path'],setup['root']/'orders',results(setup,'retired',1,'unknown'),as_of='2026-10-20T12:00:00Z')
 assert r['rows'][0]['net_profit'] is None and r['rejected']['invalid_result_or_close_evidence']==1

def test_rehashed_forged_price_is_detected_against_original_quote(setup):
 p=seal(setup);d=json.loads(p.read_text());d.pop('payload_sha256');d['decimal_odds']=100.;d['payload_sha256']=hashlib.sha256(canonical(d)).hexdigest();p.write_text(json.dumps(d))
 r=evaluate_paper(setup['policy_path'],setup['root']/'orders',results(setup),as_of='2026-10-20T12:00:00Z')
 assert r['valid_orders']==0 and r['rejected']['invalid_order_evidence']==1

def test_fresh_archived_close_reconstructs_no_vig_reference(setup):
 seal(setup);q=make_quote(setup['root'],setup['event'],'closing','2026-10-20T09:55:00Z','2026-10-20T09:55:01Z','2026-10-20T09:54:00Z',1.8,2.1)
 r=evaluate_paper(setup['policy_path'],setup['root']/'orders',results(setup),closings=[dict(event_id='e1',receipt=q)],as_of='2026-10-20T12:00:00Z')
 assert r['by_circuit']['ATP']['closing_coverage']==1 and r['rows'][0]['clv_units']>0
 assert not r['by_circuit']['ATP']['predeclared_evidence_gate']

def test_late_result_and_changed_model_remain_blocked(setup):
 seal(setup);r=evaluate_paper(setup['policy_path'],setup['root']/'orders',results(setup),as_of='2026-10-20T11:01:00Z')
 assert r['rows'][0]['net_profit'] is None
 setup['asset'].write_bytes(b'changed');r=evaluate_paper(setup['policy_path'],setup['root']/'orders',results(setup),as_of='2026-10-20T12:00:00Z')
 assert r['valid_orders']==0 and not r['production_approved']


def test_active_code_cannot_be_certified_using_an_unrelated_path(setup):
 d=json.loads(setup['policy_path'].read_text());value=d['candidate_code_sha256'].pop('weather.py');d['candidate_code_sha256']['other/weather.py']=value;setup['policy_path'].write_text(json.dumps(d))
 with pytest.raises(ValueError,match='active candidate'):load_policy(setup['policy_path'])

def test_probability_metrics_compare_same_time_market_and_study_remains_provisional(setup):
 seal(setup);r=evaluate_paper(setup['policy_path'],setup['root']/'orders',results(setup),as_of='2026-10-20T12:00:00Z')
 assert r['by_circuit']['ATP']['completed_match_probability_metrics']['model']['n']==1
 assert r['by_circuit']['ATP']['completed_match_probability_metrics']['same_time_no_vig_market']['n']==1
 assert not r['evaluation_period_complete'] and not r['by_circuit']['ATP']['predeclared_evidence_gate']


def test_adequate_mock_evidence_cannot_end_study_early(setup,monkeypatch):
 # Artificial scaled-down policy and interval isolate the optional-stopping gate.
 import tennis_engine.paper_validation as module
 d=json.loads(setup['policy_path'].read_text());d['minimum_events_per_circuit']=1;d['minimum_competitions_per_circuit']=1;setup['policy_path'].write_text(json.dumps(d));setup['policy']=load_policy(setup['policy_path'])
 seal(setup);q=make_quote(setup['root'],setup['event'],'closing','2026-10-20T09:55:00Z','2026-10-20T09:55:01Z','2026-10-20T09:54:00Z',1.8,2.1)
 monkeypatch.setattr(module,'_interval',lambda *args:[.1,.2])
 kwargs=dict(closings=[dict(event_id='e1',receipt=q)])
 before=evaluate_paper(setup['policy_path'],setup['root']/'orders',results(setup),as_of='2026-10-20T12:00:00Z',**kwargs)
 after=evaluate_paper(setup['policy_path'],setup['root']/'orders',results(setup),as_of='2027-01-02T12:00:00Z',**kwargs)
 assert not before['by_circuit']['ATP']['predeclared_evidence_gate']
 assert after['by_circuit']['ATP']['predeclared_evidence_gate']
 assert not after['production_approved'] and not after['actual_execution_verified']
