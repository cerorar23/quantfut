"""Operational guards: unavailable sources and failed witnesses stay non-actionable."""
import importlib.util
import json
from pathlib import Path

from nba.audit import Ledger,digest


def worker():
    path=Path(__file__).parents[1]/'ops/capture_worker.py'
    spec=importlib.util.spec_from_file_location('nba_capture_worker_test',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def config():
    return dict(max_total_bytes=10000000,min_free_host_bytes=0,backup_keep=2)


def fake_capture(root,url,allowed):
    root=Path(root);(root/'blobs').mkdir(parents=True,exist_ok=True)
    temporary=root/'body';temporary.write_bytes(b'<html>blocked</html>')
    hashed=digest(temporary);temporary.replace(root/'blobs'/hashed)
    result=dict(raw_sha256=hashed,http_status=200,url=url)
    Ledger(root/'receipts.sqlite').append('public_response_received',result)
    return result


def test_storage_hold_performs_no_http_or_timestamp(tmp_path,monkeypatch):
    module=worker();(tmp_path/'original').write_bytes(b'preserved')
    def forbidden(*args):raise AssertionError('external request during storage hold')
    monkeypatch.setattr(module,'capture',forbidden);monkeypatch.setattr(module,'stamp',forbidden)
    limits=config();limits['max_total_bytes']=0
    result=module.cycle(tmp_path,limits)
    assert result['state']=='storage_hold' and result['production_enabled'] is False
    assert (tmp_path/'original').read_bytes()==b'preserved'


def test_http_200_without_nba_payload_is_degraded(tmp_path,monkeypatch):
    module=worker();calls=[]
    def capture(root,url,allowed):calls.append(url);return fake_capture(root,url,allowed)
    monkeypatch.setattr(module,'capture',capture)
    monkeypatch.setattr(module,'stamp',lambda *args:dict(state='verified'))
    result=module.cycle(tmp_path,config())
    assert result['state']=='source_degraded' and result['source_valid'] is False
    assert not any('/roster' in url for url in calls)
    assert result['backup_verified'] is None and result['scheduled_events']==0
    assert result['periodic_copies'] is False and not (tmp_path/'backups').exists()
    assert result['production_enabled'] is False and result['F7_started'] is False
    assert result['paid_API_calls']==0 and result['external_messages']==0


def test_failed_anchor_not_retried_on_next_capture(tmp_path,monkeypatch):
    module=worker();attempts=[]
    monkeypatch.setattr(module,'capture',fake_capture)
    def fail(*args):attempts.append(True);raise TimeoutError('unavailable witness')
    monkeypatch.setattr(module,'stamp',fail)
    first=module.cycle(tmp_path,config());second=module.cycle(tmp_path,config())
    assert first['anchor']==dict(state='unverified',reason='TimeoutError',automatic_retry=False)
    assert second['anchor'] is None and len(attempts)==1
    assert second['contracts_verified'] is False and second['availability_verified'] is False
    state=json.loads((tmp_path/'state.json').read_bytes())
    assert state['last_anchor_attempt_epoch']>0


def valid_capture(root,url,allowed):
    root=Path(root);(root/'blobs').mkdir(parents=True,exist_ok=True)
    if '/scoreboard?' in url:body=dict(leagues=[dict(slug='nba')],events=[])
    elif '/injuries?' in url:body=dict(injuries=[])
    else:body=dict(athletes=[])
    path=root/'body';path.write_text(json.dumps(body));hashed=digest(path);path.replace(root/'blobs'/hashed)
    receipt=dict(url=url,http_status=200,raw_sha256=hashed)
    Ledger(root/'receipts.sqlite').append('public_response_received',receipt);return receipt


def test_blocked_optional_evidence_preserved_without_new_requests_or_backups(tmp_path,monkeypatch):
    module=worker();url='https://sports.caliente.mx/es_MX/Basquetbol'
    prior=fake_capture(tmp_path/'captures',url,{url})
    # Preserve an actual failure receipt separately from the success fixture.
    prior=dict(prior,http_status=403);Ledger(tmp_path/'captures/receipts.sqlite').append('public_response_received',prior)
    (tmp_path/'backups').mkdir();(tmp_path/'backups/old.tar.gz').write_bytes(b'old')
    calls=[]
    def received(*args):calls.append(args[1]);return valid_capture(*args)
    monkeypatch.setattr(module,'capture',received);monkeypatch.setattr(module,'stamp',lambda *args:dict(state='verified'))
    limits=dict(config(),quarantined_public_sources=[url])
    result=module.cycle(tmp_path,limits)
    assert result['state']=='capturing' and result['optional_source_issues'][0]['last_receipt']==prior
    assert not result['bookmaker_props_coverage_verified'] and url not in calls
    assert list((tmp_path/'backups').iterdir())==[tmp_path/'backups/old.tar.gz']
    (tmp_path/'captures/blobs'/prior['raw_sha256']).write_bytes(b'tampered')
    import pytest
    with pytest.raises(ValueError,match='evidence changed'):module.quarantined_sources(tmp_path/'captures',[url])


def test_hourly_required_failure_does_not_disappear_on_next_cycle(tmp_path,monkeypatch):
    module=worker()
    def received(root,url,allowed):
        row=valid_capture(root,url,allowed)
        return dict(row,http_status=503) if '/injuries?' in url else row
    monkeypatch.setattr(module,'capture',received);monkeypatch.setattr(module,'stamp',lambda *args:dict(state='verified'))
    assert module.cycle(tmp_path,config())['state']=='source_degraded'
    second=module.cycle(tmp_path,config())
    assert second['state']=='source_degraded' and len(second['required_sources'])==2
