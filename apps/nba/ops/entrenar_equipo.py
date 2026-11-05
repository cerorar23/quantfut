"""Entrenamiento LOCAL de ratings por posesión, ritmo, varianza de regulación y probabilidad de OT.

Entrada: exportación SELECT de equipos con recepción/corte. Nunca conecta a producción ni publica artefactos.
    python apps/nba/ops/entrenar_equipo.py exportacion.json equipo.json
"""
from collections import Counter, defaultdict, deque
from datetime import date, datetime, UTC
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from nba.v2 import nucleo
from nba.v2.duracion import minutos_partido

P = nucleo.Parametros(eta=.045, arrastre=.65, eta_liga=.01, efecto_b2b=2.90)
VENTANA_RITMO = 10


def posesiones(m):
    if m.get('posesiones') is not None:
        return float(m['posesiones'])
    campos = ('tiros_campo_intentados', 'tiros_libres_intentados', 'rebotes_ofensivos', 'perdidas')
    if any(m.get(k) is None for k in campos):
        return None
    return float(m[campos[0]] + .44 * m[campos[1]] - m[campos[2]] + m[campos[3]])


def preparar(obj):
    corte = datetime.fromisoformat(obj['captured_at_utc'])
    if corte.tzinfo is None:
        raise ValueError('corte de recepción sin zona')
    elegidos, descartes = {}, Counter()
    for pid, fecha, temporada, local, visit, l, v, rec_l, rec_v in obj['rows']:
        recepciones = [datetime.fromisoformat(r) for r in (rec_l, rec_v)]
        if any(r.tzinfo is None or r > corte for r in recepciones):
            raise ValueError('recepción posterior al corte exportado')
        if date.fromisoformat(fecha) >= corte.date():
            raise ValueError('fecha objetivo o futura en entrenamiento')
        dur_l, dur_v = minutos_partido(l.get('minutos')), minutos_partido(v.get('minutos'))
        pos_l, pos_v = posesiones(l), posesiones(v)
        if dur_l is None or dur_v is None or dur_l != dur_v or pos_l is None or pos_v is None or min(pos_l, pos_v) <= 0:
            descartes['sin_exposicion_verificable'] += 1
            continue
        if local == visit or not np.isfinite([l['puntos'], v['puntos'], pos_l, pos_v]).all() or l['puntos'] == v['puntos']:
            descartes['marcador_invalido'] += 1
            continue
        g = dict(pid=int(pid), fecha=fecha, temporada=temporada, local=local, visit=visit,
                 pl=float(l['puntos']), pv=float(v['puntos']), posesiones=(pos_l + pos_v) / 2,
                 duracion=dur_l, ot=int((dur_l - 48) / 5))
        clave = (fecha, local, visit)
        if clave in elegidos:
            previo = elegidos[clave]
            if previo is None:
                continue
            if (previo['pl'], previo['pv']) != (g['pl'], g['pv']):
                elegidos[clave] = None; descartes['conflicto_identidad'] += 1
            else:
                descartes['duplicado_conciliado'] += 1
        else:
            elegidos[clave] = g
    juegos = sorted((g for g in elegidos.values() if g is not None), key=lambda g: (g['fecha'], g['pid']))
    return juegos, dict(descartes)


def recorrer(juegos):
    r, ultimo, ritmo = nucleo.Ratings(), {}, defaultdict(lambda: deque(maxlen=VENTANA_RITMO))
    dias = defaultdict(list)
    for g in juegos:
        dias[g['fecha']].append(g)
    temporada, registros = None, []
    for dia in sorted(dias):
        fecha = date.fromisoformat(dia)
        actual = dias[dia][0]['temporada']
        if temporada is not None and temporada != actual:
            nucleo.nueva_temporada(r, P)
        temporada = actual
        # Todas las predicciones del día preceden a cualquier actualización de ese día.
        for g in dias[dia]:
            dl = (fecha - ultimo[g['local']]).days if g['local'] in ultimo else 7
            dv = (fecha - ultimo[g['visit']]).days if g['visit'] in ultimo else 7
            p_l, p_v = r.esperado(g['local'], g['visit'], nucleo.ajuste_descanso(dl, dv, P))
            if len(ritmo[g['local']]) >= 5 and len(ritmo[g['visit']]) >= 5:
                pace = float((np.mean(ritmo[g['local']]) + np.mean(ritmo[g['visit']])) / 2)
                registros.append(dict(g, mu_l=p_l * pace / 100, mu_v=p_v * pace / 100, ritmo_proyectado=pace))
        for g in dias[dia]:
            dl = (fecha - ultimo[g['local']]).days if g['local'] in ultimo else 7
            dv = (fecha - ultimo[g['visit']]).days if g['visit'] in ultimo else 7
            nucleo.actualizar(r, g['local'], g['visit'], g['pl'] * 100 / g['posesiones'], g['pv'] * 100 / g['posesiones'],
                              P, nucleo.ajuste_descanso(dl, dv, P))
            for t in (g['local'], g['visit']):
                ultimo[t] = fecha
                ritmo[t].append(g['posesiones'] * 48 / g['duracion'])
    return r, ultimo, ritmo, registros


