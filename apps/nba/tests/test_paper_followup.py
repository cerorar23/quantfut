from copy import deepcopy
from datetime import timedelta
from hashlib import sha256
import json
import sqlite3
import httpx

import pytest

from nba import paper, paper_followup as followup
from nba.audit import digest, write_json
from test_paper import cohort, register, NOW, TIP, EVENT


def game(status=1):
    def team(name,identity):
        return dict(teamId=identity,teamCity='Test',teamName=name,players=[],inactives=[],
                    statistics=dict(points=0,reboundsTotal=0,assists=0))
    result=dict(gameId='0022600001',gameTimeUTC=TIP.isoformat(),gameStatus=status,
        homeTeamId=10,awayTeamId=20,homeTeam=team('Home',10),awayTeam=team('Away',20))
    if status==3:
        stats=dict(points=20,reboundsTotal=6,assists=5,minutes='30:00')
        result['homeTeam']['players']=[dict(personId=1,statistics=stats)]
        result['homeTeam']['statistics']=dict(points=20,reboundsTotal=6,assists=5)
    return result


def source(root,data,clock,url='https://www.nba.com/game/bos-vs-det-0022600001'):
    root.mkdir(parents=True,exist_ok=True)
    raw=('<script id="__NEXT_DATA__">'+json.dumps(dict(props=dict(pageProps=dict(game=data))))+'</script>').encode()
    hashed=sha256(raw).hexdigest();(root/hashed).write_bytes(raw)
    return dict(url=url,http_status=200,raw_sha256=hashed,first_received_at_utc=clock.isoformat())


@pytest.fixture
def planned(cohort,monkeypatch):
    register(cohort)
    rows=paper.verify_registration(cohort/'run')
    write_json(cohort/'cohort.json',dict(units=len(rows),rows=[dict(event_id=r['event_id'],player_id=r['player_id'],market=r['market'],
        registration=(cohort/'run').as_posix(),registration_seal_sha256=digest(cohort/'run/seal.json'),sealed_at_utc=r['sealed_at_utc']) for r in rows]))
    receipt=source(cohort/'blobs',game(),NOW)
    write_json(cohort/'receipts.json',[receipt])
    monkeypatch.setattr(followup,'now_utc',lambda:NOW)
    followup.build_plan(cohort/'cohort.json',cohort/'receipts.json',cohort/'blobs',cohort/'plan')
    return cohort


def test_exact_mapping_and_pre_due_execution_no_requests(planned,monkeypatch):
    plan=followup.verify_plan(planned/'plan')
    assert plan['mappings'][0]['nba_game_id']=='0022600001' and plan['unique_units']==3
    monkeypatch.setattr(followup,'capture',lambda *a:pytest.fail('not due'))
    result=followup.advance(planned/'plan',planned/'state.sqlite',planned/'before')
    assert result['executed']==[] and result['completed_events']==0
    (planned/'blobs'/plan['mappings'][0]['raw_sha256']).write_bytes(b'changed')
    with pytest.raises(ValueError,match='input changed'):followup.verify_plan(planned/'plan')


@pytest.mark.parametrize('mutation',['time','team','id','hash','receipt'])
def test_official_source_rejects_mismatch(planned,mutation):
    data=game();receipt=json.loads((planned/'receipts.json').read_bytes())[0]
    if mutation=='time':data['gameTimeUTC']='not a timestamp'
    elif mutation=='team':data['homeTeamId']=99
    elif mutation=='id':data['gameId']='0022600002'
    receipt=source(planned/'changed',data,NOW)
    raw=(planned/'changed'/receipt['raw_sha256']).read_bytes()
    if mutation=='hash':raw+=b'changed'
    if mutation=='receipt':receipt['first_received_at_utc']=(NOW+timedelta(seconds=1)).isoformat()
    with pytest.raises((ValueError,KeyError)):followup.official_metadata(raw,receipt,NOW.isoformat())


@pytest.mark.parametrize('state,expected',[('Available','explicit_available_observed'),('Active','unknown'),('Out','explicit_out_observed'),(None,'unknown')])
def test_availability_does_not_infer_health_from_roster(planned,state,expected):
    data=game();data['homeTeam']['players']=[dict(personId=1,status=state)]
    mapping=followup.verify_plan(planned/'plan')['mappings'][0]
    receipt=source(planned/'pregame',data,TIP-timedelta(minutes=2))
    result=followup.availability_review(data,mapping,receipt,[1,99])
    assert result['rows'][0]['state']==expected and result['rows'][1]['state']=='unknown'
    assert not result['availability_final_verified'] and not result['actionable']
    data['homeTeam']['inactives']=[dict(personId=1)]
    assert followup.availability_review(data,mapping,receipt,[1])['rows'][0]['state']=='official_inactive'


