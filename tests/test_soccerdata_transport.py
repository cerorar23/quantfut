import gzip
import hashlib
import json
from datetime import datetime, timezone

import pytest

from qf.ingest.soccerdata_transport import OriginalStore, SourceUnavailable, bind_reader


def receipt(raw, failed=False):
    return {'sha256':hashlib.sha256(raw).hexdigest(),
            'received_at':datetime.now(timezone.utc).isoformat(), 'provider_error':failed}


def test_verified_cache_reuses_receipt_even_when_reader_requests_refresh(tmp_path):
    calls=[]
    raw=b'{"events":[]}'
    def scrape(url):
        calls.append(url)
        return raw,receipt(raw)
    store=OriginalStore(tmp_path,scrape)
    url='https://api.sofascore.com/api/v1/event/1'
    assert store.reader_get(url,no_cache=True).read()==raw
    first=store.used[url]
    assert store.reader_get(url,no_cache=True).read()==raw
    assert store.used[url]==first and len(calls)==1


def test_error_cache_does_not_retry_or_become_empty_data(tmp_path):
    calls=[]
    def scrape(url):
        calls.append(url)
        return b'blocked',receipt(b'blocked',True)
    store=OriginalStore(tmp_path,scrape)
    for _ in range(2):
        with pytest.raises(SourceUnavailable):
            store.load('https://fbref.com/en/comps/')
    assert len(calls)==1


def test_tampered_cache_rejected_before_parser(tmp_path):
    store=OriginalStore(tmp_path,lambda _: (b'original',receipt(b'original')))
    url='https://fbref.com/en/comps/'
    store.load(url)
    body,_=store.paths(url)
    body.write_bytes(gzip.compress(b'changed'))
    with pytest.raises(ValueError,match='hash_or_url'):
        store.load(url)


def test_deferred_fbref_tables_exposed_but_original_preserved(tmp_path):
    raw=b'<html><!--note--><!--<table id="comps"></table>--></html>'
    store=OriginalStore(tmp_path,lambda _:(raw,receipt(raw)))
    url='https://fbref.com/en/comps/'
    assert store.reader_get(url).read()==b'<html><!--note--><table id="comps"></table></html>'
    assert store.load(url)[0]==raw


@pytest.mark.parametrize('url',['http://fbref.com/en/', 'https://example.com/',
    'https://fbref.com:443/en/', 'https://a:b@fbref.com/en/', 'https://fbref.com/en/#x'])
def test_bad_destination_never_calls_transport(tmp_path,url):
    store=OriginalStore(tmp_path,lambda _:pytest.fail('network called'))
    with pytest.raises(ValueError,match='unapproved'):
        store.load(url)


def test_reader_keeps_upstream_parser_and_provider_configuration(tmp_path):
    class Upstream:
        @classmethod
        def _all_leagues(cls):
            return {'domestic':'native'}
        def __init__(self):
            self.mapping=self._all_leagues()
            self._session=self._init_session()
            self._driver=self._init_webdriver()
        def read_schedule(self):
            return json.load(self.get('https://fbref.com/en/comps/'))['matches']
    raw=b'{"matches":[1,2]}'
    reader=bind_reader(Upstream,OriginalStore(tmp_path,lambda _:(raw,receipt(raw))))
    assert reader.mapping=={'domestic':'native'}
    assert reader._session is None and reader._driver is None
    assert reader.read_schedule()==[1,2]
    with pytest.raises(RuntimeError,match='direct_source'):
        reader._download_and_save('https://fbref.com/en/')
