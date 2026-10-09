"""Official current roster listing and event-scoped injury observations."""
from datetime import datetime
from urllib.parse import urlsplit
import re
from .context import name_key,utc


def team_identity(summaries,profiles):
    catalog={}
    for profile in profiles:
        info=profile['team']['info'];name=name_key(info['TEAM_CITY']+' '+info['TEAM_NAME'])
        if name in catalog:raise ValueError('ambiguous official team name')
        catalog[name]=info['TEAM_ID']
    mapping={}
    for summary in summaries:
        for competitor in summary['header']['competitions'][0]['competitors']:
            team=competitor['team'];key='espn:'+str(team['id']);name=name_key(team['displayName'])
            if name not in catalog:raise ValueError('official team name not matched')
            if key in mapping and mapping[key]!=catalog[name]:raise ValueError('conflicting ESPN team identity')
            mapping[key]=catalog[name]
    if len(set(mapping.values()))!=len(mapping):raise ValueError('ambiguous cross-provider team mapping')
    return mapping


def official_roster(page,receipt):
    source=urlsplit(receipt['url']);match=re.fullmatch(r'/team/(\d+)/[^/]+',source.path)
    if source.hostname!='www.nba.com' or receipt['http_status']!=200 or not match:raise ValueError('official team profile required')
    expected=int(match[1]);team=page['team'];info=team['info']
    if int(team['id'])!=expected or info['TEAM_ID']!=expected:raise ValueError('official team mismatch')
    if info['SEASON_YEAR']!='2026-27' or team['scheduleSeason']!='2026-27':raise ValueError('stale official team season')
    rows=[];seen=set()
    for row in team['roster']:
        pid=row['PLAYER_ID']
        if type(pid) is not int or pid<=0 or pid in seen:raise ValueError('invalid or duplicate official player')
        seen.add(pid)
        if row['TeamID']!=expected or str(row['SEASON'])!='2026' or row['LeagueID']!='00':raise ValueError('roster season/team mismatch')
        dob=datetime.strptime(row['BIRTH_DATE'],'%b %d, %Y').date()
        if dob>=utc(receipt['first_received_at_utc']).date():raise ValueError('future birth date')
        rows.append(dict(nba_player_id=pid,nba_team_id=expected,name=row['PLAYER'],date_of_birth=dob.isoformat(),
            team_abbreviation=info['TEAM_ABBREVIATION'],season='2026-27',source_url=receipt['url'],source_sha256=receipt['raw_sha256'],
            first_received_at_utc=receipt['first_received_at_utc'],official_roster_listing_verified=True,
            supplemental_status_raw=row.get('SUPPLEMENTAL_STATUS'),acquisition_raw=row.get('HOW_ACQUIRED'),
            active_contract_verified=False,game_specific_available=None,availability_verified=False,role_verified=False,actionable=False))
    if not rows:raise ValueError('empty official roster cannot verify membership')
    return rows


def current_identity(espn_players,official,team_map):
    unique={};ids=set();suffix_candidates={}
    def without_suffix(name):return re.sub(r' (?:jr|sr|ii|iii|iv)$','',name_key(name))
    for row in official:
        key=(row['nba_team_id'],name_key(row['name']),row['date_of_birth'])
        if key in unique or row['nba_player_id'] in ids:raise ValueError('ambiguous official current identity')
        unique[key]=row;ids.add(row['nba_player_id'])
        suffix_key=(row['nba_team_id'],without_suffix(row['name']),row['date_of_birth'])
        suffix_candidates.setdefault(suffix_key,[]).append(row)
    output=[]
    for person in espn_players:
        team=team_map.get(person['team_id']);match=unique.get((team,name_key(person['name']),person['date_of_birth']))
        method='exact name/team/birth' if match else None
        if match is None:
            candidates=suffix_candidates.get((team,without_suffix(person['name']),person['date_of_birth']),[])
            if len(candidates)==1:
                match=candidates[0];method='generational suffix only, exact team/birth and unique candidate'
        if match and person.get('nba_player_id') not in {None,match['nba_player_id']}:raise ValueError('prior identity disagrees with current official source')
        output.append(dict(person,current_nba_player_id=match['nba_player_id'] if match else None,
            current_nba_team_id=team if match else None,current_official_identity_verified=bool(match),
            current_official_roster_listing_verified=bool(match),current_official_proof_sha256=match['source_sha256'] if match else None,
            current_official_received_at_utc=match['first_received_at_utc'] if match else None,
            current_identity_match_method=method,current_official_name=match['name'] if match else None,
            # A training-camp/supplemental roster listing does not prove a contract or an active game roster.
            active_contract_verified=False,availability_verified=False,role_verified=False,actionable=False))
    return output