def ajustar_dispersion_ot(registros):
    if len(registros) < 200:
        raise ValueError('muestra insuficiente para congelar dispersión y OT')
    normales = [g for g in registros if g['ot'] == 0]
    if len(normales) < 150:
        raise ValueError('faltan finales sin prórroga para ajustar regulación')
    rm = np.array([(g['pl'] - g['pv']) - (g['mu_l'] - g['mu_v']) for g in normales])
    rt = np.array([(g['pl'] + g['pv']) - (g['mu_l'] + g['mu_v']) for g in normales])
    x = np.column_stack([np.ones(len(registros)), [abs(g['mu_l'] - g['mu_v']) for g in registros]])
    y = np.array([g['ot'] > 0 for g in registros], float)
    rate = (y.sum() + 1) / (len(y) + 2)
    initial = [float(np.log(rate / (1 - rate))), 0.]
    def loss(w):
        z = x @ w
        return float(np.mean(np.logaddexp(0, z) - y * z) + .001 * w[1] ** 2)
    fit = minimize(loss, initial, method='L-BFGS-B', bounds=[(None, None), (None, 0.)])
    if not fit.success:
        raise ValueError('el ajuste de OT no convergió')
    return dict(sigma_margen=float(np.std(rm, ddof=1)), sigma_total=float(np.std(rt, ddof=1)),
                ot=dict(intercepto=float(fit.x[0]), abs_margen=float(fit.x[1]), tasa_observada=float(y.mean()),
                        partidos=len(y), prorroga_detectada_por='duracion_validada_48_mas_5k'))


def entrenar(origen: Path, destino: Path):
    if destino.exists():
        raise ValueError('el artefacto de salida debe ser nuevo; no se sobrescriben versiones')
    raw = origen.read_bytes();obj = json.loads(raw.decode('utf-8-sig'))
    juegos, descartes = preparar(obj)
    if not juegos:
        raise ValueError('sin partidos con exposición verificable')
    r, ultimo, ritmo, registros = recorrer(juegos)
    # La receta está fijada; no elige variante mirando la temporada de prueba.
    usados = [g for g in registros if g['temporada'] > juegos[0]['temporada']]
    disp = ajustar_dispersion_ot(usados)
    artefacto = dict(formato='nba-equipo-congelado-1', unidad_ratings='puntos_por_100_posesiones',
        objetivo_simulacion='regulacion_mas_prorroga', conocido_en_utc=max(datetime.now(UTC),datetime.fromisoformat(obj['captured_at_utc'])).isoformat(),
        capturado_en_utc=obj['captured_at_utc'],
        datos_hasta=max(g['fecha'] for g in juegos), vigencia_horas=72,
        ataque=r.ataque, defensa=r.defensa, liga=r.liga, localia=r.localia, partidos=r.partidos,
        ritmo={t:float(np.mean(h)) for t,h in ritmo.items()},
        ultimos={t:f.isoformat() for t,f in ultimo.items()}, efecto_b2b=P.efecto_b2b,
        posesiones_referencia=float(np.mean([g['ritmo_proyectado'] for g in usados])),
        **disp, hashes_entradas={origen.name:hashlib.sha256(raw).hexdigest()},
        receta=dict(eta=P.eta, arrastre=P.arrastre, eta_liga=P.eta_liga, ventana_ritmo=VENTANA_RITMO,
                    predicciones_antes_de_actualizar_dia=True), descartes=descartes,
        evaluacion=dict(tipo='ajuste_local_no_certificacion_prospectiva', partidos=len(usados)))
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(artefacto, sort_keys=True, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(dict(partidos=len(juegos), descartes=descartes, datos_hasta=artefacto['datos_hasta'],
                         ot=artefacto['ot'], sigma_margen=artefacto['sigma_margen'], sigma_total=artefacto['sigma_total'],
                         sha256=hashlib.sha256(destino.read_bytes()).hexdigest()), indent=2))


if __name__ == '__main__':
    entrenar(Path(sys.argv[1]), Path(sys.argv[2]))
