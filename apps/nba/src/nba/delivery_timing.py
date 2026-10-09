"""Timing from a complete exported ledger; absent stages remain unknown."""
import hashlib
import json
import numpy as np

from .audit import canonical
from .context import utc
from .markets import number


def timing_report(rows):
    previous='0'*64
    seals,attempts,states={}, {}, {}
    durations,acks,anomalies=[],[],[]
    missing_acks=0
    evidence_kinds={'simulated':0,'unclassified':0}
    for count,row in enumerate(rows,1):
        seq,received,kind,raw_payload,prev,hashed,raw_event=row
        event=dict(seq=seq,received_at=received,kind=kind,payload=raw_payload,previous_hash=prev)
        if isinstance(seq,bool) or seq!=count or prev!=previous or raw_event!=canonical(event) or hashlib.sha256(raw_event.encode()).hexdigest()!=hashed:
            raise ValueError('complete valid delivery ledger required')
        previous=hashed
        payload=json.loads(raw_payload);identifier=payload.get('id')
        if kind=='notification_sealed_before_queue':
            if identifier in seals:raise ValueError('duplicate notification seal')
            seals[identifier]=utc(received)
        elif kind=='notification_send_attempt':
            if identifier in attempts:raise ValueError('duplicate notification intent')
            attempts[identifier]=utc(payload['attempted_at_utc'])
            if identifier not in seals or attempts[identifier]<seals[identifier]:
                anomalies.append(dict(id=identifier,reason='intent_before_or_without_seal'))
        elif kind=='notification_send_result':
            outcome=payload['outcome'];state=outcome['state']
            if state not in {'sent','rejected','unknown'}:raise ValueError('invalid transport result')
            states[state]=states.get(state,0)+1
            evidence_kinds['simulated' if outcome.get('synthetic_sender') is True else 'unclassified']+=1
            duration=number(outcome['request_duration_seconds'])
            if duration<0:raise ValueError('negative transport duration')
            durations.append(duration)
            response=utc(outcome['response_recorded_at_utc'])
            if identifier not in attempts or response<attempts[identifier]:
                anomalies.append(dict(id=identifier,reason='response_before_or_without_intent'))
            ack=outcome.get('acknowledged_at_utc') if state=='sent' else None
            if state=='sent' and ack is None:missing_acks+=1
            if ack is not None:
                acknowledged=utc(ack)
                if identifier not in seals or identifier not in attempts or not seals[identifier]<=attempts[identifier]<=acknowledged<=response:
                    anomalies.append(dict(id=identifier,reason='invalid_service_ack_time_order'))
                else:acks.append((acknowledged-seals[identifier]).total_seconds())
    def summarize(values):
        return dict(n=len(values),p50_seconds=float(np.quantile(values,.5)) if values else None,
                    p95_seconds=float(np.quantile(values,.95)) if values else None)
    return dict(ledger_events=len(rows),ledger_head=previous,recorded_intents=len(attempts),transport_result_states=states,
        transport_duration=summarize(durations),seal_to_service_ack=summarize(acks),sent_without_ack=missing_acks,
        time_order_anomalies=anomalies,evidence_kinds=evidence_kinds,
        input_receipt_and_calculation_stages_known=False,subscriber_receipt_verified=False,
        real_channel_latency_demonstrated=False,external_anchor=False)
