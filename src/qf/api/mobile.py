"""Real mobile content; feature controls never override model publication gates.

Access is checked before serialization. Public allocations are fixed per sealed
batch so refreshing as matches start cannot expose a rotating premium catalog.
"""
from __future__ import annotations

import copy
import logging
import math
from collections import defaultdict
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg.errors import UndefinedTable

from . import console, cuentas, fichas, panel, partido_mercados, rewards
from ..comercial import suscripciones, mobile_updates
from ..comercial.auditoria import audit
from ..db import conn, query, query_one
from ..config import settings
from ..publish import alta_prob_datos, alta_prob_ext, escalera_datos, ventana

router = APIRouter(tags=["mobile"])
_bearer = HTTPBearer(auto_error=False)
# Escalera: el escalón gratis sale del rango que puede elegir la regla del 80 % en 7 días
# (84-95 %; antes 75-90 %, el de la cuota 1,25-1,40, que ya casi no se daría).
PROB_MIN, PROB_MAX = .75, .97
# Alta probabilidad: lo que se MUESTRA es 73-95 % (decisión del usuario, 2026-10-12; el 11-oct
# se había ampliado a 62-95 %). Es un filtro de lectura: `alta_prob_ext` sigue sellando
# candidatos desde 62 % y sus filas inmutables no se tocan; solo dejan de mostrarse.
HIGH_MIN, HIGH_MAX = .73, .95
# Días de agenda que recibe la app (decisión del titular, 2026-10-12): una semana, agrupada por día.
DIAS_AGENDA = 7
# Gratis (decisión del usuario, 2026-10-27; sustituye «uno por mercado, hasta 4, cuota
# ≤ 1,60»): el 10 % de los pronósticos publicados en el lote del día, redondeado hacia
# arriba, los de mayor probabilidad, sin rango de cuota. Un rango 1,40-1,50 se probó el
# mismo día y se descartó: con 73-95 % de probabilidad no se publica ninguna cuota ahí.
FREE_FRACTION = .10
SECTIONS = {
    'agenda': 'Calendario de partidos', 'alta_probabilidad': 'Alta probabilidad',
    'escalera': 'Reto Escalera', 'estadisticas': 'Estadísticas del partido',
    'h2h': 'H2H, alineaciones y bajas', 'vip': 'Planes y acceso VIP',
    'nba': 'NBA', 'comunidad': 'La Grada', 'notificaciones': 'Notificaciones',
    'balance': 'Balance y seguimiento', 'medicion': 'Medición y errores',
    'idiomas': 'Idiomas', 'compras': 'Compras',
}


def features() -> dict:
    try:
        rows = query('SELECT section, enabled, message, updated_at FROM mobile_features')
    except UndefinedTable:
        raise HTTPException(503, 'Configuración móvil pendiente de instalar') from None
    existing = {r['section']: r for r in rows}
    return {key: existing.get(key, {'section': key, 'enabled': False,
                                   'message': 'Modelo en entrenamiento'})
            for key in SECTIONS}


def config() -> dict:
    return {**mobile_updates.configuration(), 'features': features(), 'probability_min': HIGH_MIN,
            'probability_max': HIGH_MAX, 'high_probability_free_fraction': FREE_FRACTION,
            'ladder_free_count': 1, 'server_time': datetime.now(timezone.utc)}


def member(creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
           request: Request = None) -> bool:
    if creds is None:
        return False
    cuentas.require_enabled()
    if request is not None and request.headers.get('x-qf-identity') == 'firebase':
        from .firebase import firebase_account
        account = firebase_account(creds, request)
    else:
        account = cuentas.current_account(creds)
    return suscripciones.active_subscription(account['account_id']) is not None


def pick_key(row: dict) -> str:
    return str(row.get('pick_key') or row['match_id'])


def probability(row: dict) -> float:
    return float(row.get('_prob_exact', row.get('prob')) or 0)


def free_quota(published: int) -> int:
    """Cuántos gratis le tocan a un lote de `published` pronósticos: el 10 %, hacia arriba."""
    return math.ceil(round(published * FREE_FRACTION, 9))


