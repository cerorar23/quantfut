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


GRUPO_DE_MERCADO = {'h2h': 'RESULTADO', 'double_chance': 'DOBLE OPORTUNIDAD', 'totals': 'GOLES',
                    'team_totals_home': 'GOLES DE EQUIPO', 'team_totals_away': 'GOLES DE EQUIPO',
                    'btts': 'AMBOS MARCAN', 'spreads': 'HÁNDICAP', 'win_to_nil': 'ESPECIALES',
                    'ht_btts': '1ª MITAD', 'ht_goal': '1ª MITAD', 'corners': 'CÓRNERS',
                    'corners_home': 'CÓRNERS', 'corners_away': 'CÓRNERS', 'cards': 'TARJETAS'}


def solo_candados(bloqueados: list[dict]) -> dict | None:
    """
    Partido sin modelo de goles (no hay lista completa que construir) pero con pronósticos VIP
    reales: se avisan SOLO con su categoría, igual que los candados de `aplicar_acceso`. Sin
    marcadores (no hay modelo que los calcule) y marcado `sin_modelo` para que la app no
    prometa lo que ni un VIP vería.
    """
    filas = [{'id': str(p.get('pick_key') or p.get('match_id')), 'grupo': GRUPO_DE_MERCADO[p['market']],
              'locked': True} for p in bloqueados if p.get('market') in GRUPO_DE_MERCADO]
    if not filas:
        return None
    filas.sort(key=lambda f: GRUPOS.index(f['grupo']))
    return {'filas': filas, 'marcadores': None, 'abiertas': 0, 'total': len(filas), 'sin_modelo': True}


def _prob_pick(pick: dict | None) -> float | None:
    try:
        p = float((pick or {})['prob'])
    except (KeyError, TypeError, ValueError):
        return None
    return p if math.isfinite(p) and 0 < p < 1 else None


def _con_pick(f: dict, pick: dict | None) -> dict:
    """Fila abierta con la probabilidad sellada y la cuota publicada del pick, si las trae."""
    prob = _prob_pick(pick)
    if prob is not None:
        f['prob'], f['nivel'], f['cuota'] = round(prob, 4), nivel(prob), round(1.0 / prob, 2)
    price = (pick or {}).get('ref_price', (pick or {}).get('price'))
    if isinstance(price, (int, float)) and price > 1:
        f['cuota'], f['cuota_tipo'] = round(float(price), 2), 'publicada'
        f['oportunidad'] = f['prob'] * float(price) > 1.02
    return f


_TITULO_DE_MERCADO = {'h2h': 'Ganador del partido', 'double_chance': 'Doble oportunidad',
                      'totals': 'Goles totales', 'team_totals_home': 'Goles del local',
                      'team_totals_away': 'Goles del visitante', 'btts': 'Ambos marcan',
                      'spreads': 'Hándicap asiático', 'win_to_nil': 'Gana a cero',
                      'ht_btts': 'Ambos anotan en el 1er tiempo', 'ht_goal': 'Gol en el 1er tiempo',
                      'corners': 'Córners totales', 'corners_home': 'Córners del local',
                      'corners_away': 'Córners del visitante', 'cards': 'Tarjetas totales'}


