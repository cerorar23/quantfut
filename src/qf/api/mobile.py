"""Real mobile content; feature controls never override model publication gates.

Access is checked before serialization. Public allocations are fixed per sealed
batch so refreshing as matches start cannot expose a rotating premium catalog.
"""
from __future__ import annotations

import copy
import logging
import math
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg.errors import UndefinedTable

from . import console, cuentas, fichas, panel, partido_mercados, rewards
from ..comercial import suscripciones
from ..comercial.auditoria import audit
from ..db import conn, query, query_one
from ..config import settings
from ..publish import alta_prob_datos, alta_prob_ext, escalera_datos

router = APIRouter(tags=["mobile"])
_bearer = HTTPBearer(auto_error=False)
PROB_MIN, PROB_MAX = .75, .90          # escalera
# Alta probabilidad ampliada (decisión del usuario, 2026-10-11): 62-95 %, con las
# filas de `alta_prob_picks` (80-95 %) y `alta_prob_ext` (62-95 %, db/057).
HIGH_MIN, HIGH_MAX = .62, .95
# Gratis: un pronóstico por mercado, el de MAYOR cuota publicada (decisión del
# usuario, 2026-10-12: la cuota manda sobre la probabilidad), con tope 1,60. Con
# 75-90 % de probabilidad las cuotas reales van de 1,01 a 1,25: un piso de 1,40
# o 1,20 deja el escaparate vacío casi siempre, así que no hay piso (solo > 1).
FREE_QUOTE_MIN, FREE_QUOTE_MAX = 1.0, 1.60
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
    return {'features': features(), 'probability_min': HIGH_MIN,
            'probability_max': HIGH_MAX, 'high_probability_free_per_market': 1,
            'high_probability_free_quote_max': FREE_QUOTE_MAX,
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


def choose_free(rows: list[dict], stream: str) -> list[dict]:
    """Only sealed eligible rows enter. Odds are publication quotes, not live."""
    lo, hi = (HIGH_MIN, HIGH_MAX) if stream == 'alta_probabilidad' else (PROB_MIN, PROB_MAX)
    valid = [r for r in rows if lo <= probability(r) <= hi]
    if stream == 'alta_probabilidad':
        priced = [r for r in valid if r.get('ref_price') is not None
                  and math.isfinite(float(r['ref_price']))
                  and FREE_QUOTE_MIN < float(r['ref_price']) <= FREE_QUOTE_MAX]
        # UNO por mercado, el de mayor cuota publicada; el empate lo decide la
        # probabilidad.
        priced.sort(key=lambda r: (-float(r['ref_price']), -probability(r), pick_key(r)))
        chosen, seen = [], set()
        for r in priced:
            if r.get('market') not in seen:
                seen.add(r.get('market'))
                chosen.append(r)
        return chosen
    if stream == 'escalera':
        valid.sort(key=lambda r: (-probability(r), -float(r.get('price') or 0), pick_key(r)))
        return valid[:1]
    raise ValueError('Unknown stream')


def top_up(rows: list[dict], free_keys: set[str], now: datetime) -> list[dict]:
    """Pronósticos sin empezar que deben pasar a gratis aunque el lote ya esté repartido.

    Regla permanente (decisión del usuario, 2026-10-12): siempre queda gratis el de
    mayor cuota de cada mercado. Solo AÑADE: nunca quita uno que el usuario ya vio, y
    no toca los que ya empezaron. Un mercado que ya tiene uno abierto gratis no suma otro.
    """
    pending = [r for r in rows if r['kickoff_utc'] > now]
    open_markets = {r.get('market') for r in pending if pick_key(r) in free_keys}
    return [r for r in choose_free(pending, 'alta_probabilidad')
            if pick_key(r) not in free_keys and r.get('market') not in open_markets]


def allocations(rows: list[dict], stream: str) -> set[str]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[str(row['batch_date'])].append(row)
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
                        'rule': 'highest_quote_per_market'})
            selected_rows = c.execute('SELECT pick_key FROM mobile_free_allocations '
                                      'WHERE stream=%s AND batch_date=%s', (stream, batch)).fetchall()
            result.update(r['pick_key'] for r in selected_rows)
    return result


