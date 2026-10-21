"""Shared append-only capture ledger. No odds requests or betting endpoints."""
from collections import Counter
from datetime import timedelta
from pathlib import Path
import hashlib,json,sqlite3
from uuid import uuid4
import requests
from pypdf import PdfReader
from tennis_engine.operations import now,utc
from tennis_engine.state_capture import TennisStateCapture
from tennis_engine.paper_validation import digest
from tennis_quality_v3.prospective import read,write_new,load


class CycleStore:
    """Atomic 4h claims survive failed requests and competing scheduler runs."""
    def __init__(self,root):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.root/'cycles.sqlite',timeout=30)
        self.db.execute('CREATE TABLE IF NOT EXISTS cycles(id TEXT PRIMARY KEY,started_at TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS cycle_results(id TEXT PRIMARY KEY REFERENCES cycles(id),report_path TEXT NOT NULL,blocked_until TEXT)')
        for table in ('cycles','cycle_results'):
            for action in ('UPDATE','DELETE'):
                self.db.execute(f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{action} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'append-only cycle'); END")
        self.db.commit()

    def claim(self,stamp):
        at=utc(stamp);self.db.execute('BEGIN IMMEDIATE')
        try:
            last=self.db.execute('SELECT started_at FROM cycles ORDER BY started_at DESC LIMIT 1').fetchone()
            blocked=self.db.execute('SELECT blocked_until FROM cycle_results WHERE blocked_until IS NOT NULL ORDER BY blocked_until DESC LIMIT 1').fetchone()
            if blocked and at<utc(blocked[0]):self.db.rollback();return None,'provider_backoff'
            if last and at<utc(last[0])+timedelta(hours=4):self.db.rollback();return None,'capture_not_due'
            identity=uuid4().hex;self.db.execute('INSERT INTO cycles VALUES(?,?)',(identity,at.isoformat()));self.db.commit()
            return identity,None
        except Exception:
            self.db.rollback();raise

    def finish(self,identity,path,blocked_until=None):
        with self.db:self.db.execute('INSERT INTO cycle_results VALUES(?,?,?)',(identity,str(Path(path).resolve()),blocked_until))


def credential(path):
    """Only return the dedicated API-Tennis key; never serialize or print it."""
    values={}
    for line in Path(path).read_text(encoding='utf8').splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            name,value=line.strip().split('=',1);values[name]=value.strip().strip('"').strip("'")
    value=values.get('API_TENNIS_KEY')
    if not value:raise ValueError('Dedicated API-Tennis credential unavailable')
    return value


def public_source(root,label,spec):
    folder=Path(root)/label;folder.mkdir(parents=True,exist_ok=False)
    receipt=dict(label=label,url=spec['url'],requested_at=now(),accepted_document=False)
    try:
        url=spec['url']
        if not (url.startswith('https://www.protennislive.com/posting/') or url.startswith('https://wtafiles.wtatennis.com/pdf/draws/')):
            raise ValueError('Unreviewed official document authority')
        response=requests.get(url,timeout=(10,35),allow_redirects=False)
        receipt.update(received_at=now(),http_status=response.status_code)
        raw=response.content
        if len(raw)>5000000:raise ValueError('Document exceeds acquisition bound')
        path=folder/('source.pdf' if raw.startswith(b'%PDF') else 'source.html');path.write_bytes(raw)
        receipt.update(source_path=str(path.resolve()),sha256=hashlib.sha256(raw).hexdigest())
        if response.status_code==200 and raw.startswith(b'%PDF'):
            pdf=PdfReader(path)
            if len(pdf.pages)!=1:raise ValueError('Unreviewed multipage schedule')
            (folder/'source.txt').write_text(pdf.pages[0].extract_text(extraction_mode='layout'),encoding='utf8')
            receipt.update(accepted_document=True,pages=1)
    except Exception as error:
        receipt.update(error_type=type(error).__name__,received_at=now())
    write_new(folder/'receipt.json',receipt)
    return receipt


def capture(config_path):
    config=read(config_path)
    if digest(config['quality_protocol'])!=config['quality_protocol_sha256']:raise ValueError('Configured quality protocol changed')
    protocol=load(config['quality_protocol']);stamp=now()
    if utc(stamp)>=utc(protocol['evaluation_end']):
        return dict(status='evaluation_window_closed',new_api_requests=0,new_odds_credits=0)
    cycles=CycleStore(config['root']);identity,reason=cycles.claim(stamp)
    if reason:
        cycles.db.close()
        return dict(status=reason,new_api_requests=0,new_odds_credits=0)
    folder=Path(config['root'])/'cycles'/identity;folder.mkdir(parents=True,exist_ok=False)
    report=dict(schema='tennis-continuous-capture-v1',cycle_id=identity,started_at=stamp,
        new_api_requests=0,new_odds_credits=0,actual_bets=0,provider_quota_confirmed=False,
        local_api_requests_per_day_limit=12,minimum_cycle_interval_hours=4,api_receipts=[],errors=[])
    blocked=None
    try:
        client=TennisStateCapture(Path(config['root'])/'state_capture',credential(config['credential_file']),daily_limit=12)
        day=utc(stamp).date()
        for tour in ('265','266'):
            before=client.store.db.execute('SELECT count(*) FROM requests').fetchone()[0]
            try:
                result=client.capture('get_fixtures',dict(date_start=(day-timedelta(days=1)).isoformat(),
                    date_stop=(day+timedelta(days=2)).isoformat(),event_type_key=tour,timezone='UTC'))
                report['api_receipts'].append(result['receipt'])
            except (RuntimeError,ValueError,OSError):
                report['errors'].append(dict(tour=tour,reason='api_capture_failed_or_daily_cap_reached'))
                latest=client.store.db.execute('SELECT id FROM requests ORDER BY requested_at DESC LIMIT 1').fetchone()
                receipt_path=Path(config['root'])/'state_capture/originals'/latest[0]/'receipt.json' if latest else None
                if receipt_path and receipt_path.is_file() and read(receipt_path).get('http_status') in (401,403,429):
                    blocked=(utc(now())+timedelta(hours=24)).isoformat()
            report['new_api_requests']+=client.store.db.execute('SELECT count(*) FROM requests').fetchone()[0]-before
            if blocked:break
        report['state_summary']=client.store.summary(now())
        client.store.db.close()
    except (ValueError,OSError):report['errors'].append(dict(reason='credential_or_store_unavailable'))
    report['public_sources']=[public_source(folder/'sources',name,spec) for name,spec in config['official_sources'].items()]
    report.update(completed_at=now(),status='captured' if not report['errors'] else 'captured_with_rejections',provider_blocked_until=blocked)
    target=folder/'capture_report.json';write_new(target,report);cycles.finish(identity,target,blocked)
    cycles.db.close()
    return dict(status=report['status'],report_path=str(target.resolve()),new_api_requests=report['new_api_requests'],
                valid_calendar_receipts=len(report['api_receipts']),new_odds_credits=0)
