"""Real mobile content; feature controls never override model publication gates.

Access is checked before serialization. Public allocations are fixed per sealed
batch so refreshing as matches start cannot expose a rotating premium catalog.
"""
from __future__ import annotations

import copy
import math
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg.errors import UndefinedTable

from . import console, cuentas, fichas, panel, rewards
from ..comercial import suscripciones
from ..comercial.auditoria import audit
from ..db import conn, query, query_one
from ..publish import alta_prob_datos, escalera_datos

router = APIRouter(tags=["mobile"])
_bearer = HTTPBearer(auto_error=False)
PROB_MIN, PROB_MAX = .75, .90
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
    return {'features': features(), 'probability_min': PROB_MIN,
            'probability_max': PROB_MAX, 'high_probability_free_fraction': .10,
            'ladder_free_count': 1, 'server_time': datetime.now(timezone.utc)}


def member(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> bool:
    if creds is None:
        return False
    cuentas.require_enabled()
    account = cuentas.current_account(creds)
    return suscripciones.active_subscription(account['account_id']) is not None


def pick_key(row: dict) -> str:
    return str(row.get('pick_key') or row['match_id'])


def probability(row: dict) -> float:
    return float(row.get('_prob_exact', row.get('prob')) or 0)


def choose_free(rows: list[dict], stream: str) -> list[dict]:
    """Only sealed eligible rows enter. Odds are publication quotes, not live."""
    valid = [r for r in rows if PROB_MIN <= probability(r) <= PROB_MAX]
    if stream == 'alta_probabilidad':
        priced = [r for r in valid if r.get('ref_price') is not None
                  and math.isfinite(float(r['ref_price'])) and float(r['ref_price']) > 1]
        priced.sort(key=lambda r: (-float(r['ref_price']), -probability(r), pick_key(r)))
        return priced[:math.ceil(len(valid) / 10)]
    if stream == 'escalera':
        valid.sort(key=lambda r: (-probability(r), -float(r.get('price') or 0), pick_key(r)))
        return valid[:1]
    raise ValueError('Unknown stream')


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
            selected_rows = c.execute('SELECT pick_key FROM mobile_free_allocations '
                                      'WHERE stream=%s AND batch_date=%s', (stream, batch)).fetchall()
            result.update(r['pick_key'] for r in selected_rows)
    return result


def high_rows() -> list[dict]:
    # The full immutable batch, including matches already started, fixes the
    # public fraction. A source gate can pause delivery but not rewrite a seal.
    rows = query(f'''SELECT a.match_id, m.league_id, m.kickoff_utc,
        COALESCE(th.display_name, th.canonical_name) AS local,
        COALESCE(ta.display_name, ta.canonical_name) AS visitante,
        a.market,a.selection,a.line,a.prob,a.ref_price,a.ref_book,a.odds_as_of,
        b.batch_date,b.chain_sha256
        FROM alta_prob_picks a JOIN matches m ON m.match_id=a.match_id
        JOIN teams th ON th.team_id=m.home_team_id JOIN teams ta ON ta.team_id=m.away_team_id
        {alta_prob_datos._sql_sellado()}
        WHERE a.prob BETWEEN %s AND %s AND b.batch_date >= current_date - 7
        ORDER BY m.kickoff_utc,a.match_id''', (PROB_MIN, PROB_MAX))
    from ..publish import alta_prob as ap
    for row in rows:
        row['texto'] = ap.texto(row['market'], row['selection'], row['line'], row['local'], row['visitante'])
    return rows


def metadata(row: dict) -> dict:
    return {**{key: row.get(key) for key in ('match_id','league_id','kickoff_utc','local','visitante','batch_date')},
            'locked': True, 'pick_key': pick_key(row)}


def high_probability(plus: bool = False, unlocks: set[tuple[str,str]] | None = None) -> dict:
    flags = features()
    base = alta_prob_datos.informe_publico()
    base = {**base, 'proximos': [], 'vip': []}
    if not flags['alta_probabilidad']['enabled'] or base['estado'] != 'activa':
        return base
    rows = high_rows()
    free = allocations(rows, 'alta_probabilidad')
    now = datetime.now(timezone.utc)
    for row in rows:
        if row['kickoff_utc'] <= now:
            continue
        public = pick_key(row) in free
        owned = ('alta_probabilidad',pick_key(row)) in (unlocks or set())
        if public or ((plus or owned) and flags['vip']['enabled']):
            value = {**row, 'prob': round(float(row['prob']), 2), 'locked': False,
                     'free': public, 'pick_key': pick_key(row)}
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


@router.get('/mobile/v1/matches/{match_id}')
def detail(match_id: str, response: Response, plus: bool = Depends(member),
           account: dict | None = Depends(rewards.optional_account)):
    response.headers['Cache-Control'] = 'no-store'
    cfg = config()
    flags = cfg['features']
    ficha = fichas._ficha(match_id)
    if ficha is None:
        raise HTTPException(404, 'Partido no encontrado')
    unlocks = rewards.entitlements(account)
    high = high_probability(plus,unlocks)
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
        prediction = query_one("SELECT markets->'1x2' AS probabilities FROM predictions "
                               "WHERE match_id=%s ORDER BY generated_at DESC LIMIT 1", (match_id,))
        ficha['probabilities'] = prediction['probabilities'] if prediction else None
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