def free_eligible(row: dict) -> bool:
    """Sin rango de cuota, pero con cuota publicada real: sin ella no se regala."""
    return quote_of({'ref_price': row.get('ref_price')}) is not None


def _free_rank(row: dict) -> tuple:
    # Mayor probabilidad; el empate lo decide la cuota más alta.
    return -probability(row), -float(row['ref_price']), pick_key(row)


def choose_free(rows: list[dict], stream: str) -> list[dict]:
    """Only sealed eligible rows enter. Odds are publication quotes, not live."""
    lo, hi = (HIGH_MIN, HIGH_MAX) if stream == 'alta_probabilidad' else (PROB_MIN, PROB_MAX)
    valid = [r for r in rows if lo <= probability(r) <= hi]
    if stream == 'alta_probabilidad':
        return sorted(filter(free_eligible, valid), key=_free_rank)[:free_quota(len(valid))]
    if stream == 'escalera':
        valid.sort(key=lambda r: (-probability(r), -float(r.get('price') or 0), pick_key(r)))
        return valid[:1]
    raise ValueError('Unknown stream')


def _by_batch(rows: list[dict]) -> dict[str, list[dict]]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[str(row['batch_date'])].append(row)
    return grouped


def top_up(rows: list[dict], free_keys: set[str], now: datetime) -> list[dict]:
    """Pronósticos sin empezar que deben pasar a gratis aunque el lote ya esté repartido.

    `rows` es un lote completo. Completa el cupo del 10 % cuando falta (p. ej. un lote
    repartido con la regla anterior): cuentan los gratis que ya empezaron y los abiertos
    que cumplen la regla. Solo AÑADE y no toca los que ya empezaron.
    """
    valid = [r for r in rows if HIGH_MIN <= probability(r) <= HIGH_MAX]
    held = sum(1 for r in valid if pick_key(r) in free_keys
               and (r['kickoff_utc'] <= now or free_eligible(r)))
    missing = free_quota(len(valid)) - held
    if missing <= 0:
        return []
    pending = [r for r in valid if r['kickoff_utc'] > now and pick_key(r) not in free_keys
               and free_eligible(r)]
    return sorted(pending, key=_free_rank)[:missing]


def cap_free(rows: list[dict], free: set[str], now: datetime) -> set[str]:
    """
    Por lote, como mucho el 10 % (hacia arriba) gratis. Los que ya empezaron siguen visibles
    con su resultado y cuentan dentro del cupo; de los abiertos quedan los de mayor
    probabilidad. Los que sobran pasan a candado, con su cuota a la vista.
    """
    kept = set()
    for batch in _by_batch(rows).values():
        begun = {pick_key(r) for r in batch if pick_key(r) in free and r['kickoff_utc'] <= now}
        pending = sorted((r for r in batch if pick_key(r) in free and r['kickoff_utc'] > now
                          and free_eligible(r)), key=_free_rank)
        room = max(free_quota(len(batch)) - len(begun), 0)
        kept |= begun | {pick_key(r) for r in pending[:room]}
    return kept


