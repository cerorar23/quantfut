"""football-data.org (v4) como testigo independiente de calendario y resultados.

Solo compara y avisa: nunca escribe en `matches` ni crea equipos o partidos. Una
diferencia se registra en `fdorg_discrepancies` y alguien la revisa. Cada respuesta
queda como original con hash y recepción real en `fdorg_originals`.

Cubre las 10 competiciones con `leagues.fdorg_code`. Reutiliza `compare()` y
`promote()` de `pitchapi_respaldo` mediante un adaptador (`to_common`), sin tocarlas.
Prórroga y penales no se comparan: la convención de goles puede diferir de la base.

Desactivado (`fdorg_settings.enabled`) o sin clave no hace nada y no falla. Una clave
rechazada (401) detiene la pasada y avisa una vez. Diseño en
docs/superpowers/specs/2026-11-01-football-data-org-respaldo-design.md.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import logging
import os
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

import httpx
from psycopg.types.json import Jsonb

from ..db import conn, query, query_one
from .pitchapi_respaldo import _same_day, compare, promote

log = logging.getLogger(__name__)
BASE = 'https://api.football-data.org/v4'
KEY_ENV = 'FOOTBALL_DATA_ORG_KEY'
LOCK_ID = 61012066
DAYS_BACK, DAYS_AHEAD_RECENT = 7, 2     # ventana de resultados (<= 10 días)
DAYS_AHEAD_FIXTURES = 9                 # ventana de calendario (<= 10 días)
PENDING_AFTER = timedelta(hours=6)      # el plan gratis puede tardar en reflejar marcadores
SHIFT_MINUTES = 90
ALERT_HORIZON_H = 72
FAILURES_BEFORE_ALERT = 3
UNAUTHORIZED = 'clave inválida o rechazada'


class Unauthorized(Exception):
    pass


class Fail(Exception):
    pass


# ---- lógica pura (probada sin base de datos) --------------------------------

def to_common(m: dict):
    """Partido de football-data.org -> forma que entiende `pitchapi_respaldo.compare()`.

    Devuelve None para lo que no se compara: aplazados, en juego, anulados y los
    terminados que no son de tiempo reglamentario.
    """
    status = m.get('status')
    if status == 'FINISHED':
        score = m.get('score') or {}
        full = score.get('fullTime') or {}
        if score.get('duration') != 'REGULAR' or full.get('home') is None or full.get('away') is None:
            return None
        norm, home, away = 'finished', full['home'], full['away']
    elif status in ('SCHEDULED', 'TIMED'):
        norm, home, away = 'scheduled', None, None
    else:
        return None
    return {'id': str(m['id']), 'league': {'id': m['competition']['code']}, 'status': norm,
            'time_utc': m['utcDate'], 'score_home': home, 'score_away': away,
            'home_team': {'id': str(m['homeTeam']['id']), 'name': m['homeTeam'].get('name')},
            'away_team': {'id': str(m['awayTeam']['id']), 'name': m['awayTeam'].get('name')}}


def _parse_ts(text: str) -> datetime:
    return datetime.fromisoformat(text.replace('Z', '+00:00'))


def compare_calendar(matches, db_rows, mapping, league_by_code, now):
    """Partidos programados: ausentes de la base o con la hora movida.

    Solo se afirma algo entre clubes con equivalencia y con un único candidato.
    """
    by_league = defaultdict(list)
    for r in db_rows:
        by_league[r['league_id']].append(r)
    out = []
    for pm in matches:
        league = league_by_code.get(pm['league']['id'])
        if league is None or pm['status'] != 'scheduled':
            continue
        home, away = mapping.get(pm['home_team']['id']), mapping.get(pm['away_team']['id'])
        if home is None or away is None:
            continue
        ko = _parse_ts(pm['time_utc'])
        if ko < now:
            continue
        hours = (ko - now).total_seconds() / 3600
        found = [r for r in by_league[league] if r['home_team_id'] == home and r['away_team_id'] == away
                 and _same_day(r['kickoff_utc'].date(), ko.date(), 1)]
        base = {'league_id': league, 'fdorg_match_id': pm['id']}
        names = {'home': pm['home_team']['name'], 'away': pm['away_team']['name'],
                 'date': str(ko.date()), 'hours_to_kickoff': round(hours, 1)}
        if not found:
            out.append({**base, 'kind': 'missing_in_db', 'match_id': None,
                        'detail': {**names, 'status': 'scheduled', 'kickoff': ko.isoformat()}})
        elif len(found) == 1:
            row = found[0]
            minutes = abs((row['kickoff_utc'] - ko).total_seconds()) / 60
            if row['status'] == 'scheduled' and minutes > SHIFT_MINUTES:
                out.append({**base, 'kind': 'kickoff_shift', 'match_id': row['match_id'],
                            'detail': {**names, 'db': row['kickoff_utc'].isoformat(),
                                       'fdorg': ko.isoformat(), 'minutes': round(minutes)}})
    return out


def apply_pending_grace(discrepancies, db_rows, now):
    """`compare()` marca pendiente a las 4 h; aquí se exigen 6 h desde el saque."""
    kickoff = {r['match_id']: r['kickoff_utc'] for r in db_rows}
    return [d for d in discrepancies
            if d['kind'] != 'result_pending' or kickoff.get(d['match_id'], now - PENDING_AFTER) <= now - PENDING_AFTER]


def alertable(d: dict) -> bool:
    if d['kind'] == 'missing_in_db':
        detail = d['detail']
        return detail.get('status') == 'scheduled' and detail.get('hours_to_kickoff', 1e9) <= ALERT_HORIZON_H
    return True


def alert_line(d: dict) -> str:
    x = d['detail']
    who = f"{x.get('home')}-{x.get('away')} {x.get('date')}"
    if d['kind'] == 'score':
        return f"score {d['league_id']} {who}: BD {x['db']} / fdorg {x['pitchapi']}"
    if d['kind'] == 'result_pending':
        return f"pendiente {d['league_id']} {who}: BD {x['db_status']} / fdorg {x['pitchapi']}"
    if d['kind'] == 'kickoff_shift':
        return f"hora {d['league_id']} {who}: BD {x['db']} / fdorg {x['fdorg']}"
    return f"falta {d['league_id']} {who} (saque en {x.get('hours_to_kickoff')} h)"


# ---- cliente, clave y base ---------------------------------------------------

class Client:
    def __init__(self, key: str, get=httpx.get):
        self.key, self._get = key, get

    def get(self, path: str, params: dict):
        received = datetime.now(timezone.utc)
        try:
            reply = self._get(BASE + path, params=params, timeout=30,
                              headers={'X-Auth-Token': self.key, 'User-Agent': 'QuantFut-respaldo/1.0'})
        except httpx.HTTPError as exc:
            raise Fail(f'red: {exc.__class__.__name__}') from exc
        return reply.status_code, reply.content, received


def settings_row() -> dict:
    return query_one('SELECT * FROM fdorg_settings WHERE id = 1') or {}


def fetch_window(client: Client, codes: list[str], d_from: date, d_to: date):
    status, body, received = client.get('/matches', {
        'competitions': ','.join(codes), 'dateFrom': str(d_from), 'dateTo': str(d_to)})
    if status == 401:
        raise Unauthorized()
    # Se guarda lo recibido aunque no sea utilizable: es la evidencia.
    with conn() as c:
        c.execute("""INSERT INTO fdorg_originals (sha256, window_from, window_to, received_at, payload_gzip)
                     VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                  (hashlib.sha256(body).hexdigest(), d_from, d_to, received, gzip.compress(body)))
    if status != 200:
        raise Fail(f'HTTP {status}')
    try:
        return json.loads(body)['matches']
    except (ValueError, KeyError) as exc:
        raise Fail('respuesta inesperada') from exc


