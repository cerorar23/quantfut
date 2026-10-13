import hashlib
import json

import pytest

from qf.ingest.sofascore_history import normalize_bundle, stat_pair
from qf.ingest.fotmob_import import Matcher


def example():
    def team(tid,name):
        return {'id':tid,'name':name,'sport':{'id':1},'gender':'M','national':False}
    def item(h,a):
        return {'key':'expectedGoals','homeValue':h,'awayValue':a}
    def players(tid,start):
        return [{'teamId':tid,'player':{'id':start+i,'name':str(start+i)},
                 'substitute':False,'statistics':{'minutesPlayed':90 if i else 0}}
                for i in range(11)]
    return {'event':{'id':123,'startTimestamp':1767268800,'status':{'type':'finished','code':100},
             'homeTeam':team(10,'A'),'awayTeam':team(20,'B'),
             'homeScore':{'normaltime':2,'current':2},'awayScore':{'normaltime':1,'current':1},
             'tournament':{'uniqueTournament':{'id':18},'category':{'alpha2':'EN'}},'season':{'year':'25/26'}},
            'statistics':{'statistics':[{'period':'ALL','groups':[{'statisticsItems':[item(1.23,0),item(1.23,0)]}]},
                {'period':'1ST','groups':[{'statisticsItems':[item(.2,0)]}]}]},
            'lineups':{'confirmed':True,'home':{'players':players(10,1)},
                'away':{'players':players(20,20),'missingPlayers':[{'player':{'id':40,'name':'Missing'},'type':'injured'}]}}}


def normalize(data,**metadata):
    raw=json.dumps(data).encode()
    meta={'sha256':hashlib.sha256(raw).hexdigest(),'captured_at':'2026-10-13T12:00:00Z',**metadata}
    return normalize_bundle('gb.championship',raw,meta)


def test_all_period_zero_and_player_namespace_are_preserved():
    row=normalize(example())
    assert row['home_xg']==1.23 and row['away_xg']==0
    assert row['provider']=='sofascore' and row['source_match_id']=='123'
    assert len(row['players'])==22 and row['players'][0]['minutes']==0
    assert all(l['complete'] for l in row['lineups'])
    assert row['absences'][0]['source_player_id']==40


def test_missing_xg_and_minutes_are_not_zero():
    p=example();p['statistics']=None
    del p['lineups']['home']['players'][0]['statistics']['minutesPlayed']
    p['lineups']['home']['players'][0]['statistics']['rating']=6.5
    row=normalize(p)
    assert row['home_xg'] is None and row['away_xg'] is None
    assert row['players'][0]['minutes'] is None


def test_duplicate_disagreement_rejected():
    p=example();p['statistics']['statistics'][0]['groups'][0]['statisticsItems'][1]['homeValue']=2.3
    with pytest.raises(ValueError,match='conflicting_duplicate_stat'):
        normalize(p)


def test_extra_time_never_uses_120_minute_xg_or_penalties():
    p=example();p['event']['status']['code']=110
    p['event']['homeScore'].update(current=4,penalties=5)
    p['statistics']['statistics'].append({'period':'2ND','groups':[{'statisticsItems':[
        {'key':'expectedGoals','homeValue':.3,'awayValue':.1}]}]})
    row=normalize(p)
    assert row['home_goals']==2 and row['home_xg']==pytest.approx(.5)
    p['statistics']['statistics'].pop()
    assert normalize(p)['home_xg'] is None
    del p['event']['homeScore']['normaltime']
    with pytest.raises(ValueError,match='normal_time_score_unavailable'):
        normalize(p)


@pytest.mark.parametrize('change',[lambda p:p['event']['tournament']['uniqueTournament'].update(id=8),
    lambda p:p['event']['homeTeam'].update(gender='F'),lambda p:p['event']['status'].update(type='inprogress')])
def test_foreign_event_or_player_identity_rejected(change):
    p=example();change(p)
    with pytest.raises(ValueError):normalize(p)


def test_receipt_and_hash_fail_closed():
    with pytest.raises(ValueError,match='invalid_capture_time'):
        normalize(example(),captured_at='2025-01-01T12:00:00Z')
    with pytest.raises(ValueError,match='original_hash_mismatch'):
        normalize(example(),sha256='0'*64)


def test_unverified_player_does_not_discard_verified_match_stats():
    p=example();p['lineups']['home']['players'][0]['teamId']=999
    row=normalize(p)
    assert row['home_xg']==1.23 and len(row['players'])==21
    assert row['lineups'][0]['complete'] is False
    assert row['statistics']['player_identity_issues'][0]['source_player_id']==1


def test_unconfirmed_lineup_is_not_a_valid_starting_xi():
    p=example();p['lineups']['confirmed']=False
    row=normalize(p)
    assert not any(l['complete'] for l in row['lineups'])
    assert all(p['starter'] is None for p in row['players'])


def test_other_provider_identity_does_not_conflict_and_new_id_is_namespaced():
    row=normalize(example())
    db={'teams':[{'team_id':1,'league_id':'gb.championship','canonical_name':'A'},
                 {'team_id':2,'league_id':'gb.championship','canonical_name':'B'}],
        'aliases':[],'leagues':[{'league_id':'gb.championship','cross_league':False}],
        'matches':[{'match_id':'existing','league_id':'gb.championship','home_team_id':1,'away_team_id':2,
                    'kickoff_utc':row['kickoff_utc'],'status':'finished','home_goals':2,'away_goals':1,
                    'external_ids':{'fotmob':'987'}}]}
    assert Matcher(db,[row],provider='sofascore').match(row)['match_id']=='existing'
    db['matches']=[]
    assert Matcher(db,[row],provider='sofascore').match(row)['match_id']=='sofascore:123'
