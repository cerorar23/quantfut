import copy
import json

import pytest

from nba import multimarket_v13_live as live
from nba.audit import write_json
from test_multimarket_v13_live import model

SINGLES = ('player_points', 'player_rebounds', 'player_assists')


def test_module_digest_does_not_depend_on_line_endings(tmp_path):
    lf, crlf, other = tmp_path / 'lf.py', tmp_path / 'crlf.py', tmp_path / 'other.py'
    lf.write_bytes(b'a = 1\nb = 2\n')
    crlf.write_bytes(b'a = 1\r\nb = 2\r\n')
    other.write_bytes(b'a = 1\nb = 3\n')
    assert live.module_digest(lf) == live.module_digest(crlf) != live.module_digest(other)
    assert len(live.module_digest()) == 64 and live.module_digest() == live.module_digest(live.__file__)


def deployed_and_fresh():
    """A 1.3.1-style model (singles only) and a refit that adds the sums and nothing else."""
    fresh = model()
    old = copy.deepcopy(fresh)
    old['version'] = 'nba-multimarket-live-1.3.1'
    old['player_fit'] = {m: v for m, v in old['player_fit'].items() if m in SINGLES}
    old['inputs'] = dict(live_module_sha256='old-module', protocol_sha256='old-protocol', players_sha256='p')
    fresh['inputs'] = dict(live_module_sha256=live.module_digest(), protocol_sha256='new-protocol', players_sha256='p')
    return fresh, old


def test_a_refit_that_only_adds_the_sums_passes_every_check():
    fresh, old = deployed_and_fresh()
    checks, detail = live.compare_models(fresh, old)
    assert all(checks.values()), checks
    assert detail['inputs_changed'] == ['live_module_sha256', 'protocol_sha256'] and detail['new_markets'] == sorted(set(live.PLAYER_MARKETS) - set(SINGLES))


@pytest.mark.parametrize('change, failing', [
    (lambda f: f['player_fit']['player_points'].update(weights=[.5, 0., 0., 0., 0.]), 'shared_player_markets_identical'),
    (lambda f: f['player_fit'].pop('player_points_assists'), 'all_player_markets_present'),
    (lambda f: f['inputs'].update(players_sha256='another'), 'inputs_changed_only_module_and_protocol'),
    (lambda f: f['inputs'].update(live_module_sha256='someone-else'), 'fitted_by_this_module'),
    (lambda f: f['fit'].update(extra=1), 'fit_identical'),
    (lambda f: f['play_probability'].update(Out=.9), 'play_probability_identical'),
    (lambda f: f.update(version='nba-multimarket-live-1.3.1'), 'version_matches'),
])
def test_each_unexpected_change_fails_its_own_check(change, failing):
    fresh, old = deployed_and_fresh()
    change(fresh)
    checks, _ = live.compare_models(fresh, old)
    assert not checks[failing] and not all(checks.values())


def test_compare_command_exits_non_zero_on_a_mismatch(tmp_path, monkeypatch, capsys):
    fresh, old = deployed_and_fresh()
    for name, value in (('new', fresh), ('old', old)):
        (tmp_path / name).mkdir()
        write_json(tmp_path / name / 'model.json', value)
    monkeypatch.setattr('sys.argv', ['live', 'compare', '--model', str(tmp_path / 'new'), '--reference', str(tmp_path / 'old')])
    with pytest.raises(SystemExit) as ok:
        live.main()
    assert ok.value.code == 0 and json.loads(capsys.readouterr().out)['ok'] is True
    fresh['fit']['extra'] = 1
    write_json(tmp_path / 'new' / 'model.json', fresh)
    with pytest.raises(SystemExit) as bad:
        live.main()
    assert bad.value.code == 1 and json.loads(capsys.readouterr().out)['checks']['fit_identical'] is False
