"""Reproducible official event listing. Membership never proves availability."""
from hashlib import sha256
from html.parser import HTMLParser
import json
import re
from urllib.parse import urlsplit

from .context import utc


class _NextData(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.inside=False
        self.blocks=[]
        self.parts=[]

    def handle_starttag(self,tag,attrs):
        if tag=='script' and dict(attrs).get('id')=='__NEXT_DATA__':
            self.inside=True
            self.parts=[]

    def handle_data(self,data):
        if self.inside:self.parts.append(data)

    def handle_endtag(self,tag):
        if tag=='script' and self.inside:
            self.blocks.append(''.join(self.parts))
            self.inside=False


def event_listing(raw,receipt,expected_game_id,as_of):
    """Read one hash-bound NBA page; reject late, mismatched or ambiguous input."""
    source=urlsplit(receipt['url'])
    if (source.scheme!='https' or source.hostname!='www.nba.com' or source.query
            or source.fragment or not re.fullmatch(r'/game/[^/]+-'+re.escape(expected_game_id),source.path)
            or not re.fullmatch(r'(001|002|004)\d{7}',expected_game_id)
            or receipt['http_status']!=200):
        raise ValueError('official event URL and successful receipt required')
    if sha256(raw).hexdigest()!=receipt['raw_sha256']:
        raise ValueError('raw evidence hash mismatch')
    received=utc(receipt['first_received_at_utc']);cut=utc(as_of)
    if received>cut:raise ValueError('receipt unavailable at cut')
    parser=_NextData();parser.feed(raw.decode('utf-8',errors='strict'))
    if len(parser.blocks)!=1:raise ValueError('one official embedded document required')
    game=json.loads(parser.blocks[0])['props']['pageProps']['game']
    if game['gameId']!=expected_game_id:raise ValueError('event ID mismatch')
    tip=utc(game['gameTimeUTC'])
    if game['gameStatus']!=1 or cut>=tip:raise ValueError('pregame listing required')
    players=[];seen=set();teams=set()
    for side in ['homeTeam','awayTeam']:
        team=game[side];tid=team['teamId']
        if type(tid) is not int or tid<=0 or tid in teams:raise ValueError('distinct official teams required')
        if game.get(side+'Id')!=tid:raise ValueError('team side mismatch')
        teams.add(tid)
        # Empty inactives does not mean that every listed player is cleared.
        for row in team['players']:
            pid=row['personId'];name=row['name']
            if type(pid) is not int or pid<=0 or pid in seen:raise ValueError('invalid or duplicated player ID')
            if not isinstance(name,str) or not name.strip():raise ValueError('player name required')
            seen.add(pid)
            players.append(dict(nba_player_id=pid,nba_team_id=tid,name=name,
                identity_name_clean='\ufffd' not in name,listed_for_event=True,
                status_raw=row.get('status'),starter_raw=row.get('starter'),
                availability_verified=False,pregame_available=None,role_verified=False))
    if not players:raise ValueError('empty player listing')
    return dict(nba_event_id=expected_game_id,tipoff_utc=tip.isoformat(),
        source_url=receipt['url'],source_sha256=receipt['raw_sha256'],
        first_received_at_utc=received.isoformat(),as_of=cut.isoformat(),
        listing_verified=True,players=players,
        inactives_raw={s:game[s].get('inactives') for s in ['homeTeam','awayTeam']},
        final_availability_verified=False,actionable=False)


def source_review(event,observations,as_of):
    """Explain source gaps for this event; this does not replace quote validation."""
    cut=utc(as_of);tip=utc(event['tipoff_utc'])
    if cut<utc(event['as_of']):raise ValueError('listing from after review cut')
    rows=[]
    allowed={'team_markets_only_observed','markets_unreadable','individual_candidates_observed','access_denied'}
    for o in observations:
        if o['status'] not in allowed:raise ValueError('unknown source review state')
        if o['nba_event_id']!=event['nba_event_id']:raise ValueError('review for another event')
        if utc(o['observed_at_utc'])>cut:raise ValueError('future source observation')
        if o['country']!='MX':raise ValueError('Mexican source review required')
        rows.append(dict(o,contract_verified=False,actionable=False))
    return dict(nba_event_id=event['nba_event_id'],as_of=cut.isoformat(),sources=rows,
        listed_players=len(event['players']),
        blockers=['individual_MX_quotes_and_provider_clock_unverified',
                  'market_specific_rules_binding_unverified','final_availability_unverified'],
        next_action=('Review new event before its tipoff; retain this event for research only'
            if cut>=tip else 'Capture player O/U pairs, market rules and explicit event availability before tipoff'),
        pregame_window_open=cut<tip,actionable=False)
