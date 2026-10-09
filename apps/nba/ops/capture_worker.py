"""Bounded public research collector. No credentials, wagers or notifications."""
from datetime import UTC,datetime
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from zoneinfo import ZoneInfo
import json,os,shutil,sqlite3,sys,time

from nba.audit import Ledger,digest,write_json
from nba.public_capture import capture
from nba.capture_backup import create_backup,prune_generated_backups
from nba.timestamp_anchor import stamp


def quarantined_sources(captures,urls):
    """Report the original blocked response; quarantine never implies recovery."""
    result=[]
    if not urls:return result
    ledger=Ledger(captures/'receipts.sqlite');ledger.verify()
    with sqlite3.connect(ledger.path) as db:
        receipts=[json.loads(r[0]) for r in db.execute('SELECT payload FROM events WHERE kind=? ORDER BY seq DESC',('public_response_received',))]
    for url in urls:
        receipt=next((r for r in receipts if r.get('url')==url),None)
        if receipt is not None and digest(captures/'blobs'/receipt['raw_sha256'])!=receipt['raw_sha256']:
            raise ValueError('quarantined source evidence changed')
        result.append(dict(url=url,state='quarantined',recovered=False,automatic_requests=False,
            last_receipt=receipt,reason='blocked optional bookmaker; no replacement props inferred'))
    return result


def cycle(root,config):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    captures=root/'captures';state_file=root/'state.json'
    state=json.loads(state_file.read_bytes()) if state_file.exists() else {}
    # Hard limits never remove original bodies or research evidence.
    used=sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    if used>config['max_total_bytes'] or shutil.disk_usage(root).free<config['min_free_host_bytes']:
        result=dict(state='storage_hold',used_bytes=used,production_enabled=False,F7_started=False)
        write_json(root/'health.json',result);return result
    now=datetime.now(UTC);day=now.astimezone(ZoneInfo('America/New_York')).strftime('%Y%m%d')
    urls=['https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates='+day]
    if time.time()-state.get('last_injury_attempt_epoch',0)>=3600:
        urls.append('https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries?limit=1000')
        state['last_injury_attempt_epoch']=time.time()
    receipts=[capture(captures,u,urls) for u in urls]
    source_valid=True;events=[]
    try:
        board=json.loads((captures/'blobs'/receipts[0]['raw_sha256']).read_bytes())
        source_valid=board['leagues'][0]['slug']=='nba' and isinstance(board['events'],list)
        events=board['events']
    except Exception:source_valid=False
    if time.time()-state.get('last_roster_attempt_epoch',0)>=3600 and source_valid:
        state['last_roster_attempt_epoch']=time.time()
        teams=sorted({str(c['team']['id']) for e in events for c in e['competitions'][0]['competitors']})
        if len(teams)>30:raise ValueError('NBA team limit exceeded')
        roster_urls=['https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/'+t+'/roster?season=2027' for t in teams]
        for url in roster_urls:receipts.append(capture(captures,url,roster_urls))
    # Retain failures of hourly feeds even when they are not requested this cycle.
    required=state.setdefault('required_sources',{})
    for receipt in receipts:
        url=receipt['url'];valid=receipt['http_status']==200
        try:
            body=json.loads((captures/'blobs'/receipt['raw_sha256']).read_bytes())
            if '/scoreboard?' in url:valid=valid and source_valid
            elif '/injuries?' in url:valid=valid and isinstance(body['injuries'],list)
            elif '/roster?' in url:valid=valid and isinstance(body['athletes'],list)
        except Exception:valid=False
        key='scoreboard' if '/scoreboard?' in url else url
        required[key]=dict(url=url,valid=valid,http_status=receipt['http_status'],raw_sha256=receipt['raw_sha256'])
    issues=quarantined_sources(captures,config.get('quarantined_public_sources',[]))
    # The snapshot proves actual HTTP response receipt, not provider publication.
    ledger=Ledger(captures/'receipts.sqlite');head=ledger.verify()
    manifest=dict(created_at_utc=datetime.now(UTC).isoformat(),ledger=head,
        receipts=receipts,files={r['raw_sha256']:r['raw_sha256'] for r in receipts},
        optional_source_issues=issues,production_enabled=False,F7_started=False)
    mfolder=root/'manifests';mfolder.mkdir(exist_ok=True)
    mf=mfolder/(str(head['events'])+'.json');write_json(mf,manifest)
    anchor=None
    if time.time()-state.get('last_anchor_attempt_epoch',0)>=86400:
        state['last_anchor_attempt_epoch']=time.time();write_json(state_file,state)
        (root/'anchors').mkdir(exist_ok=True)
        try:anchor=stamp('/usr/bin/openssl','/etc/ssl/certs/ca-certificates.crt',mf,root/'anchors'/str(head['events']))
        except Exception as e:anchor=dict(state='unverified',reason=type(e).__name__,automatic_retry=False)
    backup=None;removed=[]
    if config.get('periodic_copies',False):
        backup=create_backup(captures,root/'backups')
        removed=prune_generated_backups(root/'backups',config['backup_keep'])
    state['last_cycle_epoch']=time.time();write_json(state_file,state)
    result=dict(state='capturing' if source_valid and all(r['valid'] for r in required.values()) else 'source_degraded',
        at_utc=datetime.now(UTC).isoformat(),receipts=len(receipts),ledger=head,anchor=anchor,
        backup_verified=backup['result']=='passed' if backup else None,
        archive_sha256=backup['archive_sha256'] if backup else None,removed_generated_backups=removed,
        periodic_copies=bool(config.get('periodic_copies',False)),required_sources=required,optional_source_issues=issues,
        bookmaker_props_coverage_verified=False,
        used_bytes=used,scheduled_events=len(events),source_valid=source_valid,
        contracts_verified=False,availability_verified=False,
        production_enabled=False,F7_started=False,paid_API_calls=0,external_messages=0)
    write_json(root/'health.json',result);return result


def main():
    import fcntl
    root=Path('/data');config=json.loads(Path('/app/config.json').read_bytes())
    lock=(root/'capture_worker.lock').open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        print(json.dumps(dict(state='already_running',network_attempted=False)),flush=True);return
    if '--once' in sys.argv:print(json.dumps(cycle(root,config)),flush=True);return
    while True:
        state=json.loads((root/'state.json').read_bytes()) if (root/'state.json').exists() else {}
        wait=config['cycle_seconds']-(time.time()-state.get('last_cycle_epoch',0))
        if wait>0:time.sleep(min(wait,30));continue
        try:print(json.dumps(cycle(root,config)),flush=True)
        except Exception as e:
            write_json(root/'health.json',dict(state='error',reason=type(e).__name__,production_enabled=False,F7_started=False))
        time.sleep(config['cycle_seconds'])


if __name__=='__main__':main()
