"""Estadísticas públicas de cada partido de NBA para la ventana de la web: forma, cara a cara y clasificación.

Solo resume marcadores finales ya validados (histórico `games.json`, `completed_games.json` de cada cohorte sellada y los
resultados oficiales que el panel ya verifica). No consulta la red, no usa cuotas ni modelos y no toca los sellos.
Cada partido se calcula «a la fecha»: solo cuentan partidos de días anteriores al suyo, así que un partido ya jugado
muestra lo que se sabía antes de empezar y no su propio resultado.

Qué NO hay, porque ninguna fuente validada lo trae: alineaciones, estadio y capacidad, ni cuotas por cuarto. No se inventan.
"""
from collections import defaultdict
from datetime import UTC, datetime
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo('America/New_York')
FORM_MATCHES = 6
H2H_MATCHES = 6
# Tipo de partido = tercer carácter del id de la NBA: 2 regular, 4 eliminatoria, 5 play-in. La clasificación solo cuenta regular.
FORM_TYPES = frozenset('245')
STANDING_TYPES = frozenset('2')

EAST = frozenset({'Atlanta Hawks', 'Boston Celtics', 'Brooklyn Nets', 'Charlotte Hornets', 'Chicago Bulls', 'Cleveland Cavaliers',
                  'Detroit Pistons', 'Indiana Pacers', 'Miami Heat', 'Milwaukee Bucks', 'New York Knicks', 'Orlando Magic',
                  'Philadelphia 76ers', 'Toronto Raptors', 'Washington Wizards'})
WEST = frozenset({'Dallas Mavericks', 'Denver Nuggets', 'Golden State Warriors', 'Houston Rockets', 'LA Clippers',
                  'Los Angeles Lakers', 'Memphis Grizzlies', 'Minnesota Timberwolves', 'New Orleans Pelicans',
                  'Oklahoma City Thunder', 'Phoenix Suns', 'Portland Trail Blazers', 'Sacramento Kings', 'San Antonio Spurs',
                  'Utah Jazz'})


def conference(team):
    return 'este' if team in EAST else 'oeste' if team in WEST else None


def season_of(day):
    """Temporada («2026-27») a la que pertenece una fecha: de octubre a septiembre."""
    year = int(day[:4]) if int(day[5:7]) >= 9 else int(day[:4]) - 1
    return f'{year}-{str(year + 1)[2:]}'


def et_day(tipoff_utc):
    return datetime.fromisoformat(tipoff_utc.replace('Z', '+00:00')).astimezone(EASTERN).date().isoformat()


def normalize(game_id, day, home, away, home_points, away_points):
    """Un partido final en la forma interna. None si falta algo o los marcadores no son un resultado."""
    if not (isinstance(game_id, str) and len(game_id) == 10 and game_id.isdigit()) or not home or not away or home == away:
        return None
    if type(home_points) is not int or type(away_points) is not int or home_points == away_points or min(home_points, away_points) < 0:
        return None
    return dict(game_id=game_id, date=day, kind=game_id[2], season=season_of(day), home=home, away=away, hp=home_points, ap=away_points)


def from_box(row):
    """Fila de `games.json` o `completed_games.json` (home/away anidados con nombre y puntos)."""
    return normalize(row.get('game_id'), row.get('date'), row['home'].get('name'), row['away'].get('name'),
                     row['home'].get('points'), row['away'].get('points'))


def merge_games(*sources):
    """Une listas de partidos por id; si dos fuentes discrepan en un marcador se descarta ese partido (no se elige uno)."""
    seen, bad = {}, set()
    for rows in sources:
        for g in rows:
            if g is None:
                continue
            old = seen.setdefault(g['game_id'], g)
            if (old['home'], old['away'], old['hp'], old['ap']) != (g['home'], g['away'], g['hp'], g['ap']):
                bad.add(g['game_id'])
    return sorted((g for k, g in seen.items() if k not in bad), key=lambda g: (g['date'], g['game_id']))


