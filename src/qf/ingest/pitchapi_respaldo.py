"""PitchAPI como verificador y respaldo de API-Football.

Resultados: solo AVISOS. Una discrepancia se registra y se avisa, nunca se
corrige sola (los IDs de partido de PitchAPI no son estables y no hay SLA).
xG: relleno de respaldo sobre terminados sin xG, con la recepción real, tras
darle 48 h a API-Football; nunca sobrescribe un valor ya capturado.

Sin clave o desactivado el job no hace nada y no falla. Una clave rechazada
(401) detiene la pasada y avisa una vez.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import logging
import os
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

from psycopg.types.json import Jsonb

from ..comercial import cifrado
from ..db import conn, query, query_one
from .pitchapi_history import Client, team_xg

log = logging.getLogger(__name__)
LOCK_ID = 61012065
KEY_CONTEXT = 'pitchapi:key'
WINDOW_DAYS = 10          # días recientes que se cotejan (una llamada por día)
XG_GRACE_HOURS = 48       # API-Football tiene primero su oportunidad
XG_LOOKBACK_DAYS = 35
MAX_DAYS, MAX_STATS = 45, 60
PENDING_AFTER = timedelta(hours=4)
MIN_VOTES, DOMINANCE = 3, 0.9
MAX_XG = 10.0


# ---- lógica pura (probada sin base de datos) --------------------------------

def kickoff_day(match: dict) -> date:
    return date.fromisoformat(match['time_utc'][:10])


def _same_day(a: date, b: date, tolerance: int) -> bool:
    return abs((a - b).days) <= tolerance


def compare(pitch_matches, db_rows, mapping, league_by_pitch, now):
    """Empareja por club y fecha. Devuelve (parejas, discrepancias, votos, sin_equivalencia).

    pitch_matches: dicts de /v1/date. db_rows: partidos canónicos con `kickoff_utc`.
    mapping: {pitch_team_id: team_id}. Ninguna discrepancia sale de un emparejamiento
    ambiguo: si hay más de un candidato no se afirma nada.
    """
    by_league = defaultdict(list)
    for r in db_rows:
        by_league[r['league_id']].append(r)
    pairs, discrepancies, votes, unmapped = [], [], [], 0
    for pm in pitch_matches:
        league = league_by_pitch.get(pm['league']['id'])
        if league is None or pm.get('status') != 'finished' or pm.get('score_home') is None:
            continue
        day = kickoff_day(pm)
        score = (pm['score_home'], pm['score_away'])
        home, away = mapping.get(pm['home_team']['id']), mapping.get(pm['away_team']['id'])
        rows = by_league[league]
        if home is None or away is None:
            unmapped += 1
            same = [r for r in rows if r['status'] == 'finished'
                    and (r['home_goals'], r['away_goals']) == score
                    and r['kickoff_utc'].date() == day]
            if len(same) == 1:
                votes.append((pm['home_team']['id'], same[0]['home_team_id'], pm['id']))
                votes.append((pm['away_team']['id'], same[0]['away_team_id'], pm['id']))
            continue
        found = [r for r in rows if r['home_team_id'] == home and r['away_team_id'] == away
                 and _same_day(r['kickoff_utc'].date(), day, 1)]
        if not found:
            discrepancies.append({'kind': 'missing_in_db', 'match_id': None, 'league_id': league,
                                  'pitch_match_id': pm['id'],
                                  'detail': {'date': str(day), 'score': list(score),
                                             'home': pm['home_team']['name'], 'away': pm['away_team']['name']}})
            continue
        if len(found) > 1:
            continue
        row = found[0]
        pairs.append((pm, row))
        if row['status'] == 'finished':
            if (row['home_goals'], row['away_goals']) != score:
                discrepancies.append({'kind': 'score', 'match_id': row['match_id'], 'league_id': league,
                                      'pitch_match_id': pm['id'],
                                      'detail': {'db': [row['home_goals'], row['away_goals']],
                                                 'pitchapi': list(score), 'date': str(day),
                                                 'home': pm['home_team']['name'], 'away': pm['away_team']['name']}})
        elif row['kickoff_utc'] < now - PENDING_AFTER:
            discrepancies.append({'kind': 'result_pending', 'match_id': row['match_id'], 'league_id': league,
                                  'pitch_match_id': pm['id'],
                                  'detail': {'db_status': row['status'], 'pitchapi': list(score),
                                             'date': str(day), 'home': pm['home_team']['name'],
                                             'away': pm['away_team']['name']}})
    return pairs, discrepancies, votes, unmapped


def promote(vote_rows, owned_clubs, mapped_teams):
    """vote_rows: (pitch_team_id, team_id, n). Devuelve [(pitch_team_id, team_id, votos)] aceptados."""
    per_team = defaultdict(Counter)
    for pitch_team, club, n in vote_rows:
        if pitch_team not in mapped_teams:
            per_team[pitch_team][club] += n
    accepted = {}
    for pitch_team, counter in per_team.items():
        (club, top), = counter.most_common(1)
        if top >= MIN_VOTES and top >= DOMINANCE * sum(counter.values()) and club not in owned_clubs:
            accepted[pitch_team] = (club, top)
    clubs = Counter(c for c, _ in accepted.values())
    return [(t, c, n) for t, (c, n) in accepted.items() if clubs[c] == 1]


def xg_targets(pairs, now):
    """Parejas elegibles para xG de respaldo: terminado hace > 48 h, sin xG y mismo marcador."""
    out = []
    for pm, row in pairs:
        if (row['status'] == 'finished' and row['home_xg'] is None and row['away_xg'] is None
                and row['kickoff_utc'] < now - timedelta(hours=XG_GRACE_HOURS)
                and (row['home_goals'], row['away_goals']) == (pm['score_home'], pm['score_away'])):
            out.append((pm, row))
    return out


def valid_xg(raw: bytes):
    xg = team_xg(raw)
    return xg if xg is not None and all(0 <= v <= MAX_XG for v in xg) else None


# ---- acceso a clave, API y base ---------------------------------------------

def settings_row() -> dict:
    return query_one('SELECT * FROM pitchapi_settings WHERE id = 1') or {}


def api_key(row: dict | None = None) -> str:
    row = row or settings_row()
    if row.get('key_enc'):
        try:
            return cifrado.descifrar(row['key_enc'], KEY_CONTEXT)
        except cifrado.CifradoError as exc:
            log.error('Clave de PitchAPI ilegible: %s', exc)
            return ''
    return os.getenv('PITCHAPI_KEY', '')


class Unauthorized(Exception):
    pass


def fetch_json(client: Client, path: str):
    status, body, received = client.get(path)
    if status == 401:
        raise Unauthorized(path)
    return status, body, received


def test_connection(key: str) -> tuple[bool, str]:
    """Prueba de la clave para el panel: una sola llamada barata."""
    if not key:
        return False, 'No hay clave'
    status, body, _ = Client(key).get('/v1/leagues')
    if status == 200:
        try:
            return True, f"{len(json.loads(body)['data']['leagues'])} ligas visibles"
        except (ValueError, KeyError):
            return False, 'Respuesta inesperada'
    if status == 401:
        return False, 'Clave inválida o revocada'
    return False, f'HTTP {status}'


def _db_window(days_from: date, days_to: date):
    return query(
        """SELECT m.match_id, m.league_id, m.kickoff_utc, m.status, m.home_team_id, m.away_team_id,
                  m.home_goals, m.away_goals, m.home_xg, m.away_xg
           FROM matches m JOIN leagues l USING (league_id)
           WHERE l.pitchapi_id IS NOT NULL
             AND m.kickoff_utc >= %s AND m.kickoff_utc < %s""",
        (datetime.combine(days_from - timedelta(days=1), datetime.min.time(), timezone.utc),
         datetime.combine(days_to + timedelta(days=2), datetime.min.time(), timezone.utc)))


def run(window_days: int = WINDOW_DAYS, now: datetime | None = None, client: Client | None = None) -> dict:
    from . import api_football as af
    now = now or datetime.now(timezone.utc)
    row = settings_row()
    if not row.get('enabled'):
        return {'skipped': 'desactivado'}
    key = api_key(row)
    if not key:
        af.record_health('pitchapi', 0, False, {'error': 'sin clave'})
        return {'skipped': 'sin clave'}
    client = client or Client(key)
    result = {'days': 0, 'discrepancies_new': 0, 'xg_filled': 0, 'votes': 0, 'teams_learned': 0, 'unmapped': 0}
    with conn() as lock:
        if not lock.execute('SELECT pg_try_advisory_lock(%s) AS locked', (LOCK_ID,)).fetchone()['locked']:
            return {'skipped': 'otra pasada en curso'}
        try:
            result.update(_run(client, now, window_days))
            ok, detail = True, result
        except Unauthorized:
            ok, detail = False, {**result, 'error': 'clave inválida o revocada'}
            _alert('PitchAPI: la clave fue rechazada (401). Revisa /control/respaldo.')
        except Exception as exc:  # noqa: BLE001 — el respaldo no puede tumbar el cron
            log.exception('Pasada de PitchAPI fallida')
            ok, detail = False, {**result, 'error': str(exc)[:200]}
        finally:
            lock.execute('SELECT pg_advisory_unlock(%s)', (LOCK_ID,))
    with conn() as c:
        c.execute('UPDATE pitchapi_settings SET last_run_at = now(), last_ok = %s, last_detail = %s WHERE id = 1',
                  (ok, Jsonb(detail)))
    af.record_health('pitchapi', detail.get('xg_filled', 0), ok, detail)
    return detail


def _alert(text: str) -> None:
    try:
        from ..publish import telegram
        telegram.alert(text)
    except Exception:  # noqa: BLE001
        log.exception('No se pudo avisar')


def _run(client: Client, now: datetime, window_days: int) -> dict:
    league_by_pitch = {r['pitchapi_id']: r['league_id']
                       for r in query('SELECT league_id, pitchapi_id FROM leagues WHERE pitchapi_id IS NOT NULL')}
    mapping = {r['pitch_team_id']: r['team_id'] for r in query('SELECT pitch_team_id, team_id FROM pitchapi_teams')}
    today = now.date()
    recent = {today - timedelta(days=i) for i in range(0, window_days)}
    # Días de los terminados sin xG que PitchAPI podría completar.
    pending_days = {r['d'] for r in query(
        """SELECT DISTINCT (m.kickoff_utc AT TIME ZONE 'UTC')::date AS d
           FROM matches m JOIN leagues l USING (league_id)
           WHERE l.pitchapi_id IS NOT NULL AND m.status = 'finished' AND m.home_xg IS NULL AND m.away_xg IS NULL
             AND m.kickoff_utc < %s AND m.kickoff_utc >= %s""",
        (now - timedelta(hours=XG_GRACE_HOURS), now - timedelta(days=XG_LOOKBACK_DAYS)))}
    days = sorted(recent | pending_days, reverse=True)[:MAX_DAYS]
    pitch_matches = []
    for d in days:
        status, body, _ = fetch_json(client, f'/v1/date/{d}')
        if status == 200:
            pitch_matches += json.loads(body)['data']['matches']
    db_rows = _db_window(min(days), max(days))
    pairs, discrepancies, votes, unmapped = compare(pitch_matches, db_rows, mapping, league_by_pitch, now)
    out = {'days': len(days), 'unmapped': unmapped, 'votes': len(votes), 'discrepancies_new': 0,
           'teams_learned': 0, 'xg_filled': 0}
    new_alertable = []
    with conn() as c:
        for pitch_team, club, pitch_match in votes:
            c.execute('INSERT INTO pitchapi_team_votes VALUES (%s, %s, %s) ON CONFLICT DO NOTHING',
                      (pitch_team, club, pitch_match))
        vote_rows = [(r['pitch_team_id'], r['team_id'], r['n']) for r in c.execute(
            'SELECT pitch_team_id, team_id, count(*) AS n FROM pitchapi_team_votes GROUP BY 1, 2').fetchall()]
        owned = {r['team_id'] for r in c.execute('SELECT team_id FROM pitchapi_teams').fetchall()}
        for pitch_team, club, n in promote(vote_rows, owned, set(mapping)):
            c.execute('INSERT INTO pitchapi_teams (pitch_team_id, team_id, votes, evidence) '
                      'VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING',
                      (pitch_team, club, n, Jsonb({'source': 'votos diarios', 'at': now.isoformat()})))
            out['teams_learned'] += 1
        for d in discrepancies:
            added = c.execute(
                """INSERT INTO pitchapi_discrepancies (kind, match_id, league_id, pitch_match_id, detail)
                   VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING RETURNING id""",
                (d['kind'], d['match_id'], d['league_id'], d['pitch_match_id'], Jsonb(d['detail']))).fetchone()
            if added:
                out['discrepancies_new'] += 1
                if d['kind'] != 'missing_in_db':
                    new_alertable.append(d)
    for pm, row in xg_targets(pairs, now)[:MAX_STATS]:
        status, body, received = fetch_json(client, f"/v1/matches/{pm['id']}/stats")
        if status != 200:
            continue
        xg = valid_xg(body)
        if xg is None:
            continue
        with conn() as c:
            # Guardar el original aunque la fila ya tenga xG: es la evidencia de lo recibido.
            c.execute("""INSERT INTO pitchapi_originals (pitch_match_id, sha256, match_id, received_at, payload_gzip)
                         VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                      (pm['id'], hashlib.sha256(body).hexdigest(), row['match_id'], received, gzip.compress(body)))
            out['xg_filled'] += c.execute(
                """UPDATE matches SET home_xg = %s, away_xg = %s, xg_source = 'pitchapi', xg_recorded_at = %s
                   WHERE match_id = %s AND status = 'finished' AND home_xg IS NULL AND away_xg IS NULL""",
                (xg[0], xg[1], received, row['match_id'])).rowcount
    if new_alertable:
        lines = [f"{d['kind']} {d['league_id']} {d['detail'].get('home')}-{d['detail'].get('away')} "
                 f"{d['detail'].get('date')}: BD {d['detail'].get('db', d['detail'].get('db_status'))} / "
                 f"PitchAPI {d['detail']['pitchapi']}" for d in new_alertable[:5]]
        _alert(f'PitchAPI: {len(new_alertable)} discrepancia(s) de resultado nuevas. Revisa /control/respaldo.\n'
               + '\n'.join(lines))
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--days', type=int, default=WINDOW_DAYS)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(run(args.days), ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
