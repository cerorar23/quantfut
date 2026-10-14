"""Enriquecimiento recibido después del primer original: identidad y reloj propios."""
import gzip
import hashlib
import json
from pathlib import Path

from psycopg.types.json import Jsonb

from .fotmob_import import records, timestamp, json_write
from .sofascore_history import normalize_bundle


def verified_observation(row, archive):
    path=Path(archive)/'raw/matches'/(row['source_match_id']+'.json.gz')
    packed=path.read_bytes();raw=gzip.decompress(packed)
    meta=json.loads(path.with_name(path.name+'.meta.json').read_text(encoding='utf-8'))
    if hashlib.sha256(raw).hexdigest()!=row['raw_sha256']:
        raise ValueError('observation_original_changed')
    if normalize_bundle(row['league_id'],raw,meta)!=row:
        raise ValueError('observation_normalization_changed')
    return packed,meta


def validate_identity(row, decision, parent):
    if decision.get('mapping_status')!='matched' or parent is None:
        raise ValueError('supplement_requires_existing_mapping')
    if (parent['match_id']!=decision['match_id'] or parent['league_id']!=row['league_id']
            or parent['status']!='finished'
            or str(parent['external_ids'].get('sofascore'))!=row['source_match_id']):
        raise ValueError('supplement_identity_changed')
    if abs(timestamp(parent['kickoff_utc'])-timestamp(row['kickoff_utc'])).total_seconds()>129600:
        raise ValueError('supplement_kickoff_changed')
    for side in ('home','away'):
        if (parent[side+'_goals']!=row[side+'_goals']
                or parent[side+'_team_id']!=decision[side+'_team_id']
                or parent[side+'_source_team_id']!=row[side+'_source_team_id']):
            raise ValueError('supplement_teams_or_score_changed')


def apply_observations(c, normalized, plan_path, archive, output):
    plan=json.loads(Path(plan_path).read_text(encoding='utf-8'))
    if plan['supplements_sha256']!=hashlib.sha256(Path(normalized).read_bytes()).hexdigest():
        raise ValueError('reviewed_supplements_changed')
    result={'observations_inserted':0,'xg_added':0,'lineups_received':0,
            'players_received':0,'absences_received':0}
    with c.transaction():
        c.execute('SELECT pg_advisory_xact_lock(61013062)')
        for row in records(normalized):
            if row['provider']!='sofascore':
                raise ValueError('unsupported_supplement_provider')
            decision=plan['decisions'][row['source_match_id']]
            packed,meta=verified_observation(row,archive)
            parent=c.execute("""SELECT h.match_id,m.league_id,m.status,m.kickoff_utc,
                m.home_goals,m.away_goals,m.home_team_id,m.away_team_id,m.external_ids,
                h.home_source_team_id,h.away_source_team_id
                FROM historical_football_matches h JOIN matches m USING(match_id)
                WHERE h.provider='sofascore' AND h.source_match_id=%s FOR UPDATE OF m""",
                (row['source_match_id'],)).fetchone()
            validate_identity(row,decision,parent)
            inserted=c.execute("""INSERT INTO historical_football_observations
                (provider,source_match_id,raw_sha256,match_id,league_id,captured_at,
                 raw_payload_gzip,raw_metadata,normalized)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT DO NOTHING RETURNING captured_at""",
                (row['provider'],row['source_match_id'],row['raw_sha256'],parent['match_id'],
                 row['league_id'],timestamp(row['captured_at']),packed,Jsonb(meta),Jsonb(row))).fetchone()
            observation=inserted or c.execute("""SELECT captured_at
                FROM historical_football_observations WHERE provider=%s
                AND source_match_id=%s AND raw_sha256=%s""",
                (row['provider'],row['source_match_id'],row['raw_sha256'])).fetchone()
            result['observations_inserted']+=bool(inserted)
            if inserted:
                for field,key in [('lineups','lineups_received'),('players','players_received'),('absences','absences_received')]:
                    result[key]+=len(row[field])
            if row['home_xg'] is not None and row['away_xg'] is not None:
                result['xg_added']+=c.execute("""UPDATE matches SET home_xg=%s,away_xg=%s,
                    xg_source='sofascore',xg_recorded_at=%s WHERE match_id=%s
                    AND status='finished' AND home_xg IS NULL AND away_xg IS NULL""",
                    (row['home_xg'],row['away_xg'],observation['captured_at'],parent['match_id'])).rowcount
    json_write(output,result)
    return result
