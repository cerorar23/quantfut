import copy
import pytest
from nba.official_context import official_roster,current_identity,event_injuries,official_event_identity,team_identity

RECEIPT=dict(url='https://www.nba.com/team/1610612738/boston-celtics',http_status=200,raw_sha256='a'*64,first_received_at_utc='2026-10-08T18:00:00Z')
def page():return dict(team=dict(id='1610612738',scheduleSeason='2026-27',info=dict(TEAM_ID=1610612738,SEASON_YEAR='2026-27',TEAM_ABBREVIATION='BOS'),
    roster=[dict(PLAYER_ID=1,TeamID=1610612738,SEASON='2026',LeagueID='00',BIRTH_DATE='MAR 03, 1998',PLAYER='Player One',SUPPLEMENTAL_STATUS=0)]))

def test_current_listing_does_not_verify_availability_or_active_contract():
    roster=official_roster(page(),RECEIPT)
    assert roster[0]['official_roster_listing_verified'] and not roster[0]['availability_verified'] and not roster[0]['active_contract_verified']
    person=dict(player_id='espn:7',team_id='espn:2',name='Player One',date_of_birth='1998-03-03',nba_player_id=None)
    merged=current_identity([person],roster,{'espn:2':1610612738})[0]
    assert merged['current_nba_player_id']==1 and merged['current_official_identity_verified']
    assert merged['availability_verified'] is False

@pytest.mark.parametrize('change',['team','season','duplicate','birth','origin'])
def test_wrong_or_stale_official_profile_rejected(change):
    data=page();receipt=dict(RECEIPT)
    if change=='team':data['team']['info']['TEAM_ID']=3
    if change=='season':data['team']['info']['SEASON_YEAR']='2025-26'
    if change=='duplicate':data['team']['roster']*=2
    if change=='birth':data['team']['roster'][0]['BIRTH_DATE']='JAN 01, 2030'
    if change=='origin':receipt['url']='https://example.com/team/1610612738/boston-celtics'
    with pytest.raises(ValueError):official_roster(data,receipt)

def test_team_birth_or_name_disagreement_never_matches():
    roster=official_roster(page(),RECEIPT)
    person=dict(player_id='espn:7',team_id='espn:2',name='Player One',date_of_birth='1998-03-04',nba_player_id=1)
    assert not current_identity([person],roster,{'espn:2':1610612738})[0]['current_official_identity_verified']
    person['date_of_birth']='1998-03-03';person['nba_player_id']=9
    with pytest.raises(ValueError):current_identity([person],roster,{'espn:2':1610612738})

def summary():return dict(header=dict(id='7',league=dict(slug='nba'),season=dict(year=2027),competitions=[dict(date='2026-10-08T23:00Z',
    status=dict(type=dict(state='pre')),competitors=[dict(team=dict(id='2')),dict(team=dict(id='5'))])]),
    injuries=[dict(team=dict(id='2'),injuries=[dict(athlete=dict(id='11',displayName='Player One'),status='Day-To-Day',date='2026-10-07T10:00Z',details=dict(returnDate='2026-10-08'))])])

def test_event_designation_stays_distinct_from_final_availability():
    rows=event_injuries(summary(),RECEIPT)
    assert rows[0]['event_id']=='espn:7' and rows[0]['event_context_verified']
    assert rows[0]['pregame_available'] is None and not rows[0]['game_specific_final_availability_verified']
    empty=summary();empty['injuries'][0]['injuries']=[]
    assert event_injuries(empty,RECEIPT)==[]

@pytest.mark.parametrize('change',['foreign_team','post_tipoff','future_injury','duplicate'])
def test_invalid_event_context_rejected(change):
    data=summary();receipt=dict(RECEIPT)
    if change=='foreign_team':data['injuries'][0]['team']['id']='9'
    if change=='post_tipoff':receipt['first_received_at_utc']='2026-10-08T23:01Z'
    if change=='future_injury':data['injuries'][0]['injuries'][0]['date']='2026-10-09T10:00Z'
    if change=='duplicate':data['injuries'][0]['injuries']*=2
    with pytest.raises(ValueError):event_injuries(data,receipt)


@pytest.mark.parametrize('change',[None,'tipoff','sides','type'])
def test_official_event_match_requires_competition_time_and_both_sides(change):
    body=summary();body['header']['season']['type']=1
    body['header']['competitions'][0]['competitors']=[dict(homeAway='away',team=dict(id='2')),dict(homeAway='home',team=dict(id='5'))]
    game=dict(gameId='0012600011',gameStatus=1,gameTimeUTC='2026-10-08T23:00Z',homeTeam=dict(teamId=1610612739),awayTeam=dict(teamId=1610612738))
    if change=='tipoff':game['gameTimeUTC']='2026-10-08T23:30Z'
    if change=='sides':game['homeTeam']['teamId']=1610612738
    if change=='type':body['header']['season']['type']=2
    receipt=dict(RECEIPT,url='https://www.nba.com/game/bos-vs-cle-0012600011')
    mapping={'espn:2':1610612738,'espn:5':1610612739}
    if change:
        with pytest.raises(ValueError):official_event_identity(game,body,receipt,RECEIPT,mapping)
    else:
        result=official_event_identity(game,body,receipt,RECEIPT,mapping)
        assert result['nba_event_id']=='0012600011' and result['identity_verified'] and not result['availability_verified']


def test_team_codes_can_differ_with_exact_official_name_proof():
    source=dict(team=dict(info=dict(TEAM_ID=1610612740,TEAM_CITY='New Orleans',TEAM_NAME='Pelicans',TEAM_ABBREVIATION='NOP')))
    summary=dict(header=dict(competitions=[dict(competitors=[dict(team=dict(id='3',displayName='New Orleans Pelicans',abbreviation='NO'))])]))
    assert team_identity([summary],[source])=={'espn:3':1610612740}
    with pytest.raises(ValueError):team_identity([summary],[source,copy.deepcopy(source)])


def test_generation_suffix_requires_exact_birth_team_and_unique_candidate():
    roster=official_roster(page(),RECEIPT);roster[0]['name']='Player One III'
    person=dict(player_id='espn:7',team_id='espn:2',name='Player One',date_of_birth='1998-03-03',nba_player_id=None)
    result=current_identity([person],roster,{'espn:2':1610612738})[0]
    assert result['current_official_identity_verified'] and result['current_official_name']=='Player One III'
    ambiguous=roster+[dict(roster[0],nba_player_id=2,name='Player One Jr.')]
    assert not current_identity([person],ambiguous,{'espn:2':1610612738})[0]['current_official_identity_verified']
    assert not current_identity([dict(person,date_of_birth='1998-03-04')],roster,{'espn:2':1610612738})[0]['current_official_identity_verified']
