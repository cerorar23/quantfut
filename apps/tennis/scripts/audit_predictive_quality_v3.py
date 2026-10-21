"""Complete offline quality diagnostics and freeze a new future comparison.

Never changes old models, repairs identities without evidence or labels the
already inspected historical cohort as confirmatory. No paid data requests.
"""
from collections import Counter
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
import numpy as np
from tennis_engine.paper_validation import load_policy,digest
from tennis_engine.model import ServeModel,training_rows
from tennis_engine.weighted_elo import WeightedEloModel,EloResult
from tennis_engine.research import pooled
from tennis_quality_v3.evaluation import identity_review,compare,reliability,MODELS
from tennis_quality_v3.prospective import read,write_new,freeze,evaluate_future


def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('workspace','output'):p.add_argument('--'+name,type=Path,required=True)
 args=p.parse_args();workspace=args.workspace.resolve();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
 root=workspace/'data/tennis/full_20261016'; improvements=workspace/'data/tennis/improvements_20261016'
 policy_path=workspace/'data/tennis/operational_readiness_20261018/financial_policy_v2.json'
 policy=load_policy(policy_path); source=root/'canonical/matches.parquet'
 inputs={str(source):digest(source),str(policy_path):digest(policy_path)}
 if digest(source)!='9e5621f2aaf2e0289e0e46afa2f03f55805fe77b820404b08303071de35e7ac2':raise ValueError('Original canonical source changed')
 data=pd.read_parquet(source).set_index('match_id',verify_integrity=True)
 identities=dict(schema='tennis-predictive-identity-quarantine-v3',circuits={},automatic_merges=0)
 for circuit in ('ATP','WTA'):
  path=root/f'models/{circuit}_current/model.json';inputs[str(path)]=digest(path)
  identities['circuits'][circuit]=identity_review(read(path)['names'])
 write_new(out/'identity_quarantine.json',identities)
 reports={};common_ids=set()
 for circuit in ('ATP','WTA'):
  folder=workspace/f'data/tennis/weighted_elo_20261017/{circuit}_v2'
  report_path=folder/'report.json';reference=read(report_path)
  for path,sha in reference['sources'].items():
   if digest(path)!=sha:raise ValueError('Archived comparison source changed')
   inputs[path]=sha
  table=folder/'predictions.parquet';inputs[str(table)]=digest(table);inputs[str(report_path)]=digest(report_path)
  frame=pd.read_parquet(table);universe=len(frame);excluded=Counter();retained=[]
  archived=pd.read_parquet(root/f'experiments/{circuit}_2026/heldout_predictions.parquet')
  if not frame[archived.columns].equals(archived):raise ValueError('Benchmark differs from its original held-out forecast rows')
  if not np.allclose(frame.current_hybrid,pooled(archived,read(improvements/f'{circuit}_pool/pool.json')),atol=1e-12,rtol=0):raise ValueError('Cached hybrid does not reproduce frozen formula')
  for name in ('weighted_elo','adaptive_elo'):
   path=folder/(name+'.json');inputs[str(path)]=digest(path)
   reference_model=WeightedEloModel.load_frozen(path,inputs[str(path)])
   if not np.allclose(frame[name],[reference_model.predict(a,b) for a,b in zip(frame.a,frame.b)],atol=1e-12,rtol=0):raise ValueError('Cached reference probabilities differ from frozen ratings')
  model=ServeModel(root/f'experiments/{circuit}_2026/model',uncertainty=False)
  denied=set(identities['circuits'][circuit]['excluded_ids'])
  for item in frame.to_dict('records'):
   row=data.loc[item['match_id']]
   if row.circuit!=circuit or not row.completed_standard or row.period<'2026-01-01' or {item['a'],item['b']}!={row.winner_id,row.loser_id} or item['y']!=int(item['a']==row.winner_id):raise ValueError('Canonical match identity/orientation differs')
   if item['a'] in denied or item['b'] in denied:excluded['ambiguous_current_identity']+=1;continue
   if item['a'] not in model.names or item['b'] not in model.names:excluded['unknown_pre2026_identity']+=1;continue
   if model.predict(item['a'],item['b'],row.surface,uncertainty=False)['unknown_effects']:excluded['untrained_player_surface_effect']+=1;continue
   if not np.isfinite([item[k] for k in MODELS]).all():excluded['missing_variant']+=1;continue
   item['competition_id']=str(row.tourney_id);retained.append(item)
  clean=pd.DataFrame(retained);clean.to_parquet(out/f'{circuit}_common_predictions.parquet',index=False)
  report=compare(clean,universe,scope='exploratory_common_2026_preyear_models')
  report['excluded']=dict(excluded);report['fit_origin']='2026-01-01';report['identity_quarantine_uses_current_knowledge']=True
  reports[circuit]=report;common_ids.update(clean.match_id)
  write_new(out/f'{circuit}_comparison.json',report)
  print(circuit,'common',len(clean),'/',universe,flush=True)
 markets_path=workspace/'data/tennis/markets_backtest_v2_20261019/fixed_contract_predictions.parquet'
 inputs[str(markets_path)]=digest(markets_path)
 markets=pd.read_parquet(markets_path);all_market_n=len(markets)
 markets=markets.loc[markets.match_id.isin(common_ids)].copy()
 markets['competition_id']=markets.match_id.map(data.tourney_id)
 diagnostics=[]
 for (circuit,best_of,contract),block in markets.groupby(['circuit','best_of','contract']):
  binary=block.loc[block.outcome.ne('push') & block.probability_no_push.notna()]
  diagnostic=reliability(binary.outcome.eq('win').astype(int).tolist(),binary.probability_no_push.tolist(),binary.competition_id.tolist())
  diagnostics.append(dict(circuit=circuit,best_of=int(best_of),contract=json.loads(contract),
    total=len(block),pushes=int(block.outcome.eq('push').sum()),binary_n=len(binary),
    quality=diagnostic,calibration_scope='Raw coherent Markov; no newly fitted calibration',
    predictive_quality_accredited=False))
 write_new(out/'all_market_quality.json',dict(families=len({r['contract']['kind'] for r in diagnostics}),
   original_probability_rows=all_market_n,after_common_identity_filter=len(markets),contracts=diagnostics,
   prospective_validation=False,all_markets_accredited=False))
 # Train references using exactly the current baseline's embargoed training rows.
 reference_paths={};artifacts=dict(policy['artifacts'])
 for circuit in ('ATP','WTA'):
  cutoff=read(root/f'models/{circuit}_current/model.json')['summary']['cutoff']
  history=training_rows(root,circuit,cutoff);models={'weighted_elo':WeightedEloModel(),'adaptive_elo':WeightedEloModel(False)}
  for period,block in history.groupby('period',sort=True):
   rows=[EloResult(r.match_id,r.winner_id,r.loser_id,r.score,int(r.best_of)) for r in block.itertuples()]
   for model in models.values():model.update_block(rows,str(period))
  reference_paths[circuit]={}
  for name,model in models.items():
   path=out/f'references/{circuit}_{name}.json';write_new(path,model.artifact())
   reference_paths[circuit][name]=str(path);artifacts[str(path)]=digest(path)
  print(circuit,'future references frozen',len(history),flush=True)
 artifacts[str(out/'identity_quarantine.json')]=digest(out/'identity_quarantine.json')
 # Include the unchanged core implementation in the quality protocol, too.
 import tennis_engine.paper_validation as core
 artifacts.update({str((Path(core.__file__).parent/name).resolve()):sha for name,sha in policy['candidate_code_sha256'].items()})
 config=dict(evaluation_start='2026-10-20T00:00:00Z',evaluation_end='2027-07-01T00:00:00Z',
  data_root=str(root),improvements_root=str(improvements),identity_review_path=str(out/'identity_quarantine.json'),
  reference_paths=reference_paths,artifacts=artifacts)
 freeze(out/'future_quality_protocol.json',config)
 (out/'future_predictions').mkdir();write_new(out/'future_results.json',[])
 write_new(out/'future_quality_initial.json',evaluate_future(out/'future_quality_protocol.json',out/'future_predictions',out/'future_results.json'))
 if any(digest(path)!=sha for path,sha in inputs.items()):raise ValueError('Input changed during audit')
 write_new(out/'summary.json',dict(schema='tennis-predictive-quality-completion-v3',
  common_cases={c:r['common_n'] for c,r in reports.items()},identity_ambiguous_groups={c:len(r['ambiguous_names']) for c,r in identities['circuits'].items()},
  excluded={c:r['excluded'] for c,r in reports.items()},market_families=10,market_contract_groups=len(diagnostics),
  input_sha256=inputs,retrospective_label='exploratory_already_inspected',future_eligible_completed=0,
  scientific_quality_accredited=False,new_odds_credits=0,odds_needed_for_quality=False,
  immutable_existing_financial_protocol=True,individual_certainty=False))
 lines=['# Calidad predictiva: resultados reales de la revisión','',
  'Evaluación exploratoria; no acredita certeza individual ni rentabilidad. Las cuotas no son entradas de esta evaluación.','',
  '| Circuito | Modelo | Casos comunes | Log-Loss | Brier | ECE | Aciertos del lado más probable |',
  '|---|---|---:|---:|---:|---:|---:|']
 for circuit,report in reports.items():
  for name,result in report['models'].items():
   m=result['metrics'];lines.append(f"| {circuit} | {name} | {m['n']} | {m['log_loss']:.5f} | {m['brier']:.5f} | {m['ece']:.5f} | {result['favourite_accuracy']:.1%} |")
 lines+=['','Bandas y coberturas completas en ATP_comparison.json y WTA_comparison.json. Intervalos por torneos y periodos, cuatro contrastes principales corregidos por multiplicidad. Las bandas no son certificados de confianza individual.',
  '', 'Identidades ambiguas excluidas de todas las variantes sobre la misma muestra. No se fusionan IDs ni se arreglan retrospectivamente los modelos congelados.',
  '', 'Diez familias revisadas por contrato y formato en all_market_quality.json. Diagnóstico de probabilidades sin calibración nueva ni aprobación general.',
  '', 'Protocolo futuro: future_quality_protocol.json. Inicio20-oct-2026; cierre1-jul-2027. Ganador, seis variantes, sin cuotas; no modificar durante la evaluación. Umbrales de diseño declarados, no estándares universales.',
  '', 'Faltan pronósticos y resultados futuros verificables. No hay servicio automático activo. El motor puede emitir investigación con seal_prediction; las etiquetas de fiabilidad requieren la evaluación prospectiva y revisión independiente.']
 (out/'RESULTADOS.md').write_text('\n'.join(lines)+'\n',encoding='utf8')


if __name__=='__main__':main()