def _fila_de_pick(pick: dict) -> dict | None:
    """Fila para un pick abierto que el análisis no lista (otro lado u otra línea)."""
    market, prob = pick.get('market'), _prob_pick(pick)
    if market not in GRUPO_DE_MERCADO or prob is None:
        return None
    line = None if pick.get('line') is None else float(pick['line'])
    grupo = 'EMPATE NO ACCIÓN' if market == 'spreads' and line == 0 else GRUPO_DE_MERCADO[market]
    titulo = 'Empate no acción' if grupo == 'EMPATE NO ACCIÓN' else _TITULO_DE_MERCADO[market]
    return _fila(grupo, titulo, market, str(pick.get('selection')), line,
                 str(pick.get('texto') or ''), prob)


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

    Una fila que es un pick abierto enseña la probabilidad SELLADA del pick, no la del
    análisis: la misma selección no puede salir con dos porcentajes en la misma pantalla
    (auditoría 2026-10-25: 76 % en el destacado y 79 % en la lista). Y un pick abierto
    cuyo lado no es el más probable del análisis («Barcelona o empate» cuando la lista da
    «Barcelona o Real Madrid») no desaparece: se añade como fila propia.
    """
    abiertas_f, cerradas = [], []
    usadas: set[str] = set()
    for f in filas:
        pick = abiertas.get(f['id'])
        if plus or pick is not None:
            f = _con_pick(dict(f), pick)
            if pick is not None:
                usadas.add(f['id'])
            abiertas_f.append(f)
        else:
            cerradas.append({'id': f['id'], 'grupo': f['grupo'], 'locked': True})
    for key, pick in abiertas.items():
        if key not in usadas and (fila := _fila_de_pick(pick)) is not None:
            abiertas_f.append(_con_pick(fila, pick))
    abiertas_f.sort(key=lambda f: -f['prob'])
    cerradas.sort(key=lambda f: GRUPOS.index(f['grupo']) if f['grupo'] in GRUPOS else len(GRUPOS))
    return abiertas_f + cerradas, (marcadores if plus or abiertas else None)


# --- acceso de la WEB (independiente del de la app) -----------------------------------------

RANGO_DESTACADO = (1.40, 1.80)   # cuota del modelo: 1/prob (o la publicada si el pick abierto la trae)
GRATIS_WEB = 3                   # mercados abiertos para quien no tiene VIP


def aplicar_acceso_web(filas: list[dict], marcadores: list[dict], abiertas: dict[str, dict],
                       plus: bool) -> tuple[list[dict], list[dict] | None, dict | None]:
    """
    Regla de la web (decisión del titular, 2026-10-28), distinta de la de la app:
    - Destacado: de TODOS los mercados del partido, también los que sin VIP salen con candado,
      el de mayor probabilidad con cuota entre 1,40 y 1,80. Se enseña abierto y gratis.
    - Gratis: el destacado y los siguientes de mayor probabilidad dentro de ese rango hasta
      sumar `GRATIS_WEB`; si el rango no da para tanto, se completa con los más probables.
    - El resto sigue con candado (solo categoría) y los picks sellados ya abiertos se conservan.
    Con VIP todo va abierto. Los marcadores no se regalan por esto: solo con VIP o con un pick abierto.
    """
    efectivas = {f['id']: _con_pick(dict(f), abiertas.get(f['id'])) for f in filas}
    en_rango = sorted((f for f in efectivas.values()
                       if f.get('cuota') and RANGO_DESTACADO[0] <= f['cuota'] <= RANGO_DESTACADO[1]),
                      key=lambda f: -f['prob'])
    elegidas = [f['id'] for f in en_rango[:GRATIS_WEB]]
    if len(elegidas) < GRATIS_WEB:
        resto = sorted((f for f in efectivas.values() if f['id'] not in elegidas), key=lambda f: -f['prob'])
        elegidas += [f['id'] for f in resto[:GRATIS_WEB - len(elegidas)]]
    gratis = {key: abiertas.get(key) or {} for key in elegidas}
    filas_out, marcadores_out = aplicar_acceso(filas, marcadores, {**abiertas, **{k: v for k, v in gratis.items() if k not in abiertas}}, plus)
    destacado = None
    if en_rango:
        destacado = dict(efectivas[en_rango[0]['id']], destacado=True, locked=False)
        pick = abiertas.get(destacado['id'])
        if pick and pick.get('pick_key'):
            destacado['pick_key'] = pick['pick_key']
        for fila in filas_out:
            if fila['id'] == destacado['id']:
                fila['destacado'] = True
    return filas_out, (marcadores if plus or abiertas else None), destacado


# --- fuentes de lambdas ---------------------------------------------------------------------

def lambdas_goles(match_id: str) -> tuple[float, float, float] | None:
    """(lambda, mu, rho): la predicción propia o, si la liga no tiene modelo o el modelo no
    conoce a alguno de los equipos (`both_teams_known=false`), el ajuste a Pinnacle."""
    row = query_one("SELECT home_lambda, away_lambda, rho, "
                    "data_completeness->>'both_teams_known' AS conocido FROM predictions WHERE match_id=%s "
                    'ORDER BY generated_at DESC LIMIT 1', (match_id,))
    if row and str(row.get('conocido')).lower() != 'false':
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
              plus: bool, web: bool = False) -> dict | None:
    """Lista completa del partido con el acceso ya aplicado; None si no hay modelo de goles.

    `web=True` aplica la regla de la web (`aplicar_acceso_web`); la app sigue con `aplicar_acceso`."""
    lam = lambdas_goles(match_id)
    if lam is None:
        return None
    filas, marcadores = filas_goles(*lam, local, visitante)
    filas += filas_primer_tiempo(lam[0], lam[1])
    corners, tarjetas = lambdas_estadisticas(match_id)
    filas += filas_estadisticas(corners, tarjetas)
    if web:
        filas, marcadores, destacado = aplicar_acceso_web(filas, marcadores, abiertas, plus)
        return {'filas': filas, 'marcadores': marcadores, 'destacado': destacado,
                'rango': list(RANGO_DESTACADO), 'abiertas': sum(not f['locked'] for f in filas),
                'total': len(filas)}
    filas, marcadores = aplicar_acceso(filas, marcadores, abiertas, plus)
    return {'filas': filas, 'marcadores': marcadores,
            'abiertas': sum(not f['locked'] for f in filas), 'total': len(filas)}