def allocations(rows: list[dict], stream: str) -> set[str]:
    grouped = _by_batch(rows)
    if stream == 'escalera' and rows:
        # One free pending step across all active challenges, not one per
        # challenge or historical batch. Freeze the choice until a new batch.
        grouped = {max(grouped): rows}
    result = set()
    for batch, candidates in grouped.items():
        with conn() as c:
            c.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))',
                      (f'mobile:{stream}:{batch}',))
            existing = c.execute('SELECT free_count FROM mobile_allocation_batches '
                                 'WHERE stream=%s AND batch_date=%s', (stream, batch)).fetchone()
            if existing is None:
                selected = choose_free(candidates, stream)
                # Never finalize an empty batch: a source may not be sealed yet.
                if not candidates:
                    continue
                c.execute('INSERT INTO mobile_allocation_batches '
                          '(stream,batch_date,candidate_count,free_count) VALUES (%s,%s,%s,%s)',
                          (stream, batch, len(candidates), len(selected)))
                for row in selected:
                    c.execute('INSERT INTO mobile_free_allocations (stream,batch_date,pick_key) '
                              'VALUES (%s,%s,%s)', (stream, batch, pick_key(row)))
                audit(c, 'mobile:allocation', 'mobile_free_batch', detail={
                    'stream': stream, 'batch_date': batch, 'total': len(candidates), 'free': len(selected)})
            if stream == 'alta_probabilidad':
                have = {r['pick_key'] for r in c.execute(
                    'SELECT pick_key FROM mobile_free_allocations WHERE stream=%s AND batch_date=%s',
                    (stream, batch)).fetchall()}
                added = top_up(candidates, have, datetime.now(timezone.utc))
                for row in added:
                    c.execute('INSERT INTO mobile_free_allocations (stream,batch_date,pick_key) '
                              'VALUES (%s,%s,%s) ON CONFLICT DO NOTHING', (stream, batch, pick_key(row)))
                if added:
                    c.execute('UPDATE mobile_allocation_batches SET free_count=%s '
                              'WHERE stream=%s AND batch_date=%s', (len(have) + len(added), stream, batch))
                    audit(c, 'mobile:allocation_topup', 'mobile_free_batch', detail={
                        'stream': stream, 'batch_date': batch, 'added': [pick_key(r) for r in added],
                        'rule': 'ten_percent_by_probability'})
            selected_rows = c.execute('SELECT pick_key FROM mobile_free_allocations '
                                      'WHERE stream=%s AND batch_date=%s', (stream, batch)).fetchall()
            result.update(r['pick_key'] for r in selected_rows)
    return result


_HIGH_COLS = """a.match_id, m.league_id, m.kickoff_utc,
        COALESCE(th.display_name, th.canonical_name) AS local,
        COALESCE(ta.display_name, ta.canonical_name) AS visitante,
        a.market,a.selection,a.line,a.prob,a.ref_price,a.ref_book,a.odds_as_of,a.fit,
        b.batch_date,b.chain_sha256"""


def visible_agenda(rows: list[dict]) -> list[dict]:
    """Inicio solo enseña lo que está por jugarse o en juego: un partido terminado sale de la
    agenda (decisión del titular, 2026-10-12) y queda en los registros históricos."""
    return [m for m in rows if m.get('estado') != 'finished']


def high_rows() -> list[dict]:
    # The full immutable batch, including matches already started, fixes the
    # public fraction. A source gate can pause delivery but not rewrite a seal.
    rows = query(f'''SELECT {_HIGH_COLS},r.outcome,r.home_goals,r.away_goals
        FROM alta_prob_picks a JOIN matches m ON m.match_id=a.match_id
        JOIN teams th ON th.team_id=m.home_team_id JOIN teams ta ON ta.team_id=m.away_team_id
        {alta_prob_datos._sql_sellado()}
        LEFT JOIN alta_prob_results r ON r.alta_id=a.alta_id
        WHERE a.prob BETWEEN %s AND %s AND b.batch_date >= current_date - 7
        ORDER BY m.kickoff_utc,a.match_id''', (HIGH_MIN, HIGH_MAX))
    if settings.alta_prob_ext_enabled:
        # Un pronóstico por partido y mercado: si la línea de 80-95 % ya lo publicó,
        # esa fila manda y la ampliada no lo repite.
        seen = {(r['match_id'], r['market'], r['selection'], r['line']) for r in rows}
        try:
            extra = query(f'''SELECT {_HIGH_COLS},a.ext_id::text AS pick_key,
                r.outcome,r.home_goals,r.away_goals
                FROM alta_prob_ext a JOIN matches m ON m.match_id=a.match_id
                JOIN teams th ON th.team_id=m.home_team_id JOIN teams ta ON ta.team_id=m.away_team_id
                {alta_prob_ext.sql_sellado()}
                LEFT JOIN alta_prob_ext_results r ON r.ext_id=a.ext_id
                WHERE a.prob BETWEEN %s AND %s AND b.batch_date >= current_date - 7
                ORDER BY m.kickoff_utc,a.match_id''', (HIGH_MIN, HIGH_MAX))
        except UndefinedTable:
            extra = []
        rows += [r for r in extra if (r['match_id'], r['market'], r['selection'], r['line']) not in seen]
        rows.sort(key=lambda r: (r['kickoff_utc'], r['match_id']))
    from ..publish import alta_prob as ap
    for row in rows:
        row['texto'] = ap.texto(row['market'], row['selection'], row['line'], row['local'], row['visitante'])
    return rows


