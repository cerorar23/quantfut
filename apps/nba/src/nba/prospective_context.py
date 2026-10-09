"""Current preseason/schedule context without promoting roster status to fitness."""
from collections import Counter
import re
from urllib.parse import urlsplit
from .context import utc,name_key


def scoreboard_events(body,received):
    now=utc(received);events=[];seen=set()
    if body['leagues'][0]['slug']!='nba':raise ValueError('wrong league')
    for e in body['events']:
        identifier='espn:'+e['id']
        if identifier in seen:raise ValueError('duplicate event')
        seen.add(identifier)
        c=e['competitions'][0];state=c['status']['type']['state'];tip=utc(e['date'])
        if state!='pre' or now>=tip:continue
        season=e['season'];kind={1:'preseason',2:'regular',3:'postseason'}.get(season['type'])
        if kind is None:raise ValueError('unknown season type')
        teams={t['homeAway']:'espn:'+t['team']['id'] for t in c['competitors']}
        if set(teams)!={'home','away'}:raise ValueError('wrong team sides')
        events.append(dict(event_id=identifier,tipoff_utc=tip.isoformat(),season_year=season['year'],season_type=kind,
            home_team_id=teams['home'],away_team_id=teams['away'],first_received_at_utc=received,
            NBA_event_id=None,actionable=False))
    return events


def roster_context(body,received,reference):
    if body['season']['year']!=2027:raise ValueError('wrong roster season')
    verified={r['player_id']:r for r in reference if r.get('identity_verified') is True}
    rows=[];seen=set();team='espn:'+body['team']['id']
    for athlete in body['athletes']:
        pid='espn:'+athlete['id']
        if pid in seen:raise ValueError('duplicate roster athlete')
        seen.add(pid);old=verified.get(pid);dob=athlete.get('dateOfBirth','')[:10]
        identity=bool(old and name_key(old['name'])==name_key(athlete['displayName']) and old.get('date_of_birth')==dob)
        rows.append(dict(player_id=pid,team_id=team,name=athlete['displayName'],date_of_birth=dob,
            nba_player_id=old['nba_player_id'] if identity else None,identity_verified=identity,
            identity_reference='prior exact name/birth NBA crosswalk' if identity else None,
            current_membership_source='current ESPN roster',current_NBA_membership_verified=False,
            roster_status_raw=athlete.get('status'),position_raw=athlete.get('position'),injuries_raw=athlete.get('injuries'),
            first_received_at_utc=received,pregame_availability=None,availability_verified=False,role_verified=False,actionable=False))
    return rows


def injury_observations(body,received):
    published=body.get('timestamp')
    if published and utc(published)>utc(received):raise ValueError('provider timestamp after own receipt')
    rows=[]
    for team in body['injuries']:
        for injury in team.get('injuries',[]):
            athlete=injury['athlete']
            identifiers={str(athlete['id'])} if athlete.get('id') else set()
            for link in athlete.get('links',[]):
                url=urlsplit(link.get('href',''))
                match=re.search(r'/nba/player/(?:[^/]+/)*id/(\d+)(?:/|$)',url.path)
                if url.hostname in {'www.espn.com','espn.com'} and match:identifiers.add(match[1])
            if len(identifiers)>1:raise ValueError('conflicting ESPN athlete links')
            pid='espn:'+identifiers.pop() if identifiers else None
            rows.append(dict(team_id='espn:'+str(team['id']),player_id=pid,name=athlete['displayName'],
                designation_raw=injury.get('status'),reported_date_raw=injury.get('date'),
                comment=injury.get('shortComment'),feed_timestamp_utc=published,first_received_at_utc=received,
                reported_date_semantics_verified=False,event_id=None,availability_verified=False,actionable=False))
    return rows
