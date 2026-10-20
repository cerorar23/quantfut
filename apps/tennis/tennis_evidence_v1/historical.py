"""Descriptive review of already archived pre-2026-model predictions.

This reuses all existing exact contracts, not a favourable subset, and combines
exact-score alternatives into one categorical task per event. It creates no
prospective results, bookmaker prices or inferred profit.
"""
from pathlib import Path
from collections import Counter
import json, math
import pandas as pd
from tennis_engine.operations import now
from tennis_engine.paper_validation import digest
from tennis_engine.benchmark import probability_metrics
from tennis_quality_v3.prospective import read, write_new
from tennis_quality_v3.evaluation import block_interval
from tennis_allmarkets_v1.contracts import score_labels, validate_mass


def categorical_metrics(outcomes: list[str], probabilities: list[dict], competitions: list[str]) -> dict:
    if not (len(outcomes)==len(probabilities)==len(competitions)) or not outcomes:
        raise ValueError('Nonempty aligned categorical observations required')
    losses=[];briers=[];bins=[[] for _ in range(10)];hits=[];confidence=[]
    for label,vector in zip(outcomes,probabilities):
        validate_mass(vector)
        if label not in vector:raise ValueError('Observed category absent from forecast')
        losses.append(-math.log(max(1e-12,vector[label])))
        briers.append(sum((v-int(k==label))**2 for k,v in vector.items()))
        predicted=max(vector,key=vector.get);p=vector[predicted];hit=int(predicted==label)
        confidence.append(p);hits.append(hit);bins[min(int(p*10),9)].append((p,hit))
    calibration=[dict(lower=i/10,upper=(i+1)/10,n=len(values),
        mean_probability=sum(p for p,y in values)/len(values) if values else None,
        observed_rate=sum(y for p,y in values)/len(values) if values else None) for i,values in enumerate(bins)]
    return dict(n=len(outcomes),vector_log_loss=sum(losses)/len(losses),vector_brier=sum(briers)/len(briers),
        observed_class_counts=dict(Counter(outcomes)),
        largest_observed_class_fraction=max(Counter(outcomes).values())/len(outcomes),
        class_balance_is_ex_post_diagnostic_not_a_fitted_benchmark=True,
        top_choice_accuracy=sum(hits)/len(hits),top_choice_ece=sum(len(values)/len(outcomes)*abs(sum(p-y for p,y in values)/len(values)) for values in bins if values),
        calibration=calibration,competition_blocks=len(set(competitions)),
        log_loss_block_ci95=block_interval(losses,competitions,draws=2000),
        calibration_gap_block_ci95=block_interval([y-p for y,p in zip(hits,confidence)],competitions,draws=2000),
        intervals_are_descriptive_not_confirmatory=True)