def record(won, lost):
    total = won + lost
    return dict(won=won, lost=lost, rate=round(won / total, 4) if total else None)


def side_view(game, team):
    """El partido desde el punto de vista de `team`."""
    home = game['home'] == team
    own, other = (game['hp'], game['ap']) if home else (game['ap'], game['hp'])
    return dict(date=game['date'], opponent=game['away'] if home else game['home'], home=home, points=own, opponent_points=other,
                won=own > other)


def streak(views):
    """Racha actual de la lista (más reciente primero): positiva si son victorias seguidas, negativa si derrotas."""
    if not views:
        return 0
    n = 0
    for v in views:
        if v['won'] != views[0]['won']:
            break
        n += 1
    return n if views[0]['won'] else -n


def averages(views):
    n = len(views)
    if not n:
        return dict(games=0, points_for=None, points_against=None)
    return dict(games=n, points_for=round(sum(v['points'] for v in views) / n, 1),
                points_against=round(sum(v['opponent_points'] for v in views) / n, 1))


def _days_between(a, b):
    return (datetime.fromisoformat(b) - datetime.fromisoformat(a)).days


def team_block(games, team, as_of):
    """Todo lo de un equipo con los partidos anteriores a `as_of` (AAAA-MM-DD)."""
    before = [g for g in games if g['date'] < as_of and team in (g['home'], g['away'])]
    views = [side_view(g, team) for g in reversed(before) if g['kind'] in FORM_TYPES]  # más reciente primero
    season = season_of(as_of)
    standing = [side_view(g, team) for g in reversed(before) if g['kind'] in STANDING_TYPES and g['season'] == season]
    previous = f'{int(season[:4]) - 1}-{season[2:4]}'
    last_year = [side_view(g, team) for g in before if g['kind'] in STANDING_TYPES and g['season'] == previous]

    def rec(rows):
        return record(sum(v['won'] for v in rows), sum(not v['won'] for v in rows))
    form = {key: [dict(v) for v in rows[:FORM_MATCHES]] for key, rows in
            (('all', views), ('home', [v for v in views if v['home']]), ('away', [v for v in views if not v['home']]))}
    # Días libres desde el último partido; tras más de 10 días (receso o inicio de temporada) no es un dato de descanso.
    rest = _days_between(views[0]['date'], as_of) - 1 if views and _days_between(views[0]['date'], as_of) <= 10 else None
    return dict(name=team, conference=conference(team), season=rec(standing),
                home=rec([v for v in standing if v['home']]), away=rec([v for v in standing if not v['home']]),
                scoring=averages(standing), last6=dict(rec(views[:FORM_MATCHES]), **averages(views[:FORM_MATCHES])),
                streak=streak(standing), rest_days=rest, back_to_back=rest == 0 if rest is not None else None,
                last_season=dict(rec(last_year), **averages(last_year)), form=form)


def standings_rank(games, team, as_of):
    """Posición en su conferencia por porcentaje de victorias, luego victorias; sin desempates oficiales de la NBA."""
    conf = conference(team)
    season = season_of(as_of)
    table = defaultdict(lambda: [0, 0])
    for g in games:
        if g['date'] >= as_of or g['kind'] not in STANDING_TYPES or g['season'] != season:
            continue
        for name, won in ((g['home'], g['hp'] > g['ap']), (g['away'], g['ap'] > g['hp'])):
            table[name][0 if won else 1] += 1
    teams = EAST if conf == 'este' else WEST if conf == 'oeste' else frozenset()
    rows = sorted(((t, *table.get(t, [0, 0])) for t in teams),
                  key=lambda r: (-(r[1] / (r[1] + r[2]) if r[1] + r[2] else 0), -r[1], r[0]))
    for i, (t, w, l) in enumerate(rows, 1):
        if t == team:
            return dict(rank=i if w + l else None, of=len(rows), conference=conf)
    return dict(rank=None, of=0, conference=conf)


