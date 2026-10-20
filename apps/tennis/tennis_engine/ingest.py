"""Download immutable source snapshots with receipts. Standard library only."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen

MCP_COMMIT = '1813a1309b7ed7ebf1c7e884b32bf675d00e4edf'


def now():
    return datetime.now(timezone.utc).isoformat()


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    temp.replace(path)


def fetch(url):
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={'User-Agent': 'TennisResearch/0.1 (bounded public data download)'}), timeout=45) as res:
                body = res.read(80_000_001)
                if len(body) > 80_000_000:
                    raise ValueError('File exceeds the 80 MB safety limit')
                return body, res.headers.get('Last-Modified')
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def download(root, source='all', seed_mcp=None):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    jobs = []
    if source in ('all', 'tml'):
        body, _ = fetch('https://stats.tennismylife.org/api/data-files')
        catalog = json.loads(body)
        save_json(root/'tml/catalog.json', catalog)
        for f in catalog['files']:
            name = PurePosixPath(f['name'])
            if name.is_absolute() or '..' in name.parts or '\\' in f['name'] or not f['name'].endswith('.csv'):
                raise ValueError('Unsafe source file name')
            parsed = urlparse(f['url'])
            if parsed.scheme != 'https' or parsed.netloc != 'stats.tennismylife.org' or parsed.path != '/data/' + f['name']:
                raise ValueError('Unexpected source URL')
            jobs.append(dict(source='tml', name=f['name'], url=f['url'], upstream_mtime=f.get('mtime'), expected_size=f.get('size')))
    if source in ('all', 'mcp'):
        body, _ = fetch(f'https://api.github.com/repos/JeffSackmann/tennis_MatchChartingProject/git/trees/{MCP_COMMIT}')
        tree = json.loads(body)
        if tree['sha'] != MCP_COMMIT or tree.get('truncated'):
            raise ValueError('MCP tree not complete or not pinned')
        save_json(root/'mcp/catalog.json', tree)
        for f in tree['tree']:
            if f['type'] == 'blob' and (f['path'].endswith('.csv') or f['path'] in ('README.md', 'data_dictionary.txt', 'MatchChart 0.3.2.xlsm')):
                from urllib.parse import quote
                jobs.append(dict(source='mcp', name=f['path'], url=f'https://raw.githubusercontent.com/JeffSackmann/tennis_MatchChartingProject/{MCP_COMMIT}/'+quote(f['path']), blob_sha1=f['sha'], expected_size=f['size']))
    manifest_path = root/'download_manifest.json'
    previous = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    prior = {(r['source'], r['name']): r for r in previous.get('files', [])}
    receipts = []

    def one(job):
        target = root/job['source']/'originals'/job['name']
        target.parent.mkdir(parents=True, exist_ok=True)
        old = prior.get((job['source'], job['name']))
        if old and old.get('status') == 'ok' and target.exists():
            blob = target.read_bytes()
            if hashlib.sha256(blob).hexdigest() == old['sha256']:
                return {**old, 'reused_local_snapshot': True}
        try:
            seed = Path(seed_mcp)/job['name'] if seed_mcp and job['source'] == 'mcp' else None
            if seed and seed.is_file():
                blob, modified = seed.read_bytes(), None
                transport = 'copied previously captured pinned original'
                received = datetime.fromtimestamp(seed.stat().st_mtime, timezone.utc).isoformat()
            else:
                blob, modified = fetch(job['url'])
                received, transport = now(), 'direct HTTPS'
            if job.get('blob_sha1'):
                digest = hashlib.sha1(b'blob '+str(len(blob)).encode()+b'\0'+blob).hexdigest()
                if digest != job['blob_sha1']:
                    raise ValueError('MCP Git blob hash mismatch')
            if job['name'].endswith('.csv') and b'<html' in blob[:500].lower():
                raise ValueError('HTML returned instead of CSV')
            if target.exists():
                raise ValueError('Existing snapshot lacks matching receipt; choose a fresh output directory')
            target.write_bytes(blob)
            return {**job, 'status': 'ok', 'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest(),
                    'received_at': received, 'http_last_modified': modified, 'transport': transport,
                    'size_matches_catalog': len(blob) == job.get('expected_size')}
        except Exception as exc:
            return {**job, 'status': 'failed', 'error': str(exc), 'attempted_at': now()}

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(one, j) for j in jobs]
        for future in as_completed(futures):
            receipts.append(future.result())
            save_json(manifest_path, {'snapshot_created_at': previous.get('snapshot_created_at', now()),
                       'mcp_commit': MCP_COMMIT, 'historical_first_availability': 'not established',
                       'licenses': {'tml': 'MIT declared on source database page', 'mcp': 'CC BY-NC-SA 4.0; research only'},
                       'files': sorted(receipts, key=lambda x: (x['source'], x['name']))})
            if len(receipts) % 20 == 0:
                print(f'Downloaded/checked {len(receipts)}/{len(jobs)}', flush=True)
    summary = {'files': len(receipts), 'ok': sum(r['status']=='ok' for r in receipts),
               'failed': [r for r in receipts if r['status'] != 'ok'],
               'bytes': sum(r.get('bytes', 0) for r in receipts)}
    save_json(root/'download_summary.json', summary)
    return summary
