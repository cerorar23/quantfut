"""Offline hypothetical ATP/WTA trained-model smoke test; not betting picks."""
import sys,json,math,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tennis_engine.research import hybrid_forecast
from tennis_engine.scoring import Rules,match_distribution
root=Path('data/tennis/full_20261016');out=Path('data/tennis/historical_geography_complete_20261018/engine_smoke.json');assert not out.exists()
rows=[];hashes={}
for circuit,a,b in [('ATP','Carlos Alcaraz','Jannik Sinner'),('WTA','Iga Swiatek','Aryna Sabalenka')]:
 model=root/'models'/(circuit+'_current');pool=Path('data/tennis/improvements_20261016')/(circuit+'_pool/pool.json')
 x=hybrid_forecast(root,model,pool,a,b,'Hard');y=hybrid_forecast(root,model,pool,b,a,'Hard')
 assert abs(x['winner_A']+x['winner_B']-1)<1e-12 and abs(x['winner_A']+y['winner_A']-1)<1e-10
 assert 0<x['serve']['p']<1 and 0<x['serve']['q']<1
 d=match_distribution(x['serve']['p'],x['serve']['q'],Rules(3,deciding_tiebreak=7));mass=sum(d.values());assert abs(mass-1)<1e-9 and all(v>=0 for v in d.values())
 rows.append(dict(circuit=circuit,hypothetical_players=[a,b],prediction=x,reversed_prediction=y,joint_probability_mass=mass,symmetry_verified=True))
 for f in [model/'model.json',model/'training_receipt.json',pool]:hashes[str(f.resolve())]=hashlib.sha256(f.read_bytes()).hexdigest()
out.write_text(json.dumps(dict(schema='tennis-offline-end-to-end-smoke-v1',actual_models_used=True,network_requests=0,hypothetical_cases_only=True,scheduled_events_verified=False,production_approved=False,all_checks_passed=True,source_sha256=hashes,cases=rows),indent=2),encoding='utf8');print('ATP/WTA trained-model inference, reversal symmetry and joint probability mass passed')