def _db_window(d_from: date, d_to: date):
    return query(
        """SELECT m.match_id, m.league_id, m.kickoff_utc, m.status, m.home_team_id, m.away_team_id,
                  m.home_goals, m.away_goals
           FROM matches m JOIN leagues l USING (league_id)
           WHERE l.fdorg_code IS NOT NULL AND m.kickoff_utc >= %s AND m.kickoff_utc < %s""",
        (datetime.combine(d_from - timedelta(days=1), datetime.min.time(), timezone.utc),
         datetime.combine(d_to + timedelta(days=2), datetime.min.time(), timezone.utc)))


def _alert(text: str) -> None:
    try:
        from ..publish import telegram
        telegram.alert(text)
    except Exception:  # noqa: BLE001
        log.exception('No se pudo avisar')


def run(now: datetime | None = None, client: Client | None = None) -> dict:
    from . import api_football as af
    now = now or datetime.now(timezone.utc)
    row = settings_row()
    if not row.get('enabled'):
        return {'skipped': 'desactivado'}
    key = os.getenv(KEY_ENV, '')
    if not key:
        af.record_health('fdorg', 0, False, {'error': 'sin clave'})
        return {'skipped': 'sin clave'}
    client = client or Client(key)
    previous = row.get('last_detail') or {}
    result = {'matches': 0, 'discrepancies_new': 0, 'votes': 0, 'teams_learned': 0, 'unmapped': 0, 'omitted': 0}
    with conn() as lock:
        if not lock.execute('SELECT pg_try_advisory_lock(%s) AS locked', (LOCK_ID,)).fetchone()['locked']:
            return {'skipped': 'otra pasada en curso'}
        try:
            result.update(_run(client, now))
            ok, detail = True, {**result, 'consecutive_failures': 0}
        except Unauthorized:
            ok, detail = False, {**result, 'error': UNAUTHORIZED, 'consecutive_failures': 1}
            if previous.get('error') != UNAUTHORIZED:
                _alert('football-data.org: la clave fue rechazada (401). Revisa FOOTBALL_DATA_ORG_KEY.')
        except Fail as exc:
            n = int(previous.get('consecutive_failures', 0)) + 1
            ok, detail = False, {**result, 'error': str(exc)[:200], 'consecutive_failures': n}
            if n == FAILURES_BEFORE_ALERT:
                _alert(f'football-data.org: {n} pasadas seguidas fallidas ({exc}).')
        except Exception as exc:  # noqa: BLE001 — el respaldo no puede tumbar el cron
            log.exception('Pasada de football-data.org fallida')
            n = int(previous.get('consecutive_failures', 0)) + 1
            ok, detail = False, {**result, 'error': str(exc)[:200], 'consecutive_failures': n}
        finally:
            lock.execute('SELECT pg_advisory_unlock(%s)', (LOCK_ID,))
    with conn() as c:
        c.execute('UPDATE fdorg_settings SET last_run_at = now(), last_ok = %s, last_detail = %s WHERE id = 1',
                  (ok, Jsonb(detail)))
    af.record_health('fdorg', detail.get('discrepancies_new', 0), ok, detail)
    return detail