def implied_goals(fit: dict | None) -> dict | None:
    """Goles esperados implícitos en las cuotas sin margen (lambdas del ajuste).

    Solo existen en los mercados de goles; en el resto el cliente muestra «—».
    """
    try:
        home, away = float(fit['lambda']), float(fit['mu'])
    except (TypeError, KeyError, ValueError):
        return None
    if not (math.isfinite(home) and math.isfinite(away)):
        return None
    return {'local': round(home, 2), 'visita': round(away, 2), 'total': round(home + away, 2)}


def quote_of(row: dict) -> float | None:
    """Cuota publicada del pronóstico (la de la fuente al sellar), si es válida."""
    try:
        price = float(row.get('ref_price') or row.get('price'))
    except (TypeError, ValueError):
        return None
    return round(price, 2) if math.isfinite(price) and price > 1 else None


def metadata(row: dict) -> dict:
    # `market` es solo la categoría (goles, córners...): permite ubicar el candado
    # en su mercado. `cuota` es el gancho comercial (decisión del titular, 2026-10-13);
    # selección, línea y probabilidad siguen sin salir.
    return {**{key: row.get(key) for key in ('match_id','league_id','kickoff_utc','local','visitante','batch_date','market')},
            'locked': True, 'pick_key': pick_key(row), 'cuota': quote_of(row)}


def high_probability(plus: bool = False, unlocks: set[tuple[str,str]] | None = None,
                     started: bool = False) -> dict:
    # started=True keeps sealed picks of matches already underway or settled,
    # tagged with their result; the same free/VIP gating applies.
    flags = features()
    base = alta_prob_datos.informe_publico()
    base = {**base, 'proximos': [], 'vip': []}
    if not flags['alta_probabilidad']['enabled'] or base['estado'] != 'activa':
        return base
    rows = high_rows()
    now = datetime.now(timezone.utc)
    free = cap_free(rows, allocations(rows, 'alta_probabilidad'), now)
    for row in rows:
        begun = row['kickoff_utc'] <= now
        if begun and not started:
            continue
        public = pick_key(row) in free
        owned = ('alta_probabilidad',pick_key(row)) in (unlocks or set())
        if public or ((plus or owned) and flags['vip']['enabled']):
            value = {**row, 'prob': round(float(row['prob']), 2), 'locked': False,
                     'free': public, 'pick_key': pick_key(row), 'started': begun}
            value['xg'] = implied_goals(value.pop('fit', None))
            value['fair_price'] = round(1 / value['prob'], 2)
            base['proximos'].append(value)
        else:
            base['vip'].append(metadata(row))
    return base


def ladder(plus: bool = False, unlocks: set[tuple[str,str]] | None = None) -> dict:
    data = copy.deepcopy(escalera_datos.informe_publico())
    flags = features()
    if not flags['escalera']['enabled'] or not data['activo']:
        return {**data, 'actuales': []}
    candidates = []
    for challenge in data['actuales']:
        exact = {p['paso']: p for p in escalera_datos._pasos(challenge['reto_id'], solo_sellados=True)}
        for step in challenge['pasos']:
            if step['outcome'] is None and step.get('batch_date'):
                step['pick_key'] = f"{challenge['reto_id']}:{step['paso']}"
                step['_prob_exact'] = exact[step['paso']]['prob']
                candidates.append(step)
    free = allocations(candidates, 'escalera')
    for challenge in data['actuales']:
        visible, private = [], []
        for step in challenge['pasos']:
            if step['outcome'] is not None:
                visible.append(step)  # Historical losses stay auditable.
            elif PROB_MIN <= probability(step) <= PROB_MAX:
                public = pick_key(step) in free
                owned = ('escalera',pick_key(step)) in (unlocks or set())
                if public or ((plus or owned) and flags['vip']['enabled']):
                    visible.append({**{k: v for k, v in step.items() if not k.startswith('_')}, 'locked': False, 'free': public})
                else:
                    private.append(metadata(step))
        challenge['pasos'], challenge['vip'] = visible, private
    return data