def head_to_head(games, home, away, as_of):
    meetings = [g for g in games if g['date'] < as_of and g['kind'] in FORM_TYPES and {g['home'], g['away']} == {home, away}]
    last = list(reversed(meetings))[:H2H_MATCHES]
    rows = [dict(date=g['date'], home=g['home'], away=g['away'], home_points=g['hp'], away_points=g['ap']) for g in last]
    wins = lambda team: sum((g['home'] == team and g['hp'] > g['ap']) or (g['away'] == team and g['ap'] > g['hp']) for g in last)
    return dict(matches=rows, home_wins=wins(home), away_wins=wins(away),
                average_total=round(sum(g['hp'] + g['ap'] for g in last) / len(last), 1) if last else None)


def event_stats(games, event_id, home, away, tipoff_utc):
    day = et_day(tipoff_utc)
    teams = []
    for team in (home, away):
        block = team_block(games, team, day)
        block['standing'] = standings_rank(games, team, day)
        teams.append(block)
    return dict(event_id=event_id, as_of=day, teams=teams, h2h=head_to_head(games, home, away, day))


def build_feed(games, events, now):
    """`events`: lista de dict(event_id, home_team, away_team, tipoff_utc). Devuelve el JSON público completo."""
    games = merge_games(games)
    out = {}
    for e in events:
        if not (isinstance(e.get('event_id'), str) and e['event_id'].isdigit()) or e['home_team'] == e['away_team']:
            continue
        out[e['event_id']] = event_stats(games, e['event_id'], e['home_team'], e['away_team'], e['tipoff_utc'])
    return dict(generated_at=now.astimezone(UTC).isoformat(), source='NBA.com (marcadores oficiales)', games_used=len(games), events=out)


# ---- lectura de las carpetas del host (solo en el CLI; los módulos de arriba no tocan el disco)
def read_history(data_dir):
    rows = json.loads((Path(data_dir) / 'games.json').read_bytes())
    return [from_box(r) for r in rows]


def read_cohorts(cohorts_dir, now):
    """(partidos terminados de cada cohorte + resultados oficiales verificados, eventos de todas las cohortes)."""
    from .multimarket_live_dashboard import LiveCohort
    games, events = [], {}
    for folder in sorted(p for p in Path(cohorts_dir).iterdir() if (p / 'bundle.seal.json').exists()):
        try:
            completed = json.loads((folder / 'completed_games.json').read_bytes())['games']
            data = LiveCohort(folder).data(now)
        except (ValueError, KeyError, OSError):
            continue  # una cohorte que no valida no aporta nada; el panel ya la marca aparte
        games.extend(from_box(g) for g in completed)
        for e in data['events']:
            if e['status'] == 'validation_hold':
                continue
            events[e['event_id']] = dict(event_id=e['event_id'], home_team=e['home_team'], away_team=e['away_team'], tipoff_utc=e['tipoff_utc'])
            if e['status'] == 'evaluated' and e.get('final'):
                games.append(normalize(e['event_id'], et_day(e['tipoff_utc']), e['home_team'], e['away_team'],
                                       e['final']['home'], e['final']['away']))
    return games, list(events.values())


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohorts', required=True)
    parser.add_argument('--data', required=True)
    parser.add_argument('--output', required=True, help='archivo JSON de salida (se reemplaza de forma atómica)')
    a = parser.parse_args()
    now = datetime.now(UTC)
    cohort_games, events = read_cohorts(a.cohorts, now)
    feed = build_feed([*read_history(a.data), *cohort_games], events, now)
    target = Path(a.output)
    temp = target.with_suffix('.tmp')
    temp.write_text(json.dumps(feed, ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf8')
    os.replace(temp, target)
    print(json.dumps(dict(events=len(feed['events']), games_used=feed['games_used'])))


if __name__ == '__main__':
    main()
