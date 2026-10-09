from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import sqlite3
import threading
import urllib.error
import urllib.request

import pytest

from nba import dashboard,paper,paper_followup as followup
from nba import multimarket_dashboard
from nba.audit import Ledger,digest,write_json
from test_paper import cohort,NOW,TIP,EVENT
from test_paper_followup import planned,game,source


@pytest.fixture
def screen(planned,monkeypatch):
    data=planned/'data';data.mkdir()
    followup.advance(planned/'plan',data/'state.sqlite',planned/'before')
    write_json(data/'health.json',dict(state='waiting',as_of=NOW.isoformat()))
    return dashboard.Dashboard(planned/'plan',data)


def finish(screen,monkeypatch,dnp=False):
    cut=TIP+timedelta(hours=4)
    received=screen.paper/'runs/final/received';received.mkdir(parents=True)
    final=game(3)
    if dnp:
        final['homeTeam']['players'][0]['statistics']=dict(minutes='00:00',points=0,reboundsTotal=0,assists=0)
        final['homeTeam']['statistics']=dict(points=0,reboundsTotal=0,assists=0)
    receipt=source(received,final,cut,'https://www.nba.com/game/bos-vs-det-0022600001/box-score')
    (received/'boxscore.html').write_bytes((received/receipt['raw_sha256']).read_bytes())
    receipt.update(game_id='0022600001',raw_file='boxscore.html');write_json(received/'receipt.json',receipt)
    mapping=screen.plan['mappings'][0];folder=received.parent/'evaluation'
    monkeypatch.setattr(paper,'now_utc',lambda:cut)
    metrics=paper.score_result(mapping['registration'],EVENT,received/'receipt.json',folder)
    payload=dict(status='scored',event_id=EVENT,job_id=EVENT+':result:4',plan_sha256=screen.plan_hash,
        evaluation='/data/runs/final/evaluation',metrics=metrics)
    Ledger(screen.paper/'state.sqlite').append('job_result',payload)
    return cut,folder,payload


def extended_screen(screen,root):
    mapping=screen.plan['mappings'][0]
    row=dict(event_id=mapping['provider_event_id'],nba_game_id=mapping['nba_game_id'],player_id=1,
        player='Test Player',team_id=mapping['home_nba_team_id'],market='player_blocks',market_label='Tapones',
        estimate=.5,range_low=0,range_high=2,line=.5,probability_over=.3,probability_under=.7,
        sealed_at_utc=NOW.isoformat(),last_feature_date=(NOW-timedelta(days=1)).date().isoformat(),
        conditional_participation=True,reference='Umbral estadístico')
    write_json(root/'bundle.json',dict(version='test-extension',created_at_utc=NOW.isoformat(),
        original_plan_sha256=screen.plan_hash,forecasts=[row],comparison=dict(markets={})))
    write_json(root/'bundle.seal.json',dict(sha256=digest(root/'bundle.json')))
    return multimarket_dashboard.MultiDashboard(screen,root)


def test_extension_reuses_original_receipts_without_writes_and_holds_missing_extra_stat(screen,tmp_path,monkeypatch):
    view=extended_screen(screen,tmp_path/'extension')
    assert view.data()['extension']['predictions'][0]['result']['status']=='pending'
    cut,folder,payload=finish(screen,monkeypatch)
    monkeypatch.setattr(screen,'data',lambda:screen.snapshot(cut))
    from datetime import datetime
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):return cut
    monkeypatch.setattr(multimarket_dashboard,'datetime',Clock)
    state=digest(screen.paper/'state.sqlite')
    # Final original three statistics exist, but no blocks: do not invent a zero.
    data=view.data()
    assert data['totals']['evaluated']==3
    assert data['extension']['predictions'][0]['result']==dict(status='validation_hold',actual=None)
    assert digest(screen.paper/'state.sqlite')==state
    assert 'pmf' not in data['extension']['predictions'][0]


def test_extension_seal_must_link_original_plan_and_precede_target(screen,tmp_path):
    root=tmp_path/'extension';view=extended_screen(screen,root)
    bundle=json.loads((root/'bundle.json').read_bytes());bundle['forecasts'][0]['sealed_at_utc']=TIP.isoformat()
    write_json(root/'bundle.json',bundle);write_json(root/'bundle.seal.json',dict(sha256=digest(root/'bundle.json')))
    with pytest.raises(ValueError,match='after target'):
        multimarket_dashboard.MultiDashboard(screen,root)


