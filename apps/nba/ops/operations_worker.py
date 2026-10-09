"""VPS operational supervision, Python 3.10 stdlib; never sends betting picks."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import urllib.request

UTC=timezone.utc
TERMINAL={'completed','deadline_exhausted','validation_error','clock_hold'}


def utc(value):
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    if result.tzinfo is None:raise ValueError('aware UTC time required')
    return result.astimezone(UTC)


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def atomic(path,value):
    path=Path(path);tmp=path.with_suffix('.tmp')
    with tmp.open('w') as stream:
        stream.write(json.dumps(value,indent=2)+'\n');stream.flush();os.fsync(stream.fileno())
    tmp.replace(path)


def store(path):
    db=sqlite3.connect(path)
    db.executescript('''
      CREATE TABLE IF NOT EXISTS claims (key TEXT PRIMARY KEY,at_utc TEXT NOT NULL,category TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS journal (seq INTEGER PRIMARY KEY,kind TEXT NOT NULL,payload TEXT NOT NULL,previous_hash TEXT NOT NULL,event_hash TEXT NOT NULL);
      CREATE TRIGGER IF NOT EXISTS claims_no_update BEFORE UPDATE ON claims BEGIN SELECT RAISE(ABORT,'immutable claim'); END;
      CREATE TRIGGER IF NOT EXISTS claims_no_delete BEFORE DELETE ON claims BEGIN SELECT RAISE(ABORT,'immutable claim'); END;
      CREATE TRIGGER IF NOT EXISTS journal_no_update BEFORE UPDATE ON journal BEGIN SELECT RAISE(ABORT,'immutable journal'); END;
      CREATE TRIGGER IF NOT EXISTS journal_no_delete BEFORE DELETE ON journal BEGIN SELECT RAISE(ABORT,'immutable journal'); END;
    ''')
    verify(db)
    return db


def verify(db):
    previous='0'*64;count=0
    for seq,kind,payload,prev,hashed in db.execute('SELECT * FROM journal ORDER BY seq'):
        count+=1
        if seq!=count or prev!=previous or hashlib.sha256(canonical([seq,kind,payload,prev]).encode()).hexdigest()!=hashed:
            raise ValueError('operations journal changed')
        previous=hashed
    return dict(events=count,head=previous)


def append(db,kind,payload):
    last=db.execute('SELECT seq,event_hash FROM journal ORDER BY seq DESC LIMIT 1').fetchone()
    seq,previous=(last[0]+1,last[1]) if last else (1,'0'*64)
    raw=canonical(payload);hashed=hashlib.sha256(canonical([seq,kind,raw,previous]).encode()).hexdigest()
    db.execute('INSERT INTO journal VALUES (?,?,?,?,?)',(seq,kind,raw,previous,hashed))


def claim(db,key,category,now,cap):
    db.execute('BEGIN IMMEDIATE')
    if db.execute('SELECT 1 FROM claims WHERE key=?',(key,)).fetchone():db.rollback();return False
    if category=='telegram' and db.execute('SELECT COUNT(*) FROM claims WHERE category=? AND substr(at_utc,1,10)=?',
        (category,now.date().isoformat())).fetchone()[0]>=cap:db.rollback();return False
    db.execute('INSERT INTO claims VALUES (?,?,?)',(key,now.isoformat(),category))
    append(db,'claimed',dict(key=key,category=category,at_utc=now.isoformat()));db.commit()
    return True


def snapshot(path,now,max_age):
    try:
        health=json.loads(Path(path).read_bytes());stamp=health.get('at_utc',health.get('as_of'))
        age=(now-utc(stamp)).total_seconds()
        if not -5<=age<=max_age and health.get('state') not in TERMINAL:
            return dict(state='stale',source_state=health.get('state'),completed_events=health.get('completed_events',0))
        return dict(state=health['state'],completed_events=health.get('completed_events',0),
            last_executed=health.get('last_result'),optional_sources_blocked=len(health.get('optional_source_issues',[])))
    except Exception:return dict(state='unreadable')


def telegram(text,private_file,expires):
    """One POST. Never expose a URL, token, chat ID or provider error text."""
    if not text.startswith('ESTADO OPERATIVO NBA\n'):raise ValueError('operational category required')
    if datetime.now(UTC)>=expires:return dict(state='expired',send_attempted=False)
    values=json.loads(Path(private_file).read_bytes())
    if set(values)!={'token','chat'} or not all(isinstance(v,str) and v for v in values.values()):
        raise ValueError('authorized operational config absent')
    payload=json.dumps(dict(chat_id=values['chat'],text=text)).encode()
    request=urllib.request.Request('https://api.telegram.org/bot'+values['token']+'/sendMessage',
        data=payload,headers={'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(request,timeout=10) as response:body=json.loads(response.read(100000))
        result=body.get('result',{})
        if (body.get('ok') is True and type(result.get('message_id')) is int
                and result['message_id']>0 and str(result.get('chat',{}).get('id'))==values['chat']):
            return dict(state='sent',message_id=result['message_id'],destination_verified=True,subscriber_receipt_verified=False)
    except Exception:pass
    return dict(state='unknown',automatic_retry=False)


def stop_pilot(name,expected_label):
    """Only the original owned paper executor; no general Docker mutations."""
    if name!='nba-paper-pilot-run67' or expected_label!='paper-run67':raise ValueError('unauthorized container')
    try:
        result=subprocess.run(['docker','inspect',name],capture_output=True,text=True,timeout=15)
        if result.returncode:raise ValueError('inspection failed')
        inspected=json.loads(result.stdout)[0]
        if inspected['Config']['Labels'].get('NBA.scope')!=expected_label:raise ValueError('ownership changed')
        if not inspected['State']['Running']:return dict(state='already_stopped',ownership_verified=True)
        result=subprocess.run(['docker','stop','--time','10',name],capture_output=True,text=True,timeout=25)
        return dict(state='stopped' if result.returncode==0 else 'unknown',ownership_verified=True,automatic_retry=False)
    except Exception:return dict(state='unknown',automatic_retry=False)


def validate_config(config):
    if config['daily_message_cap']!=20 or config['cycle_seconds']!=30 or config['production_ready'] or config['periodic_copies']:
        raise ValueError('operations scope changed')
    if config['paper_container']!='nba-paper-pilot-run67' or config['paper_label']!='paper-run67':raise ValueError('paper scope changed')
    for key in ('capture_health','paper_health','private_file','data','design'):
        path=Path(config[key])
        if not path.is_absolute() or '..' in path.parts or not path.is_relative_to('/home/qf/nba-isolated'):
            raise ValueError('unsafe operational path')
    if hashlib.sha256(Path(config['design']).read_bytes()).hexdigest()!=config['design_sha256']:
        raise ValueError('scientific design changed')


def cycle(config,*,clock=None,sender=telegram,stopper=stop_pilot):
    from datetime import timedelta
    validate_config(config);now=(clock or (lambda:datetime.now(UTC)))()
    root=Path(config['data']);root.mkdir(parents=True,exist_ok=True)
    old=json.loads((root/'status.json').read_bytes()) if (root/'status.json').exists() else {}
    if old.get('as_of') and now<utc(old['as_of']):raise ValueError('operations clock rollback')
    components=dict(capture=snapshot(config['capture_health'],now,1800),paper=snapshot(config['paper_health'],now,120))
    outcomes=[]
    with store(root/'operations.sqlite') as db:
        terminal=components['paper']['state'] in TERMINAL
        if terminal:
            key='stop:'+components['paper']['state']
            if claim(db,key,'stop',now,config['daily_message_cap']):
                result=stopper(config['paper_container'],config['paper_label'])
                append(db,'stop_result',dict(key=key,result=result));db.commit();outcomes.append(dict(category='stop',result=result))
        signature=hashlib.sha256(canonical(components).encode()).hexdigest()
        if signature!=old.get('signature'):
            # A recurring state change has its own sequence. Identical restart state never sends twice.
            transition=old.get('transition',0)+1
            key='telegram:'+str(transition)+':'+signature
            if claim(db,key,'telegram',now,config['daily_message_cap']):
                text=('ESTADO OPERATIVO NBA\nCaptura: '+components['capture']['state']+
                    '. Fuentes opcionales en cuarentena: '+str(components['capture'].get('optional_sources_blocked',0))+
                    '.\nPiloto: '+components['paper']['state']+'. Partidos evaluados: '+str(components['paper'].get('completed_events',0))+
                    '.\nSeguimiento y alertas activos en VPS. Investigación; apuestas reales desactivadas.\n'+now.isoformat())
                try:result=sender(text,config['private_file'],now+timedelta(seconds=60))
                except Exception:result=dict(state='unknown',automatic_retry=False)
                append(db,'telegram_result',dict(key=key,result=result));db.commit();outcomes.append(dict(category='telegram',result=result))
            elif db.execute('SELECT 1 FROM claims WHERE key=?',(key,)).fetchone():
                # Crash after the durable claim: retain uncertainty and suppress retry.
                outcomes.append(dict(category='telegram',result=dict(state='unknown',automatic_retry=False,previous_claim=True)))
            else:transition=old.get('transition',0)
        else:transition=old.get('transition',0)
        # If the daily cap blocked this transition retain the prior signature to admit it after reset.
        accepted=signature==old.get('signature') or any(o['category']=='telegram' for o in outcomes)
        report=dict(as_of=now.isoformat(),state='monitoring',components=components,signature=signature if accepted else old.get('signature'),
            transition=transition,last_outcomes=outcomes,last_message=next((o['result'] for o in outcomes if o['category']=='telegram'),old.get('last_message')),
            journal=verify(db),daily_message_cap=20,automatic_message_retry=False,scientific_confirmation_started=False,
            real_account_tickets_received=0,production_ready=False,operational_bets=0,periodic_copies=False)
    atomic(root/'status.json',report);return report


def main():
    import fcntl
    config_path=Path(sys.argv[1]);config=json.loads(config_path.read_bytes());validate_config(config)
    root=Path(config['data']);root.mkdir(parents=True,exist_ok=True)
    with (root/'worker.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:print(json.dumps(dict(state='already_running',send_attempted=False)));return
        previous_wall=datetime.now(UTC);previous_mono=time.monotonic();ready=False
        while True:
            wall=datetime.now(UTC);mono=time.monotonic()
            if abs((wall-previous_wall).total_seconds()-(mono-previous_mono))>5:raise ValueError('operations clock jump')
            previous_wall=wall;previous_mono=mono
            report=cycle(config)
            if '--once' in sys.argv:print(json.dumps(report));return
            if not ready:
                # systemd start completes only after the live process owns the lock
                # and finishes its first durable cycle. Type=simple races slow startup.
                address=os.environ.get('NOTIFY_SOCKET')
                if address:
                    import socket
                    if address.startswith('@'):address='\0'+address[1:]
                    with socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM) as notifier:
                        notifier.connect(address);notifier.sendall(b'READY=1')
                ready=True
            time.sleep(config['cycle_seconds'])


if __name__=='__main__':main()