@router.get('/mobile/v1/config')
def mobile_config(response: Response):
    response.headers['Cache-Control'] = 'no-store'
    return config()


@router.get('/mobile/v1/home')
def home(response: Response, fecha: str | None = Query(None, pattern=r'^\d{4}-\d{2}-\d{2}$'),
         tz: int = Query(0, ge=-720, le=840), plus: bool = Depends(member),
         account: dict | None = Depends(rewards.optional_account)):
    response.headers['Cache-Control'] = 'no-store'
    cfg = config()
    flags = cfg['features']
    try:
        start, end = fichas.ventana(fecha, tz, DIAS_AGENDA)
    except ValueError:
        raise HTTPException(422, 'Fecha inválida') from None
    agenda = visible_agenda(fichas._agenda(start, end, None)) if flags['agenda']['enabled'] else []
    if agenda and flags['estadisticas']['enabled']:
        probabilities = {r['match_id']: uno_x_dos(r)[0] for r in query(
            "SELECT DISTINCT ON (match_id) match_id, markets->'1x2' AS probabilities, market_consensus, "
            "data_completeness->>'both_teams_known' AS conocido "
            "FROM predictions WHERE match_id=ANY(%s) ORDER BY match_id,generated_at DESC",
            ([r['match_id'] for r in agenda],))}
        for row in agenda:
            row['probabilities'] = probabilities.get(row['match_id'])
    for row in agenda:
        row['pronostico_desde'] = pronostico_desde(row.get('kickoff_utc'))
    unlocks = rewards.entitlements(account)
    return {'config': cfg, 'plus': plus, 'agenda': agenda,
            'alta_probabilidad': high_probability(plus,unlocks), 'escalera': ladder(plus,unlocks),
            'rewards': rewards.public_settings(),
            'plans': suscripciones.plans(only_active=True) if flags['vip']['enabled'] else []}


def pronostico_desde(kickoff) -> str | None:
    """Cuándo se calcula el pronóstico del partido (03:00 de México de su día): ver `ventana`."""
    if isinstance(kickoff, str):
        try:
            kickoff = datetime.fromisoformat(kickoff.replace('Z', '+00:00'))
        except ValueError:
            return None
    if not isinstance(kickoff, datetime):
        return None
    if kickoff.tzinfo is None:
        kickoff = kickoff.replace(tzinfo=timezone.utc)
    return ventana.desbloqueo(kickoff).isoformat()


def uno_x_dos(row: dict | None) -> tuple[dict | None, bool]:
    """(1X2 que se muestra, si es del modelo propio).

    Si el modelo no conoce a alguno de los equipos (`both_teams_known=false`:
    ascendido o club que vuelve tras años fuera) su 1X2 no significa nada —la
    auditoría del 2026-10-21 encontró Coventry local al 7,7 % con el mercado al
    30 %— y se muestra el consenso sin margen del mercado guardado en la misma
    fila, o nada. `row` trae `probabilities` (o `markets`), `market_consensus` y
    `conocido`.
    """
    if not row:
        return None, False
    if str(row.get('conocido')).lower() != 'false':
        probs = row.get('probabilities')
        if probs is None and isinstance(row.get('markets'), dict):
            probs = row['markets'].get('1x2')
        return probs, True
    cons = row.get('market_consensus')
    try:
        trio = [float(cons[k]) for k in ('home', 'draw', 'away')]
    except (TypeError, KeyError, ValueError):
        return None, False
    total = sum(trio)
    if not all(math.isfinite(x) and x > 0 for x in trio) or total <= 0:
        return None, False
    return {k: x / total for k, x in zip(('home', 'draw', 'away'), trio)}, False


