"""One bounded ATP/WTA capture. No scheduler or betting side effects."""
import argparse
from datetime import datetime,timedelta,timezone
import json
import os
from pathlib import Path

from tennis_engine.operations import now
from tennis_engine.state_capture import TennisStateCapture


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--credential-file',type=Path)
    p.add_argument('--import-probe',type=Path)
    p.add_argument('--daily-limit',type=int,default=24)
    args=p.parse_args()
    key=os.environ.get('API_TENNIS_KEY')
    if args.credential_file:
        values=dict(line.strip().split('=',1) for line in args.credential_file.read_text().splitlines()
                    if line.strip() and not line.lstrip().startswith('#') and '=' in line)
        key=values.get('API_TENNIS_KEY')
    if not key:raise ValueError('Configure API_TENNIS_KEY locally; never pass it on the command line')
    client=TennisStateCapture(args.root,key,args.daily_limit)
    imported=0
    if args.import_probe:
        manifest=json.loads((args.import_probe/'manifest.json').read_text())
        for row in manifest:
            if row['method'] not in ('get_fixtures','get_livescore') or row.get('success')!=1 or row.get('http_status')!=200:continue
            imported+=client.store.ingest({'id':'legacy_'+row['sha256'],'method':row['method'],
                'requested_at':row['requested_at'],'received_at':row['received_at'],
                'source_path':str((args.import_probe/(row['label']+'.json')).resolve()),'sha256':row['sha256']})
    start=datetime.now(timezone.utc).date();stop=start+timedelta(days=2)
    captures=[]
    for event_type in ('265','266'):
        result=client.capture('get_fixtures',{'date_start':start.isoformat(),'date_stop':stop.isoformat(),
                    'event_type_key':event_type,'timezone':'UTC'})
        captures.append({'receipt_id':result['receipt']['id'],'observations_added':result['observations_added']})
    stamp=now()
    report={'created_at':stamp,'imported_observations':imported,'new_api_tennis_requests':len(captures),
            'captures':captures,'summary':client.store.summary(stamp),
            'the_odds_api_requests':0,'background_schedule_active':False,
            'local_daily_cap':args.daily_limit,'provider_plan_quota_verified':False,
            'strict_load_observations':len(client.store.load_history(stamp)),
            'reviewed_timelines':[client.store.timeline('api_tennis:'+i,stamp) for i in ('12171959','12171967')]}
    path=args.root/('report_'+stamp.replace(':','-')+'.json')
    with path.open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
    print(json.dumps({'report':str(path),'new_api_tennis_requests':2,'summary':report['summary']}))


if __name__=='__main__':main()
