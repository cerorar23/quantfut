"""Normaliza originales SofaScore sin anticipar recepción ni mezclar IDs."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json

from .fotmob_history import number
from .fotmob_import import timestamp
from ..league_policy import require_supported_league

# Se verifica el torneo y país en cada calendario; los IDs son del proveedor.
TOURNAMENTS = {
    'gb.premier_league': 17, 'gb.championship': 18,
    'es.laliga': 8, 'es.laliga2': 54, 'it.serie_a': 23, 'it.serie_b': 53,
    'fr.ligue_1': 34, 'fr.ligue_2': 182, 'de.bundesliga': 35, 'de.bundesliga2': 44,
    'nl.eredivisie': 37, 'pt.primeira': 238, 'ar.primera': 155,
    'br.serie_a': 325, 'mx.liga_mx': 11620,
    'us.mls': 242, 'ch.super_league': 215, 'dk.superliga': 39,
    'no.eliteserien': 20, 'se.allsvenskan': 40, 'tr.super_lig': 52,
    'eu.ucl': 7, 'eu.uel': 679,
}


def positive_id(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def stat_pair(statistics, key, period='ALL'):
    """Repeticiones idénticas se aceptan; valores discrepantes se rechazan."""
    pairs = set()
    for section in (statistics or {}).get('statistics') or []:
        if section.get('period') != period:
            continue
        for group in section.get('groups') or []:
            for item in group.get('statisticsItems') or []:
                if item.get('key') != key:
                    continue
                pair = tuple(number(item.get(side+'Value')) for side in ('home','away'))
                if None not in pair:
                    pairs.add(pair)
    if len(pairs) > 1:
        raise ValueError('conflicting_duplicate_stat:' + key)
    return next(iter(pairs)) if pairs else (None, None)


def score(event, side):
    data = event.get(side+'Score') or {}
    value = data.get('normaltime')
    if value is None and (event.get('status') or {}).get('code') == 100:
        value = data.get('current')
    if isinstance(value,bool) or not isinstance(value,int) or not 0 <= value < 100:
        raise ValueError('normal_time_score_unavailable')
    return value


def normalize_bundle(league, raw, metadata):
    require_supported_league(league)
    if hashlib.sha256(raw).hexdigest() != metadata['sha256']:
        raise ValueError('original_hash_mismatch')
    payload = json.loads(raw)
    event = payload['event']
    tid = ((event.get('tournament') or {}).get('uniqueTournament') or {}).get('id')
    allowed = {TOURNAMENTS[league]}
    if league == 'mx.liga_mx':
        allowed.add(11621)  # Torneos Apertura/Clausura de la misma competición.
    historical_arg_cup = (league == 'ar.primera' and tid == 13475
                          and str((event.get('season') or {}).get('year')) == '2024')
    if historical_arg_cup:
        allowed.add(13475)  # Copa de la Liga 2024: solo asociación histórica existente.
    if tid not in allowed:
        raise ValueError('wrong_tournament')
    category = (event.get('tournament') or {}).get('category') or {}
    if not league.startswith('eu.'):
        country = str(category.get('alpha2') or (category.get('country') or {}).get('alpha2') or '').lower()
        expected = {'en','gb'} if league.startswith('gb.') else {league.split('.')[0]}
        if country not in expected:
            raise ValueError('wrong_competition_country')
    if (event.get('status') or {}).get('type') != 'finished':
        raise ValueError('unfinished_event')
    teams = {side:event[side+'Team'] for side in ('home','away')}
    for team in teams.values():
        if not positive_id(team.get('id')) or team.get('sport',{}).get('id') != 1:
            raise ValueError('invalid_team_or_sport')
        if team.get('national') or team.get('gender') not in (None,'M'):
            raise ValueError('wrong_team_category')
    if teams['home']['id'] == teams['away']['id']:
        raise ValueError('same_team')
    if not positive_id(event.get('id')) or not isinstance(event.get('startTimestamp'),int) or isinstance(event['startTimestamp'],bool):
        raise ValueError('invalid_event_identity')
    kickoff = datetime.fromtimestamp(event['startTimestamp'],timezone.utc)
    captured = timestamp(metadata['captured_at'])
    if historical_arg_cup and kickoff.year != 2024:
        raise ValueError('wrong_historical_competition_year')
    if not kickoff <= captured <= datetime.now(timezone.utc):
        raise ValueError('invalid_capture_time')
    statistics = payload.get('statistics')
    code = event.get('status',{}).get('code')
    # AET/AP use only the first 90 minutes. Never mix 120-minute xG with 1x2.
    if code == 100:
        xg = stat_pair(statistics,'expectedGoals')
    else:
        first = stat_pair(statistics,'expectedGoals','1ST')
        second = stat_pair(statistics,'expectedGoals','2ND')
        xg = tuple(first[i]+second[i] if first[i] is not None and second[i] is not None else None for i in range(2))
    row = {'provider':'sofascore','source_match_id':str(event['id']),
           'league_id':league,'season':str((event.get('season') or {}).get('year') or (event.get('season') or {}).get('name') or kickoff.year),
           'kickoff_utc':kickoff.isoformat(),'captured_at':captured.isoformat(),
           'raw_sha256':metadata['sha256'],'home_xg':xg[0],'away_xg':xg[1],
           'statistics':{'response':statistics,'normal_time_only':code!=100},
           'counts':{},'lineups':[],'players':[],'absences':[]}
    for side in ('home','away'):
        row[side+'_source_team_id'] = str(teams[side]['id'])
        row[side+'_name'] = teams[side]['name']
        row[side+'_goals'] = score(event,side)
    if historical_arg_cup:
        row['historical_tournament_id'] = 13475
    for target,key in [('shots','totalShotsOnGoal'),('shots_target','shotsOnTarget'),('corners','cornerKicks')]:
        pair = stat_pair(statistics,key) if code==100 else (None,None)
        for side,value in zip(('home','away'),pair):
            row['counts'][side+'_'+target] = value
    lineup = payload.get('lineups') or {}
    confirmed = lineup.get('confirmed') is True
    row['statistics']['lineup_confirmed'] = confirmed
    row['statistics']['player_identity_issues'] = []
    seen = set()
    for side in ('home','away'):
        data = lineup.get(side) or {}
        players = data.get('players') or []
        starters, substitutes = [], []
        for entry in players:
            p = entry.get('player') or {}
            pid = p.get('id')
            if not positive_id(pid) or not p.get('name'):
                continue
            if pid in seen:
                raise ValueError('player_team_or_identity_conflict')
            if entry.get('teamId') != teams[side]['id']:
                # Some academy substitutes carry their current U21 team ID.
                # Preserve the original and omit only this unverified player.
                row['statistics']['player_identity_issues'].append({
                    'side':side,'source_player_id':pid,'reported_team_id':entry.get('teamId')})
                continue
            seen.add(pid)
            if entry.get('substitute') is False:
                starters.append(entry)
            elif entry.get('substitute') is True:
                substitutes.append(entry)
            stats = entry.get('statistics')
            if isinstance(stats,dict) and stats:
                row['players'].append({'side':side,'source_player_id':pid,'player_name':p['name'],
                    'minutes':number(stats.get('minutesPlayed')),
                    'starter':not entry['substitute'] if confirmed and isinstance(entry.get('substitute'),bool) else None,
                    'statistics':stats})
        ids = [e['player']['id'] for e in starters]
        if players:
            row['lineups'].append({'side':side,'formation':data.get('formation'),
                'complete':confirmed and len(ids)==11 and len(set(ids))==11,
                'starters':starters,'substitutes':substitutes})
        for absent in data.get('missingPlayers') or []:
            p = absent.get('player') or {}
            if positive_id(p.get('id')) and p.get('name'):
                row['absences'].append({'side':side,'source_player_id':p['id'],
                    'player_name':p['name'],'availability':absent})
    return row
