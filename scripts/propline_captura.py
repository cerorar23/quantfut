#!/usr/bin/env python3
"""Captura programada de cierres de PropLine (plan Hobby: histórico de solo 30 días, así que el archivo propio se construye aquí).

Cada ejecución pide, por deporte, los partidos que empiezan en las próximas horas (o acaban de empezar) y guarda
`/odds/closing` de unas pocas casas. Un partido se vuelve a pedir en cada pasada hasta que ha empezado; luego queda
marcado como final (`.final`) y no se toca más. Tope diario de peticiones propio.

  python propline_captura.py --env .env.propline2 --out data/propline
"""
import argparse
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = 'https://api.prop-line.com'
DAILY_CAP = 4000          # Hobby: 5.000 al día
AHEAD_HOURS = 4           # empezar a capturar 4 h antes del inicio
BEHIND_MINUTES = 400      # el cierre queda fijo al empezar: basta una pasada después del inicio
FOOTBALL = ['soccer_la_liga', 'soccer_bundesliga', 'soccer_serie_a', 'soccer_ligue_1', 'soccer_eredivisie', 'soccer_primeira_liga',
            'soccer_liga_mx', 'soccer_mls', 'soccer_brasileirao', 'soccer_argentina_primera', 'soccer_turkey_super_lig',
            'soccer_uefa_champions_league', 'soccer_uefa_europa_league', 'soccer_germany_bundesliga2']
TENNIS_MARKETS = 'h2h,spreads,totals,total_games,total_sets,set_spread,total_tiebreaks'
FOOTBALL_MARKETS = 'h2h,totals,spreads,european_handicap,both_teams_to_score,double_chance,draw_no_bet,correct_score'
NBA_MARKETS = ('h2h,spreads,totals,player_points,player_rebounds,player_assists,player_threes')
SHARP = 'pinnacle,bovada,matchbook,kalshi'
US = 'pinnacle,bovada,draftkings,fanduel,betmgm,betrivers,unibet'
JOBS = ([('tennis', TENNIS_MARKETS, SHARP + ',draftkings', lambda e: e.get('tier') in ('atp', 'wta', 'challenger') and e['away_team'].strip() and '/' not in e['home_team'] + e['away_team'])]
        + [('basketball_nba', NBA_MARKETS, US, lambda e: True)]
        + [(s, FOOTBALL_MARKETS, SHARP + ',draftkings,fanduel', lambda e: True) for s in FOOTBALL])


def log(msg):
    print(datetime.now(timezone.utc).strftime('%m-%d %H:%M:%S'), msg, flush=True)


class Api:
    def __init__(self, key, state_path):
        self.key, self.state_path = key, state_path
        today = datetime.now(timezone.utc).date().isoformat()
        st = json.loads(state_path.read_text()) if state_path.exists() else {}
        self.state = st if st.get('day') == today else dict(day=today, calls=0)

    def get(self, path, **q):
        if self.state['calls'] >= DAILY_CAP:
            raise SystemExit('tope diario propio alcanzado')
        url = BASE + path + ('?' + urllib.parse.urlencode(q) if q else '')
        for attempt in range(4):
            req = urllib.request.Request(url, headers={'X-API-Key': self.key})
            try:
                self.state['calls'] += 1
                with urllib.request.urlopen(req, timeout=90) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep(int(e.headers.get('Retry-After', 30)))
                elif e.code in (401, 403):
                    raise SystemExit(f'clave rechazada (HTTP {e.code})')
                elif e.code == 404:
                    return None
                else:
                    time.sleep(5 * (attempt + 1))
            except (urllib.error.URLError, TimeoutError, ValueError, ConnectionError):
                time.sleep(5 * (attempt + 1))
        return None

    def save_state(self):
        self.state_path.write_text(json.dumps(self.state))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--env', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    key = dict(l.strip().split('=', 1) for l in a.env.read_text().splitlines() if '=' in l)['PROPLINE_KEY']
    a.out.mkdir(parents=True, exist_ok=True)
    api = Api(key, a.out / 'estado.json')
    now = datetime.now(timezone.utc)
    total = new = 0
    for sport, markets, books, keep in JOBS:
        events = api.get(f'/v1/sports/{sport}/events') or []
        for e in events:
            start = datetime.fromisoformat(e['commence_time'].replace('Z', '+00:00'))
            if not (now - timedelta(minutes=BEHIND_MINUTES) <= start <= now + timedelta(hours=AHEAD_HOURS)) or not keep(e):
                continue
            base = a.out / sport / str(e['id'])
            if base.with_suffix('.final').exists():
                continue
            body = api.get(f"/v1/sports/{sport}/events/{e['id']}/odds/closing", markets=markets, bookmakers=books)
            if not body:
                continue
            base.parent.mkdir(parents=True, exist_ok=True)
            tmp = base.with_suffix('.tmp')
            with gzip.open(tmp, 'wt', encoding='utf-8') as f:
                json.dump(dict(captured_at=now.isoformat(), event=e, closing=body), f, separators=(',', ':'))
            os.replace(tmp, base.with_suffix('.json.gz'))
            if start <= now:
                base.with_suffix('.final').write_text(now.isoformat())
            total += 1
    api.save_state()
    log(f"capturados={total} peticiones_hoy={api.state['calls']}")


if __name__ == '__main__':
    sys.exit(main())
