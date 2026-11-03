"""Archivo SofaScore local: un partido son hasta 13 bloques `.json.gz` más `manifest.json`.

Verifica cada bloque contra el hash del manifest, compone un único original canónico y lo
normaliza con las mismas reglas que los originales de Apify (`sofascore_history`). Proveedor
propio: su reloj de captura es la descarga local, no el actor, y así nada que cargue
`sofascore` puede confundirse con él. No escribe en la base.

Línea de órdenes (solo lectura sobre la base; el plan nunca crea partidos):
    normalize     archivo local -> normalized.jsonl.gz
    snapshot-sql  imprime la consulta que exporta el estado de `matches` para emparejar
    plan          emparejamiento con `matches` (reutiliza `fotmob_import.plan`)
    verify        comprueba el plan contra los archivos de los que salió
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .fotmob_import import TOLERANCE, json_write, plan, records, timestamp
from .sofascore_history import TOURNAMENTS, normalize_payload, stat_pair
from ..league_policy import require_supported_league

PROVIDER = 'sofascore_local'
REQUIRED = ('event', 'statistics', 'lineups')
# Ventana de asentamiento del scraper (`refresh.window_hours`, 72 h por defecto): un partido
# observado antes de inicio + ventana es provisional y el scraper lo vuelve a leer después.
SETTLEMENT_WINDOW = timedelta(hours=72)


def datetime_from(epoch_seconds):
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)


def match_dir(root, event_id):
    s = str(event_id)
    return Path(root) / 'events' / s[:2] / s[2:5] / s


def read_match(folder):
    """Devuelve (bloques, estados, manifest). Un bloque `ok` con hash distinto invalida el partido."""
    folder = Path(folder)
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    blocks, states = {}, {}
    for name, meta in (manifest.get('slices') or {}).items():
        if meta.get('state') != 'ok':
            states[name] = {'state': meta.get('state'), 'empty': meta.get('empty')}
            continue
        path = folder / (name + '.json.gz')
        if not path.is_file():
            raise ValueError('slice_missing:' + name)
        raw = gzip.decompress(path.read_bytes())
        if hashlib.sha256(raw).hexdigest() != meta.get('sha256'):
            raise ValueError('slice_hash_mismatch:' + name)
        blocks[name] = json.loads(raw)
        states[name] = {'state': 'ok', 'sha256': meta['sha256'],
                        'fetched_at': meta['fetched_at'], 'bytes': meta.get('bytes')}
    return blocks, states, manifest


def compose_original(blocks):
    """JSON canónico de todos los bloques: mismo contenido, mismo hash, sin depender del orden."""
    raw = json.dumps(blocks, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return raw, hashlib.sha256(raw).hexdigest()


def normalize_local_bundle(league, blocks, states, manifest):
    """(fila normalizada, original canónico en bytes, metadatos). La recepción real es el último
    `fetched_at` entre los bloques recibidos."""
    require_supported_league(league)
    missing = [name for name in REQUIRED if name not in blocks]
    if missing:
        raise ValueError('required_slice_missing:' + ','.join(missing))
    event = blocks['event']
    if manifest.get('id') != event.get('id'):
        raise ValueError('manifest_event_mismatch')
    observed = (manifest.get('observation') or {}).get('observed_at_utc')
    start = event.get('startTimestamp')
    if observed is not None and start is not None and timestamp(observed) - datetime_from(start) < SETTLEMENT_WINDOW:
        raise ValueError('provisional_record')
    raw, sha256 = compose_original(blocks)
    received = [s['fetched_at'] for s in states.values() if s.get('state') == 'ok']
    captured = max(received, key=timestamp)
    payload = {'event': event, 'statistics': blocks['statistics'], 'lineups': blocks['lineups']}
    # El archivo se descargó meses o años después: `teamId` de cada jugador es su club en
    # esa fecha, así que no sirve para rechazar jugadores del once de aquel día.
    row = normalize_payload(league, payload, sha256, captured, PROVIDER, strict_team_id=False)
    # Este origen nombra los tiros a puerta `shotsOnGoal`; el de Apify, `shotsOnTarget`.
    # Se completa solo aquí para no alterar la normalización de lo que ya está guardado.
    if (event.get('status') or {}).get('code') == 100:
        pair = stat_pair(blocks['statistics'], 'shotsOnGoal')
        for side, value in zip(('home', 'away'), pair):
            if row['counts'].get(side + '_shots_target') is None:
                row['counts'][side + '_shots_target'] = value
    meta = {'sha256': sha256, 'captured_at': captured, 'slices': states,
            'observation': manifest.get('observation'), 'manifest_created_at': manifest.get('created_at')}
    return row, raw, meta


def league_tournaments(league):
    """Torneos de SofaScore que forman una liga: México juega Apertura y Clausura por separado."""
    tournaments = [TOURNAMENTS[league]]
    if league == 'mx.liga_mx':
        tournaments.append(11621)
    return tournaments


def finished_event_ids(root, tournaments, since=None):
    """IDs de los partidos terminados de todas las temporadas de los torneos, según su calendario.
    `since` (fecha ISO) deja solo los que empezaron en ese día o después."""
    floor = timestamp(since + 'T00:00:00+00:00' if since and len(since) == 10 else since).timestamp() if since else None
    ids = []
    for tournament in ([tournaments] if isinstance(tournaments, int) else tournaments):
        seasons = Path(root) / 'tournaments' / str(tournament) / 'seasons'
        for schedule in sorted(seasons.glob('*/schedule/round_*.json.gz')):
            for event in json.loads(gzip.decompress(schedule.read_bytes())).get('events') or []:
                if (event.get('status') or {}).get('type') != 'finished':
                    continue
                if floor is not None and (event.get('startTimestamp') or 0) < floor:
                    continue
                ids.append(event['id'])
    return sorted(set(ids))


def normalize_archive(root, league, output, since=None):
    """Escribe `normalized.jsonl.gz` y `normalization-report.json` (mismo formato que fotmob_import)."""
    require_supported_league(league)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    cache = output / 'normalized.jsonl.gz'
    if cache.exists():
        raise ValueError('normalized_output_exists')
    errors, valid = [], 0
    # mtime=0: sin la fecha en la cabecera gzip, el mismo contenido da siempre el mismo hash.
    with gzip.GzipFile(cache, 'wb', mtime=0) as raw_out, io.TextIOWrapper(raw_out, encoding='utf-8') as handle:
        for event_id in finished_event_ids(root, league_tournaments(league), since):
            try:
                blocks, states, manifest = read_match(match_dir(root, event_id))
                row, _raw, _meta = normalize_local_bundle(league, blocks, states, manifest)
                handle.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
                valid += 1
            except (ValueError, KeyError, TypeError, OSError) as exc:
                errors.append({'source_match_id': str(event_id), 'reason': str(exc), 'type': type(exc).__name__})
    result = {'provider': PROVIDER, 'league_id': league, 'since': since, 'valid': valid, 'errors': errors,
              'normalized_sha256': hashlib.sha256(cache.read_bytes()).hexdigest()}
    json_write(output / 'normalization-report.json', result)
    return result


# Una sola consulta de solo lectura; el resultado es el `snapshot` que espera `fotmob_import.plan`.
SNAPSHOT_SQL = """
SELECT json_build_object(
  'leagues', (SELECT json_agg(json_build_object('league_id', league_id, 'cross_league', cross_league))
              FROM leagues WHERE league_id = '{league}'),
  'teams', (SELECT json_agg(json_build_object('team_id', team_id, 'league_id', league_id,
              'canonical_name', canonical_name, 'display_name', display_name))
            FROM teams WHERE league_id = '{league}'),
  'aliases', (SELECT json_agg(json_build_object('team_id', a.team_id, 'alias', a.alias))
              FROM team_aliases a JOIN teams t USING (team_id) WHERE t.league_id = '{league}'),
  'matches', (SELECT json_agg(json_build_object('match_id', match_id, 'league_id', league_id,
              'kickoff_utc', kickoff_utc, 'home_team_id', home_team_id, 'away_team_id', away_team_id,
              'status', status, 'home_goals', home_goals, 'away_goals', away_goals,
              'external_ids', external_ids))
              FROM matches WHERE league_id = '{league}' AND kickoff_utc >= '{since}'::timestamptz)
);
"""


def snapshot_sql(league, since):
    if not league.replace('.', '').replace('_', '').isalnum():
        raise ValueError('invalid_league')
    timestamp(since + 'T00:00:00+00:00' if len(since) == 10 else since)  # valida la fecha
    return SNAPSHOT_SQL.format(league=league, since=since).strip()


def verify_plan(plan_path, normalized_path, snapshot_path):
    """Comprueba el plan contra los mismos archivos de los que salió. Devuelve `ok` y los problemas."""
    reviewed = json.loads(Path(plan_path).read_text(encoding='utf-8'))
    snapshot = json.loads(Path(snapshot_path).read_text(encoding='utf-8'))
    problems = []
    if reviewed.get('provider') != PROVIDER:
        problems.append('provider_is_not_' + PROVIDER)
    if reviewed['normalized_sha256'] != hashlib.sha256(Path(normalized_path).read_bytes()).hexdigest():
        problems.append('normalized_changed_after_plan')
    if reviewed['snapshot_sha256'] != hashlib.sha256(Path(snapshot_path).read_bytes()).hexdigest():
        problems.append('snapshot_changed_after_plan')
    matches = {m['match_id']: m for m in snapshot['matches']}
    seen, gaps, totals = {}, [], Counter()
    for row in records(normalized_path):
        sid = row['source_match_id']
        decision = reviewed['decisions'].get(sid)
        if decision is None:
            problems.append('no_decision:' + sid)
            continue
        totals[decision['mapping_status']] += 1
        if decision['mapping_status'] != 'matched':
            problems.append('not_matched:%s:%s' % (sid, decision.get('mapping_reason')))
            continue
        match = matches.get(decision['match_id'])
        if match is None:
            problems.append('match_not_in_snapshot:' + sid)
            continue
        if decision['match_id'] in seen:
            problems.append('duplicate_target:%s:%s' % (sid, seen[decision['match_id']]))
        seen[decision['match_id']] = sid
        if match['status'] != 'finished' or (row['home_goals'], row['away_goals']) != (
                match['home_goals'], match['away_goals']):
            problems.append('score_differs:' + sid)
        if (decision['home_team_id'], decision['away_team_id']) != (match['home_team_id'], match['away_team_id']):
            problems.append('teams_differ:' + sid)
        gap = abs(timestamp(row['kickoff_utc']) - timestamp(match['kickoff_utc']))
        gaps.append(gap.total_seconds() / 60)
        if gap > TOLERANCE:
            problems.append('kickoff_gap_over_tolerance:' + sid)
        known = (match.get('external_ids') or {}).get('sofascore')
        if known is not None and str(known) != sid:
            problems.append('external_id_differs:' + sid)
    uncovered = sorted(m['match_id'] for m in snapshot['matches']
                       if m['status'] == 'finished' and m['match_id'] not in seen)
    return {'ok': not problems, 'problems': problems, 'totals': dict(totals),
            'max_kickoff_gap_minutes': max(gaps) if gaps else None,
            'production_finished_without_source': uncovered}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    cmd = commands.add_parser('normalize')
    cmd.add_argument('--archive', required=True)
    cmd.add_argument('--league', required=True)
    cmd.add_argument('--output', required=True)
    cmd.add_argument('--since', help='solo partidos que empezaron desde esta fecha (AAAA-MM-DD, UTC)')
    cmd = commands.add_parser('snapshot-sql')
    cmd.add_argument('--league', required=True)
    cmd.add_argument('--since', required=True)
    cmd = commands.add_parser('plan')
    cmd.add_argument('--normalized', required=True)
    cmd.add_argument('--snapshot', required=True)
    cmd.add_argument('--output', required=True)
    cmd = commands.add_parser('verify')
    cmd.add_argument('--plan', required=True)
    cmd.add_argument('--normalized', required=True)
    cmd.add_argument('--snapshot', required=True)
    args = parser.parse_args()
    if args.command == 'normalize':
        result = normalize_archive(args.archive, args.league, args.output, args.since)
    elif args.command == 'snapshot-sql':
        print(snapshot_sql(args.league, args.since))
        return
    elif args.command == 'plan':
        result = plan(args.normalized, args.snapshot, args.output)
    else:
        result = verify_plan(args.plan, args.normalized, args.snapshot)
    print(json.dumps(result, ensure_ascii=True, default=str), flush=True)


if __name__ == '__main__':
    main()
