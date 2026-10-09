import hashlib
import pytest
from nba.audit import canonical
from nba.delivery_timing import timing_report

NOW='2026-10-08T12:00:00Z'


def events(result=None,attempt='2026-10-08T12:00:01Z'):
    payloads=[('notification_sealed_before_queue',dict(id='test',payload={'kind':'operational_test'})),
        ('notification_send_attempt',dict(id='test',attempted_at_utc=attempt))]
    if result is not None:payloads.append(('notification_send_result',dict(id='test',outcome=result)))
    rows=[];previous='0'*64
    for seq,(kind,payload) in enumerate(payloads,1):
        event=dict(seq=seq,received_at=NOW,kind=kind,payload=canonical(payload),previous_hash=previous)
        raw=canonical(event);hashed=hashlib.sha256(raw.encode()).hexdigest()
        rows.append((seq,NOW,kind,event['payload'],previous,hashed,raw));previous=hashed
    return rows


def outcome(**changes):
    return dict(dict(state='sent',request_duration_seconds=.5,response_recorded_at_utc='2026-10-08T12:00:02Z',
        acknowledged_at_utc='2026-10-08T12:00:01.5Z',synthetic_sender=True),**changes)


def test_missing_ack_is_not_zero_latency():
    r=timing_report(events(outcome(acknowledged_at_utc=None)))
    assert r['sent_without_ack']==1 and r['seal_to_service_ack']['p95_seconds'] is None


def test_actual_timeline_arithmetic_but_no_real_channel_claim():
    r=timing_report(events(outcome()))
    assert r['seal_to_service_ack']==dict(n=1,p50_seconds=1.5,p95_seconds=1.5)
    assert r['transport_duration']['p50_seconds']==.5
    assert not r['real_channel_latency_demonstrated'] and not r['subscriber_receipt_verified']


@pytest.mark.parametrize('change',[dict(acknowledged_at_utc='2026-10-08T12:00:00.5Z'),
    dict(acknowledged_at_utc='2026-10-08T12:00:03Z'),dict(response_recorded_at_utc='2026-10-08T11:59:59Z')])
def test_invalid_clock_order_excluded_from_ack_metrics(change):
    r=timing_report(events(outcome(**change)))
    assert r['time_order_anomalies'] and r['seal_to_service_ack']['n']==0


@pytest.mark.parametrize('value',[-1,float('nan'),True])
def test_invalid_duration_rejected(value):
    if value!=value:
        with pytest.raises(ValueError):events(outcome(request_duration_seconds=value))
    else:
        with pytest.raises(ValueError):timing_report(events(outcome(request_duration_seconds=value)))


def test_partial_or_changed_ledger_rejected():
    rows=events(outcome())
    with pytest.raises(ValueError):timing_report(rows[1:])
    changed=list(rows[0]);changed[3]='{}';rows[0]=changed
    with pytest.raises(ValueError):timing_report(rows)


def test_queued_or_interrupted_message_does_not_generate_a_result():
    r=timing_report(events())
    assert r['recorded_intents']==1 and r['transport_duration']['n']==0 and r['seal_to_service_ack']['n']==0


@pytest.mark.parametrize('state',['unknown','rejected'])
def test_failure_has_no_service_ack_even_if_field_present(state):
    r=timing_report(events(outcome(state=state)))
    assert r['seal_to_service_ack']['n']==0 and r['transport_result_states']=={state:1}
