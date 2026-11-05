"""Evaluación retrospectiva temporal de la receta de posesiones/OT; no acredita recepción histórica ni el híbrido de jugadores."""
from datetime import date
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.special import expit

from entrenar_equipo import preparar, recorrer, ajustar_dispersion_ot
from nba.v2 import nucleo, evaluacion


def evaluar(origen, destino, desde='2025-10-01', hasta='2026-04-30'):
    raw = origen.read_bytes()
    juegos, descartes = preparar(json.loads(raw.decode('utf-8-sig')))
    _, _, _, registros = recorrer(juegos)
    ajuste = [g for g in registros if '2022-10-01' <= g['fecha'] <= '2024-06-30']
    prueba = [g for g in registros if desde <= g['fecha'] <= hasta]
    if len(prueba)<10:raise ValueError('muestra insuficiente en la ventana temporal')
    d = ajustar_dispersion_ot(ajuste)
    referencia = float(np.mean([g['ritmo_proyectado'] for g in ajuste]))
    base = float(np.mean([g['pl'] > g['pv'] for g in ajuste]))
    p, y, grupos, ot_p, ot_y, totales = [], [], [], [], [], []
    for g in prueba:
        po = float(expit(d['ot']['intercepto'] + d['ot']['abs_margen'] * abs(g['mu_l'] - g['mu_v'])))
        escala = np.sqrt(g['ritmo_proyectado'] / referencia)
        m = nucleo.simular_con_ot(g['mu_l'], g['mu_v'], d['sigma_margen'] * escala,
            d['sigma_total'] * escala, g['ritmo_proyectado'], po, n=20000, semilla=g['pid'])
        p.append(float(np.mean(m.muestras[:, 0] > m.muestras[:, 1])))
        y.append(float(g['pl'] > g['pv'])); grupos.append(g['fecha'])
        ot_p.append(po); ot_y.append(float(g['ot'] > 0))
        total = m.muestras.sum(axis=1)
        bajo, alto = np.quantile(total, [.1,.9])
        observado = g['pl'] + g['pv']
        condicionada = total[(m.prorrogas > 0) == (g['ot'] > 0)]
        cb, ca = np.quantile(condicionada, [.1,.9])
        totales.append((g['ot'] > 0, observado, float(total.mean()), bajo <= observado <= alto,
                        float(condicionada.mean()), cb <= observado <= ca))
    p, y = np.array(p), np.array(y)
    r = dict(tipo='retrospectivo_walk_forward_por_fecha',
        acredita_recepcion_historica=False, acredita_hibrido_jugadores=False,
        calibracion_prospectiva_certificada=False,
        ajuste_hasta='2024-06-30', prueba_desde=desde, prueba_hasta=hasta,
        hashes_entradas={origen.name: hashlib.sha256(raw).hexdigest()}, descartes=descartes,
        ganador=evaluacion.informe_binario(p, y, np.full(len(p), base), grupos=grupos),
        ot=dict(prob_media=float(np.mean(ot_p)), frecuencia=float(np.mean(ot_y)),
                brier=evaluacion.brier(ot_p, ot_y), logloss=evaluacion.logloss(ot_p, ot_y)),
        totales_por_ot={str(ot):dict(n=len(sel), rmse=evaluacion.rmse([x[1] for x in sel],[x[2] for x in sel]),
                       cobertura80_incondicional=float(np.mean([x[3] for x in sel])),
                       rmse_condicionado_ot=evaluacion.rmse([x[1] for x in sel],[x[4] for x in sel]),
                       cobertura80_condicionada_ot=float(np.mean([x[5] for x in sel])))
                       for ot in (False,True) if (sel := [x for x in totales if x[0] == ot])},
        fiabilidad=[dict(desde=k/10,hasta=(k+1)/10,n=int(s.sum()),prob_media=float(p[s].mean()),
                        tasa=float(y[s].mean())) for k in range(10)
                     if (s := (p >= k/10) & (p < (k+1)/10)).any()])
    if destino.exists():
        raise ValueError('no se sobrescribe evidencia')
    destino.write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding='utf8')
    print(json.dumps({'n':len(p),'brier':r['ganador']['brier'],'logloss':r['ganador']['logloss'],
                      'pendiente':r['ganador']['pendiente'],'ot':r['ot']}))


if __name__ == '__main__':
    evaluar(Path(sys.argv[1]), Path(sys.argv[2]), *sys.argv[3:5])