@pytest.mark.parametrize('mutation',['none','book','line','stale','after_tip','duplicate'])
def test_close_only_exact_fresh_contract(planned,mutation):
    forecast=paper.verify_registration(planned/'run')[0];cut=TIP-timedelta(minutes=2)
    quote=dict(forecast['reference_quote'],over_decimal=2.,under_decimal=1.8,
        first_received_at_utc=cut.isoformat(),source_updated_at_utc=cut.isoformat())
    quotes=[quote]
    if mutation=='book':quote['book']='other'
    elif mutation=='line':quote['line']+=1
    elif mutation=='stale':quote['source_updated_at_utc']=(cut-timedelta(seconds=61)).isoformat()
    elif mutation=='after_tip':cut=TIP
    elif mutation=='duplicate':quotes.append(deepcopy(quote))
    result=followup.compare_close(forecast,quotes,cut.isoformat())
    assert result['comparable']==(mutation=='none')
    if result['comparable']:
        assert result['raw_price_clv']==pytest.approx(forecast['hypothetical_entry']['decimal']/result['closing_decimal']-1)
        assert not result['operational_profit_proved']


def test_lifecycle_final_scoring_repetition_and_immutable_claims(planned,monkeypatch):
    cut=TIP+timedelta(hours=4,minutes=1);calls=[]
    monkeypatch.setattr(followup,'now_utc',lambda:cut)
    monkeypatch.setattr(paper,'now_utc',lambda:cut)
    def captured(root,url,allowed):
        calls.append(url)
        return source(root/'blobs',game(3),cut,url)
    monkeypatch.setattr(followup,'capture',captured)
    result=followup.advance(planned/'plan',planned/'state.sqlite',planned/'after')
    assert result['status']=='completed' and result['summary']['units']==3 and len(calls)==1
    again=followup.advance(planned/'plan',planned/'state.sqlite',planned/'again')
    assert again['executed']==[] and len(calls)==1 and again['summary']['units']==3
    with sqlite3.connect(planned/'state.sqlite') as db:
        with pytest.raises(sqlite3.IntegrityError):db.execute('DELETE FROM claims')


def test_failed_result_is_not_retried_but_next_fixed_window_can_run(planned,monkeypatch):
    cut=TIP+timedelta(hours=4,minutes=1);calls=[]
    monkeypatch.setattr(followup,'now_utc',lambda:cut)
    monkeypatch.setattr(paper,'now_utc',lambda:cut)
    def captured(root,url,allowed):
        calls.append(url);receipt=source(root/'blobs',game(),cut,url);receipt['http_status']=403
        return receipt
    monkeypatch.setattr(followup,'capture',captured)
    first=followup.advance(planned/'plan',planned/'state.sqlite',planned/'fail')
    assert first['executed'][-1]['status']=='source_or_validation_failure'
    followup.advance(planned/'plan',planned/'state.sqlite',planned/'fail_again')
    assert len(calls)==1
    cut=TIP+timedelta(hours=6,minutes=1)
    followup.advance(planned/'plan',planned/'state.sqlite',planned/'next')
    assert len(calls)==2


def test_pregame_once_and_no_closing_key_no_paid_call(planned,monkeypatch):
    cut=TIP-timedelta(minutes=1);calls=[]
    monkeypatch.setattr(followup,'now_utc',lambda:cut)
    monkeypatch.setattr(followup,'capture',lambda root,url,allowed: (calls.append(url) or source(root/'blobs',game(),cut,url)))
    result=followup.advance(planned/'plan',planned/'state.sqlite',planned/'pre')
    assert {r['status'] for r in result['executed']}=={'pregame_observed','credentials_absent'}
    assert len(calls)==1
    followup.advance(planned/'plan',planned/'state.sqlite',planned/'repeat')
    assert len(calls)==1


