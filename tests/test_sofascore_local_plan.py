import gzip
import json

import pytest

from qf.ingest.fotmob_import import apply_import, plan
from qf.ingest.sofascore_local import PROVIDER, snapshot_sql, verify_plan


def row(sid='555', home_goals=0, away_goals=1, kickoff='2025-08-23T17:30:00+00:00'):
    return {'provider': PROVIDER, 'source_match_id': sid, 'league_id': 'it.serie_a',
            'kickoff_utc': kickoff, 'home_goals': home_goals, 'away_goals': away_goals,
            'home_source_team_id': '2713', 'away_source_team_id': '2689',
            'home_name': 'Genoa', 'away_name': 'Lecce'}


def snapshot(**match):
    base = {'match_id': 'it.serie_a:2526:genoa-lecce:20250823', 'league_id': 'it.serie_a',
            'kickoff_utc': '2025-08-23T17:30:00+00:00', 'home_team_id': 1, 'away_team_id': 2,
            'status': 'finished', 'home_goals': 0, 'away_goals': 1, 'external_ids': {}}
    base.update(match)
    return {'leagues': [{'league_id': 'it.serie_a', 'cross_league': False}],
            'teams': [{'team_id': 1, 'league_id': 'it.serie_a', 'canonical_name': 'Genoa', 'display_name': None},
                      {'team_id': 2, 'league_id': 'it.serie_a', 'canonical_name': 'Lecce', 'display_name': None}],
            'aliases': [], 'matches': [base]}


def prepare(tmp_path, rows, snap):
    normalized = tmp_path / 'normalized.jsonl.gz'
    with gzip.open(normalized, 'wt', encoding='utf-8') as handle:
        for r in rows:
            handle.write(json.dumps(r) + '\n')
    snapshot_path = tmp_path / 'snapshot.json'
    snapshot_path.write_text(json.dumps(snap), encoding='utf-8')
    output = tmp_path / 'plan.json'
    result = plan(normalized, snapshot_path, output)
    return normalized, snapshot_path, output, result


def test_partido_emparejado_y_plan_verificado(tmp_path):
    normalized, snap, out, result = prepare(tmp_path, [row()], snapshot())
    assert result['totals'] == {'matched': 1}
    decision = json.loads(out.read_text())['decisions']['555']
    assert decision['match_id'] == 'it.serie_a:2526:genoa-lecce:20250823'
    report = verify_plan(out, normalized, snap)
    assert report['ok'] and report['max_kickoff_gap_minutes'] == 0
    assert report['production_finished_without_source'] == []


def test_marcador_distinto_es_conflicto(tmp_path):
    normalized, snap, out, result = prepare(tmp_path, [row(home_goals=2)], snapshot())
    assert result['totals'] == {'conflict': 1}
    report = verify_plan(out, normalized, snap)
    assert not report['ok'] and report['problems'][0].startswith('not_matched:555')


def test_el_archivo_local_nunca_crea_partidos(tmp_path):
    normalized, snap, out, result = prepare(
        tmp_path, [row(kickoff='2025-09-30T17:30:00+00:00')], snapshot())
    assert result['totals'] == {'unresolved': 1}
    decision = json.loads(out.read_text())['decisions']['555']
    assert decision['mapping_reason'] == 'local_archive_never_creates' and decision['match_id'] is None


def test_id_externo_de_sofascore_debe_coincidir(tmp_path):
    _, _, _, bad = prepare(tmp_path, [row()], snapshot(external_ids={'sofascore': '999'}))
    assert bad['totals'] == {'conflict': 1}
    good_dir = tmp_path / 'ok'
    good_dir.mkdir()
    _, _, _, good = prepare(good_dir, [row()], snapshot(external_ids={'sofascore': '555'}))
    assert good['totals'] == {'matched': 1}


def test_plan_detecta_que_los_archivos_cambiaron(tmp_path):
    normalized, snap, out, _ = prepare(tmp_path, [row()], snapshot())
    with gzip.open(normalized, 'wt', encoding='utf-8') as handle:
        handle.write(json.dumps(row(home_goals=3)) + '\n')
    report = verify_plan(out, normalized, snap)
    assert 'normalized_changed_after_plan' in report['problems']
    snap.write_text(json.dumps(snapshot(home_goals=3)), encoding='utf-8')
    assert 'snapshot_changed_after_plan' in verify_plan(out, normalized, snap)['problems']


def test_partido_de_produccion_sin_origen_se_informa(tmp_path):
    extra = dict(snapshot()['matches'][0], match_id='it.serie_a:2627:genoa-lecce:20261031',
                 kickoff_utc='2026-10-31T17:30:00+00:00')
    snap = snapshot()
    snap['matches'].append(extra)
    normalized, snap_path, out, _ = prepare(tmp_path, [row()], snap)
    report = verify_plan(out, normalized, snap_path)
    assert report['ok'] and report['production_finished_without_source'] == ['it.serie_a:2627:genoa-lecce:20261031']


def test_consulta_de_snapshot_rechaza_ligas_raras():
    assert "league_id = 'it.serie_a'" in snapshot_sql('it.serie_a', '2023-08-01')
    with pytest.raises(ValueError, match='invalid_league'):
        snapshot_sql("it.serie_a'; DROP TABLE matches; --", '2023-08-01')


def test_apply_import_de_apify_no_acepta_el_proveedor_local(tmp_path):
    normalized, _, out, _ = prepare(tmp_path, [row()], snapshot())
    with pytest.raises(ValueError, match='unsupported_provider'):
        apply_import(None, normalized, out, tmp_path, tmp_path / 'report.json')
