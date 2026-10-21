import json
import pandas as pd
import pytest
from tennis_engine.identities import Registry,reconcile
from tennis_engine.operations import Capture,coverage,quote_gate,utc,select_books
from tennis_engine.settlement import settle,ledger,PINNACLE_RULE
from tennis_engine.research import fit_pool,pooled,calibration_bins,months


def test_identity_similarity_never_assigns_ambiguous_player(tmp_path):
    frame=pd.DataFrame({'circuit':['ATP','ATP'],'winner_id':['atp:1','atp:2'],
                        'winner_name':['Alex Smith','Adam Smith'],'loser_id':['atp:3']*2,'loser_name':['Other Player']*2})
    registry=Registry(tmp_path/'ids.sqlite');registry.seed(frame)
    assert registry.candidates('ATP','A. Smith')
    assert registry.resolve('the_odds_api','ATP','name:A. Smith') is None
    registry.bind('the_odds_api','ATP','name:A. Smith','atp:1','Tournament draw ID links','reviewer')
    assert registry.resolve('the_odds_api','ATP','name:A. Smith')=='atp:1'
    assert registry.resolve('the_odds_api','WTA','name:A. Smith') is None
    with pytest.raises(ValueError): registry.bind('the_odds_api','ATP','name:A. Smith','atp:2','conflict','reviewer')
    with pytest.raises(ValueError): registry.bind('the_odds_api','ATP','name:Other','atp:3','','reviewer')


def event():
    return {'id':'event1','sport_key':'tennis_atp_test','home_team':'A','away_team':'B','commence_time':'2026-10-17T14:00:00Z'}


def test_time_gate_does_not_treat_commence_as_verified_start():
    book={'last_update':'2026-10-17T11:58:00Z'};received='2026-10-17T11:59:00Z';decision='2026-10-17T12:00:00Z'
    fixture={'event_id':'event1','status':'scheduled','observed_at':received,'evidence':'official schedule/status receipt'}
    assert not quote_gate(event(),book,{},received,decision,True)['eligible']
    assert quote_gate(event(),book,{},received,decision,True,fixture)['eligible']
    assert not quote_gate(event(),book,{},received,decision,False,fixture)['eligible']
    assert not quote_gate(event(),book,{},'2026-10-17T12:01:00Z',decision,True,fixture)['eligible']
    assert not quote_gate(event(),book,{'last_update':'2026-10-17T10:00:00Z'},received,decision,True,fixture)['eligible']
    fixture['status']='in_play'
    assert not quote_gate(event(),book,{},received,decision,True,fixture)['eligible']
    assert utc('2026-10-17T06:00:00-06:00')==utc(decision)
    with pytest.raises(ValueError): utc('2026-10-17T12:00:00')


def test_coverage_never_compares_different_lines():
    e=event();e['bookmakers']=[{'key':'one','markets':[{'key':'totals','outcomes':[{'name':'Over','point':22.5,'price':1.9}]}]},
                             {'key':'two','markets':[{'key':'totals','outcomes':[{'name':'Over','point':23.5,'price':2.1},{'name':'Over','point':22.5,'price':2.0}]}]}]
    report=coverage([e]); assert len(report['best_observed_prices'])==2
    assert all(not row['executable'] for row in report['best_observed_prices'])
    assert next(row for row in report['best_observed_prices'] if row['line']==22.5)['decimal_odds']==2


def test_book_selection_preserves_market_breadth_without_requesting_lay():
    inventory={'bookmakers':[{'key':'wide','markets':[{'key':m} for m in ('h2h','spreads','totals')]},
                            {'key':'sets','markets':[{'key':'h2h_s1'},{'key':'h2h_lay'}]},
                            {'key':'duplicate','markets':[{'key':'h2h'}]}]}
    books,markets=select_books(inventory,2)
    assert books==['wide','sets'] and set(markets)=={'h2h','spreads','totals','h2h_s1'}


def test_capture_budget_receipts_and_no_secret(tmp_path):
    requests=[]
    def transport(path,params):
        requests.append(path)
        return b'[]',{'x-requests-last':'0' if path=='sports' else '1','x-requests-remaining':'99','x-requests-used':'1'}
    client=Capture(tmp_path,'secret-not-persisted',cap=1,account_reserve=90,transport=transport)
    client.request('sports')
    client.request('sports/tennis_atp_test/odds',{'bookmakers':'pinnacle,betway','markets':'h2h'})
    with pytest.raises(ValueError): client.request('sports/tennis_atp_test/odds',{'bookmakers':'pinnacle','markets':'h2h'})
    assert len(requests)==2
    for path in (tmp_path/'snapshots').rglob('*.json'): assert 'secret-not-persisted' not in path.read_text()
    assert len(list((tmp_path/'snapshots').iterdir()))==2
    other=Capture(tmp_path,'secret',cap=1,account_reserve=90,transport=transport);other.request('sports')
    with pytest.raises(ValueError): other.request('sports/tennis_atp_test/odds',{'regions':'eu','markets':'h2h'})


