import copy
import hashlib
import json
import pytest
from tennis_engine.operations import Capture,quote_gate
from tennis_engine.shadow import run_shadow,verify_record,metadata_gate,capture_phase
from tennis_engine.markets import compare_offered


EVENT={'id':'e1','sport_key':'tennis_atp_test','home_team':'A','away_team':'B','commence_time':'2026-10-18T10:00:00Z'}
PREDICTION={'winner_A':.6,'winner_B':.4,'serve':{'p':.65,'q':.61},'best_of':3,'deciding_tiebreak':7,'cutoff':'2026-10-16'}
META={'surface':'Hard','best_of':3,'deciding_tiebreak':7,'metadata_verified':True,
      'source_url':'https://official.example','valid_from':'2026-10-01','valid_to':'2026-10-31'}


def test_lines_pushes_de_vig_and_unsupported_market_remain_distinct():
    event={**EVENT,'bookmakers':[{'key':'book','markets':[
        {'key':'h2h','outcomes':[{'name':'A','price':1.8},{'name':'B','price':2.2}]},
        {'key':'alternate_totals','outcomes':[{'name':'Over','point':20,'price':2.},
           {'name':'Under','point':20,'price':1.9},{'name':'Over','point':21.5,'price':2.1}]},
        {'key':'h2h_s4','outcomes':[{'name':'A','price':1.9}]}]}]}
    rows=compare_offered(event,PREDICTION)
    over=next(r for r in rows if r['selection']=='Over' and r['line']==20)
    assert over['push']>0
    assert over['conditional_expected_return']==pytest.approx(over['win']-over['loss'])
    assert over['model_probability_no_push']==pytest.approx(over['win']/(1-over['push']))
    unpaired=next(r for r in rows if r['line']==21.5)
    assert 'de_vig_probability_no_push' not in unpaired
    assert rows[-1]['status']=='unsupported_market'
    assert not any(r['executable'] or r['best_fresh_price'] for r in rows)


def test_expired_edition_and_invalid_window_fail_closed():
    assert metadata_gate(EVENT,{**META,'valid_to':'2026-10-17'})==['tournament_edition_expired']
    with pytest.raises(ValueError):capture_phase(EVENT['commence_time'],EVENT['commence_time'],120)
    assert not quote_gate(EVENT,{}, {},'bad','bad',True)['eligible']


def test_numbered_sets_preserve_continuity_and_unplayed_mass():
    from tennis_engine.scoring import set_winner,match_distribution,market,Rules
    dist=match_distribution(.66,.60)
    assert set_winner(.66,.60,1)['win']==pytest.approx(market(dist,'first_set',selection='A')['win'])
    second=set_winner(.66,.60,2)
    assert second['push']==0
    assert second['win']==pytest.approx(set_winner(.60,.66,2,selection='B')['win'])
    third=set_winner(.66,.60,3)
    assert third['push']==pytest.approx(sum(p for (sa,sb,*_),p in dist.items() if sa+sb==2))
    assert sum(third.values())==pytest.approx(1)


