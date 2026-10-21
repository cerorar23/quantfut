import json
from dataclasses import asdict
import pytest
from tennis_engine.scoring import Rules,set_winner
from tennis_engine.settlement import PINNACLE_RULE
from tennis_markets_v2 import Contract,MarketEngine
from tennis_markets_v2.offers import API_KEYS,from_api,price_offers
from tennis_markets_v2.settlement import settle_contract
from tennis_markets_v2.evaluation import evaluate_rows

@pytest.fixture(scope='module')
def engine():return MarketEngine(.65,.62)

def test_full_board_is_mass_conserving_and_nonexecutable(engine):
 board=engine.standard_board()
 assert len(board)==78 and len({r['contract']['kind'] for r in board})==10
 assert all(abs(sum(r[k] for k in ('win','push','loss'))-1)<1e-10 for r in board)
 assert all(not r['executable'] and not r['production_approved'] for r in board)
 assert sum(engine.probabilities(Contract('correct_score','exact',score=s))['win'] for s in ((2,0),(2,1),(0,2),(1,2)))==pytest.approx(1.)

@pytest.mark.parametrize('number',[1,2,3])
def test_numbered_set_matches_independent_existing_winner_kernel(engine,number):
 actual=engine.probabilities(Contract('set_winner','A',set_number=number))
 expected=set_winner(.65,.62,number)
 assert actual==pytest.approx(expected,abs=1e-10)

@pytest.mark.parametrize('kind,line,number',[('games_total',22,None),('games_handicap',-3,None),('sets_total',2,None),('sets_handicap',-1,None),('set_games_total',10,2),('set_games_handicap',-2,2)])
def test_complementary_lines_keep_push_probability(engine,kind,line,number):
 total='total' in kind
 a=engine.probabilities(Contract(kind,'over' if total else 'A',line,number))
 b=engine.probabilities(Contract(kind,'under' if total else 'B',line if total else -line,number))
 assert a['win']==pytest.approx(b['loss']) and a['push']==pytest.approx(b['push'])

def test_reversal_symmetry_for_second_set_game_lines(engine):
 reversed_model=MarketEngine(.62,.65)
 a=engine.probabilities(Contract('set_games_handicap','A',-1.5,2))
 b=reversed_model.probabilities(Contract('set_games_handicap','B',-1.5,2))
 assert a==pytest.approx(b,abs=1e-10)

def test_best_of_five_and_unplayed_period_contract():
 model=MarketEngine(.65,.62,Rules(5,deciding_tiebreak=10))
 assert model.probabilities(Contract('set_winner','A',set_number=5))['push']>0
 assert model.probabilities(Contract('correct_score','exact',score=[3,2]))['win']>0

@pytest.mark.parametrize('contract',[Contract('games_total','over',22.25),Contract('sets_total','over',True),Contract('set_winner','A',set_number=True),Contract('correct_score','exact',score=(3,0)),Contract('winner','A',line=1),Contract('aces','over',8.5)])
def test_unsupported_contracts_are_rejected(engine,contract):
 with pytest.raises(ValueError):engine.quote(contract)

event=dict(id='e',sport_key='tennis_atp_example',home_team='Player A',away_team='Player B',commence_time='2026-10-20T10:00:00Z')

@pytest.mark.parametrize('key',sorted(API_KEYS))
def test_every_documented_key_has_explicit_mapping(engine,key):
 total=key in ('totals','alternate_totals','alternate_set_totals','totals_s1','alternate_totals_s1','alternate_totals_s2')
 winner=key.startswith('h2h')
 outcome=dict(name='Over' if total else 'Player A',price=1.9)
 if not winner:outcome['point']=2.5 if key=='alternate_set_totals' else 10.5 if '_s1' in key or '_s2' in key else -1.5 if 'spread' in key else 22.5
 assert engine.quote(from_api(key,outcome,event))['win']>=0

