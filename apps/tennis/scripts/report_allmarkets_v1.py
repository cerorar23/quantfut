"""Create new human-readable views; never change sealed forecasts or protocols."""
from pathlib import Path
import argparse
from collections import Counter
from tennis_quality_v3.prospective import read, write_new
from tennis_engine.paper_validation import digest

LABELS={'winner':'Ganador del partido','set_winner':'Ganador de cada set',
    'games_total':'Total de juegos del partido','games_handicap':'Hándicap de juegos del partido',
    'sets_total':'Total de sets','sets_handicap':'Hándicap de sets',
    'tiebreak':'Al menos un tiebreak','correct_score':'Marcador final por sets',
    'set_games_total':'Total de juegos de cada set','set_games_handicap':'Hándicap de juegos de cada set'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    args=parser.parse_args();root=args.root
    records=[read(path) for path in sorted((root/'predictions').glob('*.json'))]
    report=read(root/'evaluation_initial.json');counts=Counter(v['circuit'] for v in records)
    tasks=sum(len(v['rows']) for v in records)
    summary=['# Seguimiento de los diez mercados de tenis','',
        f"{len(records)} partidos ({counts['ATP']} ATP y {counts['WTA']} WTA), {tasks} contratos registrados antes de los encuentros; cero resultados evaluados en esta primera entrega.", '',
        '**Estado: seguimiento prospectivo en marcha. Calidad y rentabilidad todavía no acreditadas.**', '',
        'Cada partido tiene 55 tareas en formato al mejor de tres. Las líneas y los sets de un mismo encuentro están relacionados: 990 contratos no equivalen a 990 partidos independientes.', '',
        '| Mercado | Contratos registrados | Resultados evaluados |','|---|---:|---:|']
    for kind,value in report['market_families'].items():
        summary.append(f"| {LABELS[kind]} | {value['registered_contract_rows']} | {value['evaluated_contract_rows']} |")
    summary += ['', 'El protocolo fija las líneas antes de conocer resultados; la evaluación separa circuito, formato, regla del tiebreak decisivo, set y línea. Hay 110 grupos observados actualmente (55 ATP y 55 WTA). Las otras combinaciones previstas solo podrán evaluarse al acumular sus propios partidos.', '',
        'Se calculan Log-Loss y Brier de todo el vector de resultados, curvas de calibración y ECE binario condicionado a acción. Los empates por línea y sets no disputados conservan su masa de probabilidad y su cuenta separada. El marcador por sets se evalúa como una sola tarea multiclase.', '',
        'Los partidos con retiro, descalificación o walkover permanecen fuera del contrato probabilístico de partido completado y dentro del denominador de cobertura. Una fuente de resultado inválida deja el evento pendiente y visible; no se borra del denominador.', '',
        'Los mínimos por contrato son 500 partidos y 30 bloques de competición, periodo cerrado, cobertura de al menos 80% y evidencia de calibración en bandas de alta confianza con al menos 200 observaciones. Son criterios de diseño, no garantías; los intervalos corrigen las múltiples comparaciones y se calculan por competiciones y fechas. Superarlos solo habilita revisión independiente.', '',
        'Las diez familias usan Markov coherente sin recalibración posterior. Su probabilidad de ganador puede diferir del híbrido del estudio original de ganador. Se conservan ambas versiones por separado.', '',
        'El registro nuevo usa su hora real de creación, posterior al registro original de ganador. El sello DigiCert anterior no cubre este protocolo ni estos registros. No se consumieron créditos de cuotas ni se ejecutaron apuestas.', '',
        '[Ver probabilidades de cada contrato](PRONOSTICOS_POR_MERCADO.md). Los JSON individuales conservan fuentes, probabilidades y huellas. El estudio va del 20 de octubre de 2026 al 1 de julio de 2027; no se declara éxito anticipado.']
    detail=['# Probabilidades prospectivas por partido y mercado','',
        'A y B siguen el orden indicado para cada encuentro. Probabilidades del modelo para partidos completados; no son garantías ni recomendaciones financieras. La alternativa complementaria se obtiene de las columnas; no se cuenta como otra observación independiente.', '']
    for value in records:
        event=value['event']
        detail += [f"## A: {event['home_team']} — B: {event['away_team']}", '',
            f"Circuito: {value['circuit']}. Inicio estimado UTC: {event['commence_time']}. Registro nuevo: {value['sealed_at']}.", '',
            '| Mercado y condición | Probabilidad favorable | Sin acción / empate | Alternativa |','|---|---:|---:|---:|']
        for row in value['rows']:
            c=row['contract'];p=row['probabilities'];label=LABELS[c['kind']]
            if c['kind']=='correct_score':
                for score,prob in p.items():detail.append(f'| {label}: {score} | {prob:.2%} | — | — |')
                continue
            if c.get('set_number'):label+=f", set {c['set_number']}"
            if c.get('line') is not None:label+=f", línea {c['line']:+g}"
            label+=f" ({'más de' if c['selection']=='over' else 'sí' if c['selection']=='yes' else 'A'})"
            detail.append(f"| {label} | {p['win']:.2%} | {p['push']:.2%} | {p['loss']:.2%} |")
        detail.append('')
    for name, lines in [('RESUMEN.md',summary),('PRONOSTICOS_POR_MERCADO.md',detail)]:
        with (root/name).open('x',encoding='utf8') as f:f.write('\n'.join(lines)+'\n')
    historical=Path('data/tennis/predictive_quality_v3_20261019_v3/all_market_quality.json')
    if historical.exists():
        source=read(historical)
        write_new(root/'historical_context.json',dict(source_path=str(historical.resolve()),source_sha256=digest(historical),
            scope='Previously inspected 2026 exploratory data; contracts differ from the new board; not prospective evidence',
            original_probability_rows=source['original_probability_rows'],filtered_probability_rows=source['after_common_identity_filter'],
            groups=[dict(circuit=r['circuit'],best_of=r['best_of'],contract=r['contract'],n=r['binary_n'],metrics=r['quality']['metrics']) for r in source['contracts']]))
    print(dict(events=len(records),contracts=tasks,groups=len(report['groups'])))


if __name__=='__main__':main()