def test_failure_retains_reservation_and_quota_missing_blocks(tmp_path):
    def transport(path,params):
        if path=='sports': return b'[]',{'x-requests-last':'0','x-requests-remaining':'10'}
        raise RuntimeError('network failure')
    client=Capture(tmp_path,'key',cap=1,account_reserve=0,transport=transport);client.request('sports')
    with pytest.raises(RuntimeError): client.request('sports/tennis_wta_test/odds',{'regions':'eu','markets':'h2h'})
    with pytest.raises(ValueError): client.request('sports/tennis_wta_test/odds',{'regions':'eu','markets':'h2h'})


def test_missing_quota_headers_and_extra_charge_stop_collection(tmp_path):
    client=Capture(tmp_path/'missing','key',transport=lambda p,a:(b'[]',{}))
    with pytest.raises(ValueError): client.request('sports')
    assert client.remaining is None
    def transport(path,params):
        return b'[]',{'x-requests-last':'0' if path=='sports' else '2','x-requests-remaining':'90'}
    client=Capture(tmp_path/'excess','key',cap=3,account_reserve=0,transport=transport)
    client.request('sports')
    with pytest.raises(ValueError): client.request('sports/tennis_atp_test/odds',{'regions':'eu','markets':'h2h'})
    assert client.remaining is None
    assert client.db.execute('SELECT sum(cost) FROM charges').fetchone()[0]==2


def bet(**changes):
    return dict({'bet_id':'1','bookmaker':'pinnacle','rule_id':PINNACLE_RULE,'placed_at':'2026-10-16T12:00:00Z',
                 'stake':100,'decimal_odds':2.1,'market':'h2h','selection':'A','match_status':'retired',
                 'completed_sets':1,'official_winner':'B','first_set_winner':'A'},**changes)


@pytest.mark.parametrize('sets,status,profit',[(0,'void',0),(1,'loss',-100),(2,'loss',-100)])
def test_retirement_is_settled_not_excluded(sets,status,profit):
    result=settle(bet(completed_sets=sets))
    assert result['status']==status and result['profit']==profit


def test_first_set_and_unknown_rules_have_distinct_financial_results():
    assert settle(bet(market='first_set'))['profit']==pytest.approx(110)
    assert settle(bet(market='other_market'))['status']=='pending'
    assert settle(bet(bookmaker='bet365'))['status']=='pending'
    assert settle(bet(placed_at='2025-01-01T00:00:00Z'))['status']=='pending'
    report=ledger([bet(),bet(bet_id='2',bookmaker='bet365')])
    assert report['count']==2 and report['pending']==1 and report['complete_roi_on_action_stake'] is None
    assert report['settled_profit']==-100 and not report['retirements_excluded']
    with pytest.raises(ValueError): ledger([bet(),bet()])
    assert ledger([bet(completed_sets=0)])['void']==1


def test_full_match_totals_and_spreads_keep_push_distinct_from_void():
    base=bet(market='totals',selection='over',match_status='completed',completed_sets=2,score_A_B='6-4 6-4',line=20)
    assert settle(base)['status']=='push'
    assert ledger([base])['settled_action_stake']==100
    assert settle({**base,'line':19.5})['status']=='win'
    assert settle({**base,'market':'spreads','selection':'B','line':4})['status']=='push'
    assert settle({**base,'match_status':'retired'})['status']=='void'
    with pytest.raises(ValueError): settle({**base,'line':20.25})


def test_pool_symmetry_and_calibration_bins():
    import numpy as np
    rng=np.random.default_rng(7)
    p=np.linspace(.1,.9,500)
    frame=pd.DataFrame({'period':['2025-01-01']*500,'model_probability':p,
                        'surface_elo_probability':p,'y':rng.binomial(1,p)})
    parameters=fit_pool(frame); flipped=frame.copy()
    flipped.model_probability=1-frame.model_probability;flipped.surface_elo_probability=1-frame.surface_elo_probability
    assert np.allclose(pooled(frame,parameters)+pooled(flipped,parameters),1)
    bins=calibration_bins([0,1,1],[0,.6,1]);assert sum(b['n'] for b in bins)==3
    assert len(months('2026-07','2026-09'))==3
    with pytest.raises(ValueError): months('2026-09','2026-07')
