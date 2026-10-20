"""Source-backed venue revisions and exact edition/date-specific bindings.

Sources must have been received before registration. Queries use both the
decision-time version and the local scheduled match date. A tournament's
primary site is not proof of the player's itinerary or of a particular court's
roof state. No city-centre geocoding or fuzzy aliases are used.
"""
from collections import Counter
from datetime import date, datetime
import hashlib
import json
import math
from pathlib import Path
import sqlite3
from typing import Any
from zoneinfo import ZoneInfo

from .operations import utc


def canonical(value: Any) -> str:
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)


class VenueRegistry:
    def __init__(self,path: Path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path);self.db.row_factory=sqlite3.Row
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS venue_sources(source_id TEXT PRIMARY KEY,body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS venue_versions(revision_id TEXT PRIMARY KEY,venue_id TEXT NOT NULL,
                recorded_at TEXT NOT NULL,body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS venue_bindings(revision_id TEXT PRIMARY KEY,binding_id TEXT NOT NULL,
                recorded_at TEXT NOT NULL,body TEXT NOT NULL);
        ''')
        for table in ('venue_sources','venue_versions','venue_bindings'):
            for operation in ('UPDATE','DELETE'):
                self.db.execute(f"CREATE TRIGGER IF NOT EXISTS {table}_{operation}_immutable BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'append-only venue registry'); END")
        self.db.commit()

    def add_source(self,source: dict[str,Any]) -> None:
        utc(source['received_at'])
        if not source.get('url','').startswith('https://'):
            raise ValueError('HTTPS source URL required')
        raw=Path(source['source_path']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=source['sha256']:
            raise ValueError('Source content does not match receipt')
        existing=self.db.execute('SELECT body FROM venue_sources WHERE source_id=?',(source['source_id'],)).fetchone()
        body=canonical(source)
        if existing:
            if existing[0]!=body:raise ValueError('Source identity already has different content')
            return
        with self.db:self.db.execute('INSERT INTO venue_sources VALUES(?,?)',(source['source_id'],body))

    def _check_sources(self,ids: list[str],recorded_at: str) -> None:
        if not ids:raise ValueError('Evidence source required')
        for identity in ids:
            row=self.db.execute('SELECT body FROM venue_sources WHERE source_id=?',(identity,)).fetchone()
            if row is None:raise ValueError('Unknown evidence source')
            source=json.loads(row[0])
            if utc(source['received_at'])>utc(recorded_at):raise ValueError('Registration predates source receipt')
            if hashlib.sha256(Path(source['source_path']).read_bytes()).hexdigest()!=source['sha256']:
                raise ValueError('Evidence source changed')

    def _insert_revision(self,table: str,identity_column: str,identity: str,recorded_at: str,body: dict[str,Any]) -> str:
        recorded=utc(recorded_at).isoformat();text=canonical(body)
        revision=hashlib.sha256(text.encode()).hexdigest()
        prior=self.db.execute(f'SELECT body FROM {table} WHERE {identity_column}=? AND recorded_at=?',(identity,recorded)).fetchall()
        if prior and any(p[0]!=text for p in prior):raise ValueError('Conflicting revisions at one registration time')
        if not self.db.execute(f'SELECT 1 FROM {table} WHERE revision_id=?',(revision,)).fetchone():
            with self.db:self.db.execute(f'INSERT INTO {table} VALUES(?,?,?,?)',(revision,identity,recorded,text))
        return revision

    def register_venue(self,venue: dict[str,Any]) -> str:
        for field in ('venue_id','name','city','country','timezone','recorded_at'):
            if not isinstance(venue.get(field),str) or not venue[field]:raise ValueError('Venue identity, location and registration time required')
        ZoneInfo(venue['timezone']);utc(venue['recorded_at'])
        if venue.get('roof_state_at_match') is not None:
            raise ValueError('Live roof state does not belong in static venue metadata')
        fields=venue.get('field_sources',{})
        for field in ('name','city','country','timezone'):
            self._check_sources(fields.get(field,[]),venue['recorded_at'])
        lat,lon=venue.get('lat'),venue.get('lon')
        if (lat is None)!=(lon is None):raise ValueError('Coordinates must be present as a pair')
        if lat is not None:
            if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in (lat,lon)) or not -90<=lat<=90 or not -180<=lon<=180:
                raise ValueError('Invalid coordinates')
            if venue.get('coordinate_scope') not in ('venue_point','venue_geometry_representative'):
                raise ValueError('Coordinates must identify the venue, not a city centre')
            precision=venue.get('coordinate_precision_m')
            if isinstance(precision,bool) or not isinstance(precision,(int,float)) or not math.isfinite(precision) or precision<=0:
                raise ValueError('Explicit coordinate precision required')
            self._check_sources(fields.get('coordinates',[]),venue['recorded_at'])
        altitude=venue.get('altitude_m')
        if altitude is not None:
            if isinstance(altitude,bool) or not isinstance(altitude,(int,float)) or not math.isfinite(altitude) or not -500<=altitude<=9000:
                raise ValueError('Invalid altitude')
            self._check_sources(fields.get('altitude_m',[]),venue['recorded_at'])
        if venue.get('indoor') is not None:
            if type(venue['indoor']) is not bool:raise ValueError('Indoor must be boolean or unknown')
            self._check_sources(fields.get('indoor',[]),venue['recorded_at'])
        return self._insert_revision('venue_versions','venue_id',venue['venue_id'],venue['recorded_at'],venue)

    def register_binding(self,binding: dict[str,Any]) -> str:
        for field in ('binding_id','provider','provider_tournament_id','provider_event_type','season','edition_id',
                      'venue_id','valid_from','valid_until','recorded_at','timezone'):
            if not isinstance(binding.get(field),str) or not binding[field]:raise ValueError('Exact provider/edition/date binding required')
        if not date.fromisoformat(binding['valid_from'])<date.fromisoformat(binding['valid_until']):
            raise ValueError('Date intervals are [valid_from, valid_until)')
        if not binding['season'].isdigit() or len(binding['season'])!=4:raise ValueError('Explicit season year required')
        if binding['surface'] not in ('Hard','Clay','Grass','Carpet',None):raise ValueError('Unknown surface encoding')
        self._check_sources(binding.get('sources',[]),binding['recorded_at'])
        if binding['surface'] is not None:self._check_sources(binding.get('surface_sources',[]),binding['recorded_at'])
        venue=self.venue(binding['venue_id'],binding['recorded_at'],inclusive=True)
        if venue is None or venue['timezone']!=binding['timezone']:
            raise ValueError('Binding must refer to a registered venue in the same timezone')
        return self._insert_revision('venue_bindings','binding_id',binding['binding_id'],binding['recorded_at'],binding)

    def venue(self,venue_id: str,decision_at: str,*,inclusive: bool=False) -> dict[str,Any] | None:
        rows=self.db.execute('SELECT * FROM venue_versions WHERE venue_id=? ORDER BY recorded_at DESC',(venue_id,)).fetchall()
        for row in rows:
            recorded=utc(row['recorded_at']);decision=utc(decision_at)
            if recorded<decision or (inclusive and recorded==decision):
                value=json.loads(row['body'])
                for ids in value.get('field_sources',{}).values():self._check_sources(ids,decision_at)
                return {**value,'revision_id':row['revision_id']}
        return None

    def resolve(self,provider: str,tournament_id: str,event_type: str,season: str,
                scheduled_start: str,decision_at: str) -> dict[str,Any]:
        decision=utc(decision_at);start=utc(scheduled_start)
        latest={}
        for row in self.db.execute('SELECT * FROM venue_bindings ORDER BY recorded_at,revision_id'):
            if utc(row['recorded_at'])<decision:latest[row['binding_id']]=row
        candidates=[]
        for row in latest.values():
            b=json.loads(row['body'])
            if (b['provider'],b['provider_tournament_id'],b['provider_event_type'],b['season'])!=(provider,str(tournament_id),event_type,str(season)):continue
            local_date=start.astimezone(ZoneInfo(b['timezone'])).date().isoformat()
            if not b['valid_from']<=local_date<b['valid_until']:continue
            self._check_sources(b['sources'],decision_at)
            self._check_sources(b.get('surface_sources',[]),decision_at) if b['surface'] is not None else None
            venue=self.venue(b['venue_id'],decision_at)
            if venue is None:continue
            if venue['timezone']!=b['timezone']:raise ValueError('Venue timezone revision conflicts with binding')
            candidates.append({'binding_revision_id':row['revision_id'],'binding':b,'venue':venue,
                               'scheduled_local_date':local_date})
        if len(candidates)!=1:
            return {'status':'ambiguous' if candidates else 'unresolved','candidates':len(candidates)}
        return {'status':'resolved','scope':'tournament_primary_site','actual_court_verified':False,
                'roof_state_at_match':None,'personal_itinerary_known':False,**candidates[0]}

    def enrich_calendar(self,rows: list[dict[str,Any]],decision_at: str,*,input_timezone: str,
                        source_received_at: str) -> dict[str,Any]:
        if input_timezone!='UTC':raise ValueError('Normalize source fixtures to explicit UTC first')
        if utc(source_received_at)>=utc(decision_at):raise ValueError('Calendar was not received before decision')
        enriched=[];issues=Counter()
        for row in rows:
            try:
                start=f"{row['event_date']}T{row['event_time']}:00+00:00"
                result=self.resolve('api_tennis',str(row['tournament_key']),row['event_type_type'],
                                    str(row['tournament_season']),start,decision_at)
            except (ValueError,KeyError,TypeError) as exc:
                result={'status':'invalid_fixture_metadata','error_type':type(exc).__name__}
            issues[result['status']]+=1
            enriched.append({'provider_event_id':str(row.get('event_key')),'tournament_name':row.get('tournament_name'),
                             'event_type':row.get('event_type_type'),'season':row.get('tournament_season'),
                             'review_flags':['provider_season_differs_from_scheduled_year']
                               if str(row.get('tournament_season'))!=str(row.get('event_date',''))[:4] else [],
                             'venue_resolution':result})
        resolved=[r for r in enriched if r['venue_resolution']['status']=='resolved']
        coordinates=sum(r['venue_resolution']['venue'].get('lat') is not None for r in resolved)
        return {'schema':'tennis-calendar-venues-v1','decision_at':decision_at,'input_timezone':'UTC',
                'calendar_received_at':source_received_at,
                'n_total':len(rows),'n_resolved':len(resolved),'n_with_coordinates':coordinates,
                'coverage':len(resolved)/len(rows) if rows else None,'statuses':dict(issues),'events':enriched,
                'probabilities_modified':False,'historical_availability_backfilled':False}


def load_seed(registry: VenueRegistry,path: Path) -> dict[str,int]:
    """Offline reproducible reviewed seed; registered clocks are never backdated."""
    seed=json.loads(Path(path).read_text(encoding='utf-8'))
    if seed.get('schema')!='tennis-venue-seed-v1':raise ValueError('Unsupported venue seed')
    for source in seed['sources']:registry.add_source(source)
    for venue in seed['venues']:registry.register_venue(venue)
    for binding in seed['bindings']:registry.register_binding(binding)
    return {k:len(seed[k]) for k in ('sources','venues','bindings')}