def test_extension_scores_received_extra_stat_and_rejects_later_body_change(screen,tmp_path,monkeypatch):
    import sys
    from datetime import datetime
    original_game=game
    def complete(status=1):
        value=original_game(status)
        if status==3:
            value['homeTeam']['players'][0]['statistics']['blocks']=2
            value['homeTeam']['statistics']['blocks']=2
            value['awayTeam']['statistics']['blocks']=0
        return value
    monkeypatch.setattr(sys.modules[__name__],'game',complete)
    view=extended_screen(screen,tmp_path/'extension')
    cut,folder,payload=finish(screen,monkeypatch)
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):return cut
    monkeypatch.setattr(multimarket_dashboard,'datetime',Clock)
    monkeypatch.setattr(screen,'data',lambda:screen.snapshot(cut))
    state=digest(screen.paper/'state.sqlite')
    first=view.data();assert first['totals']['evaluated']==3
    assert first['extension']['predictions'][0]['result']==dict(status='evaluated',actual=2)
    raw=folder.parent/'received/boxscore.html';raw.write_bytes(raw.read_bytes()+b'changed')
    second=view.data()
    assert second['extension']['predictions'][0]['result']['status']=='validation_hold'
    assert second['extension']['predictions'][0]['result']['actual'] is None
    assert digest(screen.paper/'state.sqlite')==state


def test_pending_projection_is_unique_readonly_and_sanitized(screen):
    before=digest(screen.paper/'state.sqlite')
    snapshot=screen.snapshot(NOW)
    assert snapshot['totals']==dict(predictions=3,players=1,events=1,evaluated=0,dnp=0,validation_holds=0)
    assert all(row['result']['actual'] is None and row['result']['status']=='pending' for row in snapshot['predictions'])
    assert not snapshot['actionable'] and snapshot['health']['pilot']['state']=='waiting'
    assert digest(screen.paper/'state.sqlite')==before
    encoded=json.dumps(snapshot)
    for forbidden in ('/data/','/home/','registration','raw_sha256','token','input_hashes','history_game_ids','pmf'):
        assert forbidden not in encoded
    assert {row['market'] for row in snapshot['predictions']}==set(dashboard.MARKETS)


def test_official_results_appear_without_changing_forecasts(screen,monkeypatch):
    original=screen.snapshot(NOW)['predictions'];cut,folder,_=finish(screen,monkeypatch)
    snapshot=screen.snapshot(cut)
    assert snapshot['totals']['evaluated']==3 and snapshot['events'][0]['status']=='evaluated'
    assert {r['market']:r['result']['actual'] for r in snapshot['predictions']}==dict(player_points=20,player_rebounds=6,player_assists=5)
    assert [r['estimate'] for r in snapshot['predictions']]==[r['estimate'] for r in original]


def test_explicit_DNP_is_separate_from_zero_count(screen,monkeypatch):
    cut,folder,_=finish(screen,monkeypatch,True)
    snapshot=screen.snapshot(cut)
    assert snapshot['totals']['evaluated']==0 and snapshot['totals']['dnp']==3
    assert snapshot['events'][0]['status']=='evaluated'
    assert all(r['result']['actual'] is None and r['result']['status']=='dnp' for r in snapshot['predictions'])


@pytest.mark.parametrize('mutation',['outcomes_hash','official_body','official_receipt','count_resealed','DNP_resealed'])
def test_tampered_result_never_publishes_actual(screen,monkeypatch,mutation):
    cut,folder,_=finish(screen,monkeypatch)
    if mutation=='outcomes_hash':(folder/'outcomes.json').write_text('[]')
    elif mutation=='official_body':(folder.parent/'received/boxscore.html').write_text('unverified')
    elif mutation=='official_receipt':
        receipt=json.loads((folder.parent/'received/receipt.json').read_bytes());receipt['http_status']=403
        write_json(folder.parent/'received/receipt.json',receipt)
    else:
        outcomes=json.loads((folder/'outcomes.json').read_bytes())
        if mutation=='count_resealed':outcomes[0]['actual']=999
        else:outcomes[0].update(played=False,actual=None)
        write_json(folder/'outcomes.json',outcomes)
        seal=json.loads((folder/'seal.json').read_bytes());seal['files']['outcomes.json']=digest(folder/'outcomes.json');write_json(folder/'seal.json',seal)
    snapshot=screen.snapshot(cut)
    assert snapshot['totals']['evaluated']==0 and snapshot['totals']['validation_holds']==1
    assert all(r['result']['actual'] is None and r['result']['status']=='validation_hold' for r in snapshot['predictions'])


