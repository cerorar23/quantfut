"""Backfill export must not invent closing prices or silently choose a fixture."""
import csv
import importlib.util
import json
from pathlib import Path

import pytest


spec = importlib.util.spec_from_file_location(
    'export_pinnacle_closes', Path(__file__).parents[1] / 'scripts/export_pinnacle_closes.py')
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)


@pytest.mark.parametrize('row', [
    {'PSH': '2', 'PSD': '3', 'PSA': '4'},
    {'PSCH': 'nan', 'PSCD': '3', 'PSCA': '4'},
    {'PSCH': '2', 'PSCD': 'inf', 'PSCA': '4'},
    {'PSCH': '2', 'PSCD': '3', 'PSCA': '1'},
    {'PSCH': '2', 'PSCD': '3'},
])
def test_only_complete_finite_explicit_closing_prices(row):
    assert export.prices(row) is None


def test_plan_is_unique_score_checked_and_does_not_replace_partial_close(tmp_path, monkeypatch):
    league = {'league_id': 'mx.liga_mx', 'fd_code': 'MEX', 'fd_extra': True}
    teams = [{'team_id': 1, 'league_id': 'mx.liga_mx', 'canonical_name': 'América'},
             {'team_id': 2, 'league_id': 'mx.liga_mx', 'canonical_name': 'Cruz Azul'}]
    match = dict(match_id='m1', league_id='mx.liga_mx', kickoff_utc='2026-10-01T02:00:00+00:00',
                 home_team_id=1, away_team_id=2, home_goals=2, away_goals=1, close_selections=0)
    snapshot = dict(checked_at='2026-10-14T19:00:00+00:00', leagues=[league], teams=teams,
                    aliases=[], matches=[match])
    source = dict(Date='01/10/2026', Time='03:00', Home='America', Away='Cruz Azul',
                  HG='2', AG='1', PSCH='2.1', PSCD='3.2', PSCA='4.3')
    path = tmp_path / 'snapshot.json'
    raw = tmp_path / 'source.csv'
    def archive(job, folder):
        with raw.open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=source)
            writer.writeheader()
            writer.writerow(source)
        return league, raw.read_bytes(), dict(status=200, url='https://www.football-data.co.uk/new/MEX.csv',
                                              sha256='source_hash', captured_at_utc='2026-10-14T19:01:00+00:00')
    monkeypatch.setattr(export, 'archive', archive)
    def plan():
        path.write_text(json.dumps(snapshot))
        return export.run(path, tmp_path / 'out')
    assert plan()['recoverable_matches'] == 1
    rows = list(csv.DictReader((tmp_path / 'out/pinnacle_cierres_recuperables.csv').open(encoding='utf-8-sig')))
    assert rows[0]['kickoff_utc'] == match['kickoff_utc']
    assert rows[0]['captured_at_utc'] != rows[0]['kickoff_utc']
    source['HG'] = '3'
    assert plan()['counts_by_league']['mx.liga_mx']['score_mismatch'] == 1
    source['HG'] = '2'
    snapshot['matches'].append(dict(match, match_id='m2'))
    assert plan()['counts_by_league']['mx.liga_mx']['ambiguous_match'] == 1
    snapshot['matches'] = [dict(match, close_selections=1)]
    assert plan()['recoverable_matches'] == 0
    snapshot['matches'] = [dict(match, close_selections=3)]
    assert plan()['counts_by_league']['mx.liga_mx']['already_complete'] == 1


def test_archive_reuse_checks_hash_and_preserves_retrieval_time(tmp_path, monkeypatch):
    import hashlib
    league = {'league_id': 'mx.liga_mx', 'fd_code': 'MEX', 'fd_extra': True}
    body = b'Date,Home,Away\n'
    receipt = dict(status=200, sha256=hashlib.sha256(body).hexdigest(), captured_at_utc='2025-01-01')
    (tmp_path / 'MEX-all.csv').write_bytes(body)
    (tmp_path / 'MEX-all.receipt.json').write_text(json.dumps(receipt))
    monkeypatch.setattr(export.httpx, 'get', lambda *args, **kwargs: pytest.fail('network on archive reuse'))
    assert export.archive((league, None), tmp_path)[2] == receipt
    (tmp_path / 'MEX-all.csv').write_bytes(b'changed')
    with pytest.raises(ValueError, match='archive_hash_mismatch'):
        export.archive((league, None), tmp_path)


def test_scraper_success_is_not_pinnacle_coverage():
    runner_spec = importlib.util.spec_from_file_location(
        'oddsharvester_zenrows', Path(__file__).parents[1] / 'scripts/oddsharvester_zenrows.py')
    runner = importlib.util.module_from_spec(runner_spec)
    runner_spec.loader.exec_module(runner)
    assert runner.complete_pinnacle_quotes([{'1x2_market': []}]) == 0
    quote = dict(bookmaker_name='Pinnacle', period='FullTime', **{'1': '2', 'X': '3', '2': '4'})
    assert runner.complete_pinnacle_quotes([{'1x2_market': [quote]}]) == 1
    for change in [dict(bookmaker_name='bet365'), dict(period='FirstHalf'), {'X': 'nan'}]:
        assert runner.complete_pinnacle_quotes([{'1x2_market': [dict(quote, **change)]}]) == 0
