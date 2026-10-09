from hashlib import sha256
import json
import pytest
from nba.event_listing import event_listing,source_review

GAME='0012600011'
CUT='2026-10-08T22:05:00Z'


def fixture():
    game=dict(gameId=GAME,gameStatus=1,gameTimeUTC='2026-10-08T23:00:00Z',
        homeTeamId=1610612739,awayTeamId=1610612738,
        homeTeam=dict(teamId=1610612739,players=[dict(personId=1,name='Player One',status='ACTIVE')],inactives=[]),
        awayTeam=dict(teamId=1610612738,players=[dict(personId=2,name='Player Two')],inactives=[]))
    receipt=dict(url='https://www.nba.com/game/bos-vs-cle-'+GAME,http_status=200,
        first_received_at_utc='2026-10-08T22:04:25Z')
    return game,receipt


def raw(game,receipt):
    body=('<script id="__NEXT_DATA__" type="application/json">'+json.dumps(dict(props=dict(pageProps=dict(game=game))))+'</script>').encode()
    return body,dict(receipt,raw_sha256=sha256(body).hexdigest())


def test_listing_is_not_medical_clearance():
    g,r=fixture();e=event_listing(*raw(g,r),GAME,CUT)
    assert e['listing_verified'] and len(e['players'])==2
    assert all(p['pregame_available'] is None and not p['availability_verified'] for p in e['players'])
    assert not e['final_availability_verified'] and not e['actionable']


@pytest.mark.parametrize('mutation',[
    lambda g,r:g.update(gameId='0012600012'),
    lambda g,r:g['awayTeam']['players'][0].update(personId=1),
    lambda g,r:g['homeTeam'].update(teamId=1610612738),
    lambda g,r:r.update(url='https://example.com/game/bos-vs-cle-'+GAME),
    lambda g,r:r.update(first_received_at_utc='2026-10-08T22:06:00Z'),
    lambda g,r:g.update(gameStatus=2),
])
def test_bad_event_context_rejected(mutation):
    g,r=fixture();mutation(g,r)
    with pytest.raises(ValueError):event_listing(*raw(g,r),GAME,CUT)


def test_receipt_hash_and_cut_are_enforced():
    g,r=fixture();b,r=raw(g,r)
    with pytest.raises(ValueError,match='hash'):event_listing(b+b' ',r,GAME,CUT)
    with pytest.raises(ValueError,match='pregame'):event_listing(b,r,GAME,'2026-10-08T23:00:00Z')


def test_corrupted_source_name_not_silently_repaired():
    g,r=fixture();g['homeTeam']['players'][0]['name']='Hugo Gonz\ufffdlez'
    e=event_listing(*raw(g,r),GAME,CUT)
    assert e['players'][0]['name']=='Hugo Gonz\ufffdlez'
    assert not e['players'][0]['identity_name_clean']


def observation():
    return dict(nba_event_id=GAME,country='MX',book='Novibet',status='team_markets_only_observed',
        observed_at_utc='2026-10-08T22:05:00Z')


def test_source_review_is_not_quote_admission():
    g,r=fixture();e=event_listing(*raw(g,r),GAME,CUT)
    result=source_review(e,[observation()],CUT)
    assert len(result['blockers'])==3 and result['pregame_window_open']
    assert not result['sources'][0]['contract_verified'] and not result['actionable']
    late=source_review(e,[observation()],'2026-10-08T23:01:00Z')
    assert not late['pregame_window_open'] and 'new event' in late['next_action']


@pytest.mark.parametrize('patch',[dict(nba_event_id='0012600012'),dict(country='US'),
    dict(observed_at_utc='2026-10-08T23:00:00Z'),dict(status='ready')])
def test_source_mismatch_or_future_rejected(patch):
    g,r=fixture();e=event_listing(*raw(g,r),GAME,CUT);o=observation();o.update(patch)
    with pytest.raises(ValueError):source_review(e,[o],CUT)


def test_offline_command_writes_review_and_preserves_existing_output(tmp_path,monkeypatch):
    from nba.cli import main
    g,r=fixture();b,r=raw(g,r)
    (tmp_path/'raw').write_bytes(b)
    (tmp_path/'receipt.json').write_text(json.dumps(r))
    (tmp_path/'observations.json').write_text(json.dumps([observation()]))
    arguments=['quantnba','audit-event-listing','--raw',str(tmp_path/'raw'),
        '--receipt',str(tmp_path/'receipt.json'),'--game-id',GAME,
        '--listing-as-of',CUT,'--as-of',CUT,'--observations',str(tmp_path/'observations.json'),
        '--output-dir',str(tmp_path/'out')]
    monkeypatch.setattr('sys.argv',arguments)
    main()
    assert json.loads((tmp_path/'out/event_listing.json').read_bytes())['listing_verified']
    assert not json.loads((tmp_path/'out/source_review.json').read_bytes())['actionable']
    before=(tmp_path/'out/event_listing.json').read_bytes()
    with pytest.raises(ValueError,match='preserve'):main()
    assert (tmp_path/'out/event_listing.json').read_bytes()==before
