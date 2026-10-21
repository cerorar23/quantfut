"""Artificial evidence exercises rejection paths; never real financial results."""
import json
from pathlib import Path
import pytest
from test_paper_validation import setup, file, sha, seal, results, make_quote
from tennis_finance_v2.audit import audit, cost_sensitivity, quote_inventory, sample_planning, write_new


def config(s):
    (s['root']/'orders').mkdir(exist_ok=True)
    p=file(s['root'],'empty.json',[])
    return file(s['root'],'audit-config.json',dict(policy_path=str(s['policy_path']),
        policy_sha256=sha(s['policy_path']), orders_root=str(s['root']/'orders'),
        results_path=str(p), closings_path=str(p), snapshot_roots=[], shadow_roots=[]))


def test_empty_study_returns_unknown_roi_and_explicit_future_blockers(setup):
    r=audit(config(setup),as_of='2026-10-19T12:00:00Z')
    assert not r['profitability_accredited'] and not r['paper_study_gate_passed']
    assert 'financial_period_not_started' in r['blockers']
    assert r['financial_report']['by_circuit']['ATP']['net_paper_roi'] is None
    assert r['cost_sensitivity_by_circuit']['ATP'][0]['full_ledger_net_roi'] is None


def test_missing_order_directory_cannot_look_like_a_valid_empty_study(setup):
    path=config(setup);d=json.loads(path.read_text());d['orders_root']=str(setup['root']/'wrong-directory');path.write_text(json.dumps(d))
    with pytest.raises(ValueError,match='ledger is absent'):audit(path)


def test_positive_paper_return_is_not_real_execution_or_accreditation(setup):
    seal(setup);path=config(setup);d=json.loads(path.read_text());d['results_path']=str(results(setup));path.write_text(json.dumps(d))
    r=audit(path,as_of='2026-10-20T12:00:00Z')
    assert r['financial_report']['by_circuit']['ATP']['net_paper_roi']==pytest.approx(1.2)
    assert not r['real_money_approved'] and not r['profitability_accredited']
    assert r['cost_sensitivity_by_circuit']['ATP'][-1]['full_ledger_net_roi']==pytest.approx(1.18)
    assert 'ATP:incomplete_closing_coverage' in r['blockers']


def test_policy_and_model_changes_are_detected_even_without_any_orders(setup):
    path=config(setup);setup['asset'].write_bytes(b'changed')
    with pytest.raises(ValueError,match='artifact changed'):audit(path)


def test_policy_rewrite_is_rejected_by_external_configuration(setup):
    path=config(setup);d=json.loads(setup['policy_path'].read_text());d['minimum_events_per_circuit']=1;setup['policy_path'].write_text(json.dumps(d))
    with pytest.raises(ValueError,match='policy changed'):audit(path)


def test_snapshots_not_bets_and_duplicate_roots_do_not_inflate_inventory(setup):
    root=Path(setup['quote']['source_path']).parent
    r=quote_inventory([root,root], '2026-10-20T08:01:00Z')
    assert r['verified_odds_responses']==1 and r['distinct_event_ids']==1
    assert r['raw_outcome_observations']==2 and r['observations_are_not_bets']
    assert r['fresh_observations']==2


def test_repeated_quotes_enlarge_observations_but_not_independent_events(setup):
    make_quote(setup['root'],setup['event'],'entry2','2026-10-20T08:00:03Z','2026-10-20T08:00:04Z','2026-10-20T08:00:00Z',2.2,1.8)
    r=quote_inventory([setup['root']], '2026-10-20T08:01:00Z')
    assert r['raw_outcome_observations']==4 and r['distinct_event_ids']==1


def test_changed_archive_and_late_receipts_cannot_enter_valid_inventory(setup):
    root=Path(setup['quote']['source_path']).parent
    r=quote_inventory([root], '2026-10-20T07:00:00Z')
    assert not r['verified_odds_responses'] and r['errors']['not_available_as_of']==1
    Path(setup['quote']['source_path']).write_text('{}')
    r=quote_inventory([root], '2026-10-20T08:01:00Z')
    assert not r['verified_odds_responses'] and r['errors']['invalid_archive']==1


def test_stale_or_already_started_quotes_are_not_fresh(setup):
    root=Path(setup['quote']['source_path']).parent
    assert quote_inventory([root], '2026-10-20T10:00:00Z')['fresh_observations']==0


def test_pending_and_voids_stay_in_full_ledger_costs():
    rows=[dict(stake=1.,net_profit=1.),dict(stake=1.,net_profit=0.)]
    assert cost_sensitivity(rows)[-1]['full_ledger_net_roi']==pytest.approx(.48)
    rows.append(dict(stake=1.,net_profit=None))
    assert all(r['full_ledger_net_roi'] is None and r['pending']==1 for r in cost_sensitivity(rows))


@pytest.mark.parametrize('stake,profit',[(float('nan'),1.),(True,1.),(-1.,1.),(1.,float('inf'))])
def test_invalid_money_is_not_accepted(stake,profit):
    with pytest.raises(ValueError):cost_sensitivity([dict(stake=stake,net_profit=profit)])


def test_sample_illustration_is_not_a_change_to_frozen_minimum():
    rows=sample_planning()
    assert rows[0]['approximate_independent_orders']>rows[-1]['approximate_independent_orders']>500
    assert all(r['frozen_policy_unchanged'] for r in rows)


def test_reports_cannot_overwrite_earlier_evidence(tmp_path):
    p=tmp_path/'report.json';write_new(p,dict(status='unknown'))
    with pytest.raises(FileExistsError):write_new(p,dict(status='profitable'))


def test_timestamp_bundle_edit_is_rejected_before_any_verification(tmp_path):
    from tennis_finance_v2.timestamp import verify_timestamp
    bundle=file(tmp_path,'bundle.json',dict(policy='original'))
    file(tmp_path,'receipt.json',dict(sha256={'bundle.json':sha(bundle)}))
    bundle.write_text('changed')
    with pytest.raises(ValueError,match='proof file changed'):
        verify_timestamp(tmp_path,Path('unused-openssl'))


def test_timestamp_receipt_cannot_select_paths_outside_proof_directory(tmp_path):
    from tennis_finance_v2.timestamp import verify_timestamp
    file(tmp_path,'receipt.json',dict(sha256={'../different-policy.json':'0'*64}))
    with pytest.raises(ValueError,match='proof file changed'):
        verify_timestamp(tmp_path,Path('unused-openssl'))
