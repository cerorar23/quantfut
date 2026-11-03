"""Sube el archivo SofaScore local (data/v3) al árbol único del VPS sin duplicar nada.

Un solo árbol: el que usa el scraper del servidor (`~/sofascore-scraper/data/v3`). Un partido
es una carpeta `events/<id[:2]>/<id[2:5]>/<id>/` y se identifica por su ID, así que subirlo dos
veces o desde dos sitios cae en la misma carpeta. Se envía solo lo que falta o lo que es más
reciente que lo del servidor. Sin `--aplicar` es un simulacro: no transfiere nada.

Reglas (iguales a las del cargador, `qf.ingest.sofascore_local`):
  * se verifica cada bloque contra el sha256 del manifest antes de enviarlo; el que no cuadra
    se descarta y se informa;
  * un partido observado antes de inicio + 72 h es provisional: no se sube salvo con
    `--incluir-provisionales`, y entonces es el scraper del servidor (`ssc refresh`) quien lo
    relee al cumplirse la ventana;
  * los calendarios (`tournaments/`) se envían sin pisar los más nuevos del servidor.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

WINDOW = timedelta(hours=72)
BATCH = 250
SSH_OPTIONS = ['-o', 'Compression=no', '-c', 'aes128-gcm@openssh.com,chacha20-poly1305@openssh.com']

REMOTE_SCRIPT = r'''
import gzip, hashlib, json, os, shutil, sys
root = os.path.expanduser(sys.argv[1])
ids = None
out = {"free_gb": round(shutil.disk_usage(os.path.dirname(root.rstrip("/")) or "/").free / 1e9, 1),
       "events": {}, "bad": []}
base = os.path.join(root, "events")
for a in sorted(os.listdir(base)) if os.path.isdir(base) else []:
    for b in os.listdir(os.path.join(base, a)):
        for eid in os.listdir(os.path.join(base, a, b)):
            if ids is not None and eid not in ids:
                continue
            folder = os.path.join(base, a, b, eid)
            try:
                man = json.load(open(os.path.join(folder, "manifest.json"), encoding="utf-8"))
            except Exception:
                out["bad"].append(eid + ":manifest")
                continue
            damaged = False
            for name, meta in (man.get("slices") or {}).items():
                if meta.get("state") != "ok":
                    continue
                try:
                    raw = gzip.decompress(open(os.path.join(folder, name + ".json.gz"), "rb").read())
                    damaged = damaged or hashlib.sha256(raw).hexdigest() != meta.get("sha256")
                except Exception:
                    damaged = True
            if damaged:
                out["bad"].append(eid)  # incompleto o alterado: se vuelve a enviar
            else:
                out["events"][eid] = (man.get("observation") or {}).get("observed_at_utc")
print(json.dumps(out))
'''


def ssh(host, *command, data=None):
    return subprocess.run(['ssh', '-o', 'ConnectTimeout=20', host, *command], input=data,
                          capture_output=True, check=True).stdout


def remote_inventory(host, remote_dir):
    raw = ssh(host, 'python3', '-', remote_dir, data=REMOTE_SCRIPT.encode())
    return json.loads(raw)


def parse(value):
    return datetime.fromisoformat(str(value).replace('Z', '+00:00')).astimezone(timezone.utc)


def read_gz(path):
    return gzip.decompress(Path(path).read_bytes())


def local_candidates(archive, include_provisional=False):
    """(a_enviar, descartados). Un partido a enviar: {id, observed, rel}."""
    send, skipped = [], {'provisional': [], 'corrupt': [], 'no_manifest': []}
    for manifest_path in sorted((Path(archive) / 'events').glob('*/*/*/manifest.json')):
        folder = manifest_path.parent
        eid = folder.name
        try:
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            observed = (manifest.get('observation') or {}).get('observed_at_utc')
            event = json.loads(read_gz(folder / 'event.json.gz'))
            start = event.get('startTimestamp')
        except (OSError, ValueError):
            skipped['no_manifest'].append(eid)
            continue
        if observed and start and parse(observed) - datetime.fromtimestamp(start, timezone.utc) < WINDOW:
            skipped['provisional'].append(eid)
            if not include_provisional:
                continue
        bad = False
        for name, meta in (manifest.get('slices') or {}).items():
            if meta.get('state') != 'ok':
                continue
            try:
                if hashlib.sha256(read_gz(folder / (name + '.json.gz'))).hexdigest() != meta.get('sha256'):
                    bad = True
            except OSError:
                bad = True
        if bad:
            skipped['corrupt'].append(eid)
            continue
        send.append({'id': eid, 'observed': observed, 'rel': folder.relative_to(archive).as_posix()})
    return send, skipped


def needs_upload(item, remote_events):
    remote = remote_events.get(item['id'])
    if remote is None:
        return True
    return bool(item['observed']) and (not remote or parse(item['observed']) > parse(remote))


def stream(archive, host, remote_dir, relative_paths, keep_newer):
    tar = shutil.which('tar')
    listing = Path(archive).parent / ('.subida_lista_%d.txt' % threading.get_ident())
    with open(listing, 'w', encoding='utf-8', newline='\n') as handle:  # tar de Git no admite CRLF
        handle.write('\n'.join(relative_paths) + '\n')
    try:
        maker = subprocess.Popen([tar, '-cf', '-', '-C', str(archive), '-T', str(listing)], stdout=subprocess.PIPE)
        flags = '--keep-newer-files ' if keep_newer else ''
        receiver = subprocess.Popen(
            ['ssh', *SSH_OPTIONS, host, 'mkdir -p %s && tar -xf - --no-same-owner %s-C %s' % (remote_dir, flags, remote_dir)],
            stdin=maker.stdout)
        maker.stdout.close()
        if receiver.wait() != 0 or maker.wait() != 0:
            raise RuntimeError('transfer_failed')
    finally:
        listing.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', default=r'C:\Users\huye\Documents\SOFASCORE\data\v3')
    parser.add_argument('--host', default='quantfut')
    parser.add_argument('--remote-dir', default='~/sofascore-scraper/data/v3')
    parser.add_argument('--incluir-provisionales', action='store_true',
                        help='sube también los de menos de 72 h para que el scraper del servidor los relea')
    parser.add_argument('--paralelo', type=int, default=6, help='conexiones simultáneas')
    parser.add_argument('--min-free-gb', type=float, default=10.0)
    parser.add_argument('--aplicar', action='store_true', help='sin esto es un simulacro')
    args = parser.parse_args()
    archive = Path(args.archive)

    remote = remote_inventory(args.host, args.remote_dir)
    print('servidor: %d partidos, %.1f GB libres, manifests ilegibles: %d'
          % (len(remote['events']), remote['free_gb'], len(remote['bad'])))
    send, skipped = local_candidates(archive, args.incluir_provisionales)
    todo = [item for item in send if needs_upload(item, remote['events'])]
    size = sum(f.stat().st_size for item in todo for f in (archive / item['rel']).iterdir())
    print('local: %d partidos asentados; a enviar %d (%.0f MB); ya en el servidor y al día %d; '
          'provisionales %d; corruptos %d; sin manifest %d'
          % (len(send), len(todo), size / 1e6, len(send) - len(todo), len(skipped['provisional']),
             len(skipped['corrupt']), len(skipped['no_manifest'])))
    if skipped['corrupt']:
        print('corruptos:', ','.join(skipped['corrupt'][:20]))
    if not args.aplicar:
        print('simulacro: no se transfirió nada')
        return 0
    if remote['free_gb'] < args.min_free_gb + size / 1e9:
        print('espacio insuficiente en el servidor', file=sys.stderr)
        return 2
    schedules = sorted(p.relative_to(archive).as_posix() for p in (archive / 'tournaments').rglob('*') if p.is_file())
    stream(archive, args.host, args.remote_dir, schedules, keep_newer=True)
    print('calendarios enviados: %d archivos' % len(schedules))
    batches = [todo[start:start + BATCH] for start in range(0, len(todo), BATCH)]
    done, lock = [0], threading.Lock()

    def send(batch):
        paths = [f.relative_to(archive).as_posix() for item in batch for f in (archive / item['rel']).iterdir()]
        stream(archive, args.host, args.remote_dir, paths, keep_newer=False)
        with lock:
            done[0] += len(batch)
            print('enviados %d / %d' % (done[0], len(todo)), flush=True)

    with ThreadPoolExecutor(max_workers=max(1, args.paralelo)) as pool:
        list(pool.map(send, batches))  # una excepción en cualquier lote detiene el resultado
    ids = [item['id'] for item in todo]
    after = remote_inventory(args.host, args.remote_dir)
    missing = [i for i in ids if i not in after['events']]
    print('verificación en el servidor: partidos %d, faltan %d, partidos dañados %d, %.1f GB libres'
          % (len(after['events']), len(missing), len(after['bad']), after['free_gb']))
    return 0 if not missing and not after['bad'] else 3


if __name__ == '__main__':
    sys.exit(main())
