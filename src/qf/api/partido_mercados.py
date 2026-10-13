"""
Lista de mercados de un partido (pestaña Pronósticos de la app).

Todo sale de (lambda, mu, rho): con ellos `pricing` reproduce EXACTAMENTE lo que
el modelo guarda en `predictions.markets` (comprobado: diferencia 0,0 en 40
predicciones), y para las ligas solo sharp los saca del ajuste a Pinnacle del
pick. Córners y tarjetas usan el modelo estadístico y SOLO sus líneas validadas
(`estadisticas_mercado.LINEAS_HABILITADAS`): cambiar líneas exige repetir su prueba.

No son picks sellados: es análisis. Lo que el usuario puede ver abierto sale de
`aplicar_acceso`; el resto va con candado y sin línea, selección, probabilidad,
cuota ni orden por probabilidad.
"""
from __future__ import annotations

import math
import time
from datetime import datetime, timezone

from ..db import query_one
from ..model import estadisticas_mercado as em
from ..model import primer_tiempo as modelo_1t
from ..model import pricing

NIVEL_ALTA, NIVEL_SOLIDA = .75, .60

# Orden canónico de las categorías (el de los candados, que no ordena por probabilidad).
GRUPOS = ('RESULTADO', 'DOBLE OPORTUNIDAD', 'EMPATE NO ACCIÓN', 'GOLES', 'GOLES DE EQUIPO',
          'AMBOS MARCAN', 'HÁNDICAP', 'ESPECIALES', '1ª MITAD', 'CÓRNERS', 'TARJETAS')

LINEAS_GOLES = (1.5, 2.5, 3.5, 4.5)
LINEAS_EQUIPO = (0.5, 1.5)
MARCADORES = 5


def nivel(prob: float) -> str:
    return 'alta' if prob >= NIVEL_ALTA else 'solida' if prob >= NIVEL_SOLIDA else 'moderada'


def _fmt(linea: float) -> str:
    return f'{linea:g}'.replace('.', ',')


def clave(market: str, selection: str, line) -> str:
    """Misma clave que usan los picks (market, selection, line) para casar fila y pick."""
    return f"{market}:{selection}:{None if line is None else float(line)}"


def _fila(grupo: str, titulo: str, market: str, selection: str, line, texto: str, prob: float,
          nota: str | None = None) -> dict:
    return {'id': clave(market, selection, line), 'grupo': grupo, 'titulo': titulo,
            'market': market, 'selection': selection, 'line': line, 'seleccion': texto,
            'prob': round(float(prob), 4), 'nivel': nivel(prob),
            'cuota': round(1.0 / prob, 2) if prob > 0 else None, 'cuota_tipo': 'justa',
            'nota': nota, 'locked': False}


def _mejor(par: dict[str, float]) -> tuple[str, float]:
    sel = max(par, key=lambda k: par[k])
    return sel, par[sel]


