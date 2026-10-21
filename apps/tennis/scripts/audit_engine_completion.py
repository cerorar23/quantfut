"""Publish a reproducible phase-level readiness inventory after completed checks.

Integrity, implemented components, data coverage and production approval are
separate states. A successful software test never clears an evidence gate.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,re
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--workspace',type=Path,default=Path.cwd())
p.add_argument('--policy',type=Path,required=True)
p.add_argument('--verify-existing',action='store_true',help='Compare to archived readiness without modifying it')
args=p.parse_args();workspace=args.workspace.resolve();code=Path(__file__).resolve().parents[1]
root=workspace/'data/tennis/historical_geography_complete_20261018'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text(encoding='utf8'))
geo=read(root/'delivery_audit.json');integrity=read(root/'engine_integrity/audit.json')
assert integrity['integrity_pass'] and not integrity['failures']
assert geo['reviewed_entries']==73 and geo['resolved_entries']==72
assert all(sha(root/n)==s for n,s in geo['files_sha256'].items())
assert all(sha(root/'comparison'/n)==s for n,s in geo['comparison_files_sha256'].items())
policy=read(args.policy);assert policy['subscription']=='paid_user_confirmed' and policy['monthly_tennis_credit_cap']==2000
# Every identified implementation is a real nonempty source file, pinned below.
capabilities={
 'data_and_identity':['ingest','normalize','identities','history'],
 'probabilities':['model','scoring','forecast','research','dynamic','calibration','weighted_elo'],
 'evaluation':['benchmark','evaluate','load_runner','historical_comparison','spatial_experiment'],
 'context':['recent_load','draw_load','context','travel','venues','historical_dataset','fixture_reviews'],
 'operations':['operations','markets','settlement','state_capture','shadow','prospective','official','audit']}
modules={}
for phase,names in capabilities.items():
 for name in names:
  f=code/'tennis_engine'/(name+'.py');assert f.is_file() and f.stat().st_size>100;compile(f.read_text(encoding='utf8'),str(f),'exec');modules[name]=sha(f)
tests_log=workspace/'.local/tennis-complete-tests.log';assert re.search(r'194 passed',tests_log.read_text(encoding='utf8',errors='replace'))
harness_log=workspace/'.local/tennis-complete-harness-final.log';log=harness_log.read_text(encoding='utf8',errors='replace')
match=re.search(r'(\d+) passed, (\d+) skipped, (\d+) warnings? in ([\d.]+)s',log);assert match,'Final harness not complete'
assert int(match[1])>=1315
feasibility=read(workspace/'data/tennis/draw_load_20261018_v2/strict_daily_feasibility.json')
assert feasibility['windows_3d_7d_ready'] is False
phases=[
 dict(phase='Originales y normalización',implementation='verified',evidence='engine_integrity/audit.json',data_limit='Historical receipt times do not establish original publication times'),
 dict(phase='Modelo matemático y Weighted Elo',implementation='implemented_tested',activation='research_only',data_limit='Classical probability model; exploratory alternatives not promoted'),
 dict(phase='Evaluación común y ablación',implementation='implemented_tested',activation='research_only',data_limit='2025/2026 observed during development; new untouched future evaluation required'),
 dict(phase='Sedes históricas y espaciales',implementation='full_queue_review_complete',resolved=72,reviewed=73,activation='not_promoted',data_limit='One historical campus ambiguous; three destination matches excluded'),
 dict(phase='Carga diaria y descanso',implementation='implemented_tested_data_gated',activation='blocked_by_evidence',data_limit='152 archived terminal singles without finite completion lower bounds; exact rest and complete doubles history unavailable'),
 dict(phase='Carga por rondas',implementation='experiment_evaluated',activation='not_promoted',data_limit='1957 common exploratory cases; uncertainty includes zero; not daily load'),
 dict(phase='Clima, itinerarios y fisiología',implementation='context_contracts_only',activation='not_activated',data_limit='No validated full weather/roof/arrival evidence or learned physiological penalty; no arbitrary fatigue score'),
 dict(phase='Cuotas y casas',implementation='implemented_partial_market_coverage',activation='research_only',data_limit='Seven supported API market keys; no guarantee of all markets/books or jointly calibrated derivatives'),
 dict(phase='Liquidación',implementation='implemented_documented_profiles_only',activation='research_only',data_limit='Other bookmaker/jurisdiction retirement rules and executable prices must be verified before full ROI'),
 dict(phase='Capturas y validación futura',implementation='implemented_bounded_capture_and_protocol',activation='not_automatic',data_limit='API-Tennis trial/quota unconfirmed; no claim of live service or new untouched outcomes')]
result=dict(schema='tennis-complete-readiness-v1',created_at=datetime.now(timezone.utc).isoformat(),
 scope='Full pending geographic review, integration, fixed retrospective evaluation and phase-level engine audit',
 research_engine_available=True,all_evidence_complete=False,production_approved=False,financial_validation=False,
 phases=phases,capabilities=capabilities,module_sha256=modules,
 current_geography=dict(registry_entries=240,georeferenced_entries=239,target_matches=11240,with_target_coordinates=11237,spatial_eligible=6568),
 legacy_integrity_readiness_superseded=True,legacy_integrity_warnings=integrity['warnings'],
 tests=dict(tennis_passed=194,general_passed=int(match[1]),general_skipped=int(match[2]),general_warnings=int(match[3]),general_seconds=float(match[4]),docker_available=False),
 paid_odds_plan_confirmed=True,monthly_tennis_credit_cap=2000,odds_credits_consumed_this_execution=0,sports_provider_requests_this_execution=0,
 preserved_models_and_frozen_artifacts=dict(baseline_receipts=6,frozen_artifacts=12),
 evidence_sha256={str(f.relative_to(workspace)):sha(f) for f in [root/'delivery_audit.json',root/'engine_integrity/audit.json',root/'comparison/protocol.json',root/'comparison/report.json',tests_log,harness_log,workspace/'data/tennis/draw_load_20261018_v2/strict_daily_feasibility.json']})
output=root/'engine_readiness.json'
if args.verify_existing:
 saved=read(output);saved.pop('created_at');candidate=dict(result);candidate.pop('created_at');assert saved==candidate,'Readiness evidence changed'
else:
 assert not output.exists(),'Readiness snapshot already exists'
 output.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps(dict(research_engine_available=True,production_approved=False,all_evidence_complete=False,tests=result['tests'])))