def _run(client: Client, now: datetime) -> dict:
    code_rows = query('SELECT league_id, fdorg_code FROM leagues WHERE fdorg_code IS NOT NULL')
    league_by_code = {r['fdorg_code']: r['league_id'] for r in code_rows}
    mapping = {r['fdorg_team_id']: r['team_id'] for r in query('SELECT fdorg_team_id, team_id FROM fdorg_teams')}
    today = now.date()
    codes = sorted(league_by_code)
    raw = {}
    for d_from, d_to in ((today - timedelta(days=DAYS_BACK), today + timedelta(days=DAYS_AHEAD_RECENT)),
                         (today, today + timedelta(days=DAYS_AHEAD_FIXTURES))):
        for m in fetch_window(client, codes, d_from, d_to):
            raw[m['id']] = m
    common = [c for c in (to_common(m) for m in raw.values()) if c is not None]
    db_rows = _db_window(today - timedelta(days=DAYS_BACK), today + timedelta(days=DAYS_AHEAD_FIXTURES))
    pairs, discrepancies, votes, unmapped = compare(common, db_rows, mapping, league_by_code, now)
    discrepancies = apply_pending_grace(discrepancies, db_rows, now)
    for d in discrepancies:
        d['fdorg_match_id'] = d.pop('pitch_match_id')
    discrepancies += compare_calendar(common, db_rows, mapping, league_by_code, now)
    out = {'matches': len(raw), 'omitted': len(raw) - len(common), 'unmapped': unmapped,
           'votes': len(votes), 'discrepancies_new': 0, 'teams_learned': 0}
    new_alertable = []
    with conn() as c:
        for fd_team, club, fd_match in votes:
            c.execute('INSERT INTO fdorg_team_votes VALUES (%s, %s, %s) ON CONFLICT DO NOTHING',
                      (fd_team, club, fd_match))
        vote_rows = [(r['fdorg_team_id'], r['team_id'], r['n']) for r in c.execute(
            'SELECT fdorg_team_id, team_id, count(*) AS n FROM fdorg_team_votes GROUP BY 1, 2').fetchall()]
        owned = {r['team_id'] for r in c.execute('SELECT team_id FROM fdorg_teams').fetchall()}
        for fd_team, club, n in promote(vote_rows, owned, set(mapping)):
            c.execute('INSERT INTO fdorg_teams (fdorg_team_id, team_id, votes, evidence) '
                      'VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING',
                      (fd_team, club, n, Jsonb({'source': 'votos diarios', 'at': now.isoformat()})))
            out['teams_learned'] += 1
        for d in discrepancies:
            added = c.execute(
                """INSERT INTO fdorg_discrepancies (kind, match_id, league_id, fdorg_match_id, detail)
                   VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING RETURNING id""",
                (d['kind'], d['match_id'], d['league_id'], d['fdorg_match_id'], Jsonb(d['detail']))).fetchone()
            if added:
                out['discrepancies_new'] += 1
                if alertable(d):
                    new_alertable.append(d)
    if new_alertable:
        _alert(f'football-data.org: {len(new_alertable)} diferencia(s) nuevas de calendario o resultado.\n'
               + '\n'.join(alert_line(d) for d in new_alertable[:5]))
    return out


def main(argv=None):
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(run(), ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