def market_card(match_id: str) -> dict | None:
    """Tarjeta para ligas sin modelo propio: probabilidades del ajuste de goles a las
    cuotas sin margen de Pinnacle (lambda, mu, rho del pick), con la misma matriz de
    marcadores del modelo. Se etiqueta `fuente: mercado`: no es una predicción propia."""
    row = query_one('SELECT fit FROM alta_prob_picks WHERE match_id=%s AND fit IS NOT NULL '
                    'ORDER BY decided_at DESC LIMIT 1', (match_id,))
    fit = row['fit'] if row else None
    try:
        lam, mu = float(fit['lambda']), float(fit['mu'])
        rho = float(fit.get('rho') or 0)
    except (TypeError, KeyError, ValueError, AttributeError):
        return None
    if not all(math.isfinite(x) and abs(x) < 10 for x in (lam, mu, rho)) or lam <= 0 or mu <= 0:
        return None
    from ..model import pricing
    return model_card(pricing.price_all_markets(lam, mu, rho), fuente='mercado')


def mercados_partido(match_id: str, ficha: dict, picks: list[dict], plus: bool, web: bool = False) -> dict | None:
    """Lista de mercados del partido con el acceso aplicado (ver partido_mercados)."""
    abiertas = {partido_mercados.clave(p.get('market'), p.get('selection'), p.get('line')): p
                for p in picks if p.get('market')}
    try:
        return partido_mercados.construir(match_id, jsonable_name(ficha, 'local', 'Local'),
                                          jsonable_name(ficha, 'visitante', 'Visitante'), abiertas, plus, web)
    except Exception:  # noqa: BLE001 - la lista es un extra: si falla, el detalle sigue
        logging.getLogger(__name__).exception('mercados del partido %s', match_id)
        return None


def jsonable_name(ficha: dict, lado: str, defecto: str) -> str:
    return str((ficha.get(lado) or {}).get('nombre') or defecto)


def live_score(match_id: str) -> dict | None:
    """Marcador en juego (db/056). Fuera de la ficha cacheada: debe ser fresco."""
    row = query_one('SELECT live_home_goals, live_away_goals, live_minute, live_status, live_updated_at '
                    'FROM matches WHERE match_id=%s AND live_status IS NOT NULL', (match_id,))
    if not row:
        return None
    return {'marcador': [row['live_home_goals'], row['live_away_goals']], 'minuto': row['live_minute'],
            'estado': row['live_status'], 'actualizado': row['live_updated_at']}


@router.get('/mobile/v1/markets/history')
def markets_history(response: Response,
                    market: str | None = Query(None, pattern=r'^[a-z_]+(,[a-z_]+)*$', max_length=200),
                    limit: int = Query(200, ge=1, le=500)):
    """Pronósticos de alta probabilidad ya resueltos (acertó/falló), uno a uno.

    Mismo universo que ve el usuario en «Hoy»: selladas y en el rango público. Las
    anuladas no cuentan. La probabilidad sale con la precisión pública reducida.
    """
    response.headers['Cache-Control'] = 'no-store'
    if not features()['alta_probabilidad']['enabled']:
        return {'items': []}
    markets = market.split(',') if market else None
    def history(table: str, results: str, key: str, sealed: str) -> list[dict]:
        return query(f'''SELECT a.match_id, m.league_id, m.kickoff_utc,
        COALESCE(th.display_name, th.canonical_name) AS local,
        COALESCE(ta.display_name, ta.canonical_name) AS visitante,
        a.market, a.selection, a.line, a.prob, a.ref_price, r.outcome, r.home_goals, r.away_goals,
        m.home_corners, m.away_corners
        FROM {table} a JOIN matches m ON m.match_id=a.match_id
        JOIN teams th ON th.team_id=m.home_team_id JOIN teams ta ON ta.team_id=m.away_team_id
        {sealed}
        JOIN {results} r ON r.{key}=a.{key}
        WHERE r.outcome IN ('win','loss') AND a.prob BETWEEN %s AND %s
          AND (%s::text[] IS NULL OR a.market = ANY(%s))
        ORDER BY m.kickoff_utc DESC, a.match_id LIMIT %s''', (HIGH_MIN, HIGH_MAX, markets, markets, limit))
    rows = history('alta_prob_picks', 'alta_prob_results', 'alta_id', alta_prob_datos._sql_sellado())
    if settings.alta_prob_ext_enabled:
        try:
            extra = history('alta_prob_ext', 'alta_prob_ext_results', 'ext_id', alta_prob_ext.sql_sellado())
        except UndefinedTable:
            extra = []
        seen = {(r['match_id'], r['market'], r['selection'], r['line']) for r in rows}
        rows += [r for r in extra if (r['match_id'], r['market'], r['selection'], r['line']) not in seen]
        rows.sort(key=lambda r: (r['kickoff_utc'], r['match_id']), reverse=True)
        rows = rows[:limit]
    from ..publish import alta_prob as ap
    for row in rows:
        row['texto'] = ap.texto(row['market'], row['selection'], row['line'], row['local'], row['visitante'])
        row['prob'] = round(float(row['prob']), 2)
    return {'items': rows}