def test_deduplicated_source_cannot_claim_earlier_receipt(tmp_path):
    import pandas as pd
    from tennis_engine.normalize import normalize
    from tennis_engine.ingest import save_json
    row={'tourney_id':'2026-a','tourney_date':'20260101','tourney_level':'A','round':'F',
         'winner_id':'1','loser_id':'2','winner_name':'A','loser_name':'B','surface':'Hard','score':'6-4 6-4','best_of':3}
    folder=tmp_path/'tml/originals';folder.mkdir(parents=True)
    receipts=[]
    for filename,received in [('2026.csv','2026-01-02T00:00:00Z'),('ongoing_tourneys.csv','2026-01-03T00:00:00Z')]:
        path=folder/filename;pd.DataFrame([row]).to_csv(path,index=False)
        receipts.append({'source':'tml','name':filename,'status':'ok','received_at':received,
                         'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    save_json(tmp_path/'download_manifest.json',{'files':receipts})
    normalize(tmp_path);frame=pd.read_parquet(tmp_path/'canonical/matches.parquet')
    assert len(frame)==1 and frame.iloc[0].received_at=='2026-01-03T00:00:00Z'
    assert len(json.loads(frame.iloc[0].source_lineage))==2


def scenario(tmp_path,monkeypatch,missing_metadata=False,fail_odds=False,flip_sides=False):
    import tennis_engine.shadow as shadow
    clock=['2026-10-18T08:00:00Z']
    monkeypatch.setattr(shadow,'now',lambda:clock[0])
    source=tmp_path/'official.json';source.write_bytes(b'scheduled A B')
    fixture={'event_id':'e1','status':'scheduled','observed_at':'2026-10-18T07:59:00Z',
             'source_url':'https://www.atptour.com/schedule','evidence':'reviewed source',
             'participants_verified':True,'provider_time_reconciled':True,
             'participants':['A','B'],'sport_key':EVENT['sport_key'],
             'provider_commence_time':EVENT['commence_time'],'source_path':str(source),
             'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
    requested=[]
    def transport(path,params):
        requested.append(path)
        if path=='sports':data=[{'group':'Tennis','key':EVENT['sport_key']}];cost=0
        elif path.endswith('/events'):data=[EVENT];cost=0
        elif path.endswith('/markets'):
            data={'id':'e1','bookmakers':[{'key':'book','markets':[{'key':'h2h'}]}]};cost=1
        else:
            # Assert forecast exists on disk BEFORE the transport sees paid odds.
            snapshots=list((tmp_path/'shadow').rglob('record.json'))
            assert snapshots and verify_record(snapshots[0])['events'][0]['prediction']==PREDICTION
            if fail_odds: raise RuntimeError('simulated failure')
            data={**EVENT,'bookmakers':[{'key':'book','last_update':'2026-10-18T08:00:01Z',
                'markets':[{'key':'h2h','outcomes':[{'name':'A','price':1.9},{'name':'B','price':2.}]}]}]}
            if flip_sides:data.update(home_team='B',away_team='A')
            cost=1
        return json.dumps(data).encode(),{'x-requests-last':str(cost),'x-requests-remaining':'100'}
    class Client(Capture):
        def __init__(self,*args):super().__init__(*args,transport=transport,clock=lambda:clock[0])
        def request(self,*args,**kwargs):
            data,receipt=super().request(*args,**kwargs)
            if args[0].endswith('/odds'):
                clock[0]='2026-10-18T08:00:03Z';receipt['received_at']='2026-10-18T08:00:02Z'
            return data,receipt
    def builder(*args):
        return {'observed_at':clock[0],'events':[{'event':EVENT,'prediction':PREDICTION,
                'identities':{'identities_verified':True},'tournament_metadata':None if missing_metadata else META,
                'capture_blockers':[],'fixture_receipt':fixture}]}
    def run():
        return run_shadow(tmp_path,tmp_path,tmp_path,tmp_path,tmp_path/'ids',tmp_path/'config','secret',
                          20,0,'eu',capture_odds=True,client_factory=Client,plan_builder=builder)
    return run,requested


def test_shadow_paid_path_uses_post_receipt_time_and_preseals(tmp_path,monkeypatch):
    run,requests=scenario(tmp_path,monkeypatch)
    result=run();record=verify_record(result['record_path'])
    assert result['paid_odds_captures']==1
    assert record['odds'][0]['release_gates'][0]['data_eligible']
    assert record['budget']['confirmed_actual_credits']==2
    assert record['odds'][0]['market_comparison'][0]['executable'] is False
    paid=len([p for p in requests if p.endswith(('/markets','/odds'))])
    result2=run()
    assert result2['paid_odds_captures']==0
    assert len([p for p in requests if p.endswith(('/markets','/odds'))])==paid


def test_missing_metadata_never_spends_even_if_other_gates_pass(tmp_path,monkeypatch):
    run,requests=scenario(tmp_path,monkeypatch,missing_metadata=True)
    assert run()['paid_odds_captures']==0
    assert not any(p.endswith(('/markets','/odds')) for p in requests)


@pytest.mark.parametrize('mode',['failure','swap'])
def test_partial_failure_or_swapped_players_preserves_forecast_and_blocks_retry(tmp_path,monkeypatch,mode):
    run,requests=scenario(tmp_path,monkeypatch,fail_odds=mode=='failure',flip_sides=mode=='swap')
    result=run();record=verify_record(result['record_path'])
    assert result['capture_errors']==1 and result['paid_odds_captures']==0
    assert record['prequote_record'] and record['events'][0]['prediction']==PREDICTION
    count=len(requests);run()
    assert len(requests)==count+2  # free sports and calendar only
