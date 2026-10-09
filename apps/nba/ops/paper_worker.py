"""Finite server-side paper lifecycle; no predictions, bets, messages or backups."""
from datetime import UTC,datetime
import json
from pathlib import Path
import sys
import time
from uuid import uuid4

from nba.audit import Ledger,digest,write_json
from nba.context import utc
from nba.paper_followup import advance,verify_plan


def verify_bundle(workspace):
    root=Path(workspace);manifest=json.loads((root/'bundle_manifest.json').read_bytes())
    for name,hashed in manifest['files'].items():
        path=root/name
        if Path(name).is_absolute() or '..' in Path(name).parts or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('unsafe worker bundle path')
        if digest(path)!=hashed:raise ValueError('worker bundle changed')
    config=json.loads((root/'worker_config.json').read_bytes());plan=verify_plan(config['plan'])
    if digest(Path(config['plan'])/'plan.json')!=manifest['original_plan_sha256']:
        raise ValueError('original plan changed')
    if (plan['total_closing_credit_cap']!=config['total_closing_credit_cap'] or config['total_closing_credit_cap']!=2
            or plan['maximum_jobs_per_run']!=3 or config['production_ready'] or config['periodic_copies']):
        raise ValueError('worker scope/budget changed')
    return config,plan


def tick(workspace,data,key_file,*,clock=None,runner=advance):
    root=Path(data);root.mkdir(parents=True,exist_ok=True)
    config,plan=verify_bundle(workspace);cut=(clock or (lambda:datetime.now(UTC)))()
    state=root/'state.sqlite'
    if not state.exists():
        with state.open('xb') as stream:stream.write((Path(workspace)/'initial_state.sqlite').read_bytes())
    chain=Ledger(state).verify()
    health=dict(as_of=cut.isoformat(),plan_sha256=digest(Path(config['plan'])/'plan.json'),ledger=chain,
        future_closing_credit_cap=2,operational_bets=0,production_ready=False,periodic_copies=False)
    previous=json.loads((root/'health.json').read_bytes()) if (root/'health.json').exists() else {}
    if previous.get('state') in ('completed','deadline_exhausted','validation_error','clock_hold'):
        return previous,True
    if cut>=utc(config['deadline_utc']):
        health.update(state='deadline_exhausted',last_result=previous.get('last_result'),missing_results_not_invented=True)
        write_json(root/'health.json',health);return health,True
    if 'as_of' in previous and cut<utc(previous['as_of']):
        health.update(state='clock_hold');write_json(root/'health.json',health);return health,True
    # No requests and no new run folders while no new job is due.
    import sqlite3
    with sqlite3.connect(state) as db:claimed={r[0] for r in db.execute('SELECT job_key FROM claims')}
    due=[j for j in plan['jobs'] if utc(j['due'])<=cut and health['plan_sha256']+':'+j['id'] not in claimed]
    if due:
        key=Path(key_file).read_text().strip() if Path(key_file).is_file() else None
        output=root/'runs'/(cut.strftime('%Y%m%dT%H%M%S')+'_'+uuid4().hex)
        result=runner(config['plan'],state,output,key)
        health.update(state='completed' if result['status']=='completed' else 'waiting',last_result=str(output/'result.json'),
            completed_events=result['completed_events'],ledger=result['state'],last_executed=result['executed'])
    else:
        health.update(state='waiting',last_result=previous.get('last_result'),completed_events=previous.get('completed_events',0))
    health['next_due_utc']=min((j['due'] for j in plan['jobs'] if utc(j['due'])>cut),default=None)
    write_json(root/'health.json',health)
    return health,health['state']=='completed'


def main():
    # Host flock protects the entire service lifetime, including separate --once invocations.
    import fcntl
    data=Path('/data');data.mkdir(exist_ok=True)
    with (data/'worker.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps(dict(state='already_running',network_attempted=False)));return
        wall=datetime.now(UTC);mono=time.monotonic()
        while True:
            current=datetime.now(UTC)
            if abs((current-wall).total_seconds()-(time.monotonic()-mono))>5:
                write_json(data/'health.json',dict(state='clock_hold',as_of=current.isoformat(),production_ready=False));return
            try:health,done=tick('/workspace',data,'/run/secrets/odds_key')
            except Exception as error:
                health=dict(state='validation_error',error_type=type(error).__name__,as_of=current.isoformat(),production_ready=False)
                write_json(data/'health.json',health);print(json.dumps(health),flush=True);return
            if '--once' in sys.argv or done:
                print(json.dumps(health),flush=True);return
            time.sleep(10)


if __name__=='__main__':main()