@router.get('/mobile/v1/markets/destacados')
def markets_destacados(response: Response, desde: date = Query(...)):
    """Destacado de fútbol de cada partido terminado desde `desde`, ya resuelto (acertó/falló)."""
    response.headers['Cache-Control'] = 'no-store'
    return {'items': partido_mercados.destacados_resueltos(desde)}


def model_card(markets, fuente: str = 'modelo') -> dict | None:
    """Probabilidades del modelo para la tarjeta del pronóstico, a 2 decimales.

    Solo sale junto a un pronóstico que el usuario puede ver: son las probabilidades
    de las que se deriva el pronóstico y no se regalan para todos los partidos.
    """
    def p(*path):
        value = markets
        for key in path:
            value = value.get(key) if isinstance(value, dict) else None
        try:
            x = float(value)
        except (TypeError, ValueError):
            return None
        return round(x, 2) if math.isfinite(x) and 0 <= x <= 1 else None

    lines = ('0.5', '1.5', '2.5')
    card = {'fuente': fuente, 'mas_1_5': p('totals', '1.5', 'over'), 'mas_2_5': p('totals', '2.5', 'over'),
            'ambos': p('btts', 'yes'),
            'local': p('1x2', 'home'), 'empate': p('1x2', 'draw'), 'visita': p('1x2', 'away'),
            'goles_local': [p('team_totals', 'home', n, 'over') for n in lines],
            'goles_visita': [p('team_totals', 'away', n, 'over') for n in lines]}
    flat = [v for k, v in card.items() if k != 'fuente' and not k.startswith('goles_')] + card['goles_local'] + card['goles_visita']
    return card if any(v is not None for v in flat) else None