def test_conflicting_cohort_mapping_is_rejected(planned):
    receipt=source(planned/'wrong',dict(game(),gameTimeUTC=(TIP+timedelta(seconds=1)).isoformat()),NOW)
    write_json(planned/'wrong_receipts.json',[receipt])
    with pytest.raises(ValueError,match='exact official'):
        followup.build_plan(planned/'cohort.json',planned/'wrong_receipts.json',planned/'wrong',planned/'bad')


def test_per_run_limit_leaves_additional_jobs_unclaimed(planned,monkeypatch):
    plan=followup.verify_plan(planned/'plan');cut=TIP-timedelta(minutes=1)
    plan['maximum_jobs_per_run']=1
    # Synthetic execution plan only; sealed real inputs still verified by the original fixture.
    plan['jobs']=[dict(plan['jobs'][0],kind='pregame',id=EVENT+':pregame:'+str(i)) for i in range(3)]
    monkeypatch.setattr(followup,'verify_plan',lambda root:plan)
    monkeypatch.setattr(followup,'now_utc',lambda:cut)
    calls=[]
    monkeypatch.setattr(followup,'capture',lambda root,url,allowed:(calls.append(url) or source(root/'blobs',game(),cut,url)))
    followup.advance(planned/'plan',planned/'state.sqlite',planned/'limit1')
    with sqlite3.connect(planned/'state.sqlite') as db:assert db.execute('SELECT COUNT(*) FROM claims').fetchone()[0]==1
    followup.advance(planned/'plan',planned/'state.sqlite',planned/'limit2')
    assert len(calls)==2


def test_uncertain_close_claim_prevents_second_paid_attempt(planned,monkeypatch):
    cut=TIP-timedelta(minutes=1);calls=[]
    monkeypatch.setattr(followup,'now_utc',lambda:cut)
    monkeypatch.setattr(followup,'capture',lambda root,url,allowed:source(root/'blobs',game(),cut,url))
    def failed(*args):
        calls.append('paid');raise OSError('timeout')
    monkeypatch.setattr(followup,'_closing_capture',failed)
    result=followup.advance(planned/'plan',planned/'state.sqlite',planned/'uncertain',key='test')
    assert any(r['status']=='source_or_validation_failure' for r in result['executed'])
    followup.advance(planned/'plan',planned/'state.sqlite',planned/'uncertain_repeat',key='test')
    assert calls==['paid']


@pytest.mark.parametrize('changed_tip',[False,True])
def test_closing_request_is_two_markets_one_book_bounded(planned,monkeypatch,changed_tip):
    from nba import odds_capture
    cut=TIP-timedelta(minutes=2);calls=[]
    class Clock(odds_capture.datetime):
        @classmethod
        def now(cls,tz=None):return cut
    monkeypatch.setattr(odds_capture,'datetime',Clock)
    monkeypatch.setattr(followup,'now_utc',lambda:cut)
    forecasts=paper.verify_registration(planned/'run')[:2]
    mapping=followup.verify_plan(planned/'plan')['mappings'][0]
    def respond(request):
        calls.append(request)
        if request.url.path.endswith('/sports'):body=[];cost=0
        else:
            assert request.url.params['bookmakers']=='sportsbet'
            assert set(request.url.params['markets'].split(','))=={f['market'] for f in forecasts}
            cost=2;body=dict(id=EVENT,sport_key='basketball_nba',home_team='Test Home',away_team='Test Away',commence_time=(TIP+timedelta(minutes=int(changed_tip))).isoformat(),
                bookmakers=[dict(key='sportsbet',markets=[dict(key=f['market'],last_update=cut.isoformat(),
                    outcomes=[dict(name=side,description='Test Player',point=f['reference_quote']['line'],price=1.9) for side in ('Over','Under')]) for f in forecasts])])
        return httpx.Response(200,json=body,headers={'x-requests-last':str(cost),'x-requests-used':'102','x-requests-remaining':'10000'})
    client=httpx.Client(transport=httpx.MockTransport(respond))
    monkeypatch.setattr(followup.httpx,'Client',lambda **kwargs:client)
    root=planned/'closing';root.mkdir()
    if changed_tip:
        with pytest.raises(ValueError,match='scope mismatch'):followup._closing_capture(root,mapping,forecasts,'test')
        assert len(calls)==2
        return
    result=followup._closing_capture(root,mapping,forecasts,'test')
    assert len(calls)==2 and result['credits']==2
    assert len(result['comparisons'])==2 and all(r['comparable'] for r in result['comparisons'])
