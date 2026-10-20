import copy
import numpy as np
import pandas as pd
import pytest
from tennis_engine.dynamic import DynamicServe,context_terms
from tennis_engine.calibration import fit_calibrator,calibrated
from tennis_engine.calibration import apply_contract
from tennis_engine.context import player_context,weather_features,haversine_km
from tennis_engine.operations import Capture
from tennis_engine.prospective import clv,evaluate_prospective,result_valid
from tennis_engine.shadow import write_immutable
import hashlib
import json
from tennis_engine.official import parse_final


def block():
    rows=[]
    for i in range(30):
        rows.append({'match_id':str(i),'period':'2025-01-01','winner_id':'a','loser_id':'b',
                     'surface':'Hard','w_svpt':60,'w_1stWon':30,'w_2ndWon':12,
                     'l_svpt':60,'l_1stWon':24,'l_2ndWon':10})
    return pd.DataFrame(rows)


def test_dynamic_updates_once_per_period_and_uncertainty_grows_after_inactivity():
    a=DynamicServe('ATP');b=DynamicServe('ATP')
    a.update(block(),'2025-01-01');b.update(block().iloc[::-1],'2025-01-01')
    first=a.predict('a','b','Hard','2025-01-02');later=a.predict('a','b','Hard','2026-01-02')
    assert first['p']==pytest.approx(.7,abs=.03)
    assert first['q']==pytest.approx(34/60,abs=.03)
    assert first==b.predict('a','b','Hard','2025-01-02')
    assert later['logit_variances_diagonal'][0]>first['logit_variances_diagonal'][0]
    assert later['p']==first['p']
    with pytest.raises(ValueError):a.update(block(),'2025-01-01')
    with pytest.raises(ValueError):a.predict('a','b','Hard','2024-01-01')


def test_context_missingness_is_not_assumed_outdoor_or_zero_age():
    missing=context_terms({});outdoor=context_terms({'server_age':25,'returner_age':25,'server_hand':'R','returner_hand':'R','indoor':False})
    assert missing['context|indoor_missing']==1
    assert 'context|indoor_missing' not in outdoor
    assert 'context|server_age_missing' not in outdoor


def test_calibration_is_fitted_on_binary_observations_and_monotone():
    p=np.linspace(.05,.95,1000);rng=np.random.default_rng(9)
    y=rng.binomial(1,.15+.7*p)
    params=fit_calibrator(y,p)
    result=calibrated(p,params)
    assert np.all(np.diff(result)>0) and np.all((result>0)&(result<1))
    assert params['slope']<1
    with pytest.raises(ValueError):fit_calibrator([1,0],[.5,.5])


def test_exact_contract_calibration_keeps_complements_and_rejects_other_lines():
    profile={'intercept':.2,'slope':.8}
    profiles={'over_22_5_games':profile}
    over=apply_contract({'win':.6,'push':0,'loss':.4},'games_total',22.5,'over',profiles)
    under=apply_contract({'win':.4,'push':0,'loss':.6},'games_total',22.5,'under',profiles)
    assert over['experimental_calibrated_win']+under['experimental_calibrated_win']==pytest.approx(1)
    assert apply_contract({'win':.6,'push':0,'loss':.4},'games_total',23.5,'over',profiles) is None
    assert apply_contract({'win':.5,'push':.1,'loss':.4},'games_total',22.5,'over',profiles) is None
    symmetric=fit_calibrator(np.tile([0,1],100),np.linspace(.1,.9,200),symmetric=True)
    assert symmetric['intercept']==0
    assert calibrated(.7,symmetric)+calibrated(.3,symmetric)==pytest.approx(1)


def receipt(tmp_path,content=b'observed source'):
    path=tmp_path/'source.json';path.write_bytes(content)
    return {'source_path':str(path),'source_sha256':hashlib.sha256(content).hexdigest()}