@router.get('/mobile/v1/matches/{match_id}')
def detail(match_id: str, response: Response, web: bool = Query(False), plus: bool = Depends(member),
           account: dict | None = Depends(rewards.optional_account)):
    response.headers['Cache-Control'] = 'no-store'
    cfg = config()
    flags = cfg['features']
    ficha = fichas._ficha(match_id)
    if ficha is None:
        raise HTTPException(404, 'Partido no encontrado')
    ficha['partido']['vivo'] = live_score(match_id)
    unlocks = rewards.entitlements(account)
    high = high_probability(plus,unlocks,started=True)
    steps = ladder(plus,unlocks)
    picks = [p for p in high['proximos'] if p['match_id'] == match_id]
    picks += [p for r in steps['actuales'] for p in r['pasos'] if p['match_id'] == match_id and p['outcome'] is None]
    vip_picks = [p for p in high['vip'] if p['match_id'] == match_id]
    vip_picks += [p for r in steps['actuales'] for p in r['vip'] if p['match_id'] == match_id]
    blocked = bool(vip_picks)
    if not flags['estadisticas']['enabled']:
        for side in ('local', 'visitante'):
            ficha[side] = {key: ficha[side].get(key) for key in ('id','nombre','escudo')}
        ficha['tabla'] = None
        ficha['partido']['estadisticas'] = None
        ficha['partido']['xg'] = None
    else:
        prediction = query_one("SELECT markets, market_consensus, "
                               "data_completeness->>'both_teams_known' AS conocido FROM predictions "
                               "WHERE match_id=%s ORDER BY generated_at DESC LIMIT 1", (match_id,))
        markets = prediction['markets'] if prediction else None
        ficha['probabilities'], del_modelo = uno_x_dos(prediction)
        propia = model_card(markets) if del_modelo else None
        ficha['modelo'] = ((propia or market_card(match_id)) if picks else None)
        ficha['mercados'] = mercados_partido(match_id, ficha, picks, plus, web)
        if ficha['mercados'] is None and blocked and not (plus and flags['vip']['enabled']):
            # Sin modelo de goles: sus pronósticos VIP se avisan aparte del gratuito (solo categoría).
            ficha['mercados'] = partido_mercados.solo_candados(vip_picks)
    if not flags['h2h']['enabled']:
        for key in ('cara_a_cara','alineaciones','bajas'):
            ficha[key] = None
    return {'config': cfg, 'ficha': ficha, 'picks': picks, 'locked': blocked and not (plus and flags['vip']['enabled'])}


@router.get('/control/configuracion-app', include_in_schema=False)
def configuration_page(request: panel.Request, user: str = Depends(console.require_console)):
    return panel._render(request, 'mobile_config.html', user, 'mobile',
                         sections=SECTIONS, features=features(), updates=mobile_updates.configuration())


@router.post('/control/actualizaciones-app', include_in_schema=False)
def updates_save(request: Request, csrf: str = Form(''),
                 app_version_android: str = Form('', max_length=60),
                 app_version_ios: str = Form('', max_length=60),
                 min_build_android: int = Form(0), min_build_ios: int = Form(0),
                 force_update_app: str = Form(''),
                 app_link: str = Form('', max_length=500),
                 ios_app_link: str = Form('', max_length=500),
                 user: str = Depends(console.require_console)):
    panel._check_post(request, user, csrf)
    if force_update_app not in ('', '1'):
        raise HTTPException(422, 'Estado inválido')
    values = dict(app_version_android=app_version_android.strip(),
                  app_version_ios=app_version_ios.strip(), min_build_android=min_build_android,
                  min_build_ios=min_build_ios, force_update_app=force_update_app == '1',
                  app_link=app_link.strip(), ios_app_link=ios_app_link.strip())
    try:
        mobile_updates.validate(values)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    with conn() as c:
        c.execute('INSERT INTO mobile_update_settings (id) VALUES (1) ON CONFLICT DO NOTHING')
        c.execute('UPDATE mobile_update_settings SET '
                  + ', '.join(f'{key}=%s' for key in values)
                  + ', updated_at=now() WHERE id=1', tuple(values.values()))
        audit(c, panel._actor(request, user), 'mobile_updates', detail=values)
    return panel._back('/control/configuracion-app', 'mobile_guardado')


@router.post('/control/configuracion-app/{section}', include_in_schema=False)
def configuration_update(section: str, request: panel.Request, enabled: str = Form(''),
                         message: str = Form('Modelo en entrenamiento', max_length=180),
                         csrf: str = Form(''), user: str = Depends(console.require_console)):
    panel._check_post(request, user, csrf)
    if section not in SECTIONS:
        raise HTTPException(404)
    if enabled not in ('', '1'):
        raise HTTPException(422, 'Estado inválido')
    with conn() as c:
        c.execute('UPDATE mobile_features SET enabled=%s,message=%s,updated_at=now() WHERE section=%s',
                  (enabled == '1', message.strip() or 'Modelo en entrenamiento', section))
        audit(c, panel._actor(request, user), 'mobile_feature', detail={
            'section': section, 'enabled': enabled == '1', 'message': message.strip()})
    return panel._back('/control/configuracion-app', 'mobile_guardado')
