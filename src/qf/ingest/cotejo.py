"""Cotejo de resultados de una fuente testigo contra `matches` (lógica pura, sin base de datos).

`compare()` empareja por club y fecha y devuelve parejas, discrepancias, votos de equivalencia de equipos y cuántos
equipos no tienen equivalencia; `promote()` decide qué equivalencias se aceptan por votos. Lo usa `fdorg_respaldo`
(football-data.org). Nunca corrige nada: solo informa.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta

PENDING_AFTER = timedelta(hours=4)
MIN_VOTES, DOMINANCE = 3, 0.9


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
