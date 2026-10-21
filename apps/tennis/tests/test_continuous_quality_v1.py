"""Artificial API replies only: no real credentials or provider requests."""
import json,sqlite3
from pathlib import Path
from types import SimpleNamespace
import pytest
from tennis_continuous_v1.capture import CycleStore,credential,capture
from tennis_continuous_v1.review import abbreviation_matches
from tennis_engine.paper_validation import digest
from tennis_engine.state_capture import TennisStateCapture


def test_four_hour_claim_is_atomic_across_two_connections(tmp_path):
    a,b=CycleStore(tmp_path),CycleStore(tmp_path)
    assert a.claim('2026-10-20T00:00:00Z')[0]
    assert b.claim('2026-10-20T00:01:00Z')==(None,'capture_not_due')
    assert a.claim('2026-10-20T03:59:59Z')==(None,'capture_not_due')
    assert b.claim('2026-10-20T04:00:00Z')[0]


def test_failed_cycle_claim_is_not_released_to_repeat_calls(tmp_path):
    a=CycleStore(tmp_path);identity,_=a.claim('2026-10-20T00:00:00Z')
    with pytest.raises(sqlite3.IntegrityError):a.db.execute('DELETE FROM cycles WHERE id=?',(identity,))
    a.db.rollback()
    assert a.claim('2026-10-20T01:00:00Z')[1]=='capture_not_due'


def test_provider_backoff_survives_new_process_and_clock_offset(tmp_path):
    a=CycleStore(tmp_path);identity,_=a.claim('2026-10-20T00:00:00Z')
    a.finish(identity,tmp_path/'report.json','2026-10-21T00:00:00Z');a.db.close()
    b=CycleStore(tmp_path)
    assert b.claim('2026-10-20T23:00:00Z')==(None,'provider_backoff')
    assert b.claim('2026-10-21T00:00:00Z')[0]


def test_calendar_abbreviation_requires_full_given_initials_and_exact_surname():
    assert abbreviation_matches('C. Alcaraz','Carlos Alcaraz')
    assert abbreviation_matches('Carlos Alcaraz','Carlos Alcaraz')
    assert abbreviation_matches('J-L. Struff','Jan-Lennard Struff')
    assert not abbreviation_matches('C. Alcaraz','Carlos Alcaraz Garfia')
    assert not abbreviation_matches('J. Smith','John Paul Smith')


def test_only_dedicated_credential_name_is_used(tmp_path):
    p=tmp_path/'private.env';p.write_text('OTHER_KEY=unused\nAPI_TENNIS_KEY="synthetic-test-value"\n')
    assert credential(p)=='synthetic-test-value'
    p.write_text('OTHER_KEY=unused\n')
    with pytest.raises(ValueError):credential(p)


@pytest.mark.parametrize('status',[401,403,429])
def test_auth_or_rate_limit_stops_second_tour_and_blocks_repeated_requests(tmp_path,monkeypatch,status):
    import importlib
    module=importlib.import_module('tennis_continuous_v1.capture')
    key=tmp_path/'key.env';key.write_text('API_TENNIS_KEY=synthetic-test-value\n')
    protocol=tmp_path/'protocol.json';protocol.write_text('{}')
    config=tmp_path/'config.json';config.write_text(json.dumps(dict(root=str(tmp_path/'run'),credential_file=str(key),
        quality_protocol=str(protocol),quality_protocol_sha256=digest(protocol),official_sources={})))
    monkeypatch.setattr(module,'load',lambda p:dict(evaluation_end='2099-01-01T00:00:00Z'))
    monkeypatch.setattr(module,'TennisStateCapture',lambda root,key,daily_limit:TennisStateCapture(root,key,daily_limit,
        transport=lambda *a,**k:SimpleNamespace(status_code=status,content=b'{"error":"synthetic-test-value"}')))
    first=capture(config)
    assert first['new_api_requests']==1 and first['valid_calendar_receipts']==0
    assert capture(config)['status']=='provider_backoff'
    originals=list((tmp_path/'run/state_capture/originals').rglob('response.json'))
    assert len(originals)==1 and b'synthetic-test-value' not in originals[0].read_bytes()


def test_changed_protocol_cannot_start_network_capture(tmp_path):
    protocol=tmp_path/'protocol.json';protocol.write_text('{}')
    config=tmp_path/'config.json';config.write_text(json.dumps(dict(quality_protocol=str(protocol),quality_protocol_sha256='0'*64)))
    with pytest.raises(ValueError,match='protocol changed'):capture(config)


def test_official_resumption_marker_prevents_new_prematch_forecast(tmp_path,monkeypatch):
    from tennis_continuous_v1 import review
    source=tmp_path/'official.pdf';source.write_bytes(b'Artificial PDF placeholder for parser guard test')
    receipt=tmp_path/'receipt.json';receipt.write_text(json.dumps(dict(accepted_document=True,http_status=200,url='https://www.protennislive.com/test.pdf',
        source_path=str(source),sha256=digest(source),received_at='2026-10-19T08:00:00Z')))
    monkeypatch.setattr(review,'PdfReader',lambda p:SimpleNamespace(pages=[SimpleNamespace(extract_text=lambda:'ORDER OF PLAY TUESDAY 20 OCTOBER 2026')]))
    monkeypatch.setattr(review,'cell_text',lambda *a:'tbf player one vs player two')
    row=dict(date='2026-10-20',players=['Player One','Player Two'],rect=[0,0,1,1],receipt_path=str(receipt),official_earliest_local='11:30')
    with pytest.raises(ValueError,match='Resumed or unfinished'):
        review.official_proof(row,dict(url='https://www.protennislive.com/test.pdf',timezone='UTC'),'2026-10-19T08:01:00Z')
