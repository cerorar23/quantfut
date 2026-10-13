from datetime import datetime,timezone
import gzip
import hashlib
import importlib
import json
from pathlib import Path

import pytest

from qf.ingest.soccerdata_transport import OriginalStore,SourceUnavailable


def test_changed_country_route_does_not_retry_known_gb_failures(tmp_path,monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]/'scripts'))
    collector=importlib.import_module('soccerdata_football_collect')
    previous=tmp_path/'previous';folder=previous/'detail-responses';folder.mkdir(parents=True)
    for sid,country in [(1,None),(2,'GB')]:
        raw=b'provider failure'
        receipt={'url':f'https://www.sofascore.com/api/v1/event/{sid}/statistics',
            'sha256':hashlib.sha256(raw).hexdigest(),
            'received_at':datetime.now(timezone.utc).isoformat(),'provider_error':True,
            'parameters':{'proxy_country':country}}
        path=folder/(str(sid)+'.json.gz')
        path.write_bytes(gzip.compress(raw))
        path.with_name(path.name+'.meta.json').write_text(json.dumps(receipt))
    calls=[]
    def scrape(url):
        calls.append(url)
        raw=b'{"statistics":[]}'
        return raw,{'sha256':hashlib.sha256(raw).hexdigest(),
            'received_at':datetime.now(timezone.utc).isoformat(),'provider_error':False}
    store=OriginalStore(tmp_path/'new',scrape)
    assert collector.import_cached_sources(store,[previous])==1
    assert store.load('https://www.sofascore.com/api/v1/event/1/statistics')[0]==b'{"statistics":[]}'
    with pytest.raises(SourceUnavailable):store.load('https://www.sofascore.com/api/v1/event/2/statistics')
    assert len(calls)==1


def test_adopted_original_keeps_actual_receipt_and_hash(tmp_path,monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]/'scripts'))
    collector=importlib.import_module('soccerdata_football_collect')
    url='https://www.sofascore.com/api/v1/event/1/lineups';raw=b'{"confirmed":true}'
    receipt={'url':url,'received_at':'2026-10-03T10:00:00Z',
        'sha256':hashlib.sha256(raw).hexdigest(),'provider_error':False}
    original=OriginalStore(tmp_path/'previous'/'originals',lambda _:pytest.fail('network'))
    original.save(url,raw,receipt)
    target=OriginalStore(tmp_path/'new',lambda _:pytest.fail('network'))
    assert collector.import_cached_sources(target,[tmp_path/'previous'])==1
    value,meta=target.load(url)
    assert value==raw and meta['received_at']==receipt['received_at'] and meta['sha256']==receipt['sha256']


def test_calendar_result_survives_unavailable_details_without_fabricated_metrics(tmp_path,monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]/'scripts'))
    collector=importlib.import_module('soccerdata_football_collect')
    class Reader:
        def read_event_details(self,event):
            return {'statistics':None,'lineups':None},[],[{'reason':'unavailable'}]
    monkeypatch.setattr(collector,'history_reader',lambda *args:Reader())
    event={'id':123,'startTimestamp':1704110400,'status':{'type':'finished','code':100},
        'homeTeam':{'id':10,'name':'A','sport':{'id':1}},
        'awayTeam':{'id':20,'name':'B','sport':{'id':1}},
        'homeScore':{'current':1},'awayScore':{'current':0},
        'tournament':{'uniqueTournament':{'id':18},'category':{'alpha2':'EN'}}}
    raw=json.dumps({'events':[event]}).encode()
    url='https://www.sofascore.com/api/v1/unique-tournament/18/season/1/events/last/0'
    receipt={'url':url,'sha256':hashlib.sha256(raw).hexdigest(),
        'received_at':'2026-10-03T10:00:00Z','provider_error':False}
    OriginalStore(tmp_path/'originals',lambda _:pytest.fail('network')).save(url,raw,receipt)
    snapshot=tmp_path/'snapshot.json';snapshot.write_text('{"matches":[]}')
    result=collector.assemble_cached(tmp_path,snapshot)
    assert result['original_bundles']==1 and result['xg_pairs']==result['players']==0
    with gzip.open(tmp_path/'prepared/normalized.jsonl.gz','rt') as handle:
        row=json.loads(handle.readline())
    assert row['home_goals']==1 and row['away_goals']==0
    assert row['home_xg'] is None and row['away_xg'] is None and row['lineups']==[]
    assert row['captured_at']=='2026-10-03T10:00:00+00:00'
    with pytest.raises(ValueError,match='already_exists'):
        collector.assemble_cached(tmp_path,snapshot)
