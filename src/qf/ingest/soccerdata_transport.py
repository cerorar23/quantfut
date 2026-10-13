"""Transporte acotado para lectores soccerdata; originales antes del parser.

El callback ejecuta ZenRows MCP. Los lectores nunca abren un navegador ni una
conexión deportiva directa. La caché conserva errores y su recepción real.
"""
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import re
from pathlib import Path
from urllib.parse import urlsplit


ALLOWED = {'api.sofascore.com', 'www.sofascore.com', 'fbref.com',
           'www.espn.com', 'site.api.espn.com', 'understat.com'}


class SourceUnavailable(RuntimeError):
    pass


def validated_url(url):
    parts = urlsplit(url)
    if (parts.scheme != 'https' or parts.netloc not in ALLOWED
            or parts.username or parts.password or parts.fragment):
        raise ValueError('unapproved_source_url')
    return url


class OriginalStore:
    def __init__(self, directory, scrape):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.scrape = scrape
        self.used = {}

    def paths(self, url):
        validated_url(url)
        key = hashlib.sha256(url.encode()).hexdigest()
        return (self.directory / (key + '.body.gz'),
                self.directory / (key + '.receipt.json'))

    def save(self, url, raw, receipt):
        body, meta = self.paths(url)
        if body.exists() or meta.exists():
            raise ValueError('original_already_exists')
        if len(raw) > 24_000_000:
            raise ValueError('source_response_too_large')
        if hashlib.sha256(raw).hexdigest() != receipt['sha256']:
            raise ValueError('original_hash_mismatch')
        captured = datetime.fromisoformat(receipt['received_at'].replace('Z', '+00:00'))
        if captured.tzinfo is None or captured > datetime.now(timezone.utc):
            raise ValueError('invalid_source_receipt')
        body.write_bytes(gzip.compress(raw))
        meta.write_text(json.dumps(dict(receipt, requested_url=url), ensure_ascii=False,
                                   indent=2, allow_nan=False), encoding='utf-8')

    def load(self, url):
        body, meta = self.paths(url)
        if body.exists() != meta.exists():
            raise ValueError('incomplete_original_cache')
        if not body.exists():
            raw, receipt = self.scrape(url)
            self.save(url, raw, receipt)
        receipt = json.loads(meta.read_text(encoding='utf-8'))
        raw = gzip.decompress(body.read_bytes())
        if (receipt['requested_url'] != url
                or hashlib.sha256(raw).hexdigest() != receipt['sha256']):
            raise ValueError('original_hash_or_url_mismatch')
        self.used[url] = receipt
        if receipt.get('provider_error'):
            raise SourceUnavailable('source_failed_cached:' + url)
        return raw, receipt

    def reader_get(self, url, filepath=None, max_age=None, no_cache=False, var=None):
        # Raw provider receipts remain authoritative even if soccerdata requests
        # a current-season refresh. A refresh requires a new run directory.
        if var is not None:
            raise ValueError('javascript_extraction_not_supported')
        raw, _ = self.load(url)
        if urlsplit(url).netloc == 'fbref.com':
            # FBref embeds deferred tables in HTML comments. Its normal browser
            # makes them visible; expose only table comments to upstream parsers.
            # The stored original and its receipt/hash stay byte-for-byte intact.
            raw = re.sub(rb'<!--(.*?)-->',
                         lambda m:m.group(1) if b'<table' in m.group(1) else m.group(0),
                         raw, flags=re.DOTALL)
        return io.BytesIO(raw)


def bind_reader(reader_class, store, **kwargs):
    """Subclass only the transport boundary; retain upstream public parsers."""
    class ZenRowsReader(reader_class):
        @classmethod
        def _all_leagues(cls):
            return reader_class._all_leagues()

        def _init_session(self, headers=None):
            return None

        def _init_webdriver(self):
            return None

        def get(self, *args, **options):
            return store.reader_get(*args, **options)

        def _download_and_save(self, *args, **options):
            raise RuntimeError('direct_source_network_disabled')

        def close(self):
            pass

    return ZenRowsReader(**kwargs)