def filas_goles(lam: float, mu: float, rho: float, local: str, visitante: str):
    """Filas del modelo de goles y los marcadores más probables."""
    m = pricing.score_matrix(lam, mu, rho)
    filas: list[dict] = []
    nombre = {'home': local, 'away': visitante}

    p1x2 = pricing.market_1x2(m)
    sel, p = _mejor(p1x2)
    txt = {'home': f'Gana {local}', 'draw': 'Empate', 'away': f'Gana {visitante}'}[sel]
    filas.append(_fila('RESULTADO', 'Ganador del partido', 'h2h', sel, None, txt, p))

    sel, p = _mejor(pricing.market_double_chance(m))
    txt = {'1X': f'{local} o empate', 'X2': f'{visitante} o empate',
           '12': f'{local} o {visitante} (sin empate)'}[sel]
    filas.append(_fila('DOBLE OPORTUNIDAD', 'Doble oportunidad', 'double_chance', sel, None, txt, p))

    dnb = pricing.market_asian_handicap(m, 0.0)
    side, p = _mejor({'home': dnb['home'], 'away': dnb['away']})
    filas.append(_fila('EMPATE NO ACCIÓN', 'Empate no acción', 'spreads', side, 0.0,
                       f'{nombre[side]} gana (empate devuelve)', p))

    for ln in LINEAS_GOLES:
        t = pricing.market_totals(m, ln)
        sel, p = _mejor({'over': t['over'], 'under': t['under']})
        filas.append(_fila('GOLES', 'Goles totales', 'totals', sel, ln,
                           f"{'Más' if sel == 'over' else 'Menos'} de {_fmt(ln)} goles", p,
                           nota=f'Goles esperados: {lam + mu:.2f}'.replace('.', ',')))

    for side in ('home', 'away'):
        for ln in LINEAS_EQUIPO:
            t = pricing.market_team_total(m, ln, side)
            sel, p = _mejor({'over': t['over'], 'under': t['under']})
            esp = lam if side == 'home' else mu
            filas.append(_fila('GOLES DE EQUIPO', f'Goles de {nombre[side]}',
                               f'team_totals_{side}', sel, ln,
                               f"{'Más' if sel == 'over' else 'Menos'} de {_fmt(ln)} goles", p,
                               nota=f'Goles esperados: {esp:.2f}'.replace('.', ',')))

    sel, p = _mejor(pricing.market_btts(m))
    filas.append(_fila('AMBOS MARCAN', 'Ambos marcan', 'btts', sel, None,
                       'Marcan los dos' if sel == 'yes' else 'No marcan los dos', p))

    fav = 'home' if p1x2['home'] >= p1x2['away'] else 'away'
    dog = 'away' if fav == 'home' else 'home'
    for side, ln in ((fav, -1.0), (fav, -1.5), (dog, 1.5)):
        home_line = ln if side == 'home' else -ln
        p = pricing.market_asian_handicap(m, home_line)[side]
        filas.append(_fila('HÁNDICAP', 'Hándicap asiático', 'spreads', side, ln,
                           f"{nombre[side]} {'+' if ln > 0 else ''}{_fmt(ln)}", p,
                           nota=f'xG: {local} {lam:.2f} · {visitante} {mu:.2f}'.replace('.', ',')))

    nil = {'home': float(m[1:, 0].sum()), 'away': float(m[0, 1:].sum())}
    side, p = _mejor(nil)
    filas.append(_fila('ESPECIALES', 'Gana a cero', 'win_to_nil', side, None,
                       f'{nombre[side]} gana sin recibir gol', p))

    marcadores = [{'marcador': r['score'], 'prob': round(r['prob'], 4)}
                  for r in pricing.market_correct_score(m, MARCADORES)]
    return filas, marcadores


def filas_primer_tiempo(lam: float, mu: float) -> list[dict]:
    """
    1ª mitad: SOLO los dos mercados que pasaron la prueba histórica y solo por el lado
    y en el tramo medido (`model/primer_tiempo`): «ambos anotan 1T: no» y «gol en 1T: sí».
    Si la probabilidad cae fuera de lo medido no se publica nada.
    """
    p = modelo_1t.probs(lam, mu)
    lo, hi = modelo_1t.PROB_MIN_VALIDADA, modelo_1t.PROB_MAX_VALIDADA
    filas: list[dict] = []
    no_ambos = 1 - p['ambos_1t_si']
    if lo <= no_ambos <= hi:
        filas.append(_fila('1ª MITAD', 'Ambos anotan en el 1er tiempo', 'ht_btts', 'no', None,
                           'No marcan los dos en el 1T', no_ambos))
    if lo <= p['gol_1t_si'] <= hi:
        filas.append(_fila('1ª MITAD', 'Gol en el 1er tiempo', 'ht_goal', 'yes', None,
                           'Habrá gol en el 1T', p['gol_1t_si']))
    return filas


def filas_estadisticas(corners: tuple[float, float] | None,
                       tarjetas: tuple[float, float] | None) -> list[dict]:
    """Córners y tarjetas: solo las líneas validadas, por el lado que validó."""
    filas: list[dict] = []
    for mercado, lam, grupo, cosa in (('corners', corners, 'CÓRNERS', 'córners'),
                                      ('cards', tarjetas, 'TARJETAS', 'tarjetas')):
        if lam is None:
            continue
        media = lam[0] + lam[1]
        for lado, ln in em.LINEAS_HABILITADAS[mercado]:
            p = em.prob(mercado, lam, lado, ln)
            filas.append(_fila(grupo, f'{cosa.capitalize()} totales', mercado, lado, ln,
                               f"{'Más' if lado == 'over' else 'Menos'} de {_fmt(ln)} {cosa}", p,
                               nota=f'Media esperada: {media:.1f}'.replace('.', ',')))
    return filas


