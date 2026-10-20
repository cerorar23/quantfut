"""Artificial catalog and transport only; no network."""
import hashlib
import json
import pytest
from tennis_refresh_v1 import plan, snapshot, promote


def previous(tmp_path):
    root = tmp_path / 'prev'
    (root / 'tml/originals').mkdir(parents=True)
    blob = b'a,b\n1,2\n'
    (root / 'tml/originals/2025.csv').write_bytes(blob)
    (root / 'download_manifest.json').write_text(json.dumps(dict(files=[dict(source='tml', name='2025.csv', status='ok', upstream_mtime='m1',
        expected_size=len(blob), sha256=hashlib.sha256(blob).hexdigest())])))
    return root


def catalog_rows():
    return [dict(name='2025.csv', url='https://stats.tennismylife.org/data/2025.csv', size=8, mtime='m1'),
            dict(name='2026.csv', url='https://stats.tennismylife.org/data/2026.csv', size=8, mtime='m9')]


def test_only_changed_files_are_downloaded_and_old_ones_reused(tmp_path):
    prev = previous(tmp_path)
    reuse, download, _ = plan(prev, catalog_rows())
    assert [f['name'] for f in reuse] == ['2025.csv'] and [f['name'] for f in download] == ['2026.csv']
    fetched = []
    out = snapshot(prev, tmp_path / 'new', catalog_rows(), fetch=lambda url: (fetched.append(url) or b'x,y\n3,4\n', None))
    assert fetched == ['https://stats.tennismylife.org/data/2026.csv'] and out['reused'] == 1
    assert (tmp_path / 'new/tml/originals/2025.csv').read_bytes() == b'a,b\n1,2\n'
    with pytest.raises(ValueError):
        snapshot(prev, tmp_path / 'new', catalog_rows(), fetch=lambda url: (b'', None))


def test_html_and_tampered_previous_are_rejected(tmp_path):
    prev = previous(tmp_path)
    with pytest.raises(ValueError, match='HTML'):
        snapshot(prev, tmp_path / 'n1', catalog_rows(), fetch=lambda url: (b'<html>blocked</html>', None))
    (prev / 'tml/originals/2025.csv').write_bytes(b'tampered')
    with pytest.raises(ValueError, match='changed on disk'):
        snapshot(prev, tmp_path / 'n2', catalog_rows(), fetch=lambda url: (b'x\n', None))


def test_promotion_requires_passing_checks_and_keeps_history(tmp_path):
    cfg = tmp_path / 'motor.json'
    cfg.write_text(json.dumps(dict(canonical='old.parquet')))
    with pytest.raises(ValueError):
        promote(cfg, 'new.parquet', dict(checks=dict(passed=False)))
    assert json.loads(cfg.read_text())['canonical'] == 'old.parquet'
    c = promote(cfg, 'new.parquet', dict(checks=dict(passed=True)))
    assert c['canonical'] == 'new.parquet' and c['canonical_history'][0]['canonical'] == 'old.parquet'