def test_daily_workload_uses_only_actual_available_times_and_does_not_assume_completeness(tmp_path):
    source=receipt(tmp_path)
    row={**source,'player_ids':['a','b'],'actual_start':'2026-10-16T10:00:00Z',
         'actual_end':'2026-10-16T12:00:00Z','received_at':'2026-10-16T12:05:00Z',
         'date_precision':'actual_utc','status':'completed','minutes':120,'sets_played':3,
         'venue':{'lat':0.,'lon':0.,'surface':'Clay'}}
    bad={**row,'date_precision':'tournament_week','minutes':900}
    result=player_context('a','2026-10-18T10:00:00Z','2026-10-18T08:00:00Z',[row,bad],
                          {'lat':0.,'lon':1.,'surface':'Hard'})
    assert result['minutes_7d']==120 and result['sets_7d']==3
    assert result['rest_hours']==46 and result['excluded_uncertain_matches']==1
    assert result['travel_km'] is None and result['surface_changed']
    assert result['travel_status']=='requires_reviewed_intertournament_transition'
    assert result['history_complete'] is False
    empty=player_context('new','2026-10-18T10:00:00Z','2026-10-18T08:00:00Z',[row])
    assert empty['minutes_7d'] is None


def test_weather_cannot_use_reanalysis_or_a_future_forecast(tmp_path):
    source=receipt(tmp_path)
    forecast={**source,'kind':'forecast','issued_at':'2026-10-18T06:00:00Z','received_at':'2026-10-18T06:01:00Z',
              'hourly':[{'time':'2026-10-18T10:00:00Z','temperature_c':25,'humidity_pct':50,'wind_kmh':12}]}
    assert weather_features(forecast,'2026-10-18T10:00:00Z','2026-10-18T08:00:00Z',False)['status']=='prior_forecast'
    assert weather_features({**forecast,'kind':'reanalysis'},'2026-10-18T10:00:00Z','2026-10-18T08:00:00Z',False)['status']=='missing_prior_forecast'
    assert weather_features(forecast,'2026-10-18T10:00:00Z','2026-10-18T08:00:00Z',None)['status']=='unknown_roof_or_indoor'


def test_paid_history_reserves_ten_credits_per_region_market_and_rejects_future(tmp_path):
    calls=[]
    def transport(path,params):
        calls.append(path)
        return b'[]',{'x-requests-last':'0' if path=='sports' else '30','x-requests-remaining':'100'}
    client=Capture(tmp_path,'secret',cap=30,account_reserve=50,transport=transport)
    client.request('sports')
    args={'date':'2020-01-01T00:00:00Z','bookmakers':'pinnacle','markets':'h2h,spreads,totals'}
    _,r=client.request('historical/sports/tennis_atp_test/odds',args)
    assert r['reserved_credits']==30
    assert client.budget_report(r['requested_at'][:7])['confirmed_actual_credits']==30
    with pytest.raises(ValueError):client.request('historical/sports/tennis_atp_test/odds',args)
    with pytest.raises(ValueError):client.request('sports/tennis_atp_test/odds',args)
    with pytest.raises(ValueError):client.request('historical/sports/tennis_atp_test/odds',{**args,'date':'2100-01-01T00:00:00Z'})
    assert len(calls)==2


def test_clv_requires_same_line_rules_and_pre_start_fresh_close():
    entry={'event_id':'e','sport_key':'tennis_atp_test','market':'totals','selection':'Over','line':22.5,
           'settlement_contract':'completed_period','captured_at':'2026-10-18T08:00:00Z','decimal_odds':2.1}
    closing={**entry,'captured_at':'2026-10-18T09:55:00Z','last_update':'2026-10-18T09:54:00Z',
             'decimal_odds':1.9,'de_vig_probability_no_push':.52}
    result=clv(entry,closing,'2026-10-18T10:00:00Z')
    assert result['price_ratio_clv']==pytest.approx(2.1/1.9-1)
    assert clv(entry,{**closing,'line':23.5},'2026-10-18T10:00:00Z')['status']=='incomparable_contract_or_line'
    assert clv(entry,{**closing,'captured_at':'2026-10-18T10:01:00Z'},'2026-10-18T10:00:00Z')['status']=='not_verified_close'


