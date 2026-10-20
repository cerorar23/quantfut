"""Audit cached inputs, without turning schedules into actual exit timestamps."""
from collections import Counter
from datetime import datetime,timezone
import hashlib,json,sqlite3
from pathlib import Path
import sys

sys.path.insert(0,str(Path('.local/tennis_next').resolve() if Path(__file__).parent.name=='.local' else Path(__file__).resolve().parents[1]))
from tennis_engine.operations import utc

root=Path('data/tennis/coordinates_20261018')
seed=json.loads((root/'registry_seed_elevation.json').read_text())
source=next(s for s in seed['sources'] if s['source_id']=='api_upcoming')
if hashlib.sha256(Path(source['source_path']).read_bytes()).hexdigest()!=source['sha256']:
    raise ValueError('Calendar source changed')
targets=json.loads(Path(source['source_path']).read_bytes())['result']
decision=datetime.now(timezone.utc).isoformat()
path=Path('data/tennis/state_capture_20261017/states.sqlite').resolve()
db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
latest={r['event_id']:dict(r) for r in db.execute('SELECT * FROM observations WHERE received_at<? ORDER BY received_at',(decision,))}
terminal=[r for r in latest.values() if r['state'] in ('completed','retired')]
prior_by_player={}
for record in terminal:
    row=json.loads(record['payload'])
    for key in (row['first_player_key'],row['second_player_key']):
        prior_by_player.setdefault(str(key),[]).append(row)
rows=[]
for target in targets:
    scheduled=target['event_date']+'T'+target['event_time']+':00+00:00'
    for key in (target['first_player_key'],target['second_player_key']):
        # Only an audit of candidate records by provider scheduled date, never a
        # claim of actual chronology, elimination, consecutive tournaments or exit.
        candidates=[r for r in prior_by_player.get(str(key),[]) if r['event_date']<target['event_date']]
        candidates.sort(key=lambda r:(r['event_date'],r['event_time'],str(r['event_key'])))
        last=candidates[-1] if candidates else None
        rows.append({'player_id':'api_tennis:'+str(key),'target_event_id':'api_tennis:'+str(target['event_key']),
            'target_provider_tournament_id':str(target['tournament_key']),
            'scheduled_after_audit':utc(scheduled)>utc(decision),
            'candidate_prior_event_id':None if last is None else 'api_tennis:'+str(last['event_key']),
            'candidate_provider_tournament_id':None if last is None else str(last['tournament_key']),
            'candidate_order_basis':'provider scheduled date only, actual chronology unverified',
            'target_debut_verified':False,'consecutive_tournaments_verified':False,
            'all_disciplines_checked':False,'actual_exit_time_available':False,
            'ready_for_reviewed_transition':False})
report={'schema':'tennis-travel-input-readiness-v1','as_of':decision,
    'calendar_source_received_at':source['received_at'],'calendar_is_cached_snapshot':True,
    'target_fixture_count':len(targets),'target_player_fixture_rows':len(rows),
    'cached_latest_event_count':len(latest),'cached_terminal_played_records':len(terminal),
    'player_fixture_rows_with_candidate_history':sum(r['candidate_prior_event_id'] is not None for r in rows),
    'verified_transitions_ready':0,'genuine_actual_exit_times_available':0,
    'states':dict(Counter(r['state'] for r in latest.values())),
    'blocking_data':['verified first participation in target edition','adequate intervening event and doubles coverage',
                     'verified previous participation closure','actual exit time or independently verified interval'],
    'sports_api_requests':0,'probabilities_modified':False,'rows':rows}
out=root/'travel_input_readiness.json'
if not out.exists():out.write_text(json.dumps(report,indent=2),encoding='utf8')
db.close()
print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