def quotes(markets):return dict(event,bookmakers=[dict(key='pinnacle',last_update='2026-10-20T09:00:00Z',markets=markets)])
def test_real_lines_de_vig_only_complementary_pairs_and_staleness(engine):
 q=quotes([dict(key='alternate_spreads',outcomes=[dict(name='Player A',point=-3.5,price=2.1),dict(name='Player B',point=3.5,price=1.8)]),dict(key='totals',outcomes=[dict(name='Over',point=22.5,price=1.9)])])
 rows=price_offers(q,engine,'2026-10-20T09:00:01Z','2026-10-20T09:01:00Z')
 assert rows[0]['quote_fresh'] and rows[0]['best_fresh_observed_price']
 assert rows[0]['de_vig_probability_no_push']+rows[1]['de_vig_probability_no_push']==pytest.approx(1)
 assert 'de_vig_probability_no_push' not in rows[2]
 stale=price_offers(q,engine,'2026-10-20T09:00:01Z','2026-10-20T09:30:00Z')
 assert all(not r['quote_fresh'] and not r['best_fresh_observed_price'] for r in stale)

def test_unknown_provider_props_remain_visible(engine):
 q=quotes([dict(key='player_aces',outcomes=[dict(name='Over',point=8.5,price=1.9)])])
 rows=price_offers(q,engine,'2026-10-20T09:00:01Z','2026-10-20T09:01:00Z')
 assert len(rows)==1 and rows[0]['status']=='unmapped_or_invalid_offer'

def bet(c):return dict(bet_id='b1',contract=json.loads(json.dumps(asdict(c))),stake=1.,decimal_odds=2.,bookmaker='pinnacle',rule_id=PINNACLE_RULE,placed_at='2026-10-19T10:00:00Z')
def result(**changes):return dict(dict(status='completed',best_of=3,completed_sets=2,score_A_B='7-6 6-4',official_winner='A'),**changes)

@pytest.mark.parametrize('c,status',[ (Contract('winner','A'),'win'),(Contract('set_winner','B',set_number=2),'loss'),(Contract('games_total','over',23),'push'),(Contract('sets_total','under',2.5),'win'),(Contract('sets_handicap','A',-1.5),'win'),(Contract('correct_score','exact',score=(2,0)),'win'),(Contract('tiebreak','yes'),'win'),(Contract('set_games_total','over',13,1),'push'),(Contract('set_games_handicap','A',-2,2),'push')])
def test_completed_settlement_contracts(c,status):
 assert settle_contract(bet(c),result())['status']==status

def test_retirement_set_stands_full_totals_void_and_unknown_props_pending():
 retired=result(status='retired',completed_sets=1,score_A_B='7-6 0-2',official_winner='B')
 assert settle_contract(bet(Contract('set_winner','A',set_number=1)),retired)['status']=='win'
 assert settle_contract(bet(Contract('set_winner','A',set_number=2)),retired)['status']=='void'
 assert settle_contract(bet(Contract('winner','B')),retired)['status']=='win'
 assert settle_contract(bet(Contract('sets_total','over',2.5)),retired)['status']=='void'
 assert settle_contract(bet(Contract('tiebreak','yes')),retired)['status']=='pending'

def test_invalid_winner_score_and_unknown_book_stay_pending():
 c=bet(Contract('winner','A'))
 assert settle_contract(c,result(official_winner='B'))['status']=='pending'
 c['bookmaker']='unknown'
 assert settle_contract(c,result())['status']=='pending'

def test_evaluator_keeps_void_push_and_missing_rules_in_coverage(engine):
 c=Contract('games_total','over',23);row=dict(circuit='ATP',bet=bet(c),result=result(),probabilities=engine.probabilities(c))
 report=evaluate_rows([row]);assert report['groups'][0]['push']==1 and report['groups'][0]['metric_coverage']==0
 assert not report['financial_evidence_verified']
 with pytest.raises(ValueError):evaluate_rows([row,row])