def aplicar_acceso(filas: list[dict], marcadores: list[dict], abiertas: dict[str, dict],
                   plus: bool) -> tuple[list[dict], list[dict] | None]:
    """
    `abiertas` = picks que el usuario ya puede ver, por clave. Con VIP se ve todo. Un partido
    con un pronóstico abierto (gratis o desbloqueado) enseña además sus marcadores más
    probables (decisión del titular, 2026-10-13): todo lo del pronóstico va abierto; los demás
    mercados siguen siendo VIP.
    Las filas sin acceso salen con candado y SOLO su categoría: sin línea, selección,
    probabilidad, nivel ni cuota, y en orden canónico (el orden por probabilidad
    filtraría cuál es más probable). Las abiertas llevan la cuota publicada del pick.
    """
    abiertas_f, cerradas = [], []
    for f in filas:
        pick = abiertas.get(f['id'])
        if plus or pick is not None:
            f = dict(f)
            price = (pick or {}).get('ref_price', (pick or {}).get('price'))
            if isinstance(price, (int, float)) and price > 1:
                f['cuota'], f['cuota_tipo'] = round(float(price), 2), 'publicada'
                f['oportunidad'] = f['prob'] * float(price) > 1.02
            abiertas_f.append(f)
        else:
            cerradas.append({'id': f['id'], 'grupo': f['grupo'], 'locked': True})
    abiertas_f.sort(key=lambda f: -f['prob'])
    cerradas.sort(key=lambda f: GRUPOS.index(f['grupo']) if f['grupo'] in GRUPOS else len(GRUPOS))
    return abiertas_f + cerradas, (marcadores if plus or abiertas else None)


# --- fuentes de lambdas ---------------------------------------------------------------------

def lambdas_goles(match_id: str) -> tuple[float, float, float] | None:
    """(lambda, mu, rho): la predicción propia o, si la liga no tiene modelo, el ajuste a Pinnacle."""
    row = query_one('SELECT home_lambda, away_lambda, rho FROM predictions WHERE match_id=%s '
                    'ORDER BY generated_at DESC LIMIT 1', (match_id,))
    if row:
        vals = (float(row['home_lambda']), float(row['away_lambda']), float(row['rho'] or 0))
    else:
        row = query_one('SELECT fit FROM alta_prob_picks WHERE match_id=%s AND fit IS NOT NULL '
                        'ORDER BY decided_at DESC LIMIT 1', (match_id,))
        fit = row['fit'] if row else None
        try:
            vals = (float(fit['lambda']), float(fit['mu']), float(fit.get('rho') or 0))
        except (TypeError, KeyError, ValueError, AttributeError):
            return None
    ok = all(math.isfinite(v) and abs(v) < 10 for v in vals) and vals[0] > 0 and vals[1] > 0
    return vals if ok else None


_TTL = 3600.0
_acc: dict[tuple[str, str], tuple[float, object]] = {}


def _acumulador(liga: str, mercado: str):
    """Acumulador de la liga con los partidos terminados hasta ahora; en caché una hora."""
    clave_ = (liga, mercado)
    hit = _acc.get(clave_)
    if hit and time.monotonic() - hit[0] < _TTL:
        return hit[1]
    from ..publish import escalera_datos
    acc = escalera_datos.Modelos(datetime.now(timezone.utc)).de(liga, mercado)
    _acc[clave_] = (time.monotonic(), acc)
    return acc


def lambdas_estadisticas(match_id: str) -> tuple[tuple[float, float] | None, tuple[float, float] | None]:
    """(córners, tarjetas) esperados por equipo; None si el modelo no tiene datos suficientes."""
    m = query_one('SELECT league_id, kickoff_utc, home_team_id, away_team_id, referee '
                  'FROM matches WHERE match_id=%s', (match_id,))
    if not m:
        return None, None
    out = []
    for mercado in ('corners', 'cards'):
        try:
            acc = _acumulador(m['league_id'], mercado)
            out.append(acc.lambdas(m['kickoff_utc'], m['home_team_id'], m['away_team_id'],
                                   m['referee']) if acc else None)
        except Exception:  # noqa: BLE001 - un fallo del modelo estadístico no tumba el detalle
            out.append(None)
    return out[0], out[1]


def construir(match_id: str, local: str, visitante: str, abiertas: dict[str, dict],
              plus: bool) -> dict | None:
    """Lista completa del partido con el acceso ya aplicado; None si no hay modelo de goles."""
    lam = lambdas_goles(match_id)
    if lam is None:
        return None
    filas, marcadores = filas_goles(*lam, local, visitante)
    filas += filas_primer_tiempo(lam[0], lam[1])
    corners, tarjetas = lambdas_estadisticas(match_id)
    filas += filas_estadisticas(corners, tarjetas)
    filas, marcadores = aplicar_acceso(filas, marcadores, abiertas, plus)
    return {'filas': filas, 'marcadores': marcadores,
            'abiertas': sum(not f['locked'] for f in filas), 'total': len(filas)}
