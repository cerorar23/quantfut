from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from tennis_engine.state_capture import StateStore,TennisStateCapture,state
from tennis_engine.weighted_elo import WeightedEloModel,EloResult,winner_games_share


def match(**kwargs):
    values=dict(event_id='one',winner_id='a',loser_id='b',score='6-4 6-4',best_of=3)
    values.update(kwargs);return EloResult(**values)


@pytest.mark.parametrize('score,expected',[('6-0 6-0',1.),('7-6 7-6',14/26),('0-6 7-6 7-6',14/32)])
def test_published_welo_game_weight_cases(score,expected):
    assert winner_games_share(score,3)==pytest.approx(expected)


def test_welo_exact_first_update_and_complementary_probabilities():
    m=WeightedEloModel();m.update_block([match()],'2025-01-01')
    delta=250/5**.4 * .5 * 12/20
    assert m.ratings['a']==pytest.approx(1500+delta)
    assert m.ratings['b']==pytest.approx(1500-delta)
    assert m.predict('a','b')+m.predict('b','a')==pytest.approx(1)
    assert m.counts['a']==1


def test_batch_is_order_invariant_and_no_same_period_outcome_enters_other_update():
    rows=[match(),match(event_id='two',winner_id='b',loser_id='c')]
    a=WeightedEloModel();b=WeightedEloModel()
    a.update_block(rows,'2025-01-01');b.update_block(rows[::-1],'2025-01-01')
    assert a.ratings==b.ratings and a.ratings['b']==pytest.approx(1500)
    assert a.counts['b']==2
    with pytest.raises(ValueError):a.update_block([match(event_id='new')],'2025-01-01')
    with pytest.raises(ValueError):a.update_block([match()],'2025-02-01')


@pytest.mark.parametrize('score',['6-4 RET','W/O','6-4 4-6','[10-8]','0-6 0-6','6-4 6-4 6-0'])
def test_welo_rejects_incomplete_or_wrong_orientation_without_mutating(score):
    m=WeightedEloModel()
    with pytest.raises(ValueError):m.update_block([match(),match(event_id='bad',score=score)],'2025-01-01')
    assert not m.ratings and not m.counts and m.last_block is None


def test_adaptive_elo_same_k_unweighted_and_different_player_match_counts():
    m=WeightedEloModel(False);m.update_block([match()],'2025-01-01')
    delta=250/5**.4*.5
    assert m.ratings['a']==pytest.approx(1500+delta)
    prior=dict(m.ratings);p=m.predict('a','c')
    m.update_block([match(event_id='two',loser_id='c')],'2025-01-02')
    assert m.ratings['a']-prior['a']==pytest.approx(250/6**.4*(1-p))


def test_frozen_welo_load_hash_and_model_runner_connection(tmp_path):
    from tennis_engine.load_runner import ModelRunner
    from tennis_engine.benchmark import BenchmarkCase
    m=WeightedEloModel();m.update_block([match()],'2025-01-01')
    path=tmp_path/'model.json';path.write_text(json.dumps(m.artifact()))
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    loaded=WeightedEloModel.load_frozen(path,digest)
    case=BenchmarkCase('target','target','a','b','2026-10-17T12:00:00Z','2026-10-18T12:00:00Z')
    output=ModelRunner(lambda c:loaded.predict(c.player_a,c.player_b)).run([case],[])
    assert output['variants']['current'][0].probability==pytest.approx(m.predict('a','b'))
    with pytest.raises(ValueError):loaded.update_block([match(event_id='new')],'2025-02-01')
    with pytest.raises(ValueError):WeightedEloModel.load_frozen(path,'0'*64)


def fixture(status='1',**kwargs):
    row=dict(event_key=1,first_player_key=10,second_player_key=20,event_status=status,
             event_type_type='Atp Singles',scores=[],statistics=[])
    row.update(kwargs);return row


def ingest(store,path,identity,stamp,rows):
    raw=json.dumps({'success':1,'result':rows}).encode();path.write_bytes(raw)
    receipt=dict(id=identity,method='get_fixtures',requested_at=stamp,received_at=stamp,
                 source_path=str(path.resolve()),sha256=hashlib.sha256(raw).hexdigest())
    return store.ingest(receipt),receipt


