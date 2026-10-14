"""Descarga histórica de PitchAPI: originales con hash y recepción real.

Solo captura. No escribe en PostgreSQL: cada respuesta se guarda tal cual
llegó (gzip + recibo) y los fallos también quedan registrados sin reintento
automático. La normalización e importación van aparte, con su propia revisión.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = 'https://api.pitchapi.dev'
USER_AGENT = 'QuantFut-historico/1.0'
MIN_SPACING = 0.25

# competición QuantFut -> liga PitchAPI (GET /v1/leagues)
COMPETITIONS = {
    'gb.premier_league': 'l_4WFCIZ', 'gb.championship': 'l_4DWyTT',
    'es.laliga': 'l_0ErfuF', 'es.laliga2': 'l_3kyHLd',
    'it.serie_a': 'l_0ALvwF', 'it.serie_b': 'l_0jy5yE',
    'de.bundesliga': 'l_1Isor4', 'de.bundesliga2': 'l_3hvsne',
    'fr.ligue_1': 'l_3FJFUl', 'fr.ligue_2': 'l_0275VP',
    'nl.eredivisie': 'l_4H43wr', 'pt.primeira': 'l_4QexZg',
    'tr.super_lig': 'l_0S1uaf', 'ch.super_league': 'l_4d6Bwl',
    'dk.superliga': 'l_49Zmno', 'no.eliteserien': 'l_0uqFK8',
    'se.allsvenskan': 'l_1XsMdH', 'us.mls': 'l_0eg6C9',
    'mx.liga_mx': 'l_3v84VE', 'br.serie_a': 'l_1D8Xrl',
    'ar.primera': 'l_45VZuL', 'eu.ucl': 'l_0bfbkO', 'eu.uel': 'l_38d9HA',
}


class Client:
    def __init__(self, key, opener=urllib.request.urlopen, sleep=time.sleep):
        self.key, self.opener, self.sleep = key, opener, sleep
        self.lock, self.last, self.blocked_until = threading.Lock(), 0.0, 0.0

    def _wait(self):
        with self.lock:
            pause = max(self.last + MIN_SPACING, self.blocked_until) - time.monotonic()
            if pause > 0:
                self.sleep(pause)
            self.last = time.monotonic()

    def get(self, path):
        """Devuelve (status, cuerpo, recibido_en). 429 respeta Retry-After; 5xx, backoff."""
        url, status, body = BASE + path, 0, b''
        for attempt in range(5):
            self._wait()
            request = urllib.request.Request(url, headers={
                'X-API-KEY': self.key, 'User-Agent': USER_AGENT, 'Accept': 'application/json'})
            try:
                with self.opener(request, timeout=45) as reply:
                    body, status = reply.read(), reply.status
            except urllib.error.HTTPError as error:
                body, status = error.read(), error.code
                wait = int(error.headers.get('Retry-After') or 0) if error.headers else 0
                if status == 429 or status >= 500:
                    with self.lock:
                        self.blocked_until = time.monotonic() + max(wait, 2 ** attempt * 2)
                    continue
            except (urllib.error.URLError, TimeoutError):
                with self.lock:
                    self.blocked_until = time.monotonic() + 2 ** attempt * 2
                continue
            return status, body, datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        return status, body, datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def store_path(archive, kind, name):
    return Path(archive) / 'raw' / kind / name


def save(archive, kind, name, url_path, status, body, received_at):
    base = store_path(archive, kind, name)
    base.parent.mkdir(parents=True, exist_ok=True)
    receipt = {'path': url_path, 'status': status, 'received_at': received_at,
               'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body)}
    base.with_name(name + '.json.gz').write_bytes(gzip.compress(body))
    base.with_name(name + '.receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    return receipt


def load(archive, kind, name):
    base = store_path(archive, kind, name)
    receipt_file = base.with_name(name + '.receipt.json')
    if not receipt_file.exists():
        return None
    receipt = json.loads(receipt_file.read_text(encoding='utf-8'))
    raw = gzip.decompress(base.with_name(name + '.json.gz').read_bytes())
    if hashlib.sha256(raw).hexdigest() != receipt['sha256']:
        raise ValueError('pitchapi_original_changed')
    return receipt, raw


def fetch(client, archive, kind, name, url_path, refetch=False):
    """Reutiliza éxitos y fallos ya guardados; solo llama si no hay recibo."""
    cached = None if refetch else load(archive, kind, name)
    if cached:
        return cached[0]
    status, body, received_at = client.get(url_path)
    return save(archive, kind, name, url_path, status, body, received_at)


def season_slug(season):
    return season.replace('/', '-')


def list_seasons(client, archive, competitions=COMPETITIONS):
    leagues = fetch(client, archive, 'catalog', 'leagues', '/v1/leagues')
    catalog = {l['id']: l for l in json.loads(load(archive, 'catalog', 'leagues')[1])['data']['leagues']}
    out = {}
    for qf_id, pitch_id in competitions.items():
        for season in catalog[pitch_id]['seasons']:
            name = f'{qf_id}_{season_slug(season)}'
            out[name] = fetch(client, archive, 'lists', name,
                              f'/v1/leagues/{pitch_id}/matches?season={season}&status=played')
    return leagues, out


def finished_matches(archive):
    """(competición_qf, temporada, partido) de todas las listas guardadas con éxito."""
    for receipt_file in sorted((Path(archive) / 'raw' / 'lists').glob('*.receipt.json')):
        name = receipt_file.name[:-len('.receipt.json')]
        receipt, raw = load(archive, 'lists', name)
        if receipt['status'] != 200:
            continue
        qf_id, season = name.rsplit('_', 1)
        for match in json.loads(raw)['data']['matches']:
            if match.get('status') == 'finished':
                yield qf_id, season, match


def download_stats(client, archive, wanted=None, workers=3):
    todo = [m['id'] for _, _, m in finished_matches(archive) if wanted is None or m['id'] in wanted]
    done = {'ok': 0, 'failed': 0}

    def one(match_id):
        receipt = fetch(client, archive, 'stats', match_id, f'/v1/matches/{match_id}/stats')
        done['ok' if receipt['status'] == 200 else 'failed'] += 1

    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(one, todo))
    return done


def team_xg(raw):
    """Pareja (local, visitante) de expected_goals del periodo All, o None si no se publica."""
    for period in json.loads(raw)['data']['periods']:
        if period['period'] != 'All':
            continue
        for group in period['groups']:
            for item in group['items']:
                if item['key'] == 'expected_goals':
                    try:
                        return float(item['home']), float(item['away'])
                    except (TypeError, ValueError):
                        return None
    return None


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive')
    parser.add_argument('command', choices=['lists', 'stats'])
    parser.add_argument('--only', help='archivo con IDs de partido PitchAPI (uno por línea)')
    parser.add_argument('--workers', type=int, default=3)
    args = parser.parse_args(argv)
    client = Client(os.environ['PITCHAPI_KEY'])
    if args.command == 'lists':
        _, out = list_seasons(client, args.archive)
        bad = {k: v['status'] for k, v in out.items() if v['status'] != 200}
        print(json.dumps({'listas': len(out), 'fallidas': bad}, ensure_ascii=False))
    else:
        wanted = set(Path(args.only).read_text().split()) if args.only else None
        print(json.dumps(download_stats(client, args.archive, wanted, args.workers)))


if __name__ == '__main__':
    main()
