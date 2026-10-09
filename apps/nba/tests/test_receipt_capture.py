import io
import json
from datetime import UTC,datetime,timedelta
from urllib.error import HTTPError

import pytest

from nba.receipt_capture import CaptureStore,contract_readiness

URL='https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json'


def mock_open(monkeypatch,fn):
    class Opener:
        def open(self,*a,**k):return fn(*a,**k)
    monkeypatch.setattr('urllib.request.build_opener',lambda *a:Opener())


def capture(tmp_path,monkeypatch,games=(),redirect=False):
    class Response(io.BytesIO):
        status=200
        headers={}
        url='https://elsewhere.test/' if redirect else URL
    raw=json.dumps(dict(scoreboard=dict(games=list(games)))).encode()
    mock_open(monkeypatch,lambda *a,**k:Response(raw))
    store=CaptureStore(tmp_path)
    return store,store.collect_public(URL,[URL])


def game(status=1,delta=3600,identifier='0022600001'):
    return dict(gameId=identifier,gameStatus=status,gameTimeUTC=(datetime.now(UTC)+timedelta(seconds=delta)).isoformat(),
        homeTeam=dict(teamId=1),awayTeam=dict(teamId=2))


def test_capture_uses_current_own_receipt_and_preserves_body(tmp_path,monkeypatch):
    s,r=capture(tmp_path,monkeypatch,[game()])
    assert s.verify_receipt(r)['source_updated_at_utc'] is None
    c=s.schedule_context(r)
    assert len(c['events'])==1 and c['events'][0]['contract_verified'] is False
    assert c['F7_started'] is False and r['original_historical_receipt_known'] is False


def test_finished_and_past_scheduled_games_not_prospective(tmp_path,monkeypatch):
    s,r=capture(tmp_path,monkeypatch,[game(3,3600),game(1,-3600,'0022600002')])
    assert s.schedule_context(r)['events']==[]


@pytest.mark.parametrize('part',['time','body','hash'])
def test_tampering_rejected(tmp_path,monkeypatch,part):
    s,r=capture(tmp_path,monkeypatch,[game()])
    if part=='time':r['first_received_at_utc']='2001-01-01T00:00:00Z'
    if part=='hash':r['receipt_event_hash']='0'*64
    if part=='body':(tmp_path/'blobs'/r['raw_sha256']).write_bytes(b'corrupt')
    with pytest.raises(ValueError):s.verify_receipt(r)


def test_duplicate_identity_rejected(tmp_path,monkeypatch):
    g=game();s,r=capture(tmp_path,monkeypatch,[g,g])
    with pytest.raises(ValueError):s.schedule_context(r)


@pytest.mark.parametrize('url',[URL+'?token=secret','http://cdn.nba.com/a','https://user:password@cdn.nba.com/a','https://unknown.test'])
def test_only_public_allowlisted_requests(tmp_path,monkeypatch,url):
    mock_open(monkeypatch,lambda *a,**k:pytest.fail('invalid URL requested'))
    with pytest.raises(ValueError):CaptureStore(tmp_path).collect_public(url,[URL])


def test_http_error_receipt_has_no_old_fallback(tmp_path,monkeypatch):
    def fail(*a,**k):raise HTTPError(URL,403,'Forbidden',{},io.BytesIO(b'blocked'))
    mock_open(monkeypatch,fail)
    s=CaptureStore(tmp_path);r=s.collect_public(URL,[URL])
    assert r['http_status']==403 and s.schedule_context(r)['state']=='unavailable'


def test_missing_contract_rules_cannot_become_verified(tmp_path,monkeypatch):
    s,r=capture(tmp_path,monkeypatch)
    c=contract_readiness({},r,None)
    assert c['state']=='incomplete' and c['contract_verified'] is False
    assert 'rule_body_hash_unverified' in c['reasons']


def test_redirect_blocked_before_following():
    from nba.receipt_capture import NoRedirect
    with pytest.raises(ValueError):NoRedirect().redirect_request(None,None,302,'redirect',{},'https://other.test')