def test_state_history_as_of_and_transitions_do_not_invent_actual_times(tmp_path):
    store=StateStore(tmp_path/'store')
    ingest(store,tmp_path/'1.json','1','2026-10-17T12:00:00Z',[fixture()])
    ingest(store,tmp_path/'2.json','2','2026-10-17T12:02:00Z',[fixture('Set 1')])
    ingest(store,tmp_path/'3.json','3','2026-10-17T14:00:00Z',[fixture('Finished')])
    before=store.timeline('api_tennis:1','2026-10-17T13:00:00Z')
    assert before['latest']['state']=='playing' and before['first_seen_terminal_at'] is None
    after=store.timeline('api_tennis:1','2026-10-17T15:00:00Z')
    assert len(after['changes'])==3 and after['first_seen_live_at'].startswith('2026-10-17T12:02')
    assert after['actual_start'] is None and after['actual_end'] is None
    assert after['provider_latency_upper_bound_seconds'] is None
    assert len(store.load_history('2026-10-17T15:00:00Z'))==1


def test_absence_unknown_status_and_retirement_are_preserved(tmp_path):
    store=StateStore(tmp_path/'store')
    ingest(store,tmp_path/'1.json','1','2026-10-17T12:00:00Z',[fixture('Set 1')])
    ingest(store,tmp_path/'2.json','2','2026-10-17T12:02:00Z',[])
    assert store.timeline('api_tennis:1','2026-10-17T15:00:00Z')['latest']['state']=='playing'
    assert state('new provider status')=='unknown' and state('Retired')=='retired'
    assert state('1')=='scheduled_unverified'


def test_ingest_is_idempotent_hash_validated_and_database_append_only(tmp_path):
    store=StateStore(tmp_path/'store');path=tmp_path/'1.json'
    n,receipt=ingest(store,path,'1','2026-10-17T12:00:00Z',[fixture()])
    assert n==1 and store.ingest(receipt)==0
    with pytest.raises(sqlite3.IntegrityError):store.db.execute('DELETE FROM observations')
    store.db.rollback()
    path.write_text('{}')
    with pytest.raises(ValueError):store.ingest(receipt)


def test_conflicting_participants_and_cancelled_corrections_are_visible(tmp_path):
    store=StateStore(tmp_path/'store')
    ingest(store,tmp_path/'1.json','1','2026-10-17T12:00:00Z',[fixture('Finished')])
    ingest(store,tmp_path/'2.json','2','2026-10-17T12:02:00Z',[fixture('Cancelled',first_player_key=30)])
    out=store.timeline('api_tennis:1','2026-10-17T15:00:00Z')
    assert out['participant_conflict'] and out['latest']['state']=='cancelled'


def test_live_correction_invalidates_terminal_load_without_erasing_as_of_history(tmp_path):
    store=StateStore(tmp_path/'store')
    ingest(store,tmp_path/'1.json','1','2026-10-17T12:00:00Z',[fixture('Finished')])
    ingest(store,tmp_path/'2.json','2','2026-10-17T14:00:00Z',[fixture('Set 2')])
    assert len(store.load_history('2026-10-17T13:00:00Z'))==1
    assert store.load_history('2026-10-17T15:00:00Z')==[]


def test_duplicate_events_reject_entire_ingestion(tmp_path):
    store=StateStore(tmp_path/'store')
    with pytest.raises(ValueError):ingest(store,tmp_path/'1.json','1','2026-10-17T12:00:00Z',[fixture(),fixture()])
    assert store.summary('2026-10-17T15:00:00Z')['observations']==0


def test_capture_whitelist_cap_and_secret_redaction(tmp_path):
    class Response:
        status_code=200
        content=json.dumps({'success':1,'result':[],'debug':'sensitivekey'}).encode()
    client=TennisStateCapture(tmp_path/'store','sensitivekey',daily_limit=1,transport=lambda *a,**k:Response())
    with pytest.raises(ValueError):client.capture('get_odds',{'timezone':'UTC'})
    output=client.capture('get_livescore',{'timezone':'UTC'})
    assert output['receipt']['response_redacted']
    assert 'sensitivekey' not in Path(output['receipt']['source_path']).read_text()
    with pytest.raises(ValueError):client.capture('get_livescore',{'timezone':'UTC'})


def test_failed_request_retains_cap_and_does_not_expose_url(tmp_path):
    def failure(*args,**kwargs):raise RuntimeError('https://secret-url/?APIkey=hidden')
    client=TennisStateCapture(tmp_path/'store','hidden',daily_limit=1,transport=failure)
    with pytest.raises(RuntimeError,match='reservation retained') as error:client.capture('get_livescore',{'timezone':'UTC'})
    assert 'hidden' not in str(error.value)
    with pytest.raises(ValueError):client.capture('get_livescore',{'timezone':'UTC'})
