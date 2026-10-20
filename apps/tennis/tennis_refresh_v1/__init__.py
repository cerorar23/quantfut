"""Weekly data refresh: TennisMyLife catalog -> changed files only -> normalize -> identity bridges -> retrain serve models -> promote.

Unchanged originals (same upstream mtime and size as the previous snapshot, local SHA-256 verified) are hard-linked
from the previous snapshot instead of downloaded again. Every snapshot is a NEW directory; the engine config is only
switched after sanity checks pass, and the previous canonical path is kept in the config history.
"""
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import pandas as pd
from tennis_engine.ingest import fetch as http_fetch, save_json
from tennis_engine.normalize import normalize
from tennis_engine.model import train
import tennis_identity_v2
import tennis_identity_v3

CATALOG_URL = 'https://stats.tennismylife.org/api/data-files'


def now():
    return datetime.now(timezone.utc).isoformat()


def catalog(fetch=http_fetch):
    body, _ = fetch(CATALOG_URL)
    files = json.loads(body)['files']
    for f in files:
        u = urlparse(f['url'])
        if u.scheme != 'https' or u.netloc != 'stats.tennismylife.org' or u.path != '/data/' + f['name']:
            raise ValueError('Unexpected catalog URL: ' + f['name'])
    return files


def plan(previous_root, files):
    prior = {r['name']: r for r in json.loads((Path(previous_root) / 'download_manifest.json').read_text(encoding='utf-8'))['files']
             if r['source'] == 'tml' and r['status'] == 'ok'}
    reuse, download = [], []
    for f in files:
        old = prior.get(f['name'])
        same = old and old.get('upstream_mtime') == f.get('mtime') and old.get('expected_size') == f.get('size')
        (reuse if same else download).append(f)
    return reuse, download, prior


def snapshot(previous_root, new_root, files, fetch=http_fetch):
    previous_root, new_root = Path(previous_root), Path(new_root)
    if new_root.exists():
        raise ValueError('New snapshot directory required')
    reuse, download, prior = plan(previous_root, files)
    receipts = []
    for f in reuse:
        old = prior[f['name']]
        src, dst = previous_root / 'tml/originals' / f['name'], new_root / 'tml/originals' / f['name']
        if hashlib.sha256(src.read_bytes()).hexdigest() != old['sha256']:
            raise ValueError('Previous original changed on disk: ' + f['name'])
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)
        receipts.append(dict(old, reused_from=str(previous_root)))
    for f in download:
        blob, modified = fetch(f['url'])
        if f['name'].endswith('.csv') and b'<html' in blob[:500].lower():
            raise ValueError('HTML returned instead of CSV: ' + f['name'])
        dst = new_root / 'tml/originals' / f['name']
        dst.parent.mkdir(parents=True, exist_ok=True)
        with dst.open('xb') as handle:
            handle.write(blob)
        receipts.append(dict(source='tml', name=f['name'], url=f['url'], upstream_mtime=f.get('mtime'), expected_size=f.get('size'),
                             status='ok', bytes=len(blob), sha256=hashlib.sha256(blob).hexdigest(), received_at=now(),
                             http_last_modified=modified, transport='direct HTTPS', size_matches_catalog=len(blob) == f.get('size')))
    save_json(new_root / 'download_manifest.json', dict(snapshot_created_at=now(), previous_snapshot=str(previous_root),
              licenses={'tml': 'MIT declared on source database page'}, files=sorted(receipts, key=lambda r: r['name'])))
    return dict(reused=len(reuse), downloaded=[dict(name=f['name'], size=f.get('size')) for f in download])


def build(new_root, as_of, previous_canonical):
    new_root = Path(new_root)
    normalize(new_root, as_of=as_of, output_root=new_root / 'canonical_raw')
    v2 = tennis_identity_v2.build(new_root / 'canonical_raw/matches.parquet', new_root / 'bridge_v2')
    v3 = tennis_identity_v3.build(new_root / 'bridge_v2/canonical/matches.parquet', new_root / 'bridge_v3')
    final = new_root / 'bridge_v3/canonical/matches.parquet'
    new, old = pd.read_parquet(final, columns=['period', 'circuit']), pd.read_parquet(previous_canonical, columns=['period', 'circuit'])
    checks = dict(rows_new=len(new), rows_previous=len(old), last_period_new=new.period.max(), last_period_previous=old.period.max(),
                  rows_not_lost=len(new) >= 0.999 * len(old), dates_advanced=new.period.max() >= old.period.max(),
                  both_circuits=set(new.circuit) == {'ATP', 'WTA'})
    models = new_root / 'models'
    for circuit in ('ATP', 'WTA'):
        summary = train(new_root / 'bridge_v3', models / f'{circuit}_current', circuit, as_of)
        checks[f'model_{circuit}_converged'] = bool(summary['optimizer_success'])
        checks[f'model_{circuit}_matches'] = summary['matches']
    checks['passed'] = (checks['rows_not_lost'] and checks['dates_advanced'] and checks['both_circuits']
                        and checks['model_ATP_converged'] and checks['model_WTA_converged'])
    return dict(canonical=str(final.resolve()), models_root=str(models.resolve()), aliases_merged=v2['aliases_merged'],
                birth_merged=len(v3['merged']), checks=checks)


def promote(config_path, canonical, report):
    config_path = Path(config_path)
    config = json.loads(config_path.read_text(encoding='utf-8'))
    if not report['checks']['passed']:
        raise ValueError('Sanity checks failed; engine config left unchanged')
    history = config.get('canonical_history', [])
    history.append(dict(canonical=config['canonical'], models_root=config.get('models_root'), replaced_at=now()))
    config.update(canonical=canonical, canonical_history=history)
    if report.get('models_root'):
        config['models_root'] = report['models_root']
    tmp = config_path.with_suffix('.tmp')
    tmp.write_text(json.dumps(config, indent=2), encoding='utf-8')
    os.replace(tmp, config_path)
    return config