def test_prospective_evaluation_deduplicates_prepost_and_keeps_no_data_unavailable(tmp_path):
    source=receipt(tmp_path)
    event={'id':'e','sport_key':'tennis_atp_test','home_team':'A','away_team':'B','commence_time':'2026-10-18T10:00:00Z'}
    fixture={**source,'event_id':'e','sport_key':event['sport_key'],'status':'scheduled',
             'observed_at':'2026-10-18T07:59:00Z','participants':['A','B'],'participants_verified':True,
             'provider_time_reconciled':True,'provider_commence_time':event['commence_time'],
             'source_url':'https://www.atptour.com/schedule','evidence':'reviewed observation'}
    record={'observed_at':'2026-10-18T08:00:00Z','prediction_sealed_at':'2026-10-18T08:00:01Z',
            'events':[{'event':event,'circuit':'ATP','capture_phase':'t_minus_120',
                       'identities':{'identities_verified':True},'fixture_receipt':fixture,
                       'prediction':{'winner_A':.6,'markov_A':.58,'surface_elo_A':.62}}]}
    write_immutable(tmp_path,record);write_immutable(tmp_path,record)
    result={**source,'event_id':'e','sport_key':event['sport_key'],'home_team':'A','away_team':'B',
            'actual_start':'2026-10-18T10:00:00Z','actual_end':'2026-10-18T12:00:00Z',
            'received_at':'2026-10-18T12:05:00Z','status':'completed','official_winner':'A','score_A_B':'6-4 6-4','best_of':3}
    assert result_valid(result) and not result_valid({**result,'official_winner':'B'})
    results=tmp_path/'results.json';results.write_text(json.dumps([result]))
    report=evaluate_prospective(tmp_path,results,tmp_path/'report.json')
    assert report['distinct_scored_events']==report['scored_event_windows']==1
    results.write_text('[]')
    empty=evaluate_prospective(tmp_path,results,tmp_path/'empty.json')
    assert empty['metrics'] is None
    results.write_text(json.dumps([result]))
    protocol={'created_at':'2026-10-18T07:00:00Z','evaluation_start':'2026-10-18T00:00:00Z',
              'evaluation_end':'2027-01-01T00:00:00Z','required_artifact_hashes':{'ATP':['not-the-frozen-model']}}
    protocol_path=tmp_path/'protocol.json';protocol_path.write_text(json.dumps(protocol))
    rejected=evaluate_prospective(tmp_path,results,tmp_path/'rejected.json',protocol_path)
    assert rejected['metrics'] is None and rejected['rejections']['different_model_or_calibration_version']==2


def test_reviewed_official_pdf_templates_bind_pair_date_and_not_before():
    event={'sport_key':'tennis_atp_shanghai_masters','home_team':'Alejandro Davidovich Fokina',
           'away_team':'Rafael Jodar','commence_time':'2026-10-18T08:30:00Z'}
    text='Rolex Shanghai Masters Hard ORDER OF PLAY - SUNDAY, OCTOBER 18, 2026 Not Before 16:30 [25] Alejandro DAVIDOVICH FOKINA (ESP) vs [12] Rafael JODAR (ESP)'
    parsed=parse_final(text,event)
    assert parsed['provider_time_reconciled'] and parsed['official_not_before']=='2026-10-18T08:30:00+00:00'
    with pytest.raises(ValueError):parse_final(text.replace(' vs ',' '),event)
    with pytest.raises(ValueError):parse_final(text.replace('2026','2025'),event)
    with pytest.raises(ValueError):parse_final(text+' Not Before 18:00',event)
    wta={'sport_key':'tennis_wta_wuhan_open','home_team':'Maja Chwalinska','away_team':'Sonay Kartal','commence_time':'2026-10-18T10:30:00Z'}
    wtext='Hard ORDER OF PLAY - SUNDAY, 18 OCTOBER 2026 Not before 6:30 PM [16] Maja CHWALINSKA POL vs Sonay KARTAL GBR'
    assert parse_final(wtext,wta)['provider_time_reconciled']