def test_duplicate_result_for_same_event_is_not_double_counted(screen,monkeypatch):
    cut,folder,payload=finish(screen,monkeypatch);Ledger(screen.paper/'state.sqlite').append('job_result',payload)
    assert screen.snapshot(cut)['totals']['validation_holds']==1


def test_wrong_plan_result_is_not_admitted(screen):
    Ledger(screen.paper/'state.sqlite').append('job_result',dict(status='scored',event_id=EVENT,plan_sha256='wrong'))
    assert screen.snapshot(NOW)['totals']['evaluated']==0


def test_changed_forecast_or_journal_rejected(screen):
    Ledger(screen.paper/'state.sqlite').append('job_result',dict(status='pending'))
    with sqlite3.connect(screen.paper/'state.sqlite') as db:
        db.execute('DROP TRIGGER events_no_update')
        db.execute("UPDATE events SET payload='{}'")
    with pytest.raises(ValueError,match='integrity'):screen.snapshot(NOW)


def test_changed_prediction_is_rejected(screen):
    folder=Path(screen.groups[EVENT][0]['registration'])
    (folder/'forecasts.json').write_text('[]')
    with pytest.raises(ValueError,match='sealed registration changed'):screen.snapshot(NOW)


@pytest.mark.parametrize('name',['/data/../../private/key','/home/qf/private','/data/runs/link'])
def test_worker_path_cannot_escape_result_root(screen,name):
    if name=='/data/runs/link':
        (screen.paper/'runs').mkdir(exist_ok=True)
        try:(screen.paper/'runs/link').symlink_to(screen.paper.parent,target_is_directory=True)
        except OSError:pytest.skip('Windows symlink privilege unavailable')
    with pytest.raises(ValueError,match='unsafe'):dashboard.worker_path(screen.paper,name)


def test_health_clock_and_staleness_are_visible(screen):
    assert dashboard.observation(screen.paper/'health.json',NOW+timedelta(seconds=121),120)['state']=='stale'
    assert dashboard.observation(screen.paper/'health.json',NOW-timedelta(seconds=6),120)['state']=='stale'


def test_http_whitelist_head_method_and_generic_failure(screen,monkeypatch):
    static=Path(__file__).parents[1]/'web'
    server=dashboard.Server(('127.0.0.1',0),dashboard.handler(screen,static))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base='http://127.0.0.1:'+str(server.server_port)
    try:
        for path in ('/nba','/nba/','/nba/styles.css','/nba/app.js','/nba/api/data'):
            with urllib.request.urlopen(base+path) as response:
                assert response.status==200 and response.headers['Cache-Control']=='no-store'
                assert response.headers['X-Content-Type-Options']=='nosniff'
        with urllib.request.urlopen(urllib.request.Request(base+'/nba',method='HEAD')) as response:
            assert not response.read() and int(response.headers['Content-Length'])>0
        for path in ('/nba/../../private/telegram.json','/nba/.env','/nba/api/source','/admin'):
            with pytest.raises(urllib.error.HTTPError) as error:urllib.request.urlopen(base+path)
            assert error.value.code==404
        with pytest.raises(urllib.error.HTTPError) as error:urllib.request.urlopen(urllib.request.Request(base+'/nba/api/data',data=b'{}'))
        assert error.value.code==405
        def broken():raise ValueError('secret never belongs in HTTP response')
        monkeypatch.setattr(screen,'data',broken)
        with pytest.raises(urllib.error.HTTPError) as error:urllib.request.urlopen(base+'/nba/api/data')
        assert error.value.code==503 and b'secret' not in error.value.read()
    finally:server.shutdown();server.server_close();thread.join()