def historical(root: Path, study_root: Path, quality_root: Path, output_root: Path) -> dict:
    output=Path(output_root);output.mkdir(parents=True,exist_ok=False)
    prediction_path=Path(study_root)/'fixed_contract_predictions.parquet'
    old_report=read(Path(study_root)/'report.json')
    if old_report['protocol']['fit_origin']!='2026-01-01' or old_report['protocol']['test_year']!=2026:
        raise ValueError('Archived pre-2026-model experiment required')
    source=Path(root)/'canonical/matches.parquet'
    if any(digest(path)!=sha for path,sha in old_report['input_sha256'].items()):
        raise ValueError('Original historical experiment changed')
    inputs={str(prediction_path.resolve()):digest(prediction_path),str((Path(study_root)/'report.json').resolve()):digest(Path(study_root)/'report.json')}
    cohorts=[]
    for circuit in ('ATP','WTA'):
        path=Path(quality_root)/f'{circuit}_common_predictions.parquet'
        inputs[str(path.resolve())]=digest(path)
        frame=pd.read_parquet(path)
        if frame.match_id.duplicated().any():raise ValueError('Duplicate common-cohort match')
        cohorts.extend(dict(match_id=r.match_id,circuit=circuit,competition_id=r.competition_id) for r in frame.itertuples())
    common=pd.DataFrame(cohorts)
    archived=pd.read_parquet(prediction_path)
    archived=archived.merge(common,on=['match_id','circuit'],how='inner',validate='many_to_one')
    matches=pd.read_parquet(source).set_index('match_id',verify_integrity=True)
    if not archived.match_id.isin(matches.index).all():raise ValueError('Historical match source absent')
    parsed={text:json.loads(text) for text in archived.contract.unique()}
    archived['kind']=archived.contract.map(lambda x:parsed[x]['kind'])
    reports=[]
    binary=archived.loc[archived.kind.ne('correct_score')]
    for (circuit,best_of,contract),group in binary.groupby(['circuit','best_of','contract'],sort=True):
        if group.match_id.duplicated().any():raise ValueError('Repeated exact contract per historical match')
        action=group.loc[group.outcome.ne('push') & group.probability_no_push.notna()]
        if not len(action):continue
        y=action.outcome.eq('win').astype(int).tolist();p=action.probability_no_push.tolist()
        metric=probability_metrics(y,p)
        vectors=[dict(win=float(v),loss=1-float(v)) for v in p]
        cat=categorical_metrics(action.outcome.tolist(),vectors,action.competition_id.tolist())
        reports.append(dict(circuit=circuit,best_of=int(best_of),contract=parsed[contract],
            registered=len(group),pushes=int(group.outcome.eq('push').sum()),coverage=len(action)/len(group),
            conditional_binary_metrics=metric,**cat))
    for (circuit,best_of),group in archived.loc[archived.kind.eq('correct_score')].groupby(['circuit','best_of']):
        outcomes=[];vectors=[];blocks=[]
        for match_id,rows in group.groupby('match_id'):
            vector={};wins=[]
            for r in rows.itertuples():
                contract=parsed[r.contract];label='-'.join(map(str,contract['score']))
                if label in vector:raise ValueError('Duplicate terminal score alternative')
                vector[label]=float(r.probability_no_push)
                if r.outcome=='win':wins.append(label)
                if r.outcome not in ('win','loss'):raise ValueError('Exact final score cannot push')
            if set(vector)!=set(score_labels(int(best_of))) or len(wins)!=1:
                raise ValueError('Incomplete exact score vector or missing unique observed winner')
            outcomes.append(wins[0]);vectors.append(vector);blocks.append(rows.competition_id.iloc[0])
        reports.append(dict(circuit=circuit,best_of=int(best_of),contract=dict(kind='correct_score',selection='vector'),
            registered=len(outcomes),pushes=0,coverage=1.,conditional_binary_metrics=None,
            **categorical_metrics(outcomes,vectors,blocks)))
    if any(digest(path)!=sha for path,sha in inputs.items()):raise ValueError('Historical inputs changed during analysis')
    summary=dict(schema='tennis-historical-evidence-review-v1',reviewed_at=now(),
        scope='exploratory_already_inspected_2026_with_pre2026_models',
        unique_matches=archived.match_id.nunique(),matches_by_circuit={c:g.match_id.nunique() for c,g in archived.groupby('circuit')},
        original_probability_rows=len(archived),distinct_tasks_after_multiclass_merge=sum(r['n'] for r in reports),
        groups=reports,families=sorted(archived.kind.unique()),source_sha256=inputs,
        prospective_observations_created=0,financial_validation=False,quality_accredited=False,
        limits=['No bookmaker prices, timestamps or paper orders in this experiment: ROI and CLV unknown',
            'Already inspected data, incomplete historical availability: not a confirmatory holdout',
            'No favourable line, period or circuit selected; all archived contract groups retained',
            'Brier vector sums across classes; binary Brier is separately labelled',
            'Coverage conditional on the common identity cohort, not universal tour coverage'])
    write_new(output/'historical_review.json',summary)
    lines=['# Evidencia histórica disponible de los diez mercados','',
        f"**{summary['unique_matches']:,} partidos terminados**: {summary['matches_by_circuit']['ATP']:,} ATP y {summary['matches_by_circuit']['WTA']:,} WTA; {len(reports)} grupos exactos y diez familias.", '',
        'Esta revisión utiliza probabilidades ya archivadas de modelos anteriores a enero de 2026. El año 2026 ya se inspeccionó: es evaluación exploratoria. No llena el registro de resultados futuros ni acredita rentabilidad.', '',
        'Menor Log-Loss/Brier es mejor. Aciertos corresponde a la alternativa más probable del contrato; en marcador por sets exige acertar el marcador exacto. ECE es descriptivo y depende de la muestra. Las líneas distintas se muestran separadas.', '',
        'La fracción de la clase más común es un diagnóstico observado después de los resultados, no un benchmark entrenado ni un pronóstico. Permite detectar tareas triviales: superar22,5juegos en BO5 puede acertarse casi siempre sin distinguir jugadores. Un porcentaje alto aislado no demuestra utilidad ni una cuota disponible.', '',
        '| Circuito | Formato | Contrato exacto | Partidos | Aciertos | Clase más común observada | Log-Loss | Brier binario | Brier vector | ECE alternativa más probable |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in reports:
        c=r['contract'];label=c['kind']
        if c.get('set_number'):label+=f" set {c['set_number']}"
        if c.get('line') is not None:label+=f" línea {c['line']}"
        binary_brier=f"{r['conditional_binary_metrics']['brier']:.4f}" if r['conditional_binary_metrics'] else '—'
        lines.append(f"| {r['circuit']} | BO{r['best_of']} | {label} | {r['n']} | {r['top_choice_accuracy']:.1%} | {r['largest_observed_class_fraction']:.1%} | {r['vector_log_loss']:.4f} | {binary_brier} | {r['vector_brier']:.4f} | {r['top_choice_ece']:.4f} |")
    lines+=['','Los JSON incluyen curvas de diez intervalos e incertidumbre por bloques. El marcador por sets es multiclase: su Brier/Log-Loss no se compara directamente con una tarea binaria. No se mezclan estas líneas con las 55 tareas del nuevo estudio ni se cambia el candidato con estos resultados.','',
        'Rentabilidad y CLV: desconocidos. No existen precios de ejecución ni órdenes en esta muestra; acertar más no demuestra beneficio. La prueba futura conserva sus reglas y fechas originales.']
    with (output/'HISTORICO.md').open('x',encoding='utf8') as f:f.write('\n'.join(lines)+'\n')
    return summary
