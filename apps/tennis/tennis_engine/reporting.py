"""Local HTML report for reviewed research evidence; no services or bet controls."""
from html import escape
from pathlib import Path


def render(audit,output,comparisons=None):
    def table(headers,rows):
        return '<table><thead><tr>'+''.join('<th>'+escape(str(h))+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join(
            '<tr>'+''.join('<td>'+escape(str(value))+'</td>' for value in row)+'</tr>' for row in rows)+'</tbody></table>'
    phases=table(['Fase','Estado','Límite actual'],[(r['phase'],r['status'],r['limit']) for r in audit['readiness']])
    models=table(['Circuito','Partidos de entrenamiento','Último periodo','Origen del modelo'],
                 [(r['circuit'],r['training_matches'],r['last_period'],r['cutoff']) for r in audit['models']])
    markets=''
    for entry in comparisons or []:
        rows=entry['rows'];event=entry['event']
        markets+='<h3>'+escape(event['home_team']+' / '+event['away_team'])+'</h3>'
        markets+='<p>'+escape(entry['label'])+'</p>'
        markets+=table(['Casa','Mercado','Selección','Línea','Cuota observada','P ganar','P devolución','Cuota justa','Cálculo','Precio utilizable hoy'],
            [(r['bookmaker'],r['market'],r['selection'],r['line'],r['decimal_odds'],
              round(r['win'],4) if 'win' in r else '—',round(r['push'],4) if 'push' in r else '—',
              round(r['fair_decimal_odds'],3) if r.get('fair_decimal_odds') else '—',
              'Calculado para investigación' if r['status']=='priced_research' else 'Pendiente','No') for r in rows])
    body=f'''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Auditoría del motor de tenis</title><style>
body{{font:16px system-ui;background:#f4f6f7;color:#152c32;margin:0}}main{{max-width:1220px;margin:auto;padding:36px}}
h1{{font-size:34px}}h2{{margin-top:38px}}.status{{background:#fff3cd;padding:20px;border-left:5px solid #a06c10}}
.metrics{{display:flex;gap:18px;flex-wrap:wrap;margin:24px 0}}.metric{{background:white;padding:20px;border-radius:10px;min-width:180px}}
.metric b{{display:block;font-size:28px;color:#176664}}table{{border-collapse:collapse;background:white;width:100%;font-size:14px}}
th,td{{padding:11px;border-bottom:1px solid #dde4e7;text-align:left}}th{{background:#dbeae8}}section{{overflow:auto}}
small{{color:#55676e}}input{{padding:12px;width:300px;max-width:80%;border:1px solid #aabfc5;border-radius:6px}}
</style><main><h1>Motor de tenis · auditoría por fases</h1><p>{escape(audit['audited_at'])}</p>
<div class="status"><b>Investigación local. Producción pendiente.</b><p>La integridad de los archivos y las pruebas del programa no demuestran rentabilidad. Las probabilidades de mercados secundarios necesitan validación propia.</p></div>
<div class="metrics"><div class="metric"><b>{audit['originals']['count']}</b>originales revisados</div><div class="metric"><b>{audit['canonical']['rows']:,}</b>partidos canónicos</div><div class="metric"><b>{audit['canonical']['eligible']:,}</b>partidos aptos</div><div class="metric"><b>{len(audit['failures'])}</b>fallos de integridad</div></div>
<h2>Estado por fase</h2><section>{phases}</section><h2>Datos usados por los modelos</h2><section>{models}</section>
<h2>Mercados observados</h2><p>Reproducción local sobre cuotas archivadas: no constituye un pronóstico emitido a la hora de esas cuotas. No se calcula ROI ni se presenta como apuesta actual.</p>
<input id="filter" aria-label="Filtrar filas de mercados" placeholder="Filtrar casa, mercado o jugador"><section id="markets">{markets or '<p>Sin comparaciones adjuntas.</p>'}</section>
<h2>Observaciones de auditoría</h2><ul>{''.join('<li>'+escape(w)+'</li>' for w in audit['warnings']+audit['failures'])}</ul>
<p><small>Los hashes permiten detectar cambios frente al recibo conservado. El almacenamiento local no es una certificación externa de hora ni un repositorio inalterable.</small></p></main>
<script>document.getElementById('filter').addEventListener('input',function(){{let q=this.value.toLowerCase();document.querySelectorAll('#markets tbody tr').forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(q))}})</script></html>'''
    Path(output).write_text(body,encoding='utf-8')