def event_injuries(body,receipt):
    header=body['header'];competition=header['competitions'][0];tip=utc(competition['date']);received=utc(receipt['first_received_at_utc'])
    if header['league']['slug']!='nba' or header['season']['year']!=2027:raise ValueError('wrong injury event league/season')
    if competition['status']['type']['state']!='pre' or received>=tip:raise ValueError('not a pregame injury observation')
    competitors={'espn:'+str(c['team']['id']) for c in competition['competitors']}
    if len(competitors)!=2:raise ValueError('invalid injury event competitors')
    rows=[];seen=set()
    for team in body.get('injuries',[]):
        tid='espn:'+str(team['team']['id'])
        if tid not in competitors:raise ValueError('injury team not in event')
        for injury in team.get('injuries',[]):
            athlete=injury['athlete'];pid='espn:'+str(athlete['id']);key=(tid,pid)
            if key in seen:raise ValueError('duplicate event injury')
            seen.add(key);reported=injury.get('date')
            if reported and utc(reported)>received:raise ValueError('future reported injury date')
            rows.append(dict(event_id='espn:'+str(header['id']),team_id=tid,player_id=pid,name=athlete['displayName'],
                tipoff_utc=tip.isoformat(),designation_raw=injury.get('status'),injury_details_raw=injury.get('details'),
                reported_date_raw=reported,reported_date_semantics_verified=False,source_url=receipt['url'],source_sha256=receipt['raw_sha256'],
                first_received_at_utc=receipt['first_received_at_utc'],event_context_verified=True,
                game_specific_final_availability_verified=False,pregame_available=None,role_verified=False,actionable=False))
    return rows


def official_event_identity(game,summary,nba_receipt,espn_receipt,team_map):
    competition=summary['header']['competitions'][0]
    if urlsplit(nba_receipt['url']).hostname!='www.nba.com' or nba_receipt['http_status']!=200:raise ValueError('official event source required')
    if not nba_receipt['url'].endswith(game['gameId']):raise ValueError('official event URL/ID mismatch')
    if game['gameStatus']!=1 or competition['status']['type']['state']!='pre':raise ValueError('not a pregame event identity')
    nba_tip=utc(game['gameTimeUTC']);espn_tip=utc(competition['date'])
    if nba_tip!=espn_tip or any(utc(r['first_received_at_utc'])>=nba_tip for r in [nba_receipt,espn_receipt]):raise ValueError('tipoff mismatch or late receipt')
    season_type={1:'001',2:'002',3:'004'}.get(summary['header']['season']['type'])
    if game['gameId'][:3]!=season_type:raise ValueError('competition type mismatch')
    sides={c['homeAway']:team_map.get('espn:'+str(c['team']['id'])) for c in competition['competitors']}
    if sides!={'home':game['homeTeam']['teamId'],'away':game['awayTeam']['teamId']}:raise ValueError('event team sides mismatch')
    return dict(event_id='espn:'+str(summary['header']['id']),nba_event_id=game['gameId'],tipoff_utc=nba_tip.isoformat(),
        home_nba_team_id=sides['home'],away_nba_team_id=sides['away'],identity_verified=True,
        source_hashes=[nba_receipt['raw_sha256'],espn_receipt['raw_sha256']],availability_verified=False,actionable=False)
