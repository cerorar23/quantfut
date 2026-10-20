"""Bounded paid historical quotes. Historical snapshots are not automatically closes."""
from pathlib import Path
from uuid import uuid4
from .operations import Capture,now,utc,coverage
from .ingest import save_json


def historical_snapshot(root,key,sport,at,cap,reserve,bookmakers='pinnacle',markets='h2h,spreads,totals'):
    client=Capture(root,key,cap,reserve)
    _,catalog_receipt=client.request('sports')
    report={'requested_at':now(),'sport_key':sport,'as_of':at,'subscription':'paid_user_confirmed',
            'historical_closing_line_verified':False,'status':'not_captured',
            'catalog_receipt':catalog_receipt,'production_approved':False}
    try:
        payload,receipt=client.request(f'historical/sports/{sport}/odds',{
            'date':at,'bookmakers':bookmakers,'markets':markets,'oddsFormat':'decimal'})
        if utc(payload['timestamp'])>utc(at):raise ValueError('Provider returned a future historical timestamp')
        events=payload['data']
        if not isinstance(events,list) or any(e.get('sport_key')!=sport for e in events):raise ValueError('Historical sport mismatch')
        report.update(status='captured_research',receipt=receipt,source_timestamp=payload['timestamp'],
                      coverage=coverage(events),event_count=len(events))
    except (ValueError,RuntimeError,KeyError,TypeError):
        report['status']='blocked_or_incomplete'
        report['reason']='Budget/reserve or source validation prevented completion; inspect original receipts and quota ledger'
    report['budget']=client.budget_report(now()[:7]);client.db.close()
    target=Path(root)/('historical_'+uuid4().hex+'.json');save_json(target,report)
    return {'report_path':str(target),**report}