_HIGH_COLS = """a.match_id, m.league_id, m.kickoff_utc,
        COALESCE(th.display_name, th.canonical_name) AS local,
        COALESCE(ta.display_name, ta.canonical_name) AS visitante,
        a.market,a.selection,a.line,a.prob,a.ref_price,a.ref_book,a.odds_as_of,a.fit,
        b.batch_date,b.chain_sha256"""


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


def metadata(row: dict) -> dict:
    # `market` es solo la categoría (goles, córners...): permite ubicar el candado
    # en su mercado. Selección, línea, probabilidad y cuota siguen sin salir.
    return {**{key: row.get(key) for key in ('match_id','league_id','kickoff_utc','local','visitante','batch_date','market')},
            'locked': True, 'pick_key': pick_key(row)}


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
    free = allocations(rows, 'alta_probabilidad')
    now = datetime.now(timezone.utc)
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
        start, end = fichas.ventana(fecha, tz, 2)
    except ValueError:
        raise HTTPException(422, 'Fecha inválida') from None
    agenda = fichas._agenda(start, end, None) if flags['agenda']['enabled'] else []
    if agenda and flags['estadisticas']['enabled']:
        probabilities = {r['match_id']: r['probabilities'] for r in query(
            "SELECT DISTINCT ON (match_id) match_id, markets->'1x2' AS probabilities "
            "FROM predictions WHERE match_id=ANY(%s) ORDER BY match_id,generated_at DESC",
            ([r['match_id'] for r in agenda],))}
        for row in agenda:
            row['probabilities'] = probabilities.get(row['match_id'])
    unlocks = rewards.entitlements(account)
    return {'config': cfg, 'plus': plus, 'agenda': agenda,
            'alta_probabilidad': high_probability(plus,unlocks), 'escalera': ladder(plus,unlocks),
            'rewards': rewards.public_settings(),
            'plans': suscripciones.plans(only_active=True) if flags['vip']['enabled'] else []}


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


def mercados_partido(match_id: str, ficha: dict, picks: list[dict], plus: bool) -> dict | None:
    """Lista de mercados del partido con el acceso aplicado (ver partido_mercados)."""
    abiertas = {partido_mercados.clave(p.get('market'), p.get('selection'), p.get('line')): p
                for p in picks if p.get('market')}
    try:
        return partido_mercados.construir(match_id, jsonable_name(ficha, 'local', 'Local'),
                                          jsonable_name(ficha, 'visitante', 'Visitante'), abiertas, plus)
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
def detail(match_id: str, response: Response, plus: bool = Depends(member),
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
    blocked = any(p['match_id'] == match_id for p in high['vip']) or any(
        p['match_id'] == match_id for r in steps['actuales'] for p in r['vip'])
    if not flags['estadisticas']['enabled']:
        for side in ('local', 'visitante'):
            ficha[side] = {key: ficha[side].get(key) for key in ('id','nombre','escudo')}
        ficha['tabla'] = None
        ficha['partido']['estadisticas'] = None
        ficha['partido']['xg'] = None
    else:
        prediction = query_one("SELECT markets FROM predictions "
                               "WHERE match_id=%s ORDER BY generated_at DESC LIMIT 1", (match_id,))
        markets = prediction['markets'] if prediction else None
        ficha['probabilities'] = markets.get('1x2') if isinstance(markets, dict) else None
        ficha['modelo'] = ((model_card(markets) or market_card(match_id)) if picks else None)
        ficha['mercados'] = mercados_partido(match_id, ficha, picks, plus)
    if not flags['h2h']['enabled']:
        for key in ('cara_a_cara','alineaciones','bajas'):
            ficha[key] = None
    return {'config': cfg, 'ficha': ficha, 'picks': picks, 'locked': blocked and not (plus and flags['vip']['enabled'])}


@router.get('/control/configuracion-app', include_in_schema=False)
def configuration_page(request: panel.Request, user: str = Depends(console.require_console)):
    return panel._render(request, 'mobile_config.html', user, 'mobile',
                         sections=SECTIONS, features=features())


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
