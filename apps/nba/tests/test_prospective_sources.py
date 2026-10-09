import io,json
from datetime import UTC,datetime,timedelta
from urllib.error import HTTPError
import pytest

from nba.caliente_public import prices
from nba.public_capture import capture,public_url
from nba.prospective_context import scoreboard_events,roster_context,injury_observations

R=dict(first_received_at_utc='2026-10-08T17:00:00Z',raw_sha256='a'*64)

def html(value='1.91',event='123',sid='5',extra=''):
    return f'<div class="selections-for-event" data-ev_id="123"><td class="mkt-sort-FTPO"><button name="add-to-slip" class="ev-{event} mkt-4 seln-{sid}" title="O 220.5" {extra}><span class="price dec">{value}</span></button></td></div>'


def test_real_price_shape_preserved_without_prop_or_contract_promotion():
    row=prices(html(),'123',R)['quotes'][0]
    assert row['decimal']==1.91 and row['market_type_raw']=='FTPO' and row['label']=='O 220.5'
    assert row['player_id'] is None and row['contract_verified'] is False and row['source_updated_at_utc'] is None


def test_other_events_and_sidebar_excluded():
    assert prices(html(event='124'),'123',R)['quotes']==[]
    sidebar=html().replace('selections-for-event','sidebar')
    assert prices(sidebar,'123',R)['quotes']==[]


@pytest.mark.parametrize('value',['nan','inf','1','-1','1001'])
def test_invalid_prices_rejected(value):
    with pytest.raises(ValueError):prices(html(value),'123',R)


def test_disabled_selection_not_available():
    assert prices(html(extra='disabled="disabled"'),'123',R)['quotes'][0]['button_disabled']


def test_conflicting_same_selection_not_silently_overwritten():
    with pytest.raises(ValueError):prices(html()+html('1.95'),'123',R)


def test_matching_duplicates_deduplicate():assert len(prices(html()+html(),'123',R)['quotes'])==1


def test_same_selection_label_aliases_preserved():
    r=prices(html()+html().replace('O 220.5','Over 220.5'),'123',R)
    assert len(r['quotes'])==1 and r['quotes'][0]['labels_observed']==['O 220.5','Over 220.5']


@pytest.mark.parametrize('url',['https://x.test/?api_key=secret','https://user:pass@x.test/','http://x.test/'])
def test_secret_or_nonHTTPS_URL_rejected(url):
    with pytest.raises(ValueError):public_url(url,[url])


def test_failed_http_does_not_become_good_data(tmp_path,monkeypatch):
    class Opener:
        def open(self,*a,**k):raise HTTPError('https://x.test/',403,'denied',{},io.BytesIO(b'403'))
    monkeypatch.setattr('urllib.request.build_opener',lambda *a:Opener())
    r=capture(tmp_path,'https://x.test/',['https://x.test/'])
    assert r['http_status']==403 and r['error']=='HTTPError' and r['actionable'] is False


def event(kind=1,state='pre',date='2026-10-08T23:00:00Z'):
    return dict(id='1',date=date,season=dict(type=kind,year=2027),competitions=[dict(status=dict(type=dict(state=state)),
        competitors=[dict(homeAway='home',team=dict(id='5')),dict(homeAway='away',team=dict(id='2'))])])


def test_preseason_is_not_regular_confirmation():
    result=scoreboard_events(dict(leagues=[dict(slug='nba')],events=[event()]),R['first_received_at_utc'])
    assert result[0]['season_type']=='preseason' and result[0]['NBA_event_id'] is None


@pytest.mark.parametrize('change',[dict(state='post'),dict(date='2026-10-08T15:00:00Z')])
def test_finished_or_past_events_excluded(change):
    assert scoreboard_events(dict(leagues=[dict(slug='nba')],events=[event(**change)]),R['first_received_at_utc'])==[]


def test_active_roster_is_not_pregame_available():
    body=dict(season=dict(year=2027),team=dict(id='2'),athletes=[dict(id='1',displayName='Player One',dateOfBirth='1999-01-01T00:00Z',status=dict(name='Active'))])
    refs=[dict(player_id='espn:1',identity_verified=True,name='Player One',date_of_birth='1999-01-01',nba_player_id=12)]
    r=roster_context(body,R['first_received_at_utc'],refs)[0]
    assert r['identity_verified'] and r['nba_player_id']==12
    assert r['pregame_availability'] is None and r['availability_verified'] is False and r['current_NBA_membership_verified'] is False


def test_changed_birthdate_rejects_old_identity():
    body=dict(season=dict(year=2027),team=dict(id='2'),athletes=[dict(id='1',displayName='Player One',dateOfBirth='1998-01-01T00:00Z')])
    refs=[dict(player_id='espn:1',identity_verified=True,name='Player One',date_of_birth='1999-01-01',nba_player_id=12)]
    assert roster_context(body,R['first_received_at_utc'],refs)[0]['nba_player_id'] is None


def test_feed_timestamp_after_receipt_rejected():
    with pytest.raises(ValueError):injury_observations(dict(timestamp='2026-10-09T00:00:00Z',injuries=[]),R['first_received_at_utc'])


def test_generic_injury_does_not_become_game_specific():
    body=dict(timestamp='2026-10-08T16:00Z',injuries=[dict(id='2',injuries=[dict(status='Out',date='2026-10-07T19:00Z',athlete=dict(id='1',displayName='Player One'))])])
    r=injury_observations(body,R['first_received_at_utc'])[0]
    assert r['designation_raw']=='Out' and r['event_id'] is None and r['availability_verified'] is False


def test_injury_without_id_uses_unique_provider_player_link():
    athlete=dict(displayName='Player One',links=[dict(href='https://www.espn.com/nba/player/_/id/123/player-one')])
    body=dict(injuries=[dict(id='2',injuries=[dict(athlete=athlete)])])
    assert injury_observations(body,R['first_received_at_utc'])[0]['player_id']=='espn:123'


def test_conflicting_provider_player_links_rejected():
    athlete=dict(id='2',displayName='Player One',links=[dict(href='https://www.espn.com/nba/player/_/id/123/player-one')])
    with pytest.raises(ValueError):injury_observations(dict(injuries=[dict(id='2',injuries=[dict(athlete=athlete)])]),R['first_received_at_utc'])


def test_unknown_player_link_preserved_without_name_guess():
    athlete=dict(displayName='Player One',links=[dict(href='https://other.test/nba/player/_/id/123/player-one')])
    row=injury_observations(dict(injuries=[dict(id='2',injuries=[dict(athlete=athlete)])]),R['first_received_at_utc'])[0]
    assert row['player_id'] is None
