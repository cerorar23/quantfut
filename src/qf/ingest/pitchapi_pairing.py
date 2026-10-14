"""Empareja originales de PitchAPI con partidos canónicos y prepara la carga de xG.

La identidad de club nunca sale de nombres: un equipo de PitchAPI solo se asocia a
un club canónico si al menos MIN_VOTES partidos independientes (misma fecha UTC y
marcador, candidato único) apuntan, con una dominancia de DOMINANCE, al
mismo club y ese club no lo comparte otro equipo. Después un partido solo se empareja si ambos clubes, el
marcador y la fecha coinciden con un único partido canónico.
"""
from collections import Counter, defaultdict
from datetime import date, timedelta
import json

from .pitchapi_history import finished_matches, load, team_xg

MIN_VOTES = 3
DOMINANCE = 0.9
MAX_XG = 10.0


def index_db(rows):
    by_league = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by_league[r['league_id']][(r['date'], r['home_goals'], r['away_goals'])].append(r)
    return by_league


def kickoff_day(match):
    return date.fromisoformat((match.get('time_utc') or match['date'])[:10])


def candidates(index, league, match, tolerance=1):
    day = kickoff_day(match)
    seen = {}
    for shift in range(-tolerance, tolerance + 1):
        for r in index[league].get((day + timedelta(days=shift), match['score_home'], match['score_away']), []):
            seen[r['match_id']] = r
    return list(seen.values())


def team_mapping(entries, index):
    votes = defaultdict(Counter)
    for league, _, match in entries:
        cands = candidates(index, league, match, tolerance=0)
        if len(cands) == 1:
            votes[match['home_team']['id']][cands[0]['home_team_id']] += 1
            votes[match['away_team']['id']][cands[0]['away_team_id']] += 1
    mapping = {}
    for team, counter in votes.items():
        (club, top), = counter.most_common(1)
        if top >= MIN_VOTES and top >= DOMINANCE * sum(counter.values()):
            mapping[team] = club
    owners = Counter(mapping.values())
    return {t: c for t, c in mapping.items() if owners[c] == 1}


def build_plan(archive, db_rows):
    entries = list(finished_matches(archive))
    index = index_db(db_rows)
    mapping = team_mapping(entries, index)
    pairs, rejected = [], Counter()
    for league, season, match in entries:
        home, away = mapping.get(match['home_team']['id']), mapping.get(match['away_team']['id'])
        if home is None or away is None:
            rejected['unmapped_team'] += 1
            continue
        found = [r for r in candidates(index, league, match)
                 if r['home_team_id'] == home and r['away_team_id'] == away]
        if len(found) != 1:
            rejected['no_canonical_match' if not found else 'ambiguous_match'] += 1
            continue
        target = found[0]
        if target['has_xg']:
            rejected['already_has_xg'] += 1
            continue
        cached = load(archive, 'stats', match['id'])
        if cached is None:
            rejected['stats_not_downloaded'] += 1
            continue
        receipt, raw = cached
        xg = team_xg(raw) if receipt['status'] == 200 else None
        if xg is None:
            rejected['xg_not_published'] += 1
            continue
        if not all(0 <= v <= MAX_XG for v in xg):
            rejected['xg_out_of_range'] += 1
            continue
        pairs.append({'match_id': target['match_id'], 'league_id': league,
                      'pitchapi_match_id': match['id'], 'home_xg': xg[0], 'away_xg': xg[1],
                      'received_at': receipt['received_at'], 'sha256': receipt['sha256']})
    ids = Counter(p['match_id'] for p in pairs)
    pairs = [p for p in pairs if ids[p['match_id']] == 1]
    return {'pairs': pairs, 'rejected': dict(rejected), 'mapped_teams': len(mapping)}


def apply_sql(plan, source='pitchapi', end='COMMIT'):
    """Una transacción; solo rellena partidos terminados sin xG y con equipos/marcador iguales."""
    values = ',\n'.join(
        "({}, {!r}::numeric, {!r}::numeric, '{}'::timestamptz)".format(
            "'" + p['match_id'].replace("'", "''") + "'",
            p['home_xg'], p['away_xg'], p['received_at']) for p in plan['pairs'])
    return f"""BEGIN;
CREATE TEMP TABLE pitch_xg(match_id TEXT, home_xg NUMERIC, away_xg NUMERIC, received_at TIMESTAMPTZ) ON COMMIT DROP;
INSERT INTO pitch_xg VALUES
{values};
WITH done AS (
  UPDATE matches m SET home_xg=s.home_xg, away_xg=s.away_xg,
         xg_source='{source}', xg_recorded_at=s.received_at
  FROM pitch_xg s WHERE m.match_id::text=s.match_id AND m.status='finished'
    AND m.home_xg IS NULL AND m.away_xg IS NULL
  RETURNING m.league_id)
SELECT league_id, count(*) FROM done GROUP BY 1 ORDER BY 1;
{end};
"""


def write_plan(plan, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(plan, f, ensure_ascii=False, indent=1)
