#!/usr/bin/env python3
"""Descarga masiva y reanudable de BetsAPI (cuotas históricas). Guarda las respuestas crudas en gzip.

Solo lectura de la API; el token sale de un archivo KEY=valor y no se imprime. Respeta x-ratelimit-*.
Lo ya descargado (archivo existente) no se vuelve a pedir, así que se puede relanzar sin gastar peticiones.

  python betsapi_descarga.py --env .env.betsapi --out data nba --since 2024-07-01
  python betsapi_descarga.py --env .env.betsapi --out data tennis --since 2025-01-01
  python betsapi_descarga.py --env .env.betsapi --out data football --leagues ligas.json --since 2024-07-01
"""
import argparse
import gzip
import http.client
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BASE = 'https://api.b365api.com'
NBA_LEAGUE = 2274
TENNIS, BASKET, SOCCER = 13, 18, 1
FATAL = ('TOKEN', 'PERMISSION', 'EXPIRE', 'LIMIT_EXCEED', 'NOT_ALLOWED', 'FORBIDDEN')


class Fatal(Exception):
    pass


def log(msg):
    print(datetime.now(timezone.utc).strftime('%m-%d %H:%M:%S'), msg, flush=True)


class Client:
    def __init__(self, token):
        self.token, self.remaining, self.reset, self.calls = token, None, 0, 0

    def _headers(self, h):
        try:
            self.remaining = int(h.get('x-ratelimit-remaining'))
            self.reset = int(h.get('x-ratelimit-reset'))
        except (TypeError, ValueError):
            pass

    def _wait_window(self, minimum=30):
        wait = max(minimum, self.reset - time.time() + 2)
        log(f'limite por hora: espero {int(wait)}s')
        time.sleep(wait)
        self.remaining = None

    def get(self, path, **q):
        q['token'] = self.token
        url = BASE + path + '?' + urllib.parse.urlencode(q)
        for attempt in range(6):
            if self.remaining is not None and self.remaining <= 3:
                self._wait_window(minimum=1)
            try:
                with urllib.request.urlopen(url, timeout=60) as r:
                    self._headers(r.headers)
                    body = json.load(r)
            except urllib.error.HTTPError as e:
                self._headers(e.headers)
                if e.code == 429:
                    self._wait_window()
                    continue
                if e.code in (401, 403):
                    raise Fatal(f'HTTP {e.code}')
                time.sleep(5 * (attempt + 1))
                continue
            except (urllib.error.URLError, TimeoutError, ValueError, OSError, http.client.HTTPException):
                time.sleep(5 * (attempt + 1))
                continue
            self.calls += 1
            if body.get('success') == 0 and any(w in str(body.get('error', '')).upper() for w in FATAL):
                raise Fatal(str(body.get('error')) + ' ' + str(body.get('error_detail', ''))[:120])
            return body
        raise RuntimeError('sin respuesta tras reintentos: ' + path)


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    with gzip.open(tmp, 'wt', encoding='utf-8') as f:
        json.dump(obj, f, separators=(',', ':'))
    os.replace(tmp, path)


def load(path):
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        return json.load(f)


def list_ended(c, root, key, **params):
    """Todas las páginas de /v3/events/ended para unos parámetros; cacheado por `key`."""
    path = root / 'list' / f'{key}.json.gz'
    if path.exists():
        return load(path)['results']
    out, page = [], 1
    while True:
        b = c.get('/v3/events/ended', page=page, **params)
        out += b.get('results') or []
        pg = b.get('pager') or {}
        if page * int(pg.get('per_page', 50)) >= int(pg.get('total', 0)) or page >= 100:
            break
        page += 1
    save(path, dict(params=params, results=out))
    return out


def fetch_odds(c, root, ev):
    path = root / 'odds' / f"{ev['id']}.json.gz"
    if path.exists():
        return False
    body = c.get('/v2/event/odds', event_id=ev['id'])
    save(path, dict(event=ev, odds=body.get('results'), success=body.get('success')))
    return True


def days(since, until):
    d = until
    while d >= since:
        yield d
        d -= timedelta(days=1)


def tennis_keep(e):
    name, h, a = e.get('league', {}).get('name', ''), e.get('home', {}).get('name', ''), e.get('away', {}).get('name', '')
    if '/' in h or '/' in a or str(e.get('time_status')) != '3' or not e.get('ss'):
        return False
    return not re.match(r'^[MW]\d{1,3}\b', name) and 'UTR' not in name and 'Davis' not in name


def run_days(c, root, sport, since, until, keep, label, skip_months=(), **extra):
    done = 0
    for d in days(since, until):
        if d.month in skip_months:
            continue
        evs = list_ended(c, root, d.strftime('%Y%m%d'), sport_id=sport, day=d.strftime('%Y%m%d'), **extra)
        for ev in evs:
            if keep(ev) and fetch_odds(c, root, ev):
                done += 1
        if d.day == 1 or d == until:
            log(f'{label} {d} peticiones={c.calls} cuotas_nuevas={done}')
    log(f'{label} listo: peticiones={c.calls} cuotas_nuevas={done}')


def run_football(c, root, leagues, since):
    cutoff = int(datetime.combine(since, datetime.min.time(), tzinfo=timezone.utc).timestamp())
    for lg in leagues:
        sub = root / lg['name']
        page, done, stop = 1, 0, False
        while not stop and page <= 100:
            path = sub / 'list' / f'p{page:03d}.json.gz'
            if path.exists():
                evs = load(path)['results']
            else:
                b = c.get('/v3/events/ended', sport_id=SOCCER, league_id=lg['league_id'], page=page)
                evs = b.get('results') or []
                save(path, dict(results=evs))
            if not evs:
                break
            for ev in evs:
                if int(ev['time']) < cutoff:
                    stop = True
                    continue
                if str(ev.get('time_status')) == '3' and fetch_odds(c, sub, ev):
                    done += 1
            page += 1
        log(f"{lg['name']} listo: peticiones={c.calls} cuotas_nuevas={done}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--env', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    sub = p.add_subparsers(dest='cmd', required=True)
    for name in ('nba', 'tennis', 'football'):
        s = sub.add_parser(name)
        s.add_argument('--since', required=True)
        s.add_argument('--until', default=date.today().isoformat())
        if name == 'football':
            s.add_argument('--leagues', type=Path, required=True)
    a = p.parse_args()
    token = dict(l.strip().split('=', 1) for l in a.env.read_text().splitlines() if '=' in l)['BETSAPI_TOKEN']
    c = Client(token)
    since, until = date.fromisoformat(a.since), date.fromisoformat(a.until)
    try:
        if a.cmd == 'nba':
            offseason = lambda e: True  # el filtro por league_id ya deja solo NBA
            run_days(c, a.out / 'nba', BASKET, since, until, offseason, 'nba', skip_months=(7, 8, 9), league_id=NBA_LEAGUE)
        elif a.cmd == 'tennis':
            run_days(c, a.out / 'tennis', TENNIS, since, until, tennis_keep, 'tenis')
        else:
            run_football(c, a.out / 'football', json.loads(a.leagues.read_text()), since)
    except Fatal as e:
        log(f'DETENIDO por la API: {e}')
        sys.exit(3)


if __name__ == '__main__':
    main()
