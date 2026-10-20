"""Retrospectively reconstructed spatial covariates, never genuine as-of data.

Edition links are exact and year-specific. Last observed tournament location is
a proxy: no departure, arrival, doubles completion or direct itinerary is implied.
Unknown immediately preceding locations are not skipped to obtain usable values.
"""
from collections import Counter,defaultdict
from datetime import date,datetime,timedelta,timezone
from functools import lru_cache
import hashlib,json,math
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from .context import haversine_km
from .operations import utc


def edition_key(circuit: str, phase: str, tournament: str) -> str:
    return f'{circuit}:{phase}:{tournament}'


def load_historical_registry(path: Path) -> dict[str,Any]:
    registry=json.loads(Path(path).read_text(encoding='utf8'))
    if registry.get('schema')!='tennis-historical-venue-links-v1' or registry.get('historical_reconstruction') is not True:
        raise ValueError('Explicit retrospective registry required')
    stamp=utc(registry['created_at']);sources={s['source_id']:s for s in registry['sources']}
    if len(sources)!=len(registry['sources']):raise ValueError('Duplicate source IDs')
    for s in sources.values():
        if utc(s['received_at'])>stamp:raise ValueError('Registry predates source receipt')
        if hashlib.sha256(Path(s['source_path']).read_bytes()).hexdigest()!=s['sha256']:
            raise ValueError('Historical source changed')
    venues={v['venue_id']:v for v in registry['venues']}
    if len(venues)!=len(registry['venues']):raise ValueError('Duplicate physical venue IDs')
    for v in venues.values():
        if v.get('timezone') is not None:ZoneInfo(v['timezone'])
        if (v.get('lat') is None)!=(v.get('lon') is None):raise ValueError('Coordinate pair required')
        if v.get('lat') is not None:
            if v.get('timezone') is None:raise ValueError('Georeferenced venue requires an IANA timezone')
            haversine_km((v['lat'],v['lon']),(v['lat'],v['lon']))
            if v.get('coordinate_scope') not in ('venue_point','venue_geometry_representative'):
                raise ValueError('City-centre position is not a venue')
            if not v.get('coordinate_sources') or any(k not in sources for k in v['coordinate_sources']):
                raise ValueError('Coordinate evidence required')
            p=v.get('coordinate_precision_m')
            if isinstance(p,bool) or not isinstance(p,(int,float)) or not math.isfinite(p) or p<=0:
                raise ValueError('Spatial representativeness allowance required')
        height=v.get('altitude_m')
        if height is not None:
            if isinstance(height,bool) or not isinstance(height,(int,float)) or not math.isfinite(height) or not -500<=height<=9000:
                raise ValueError('Invalid terrain height')
            if not v.get('altitude_sources') or any(k not in sources for k in v['altitude_sources']):
                raise ValueError('Terrain evidence required')
    seen=set()
    for link in registry['links']:
        key=edition_key(link['circuit'],link['phase'],link['tourney_id'])
        if key in seen:raise ValueError('Ambiguous edition binding')
        seen.add(key)
        season=int(link['tourney_id'].split('-')[0])
        if season not in (2024,2025) or link['evidence_season']!=season:
            raise ValueError('Evidence must explicitly concern this historical season')
        if link['venue_id'] not in venues or not link.get('edition_sources'):
            raise ValueError('Historical edition/venue evidence required')
        if any(k not in sources for k in link['edition_sources']):raise ValueError('Unknown edition source')
    match_seen=set()
    for link in registry.get('match_links',[]):
        if link['match_id'] in match_seen:raise ValueError('Ambiguous match venue binding')
        match_seen.add(link['match_id'])
        season=int(link['tourney_id'].split('-')[0])
        if season not in (2024,2025) or link['evidence_season']!=season:
            raise ValueError('Match venue evidence must concern this historical season')
        if link['venue_id'] not in venues or not link.get('edition_sources') or any(k not in sources for k in link['edition_sources']):
            raise ValueError('Match venue evidence required')
    return registry


@lru_cache(maxsize=4096)
def clock_range(origin_zone: str,target_zone: str,first: str,last: str) -> tuple[float,float]:
    """Offsets across the recorded source-week reference interval, not match times.

    Probe both zones at the same UTC instants. Midnight/noon/end-of-day are
    calculation probes only, never imputed start/end times. If DST changes the
    difference, retain a range and leave the scalar feature missing.
    """
    a,b=ZoneInfo(origin_zone),ZoneInfo(target_zone)
    start=date.fromisoformat(first);end=date.fromisoformat(last)+timedelta(days=6)
    values=[]
    for i in range((end-start).days+1):
        day=start+timedelta(days=i)
        for hour in (0,12,23):
            point=datetime(day.year,day.month,day.day,hour,tzinfo=timezone.utc)
            values.append((point.astimezone(b).utcoffset()-point.astimezone(a).utcoffset()).total_seconds()/3600)
    return min(values),max(values)


def prepare_historical_dataset(frame: pd.DataFrame,registry: dict[str,Any]) -> tuple[pd.DataFrame,dict[str,Any]]:
    required={'circuit','source_group','tourney_id','period','match_id','winner_id','loser_id','score','completed_standard'}
    if not required<=set(frame.columns):raise ValueError('Canonical match columns missing')
    if frame.match_id.duplicated().any():raise ValueError('Duplicate canonical matches')
    if frame.empty:raise ValueError('Historical match data required')
    if frame.period.isna().any():raise ValueError('Recorded source period required')
    if frame.period.max()>='2026-01-01' or frame.tourney_id.str.match(r'202[6-9]-').any():
        raise ValueError('This research dataset must exclude 2026 and later')
    if registry.get('historical_reconstruction') is not True:raise ValueError('Retrospective registry required')
    links={edition_key(x['circuit'],x['phase'],x['tourney_id']):x for x in registry['links']}
    match_links={x['match_id']:x for x in registry.get('match_links',[])}
    if len(match_links)!=len(registry.get('match_links',[])):raise ValueError('Duplicate match venue')
    venues={x['venue_id']:x for x in registry['venues']}
    def row_link(row):
        link=match_links.get(row.match_id)
        if link is not None:
            if (row.circuit,row.source_group,row.tourney_id)!=(link['circuit'],link['phase'],link['tourney_id']):
                raise ValueError('Match venue link does not match canonical edition')
            return link
        return links.get(edition_key(row.circuit,row.source_group,row.tourney_id))
    blocks={};players=defaultdict(dict);player_sites=defaultdict(set)
    for (circuit,phase,identity),group in frame.groupby(['circuit','source_group','tourney_id'],sort=False):
        key=edition_key(circuit,phase,identity)
        first,last=group.period.min(),group.period.max()
        entry={'block_id':key,'circuit':circuit,'phase':phase,'tourney_id':identity,'first':first,'last':last,
               'n':len(group),'name':group.tourney_name.iloc[0] if 'tourney_name' in group else identity}
        entry['comparison_block_id']=links.get(key,{}).get('competition_group_id',key)
        blocks[key]=entry
        for player in set(group.winner_id)|set(group.loser_id):players[player][key]=entry
        for row in group.itertuples(index=False):
            link=row_link(row);site=None if link is None else link['venue_id']
            for player in (row.winner_id,row.loser_id):player_sites[player,key].add(site)
    # TML sometimes encodes rubbers of one tie as separate tournament IDs.
    # Preserve source IDs, but use the provider tie as the indivisible time block.
    logical=defaultdict(list)
    for block in blocks.values():logical[block['comparison_block_id']].append(block)
    for siblings in logical.values():
        first=min(b['first'] for b in siblings);last=max(b['last'] for b in siblings)
        for b in siblings:b['first']=first;b['last']=last
    targets=frame.loc[frame.source_group.eq('tour') & frame.tourney_id.str.match(r'202[45]-')].copy()
    events=[]
    for key,block in blocks.items():
        if block['phase']=='tour' and block['tourney_id'].startswith(('2024-','2025-')):
            link=links.get(key);v=venues.get(link['venue_id']) if link else None
            per_match=[x for x in match_links.values() if (x['circuit'],x['phase'],x['tourney_id'])==(block['circuit'],block['phase'],block['tourney_id'])]
            match_sites={x['venue_id'] for x in per_match}
            status='unlinked' if v is None else 'named_without_coordinates' if v.get('lat') is None else 'georeferenced'
            if per_match:
                status='match_level_complete' if len(per_match)==block['n'] else 'match_level_partial'
            resolutions=[row_link(row) for row in frame.loc[frame.circuit.eq(block['circuit']) & frame.source_group.eq(block['phase']) & frame.tourney_id.eq(block['tourney_id'])].itertuples(index=False)]
            events.append({**block,'venue_id':None if v is None else v['venue_id'],
                'venue_status':status,'match_level_venue_ids':sorted(match_sites),'n_match_venue_links':len(per_match),
                'n_matches_with_venue_identity':sum(x is not None for x in resolutions),
                'n_matches_with_coordinates':sum(x is not None and venues[x['venue_id']].get('lat') is not None for x in resolutions),
                'partition':partition(block),'evidence_season':None if link is None else link['evidence_season']})
    def player_features(player: str,target: dict[str,Any]) -> dict[str,Any]:
        output={'previous_observed_block_id':None,'previous_venue_id':None,'distance_km':None,
                'delta_altitude_m':None,'delta_timezone_hours':None,'timezone_delta_min':None,
                'timezone_delta_max':None,'status':'no_earlier_observed_tournament',
                'rest_hours':None,'direct_itinerary_verified':False,'doubles_coverage_complete':False}
        history=[b for b in players[player].values() if b['tourney_id']!=target['tourney_id'] and b['comparison_block_id']!=target['comparison_block_id'] and b['first']<=target['first']]
        # Treat each recorded period conservatively as a seven-day reference
        # interval. This is an ambiguity guard, not a reconstructed match end.
        if any(date.fromisoformat(b['last'])+timedelta(days=6)>=date.fromisoformat(target['first']) for b in history):
            output['status']='ambiguous_same_or_overlapping_source_period';return output
        if not history:return output
        last=max(b['last'] for b in history);candidates=[b for b in history if b['last']==last]
        # Qualifying/main draw of a single prior edition may share one anchor.
        ids={b['comparison_block_id'] for b in candidates}
        # Unlinked qualifying/main-draw phases of one raw edition remain one event.
        if len(ids)>1 and len({b['tourney_id'] for b in candidates})==1:ids={candidates[0]['tourney_id']}
        if len(ids)!=1:
            output['status']='ambiguous_previous_source_period';return output
        prior=next((b for b in candidates if b['phase']=='tour'),candidates[0])
        output['previous_observed_block_id']=prior['block_id']
        output['previous_source_period']=prior['last']
        observed=player_sites[player,prior['block_id']]
        if None in observed:output['status']='immediate_previous_edition_unlinked';return output
        if len(observed)!=1:output['status']='previous_edition_has_multiple_observed_venues';return output
        source=venues[next(iter(observed))];output['previous_venue_id']=source['venue_id']
        if target.get('target_venue_id') is None:output['status']='target_edition_unlinked';return output
        destination=venues[target['target_venue_id']]
        if any(v.get('lat') is None for v in (source,destination)):
            output['status']='coordinate_pair_unavailable';return output
        output['distance_km']=haversine_km((source['lat'],source['lon']),(destination['lat'],destination['lon']))
        output['distance_kind']='geodesic_between_observed_tournament_venues_not_actual_trip'
        output['distance_spatial_allowance_km']=(source['coordinate_precision_m']+destination['coordinate_precision_m'])/1000
        output['coarse_venue_reference']=max(source['coordinate_precision_m'],destination['coordinate_precision_m'])>1000
        if source.get('altitude_m') is not None and destination.get('altitude_m') is not None:
            output['delta_altitude_m']=destination['altitude_m']-source['altitude_m']
        low,high=clock_range(source['timezone'],destination['timezone'],target['first'],target['last'])
        output['timezone_delta_min']=low;output['timezone_delta_max']=high
        output['delta_timezone_hours']=low if low==high else None
        output['timezone_reference']='recorded_source_period_through_last_period_plus_six_days'
        output['status']='spatial_proxy_complete' if output['delta_altitude_m'] is not None and low==high else 'spatial_proxy_partial'
        return output
    features={};rows=[]
    for r in targets.itertuples(index=False):
        block=dict(blocks[edition_key(r.circuit,r.source_group,r.tourney_id)])
        link=row_link(r);block['target_venue_id']=None if link is None else link['venue_id']
        a,b=sorted((r.winner_id,r.loser_id))
        key_a=(a,block['block_id'],block['target_venue_id']);key_b=(b,block['block_id'],block['target_venue_id'])
        for key,player in ((key_a,a),(key_b,b)):
            if key not in features:features[key]=player_features(player,block)
        fa,fb=features[key_a],features[key_b]
        venue=venues[link['venue_id']] if link else None
        item={'match_id':r.match_id,'circuit':r.circuit,'edition_id':r.tourney_id,'block_id':block['block_id'],
              'edition_source_period_first':block['first'],'edition_source_period_last':block['last'],
              'comparison_block_id':block['comparison_block_id'],
              'partition':partition(block),'calendar_month_block':block['first'][:7],
              'player_a':a,'player_b':b,'y':int(r.winner_id==a),'score':r.score,
              'completed_standard':bool(r.completed_standard),'venue_id':None if venue is None else venue['venue_id'],
              'target_coordinate_available':venue is not None and venue.get('lat') is not None,
              'target_coordinate_precision_m':None if venue is None else venue.get('coordinate_precision_m'),
              'date_precision':'source_tournament_period_not_individual_match_day',
              'historical_reconstruction':True,'genuine_asof_validation':False,
              'source_received_at':getattr(r,'received_at',None),'venue_evidence_registered_at':registry['created_at'],
              'exploratory_2025':r.tourney_id.startswith('2025-'),'personal_itinerary_known':False,'rest_hours':None}
        for side,values in [('a',fa),('b',fb)]:
            for name,value in values.items():item[side+'_'+name]=value
        keys=('distance_km','delta_altitude_m','delta_timezone_hours')
        complete=all(values[k] is not None for values in (fa,fb) for k in keys)
        item['spatial_complete_both_players']=complete
        item['coarse_venue_reference_used']=any(values.get('coarse_venue_reference',False) for values in (fa,fb))
        item['eligible_spatial_probability_cohort']=complete and item['completed_standard'] and item['partition']!='boundary_quarantine'
        for name in keys:item['difference_'+name]=fa[name]-fb[name] if fa[name] is not None and fb[name] is not None else None
        rows.append(item)
    dataset=pd.DataFrame(rows)
    if not dataset.empty and dataset.groupby('block_id').partition.nunique().max()!=1:
        raise RuntimeError('Tournament was split across partitions')
    if not dataset.empty and dataset.groupby('comparison_block_id').partition.nunique().max()!=1:
        raise RuntimeError('Provider tie was split across partitions')
    report={'schema':'tennis-historical-spatial-dataset-v1','historical_reconstruction':True,
            'genuine_asof_validation':False,'n_history_matches':len(frame),'n_target_matches':len(dataset),
            'n_target_blocks':len(events),'edition_statuses':dict(Counter(e['venue_status'] for e in events)),
            'n_comparison_blocks':int(dataset.comparison_block_id.nunique()) if len(dataset) else 0,
            'n_with_target_venue':int(dataset.venue_id.notna().sum()) if len(dataset) else 0,
            'n_with_target_coordinates':int(dataset.target_coordinate_available.sum()) if len(dataset) else 0,
            'n_spatial_complete_both_players':int(dataset.spatial_complete_both_players.sum()) if len(dataset) else 0,
            'n_eligible_spatial_probability_cohort':int(dataset.eligible_spatial_probability_cohort.sum()) if len(dataset) else 0,
            'n_eligible_without_coarse_reference':int((dataset.eligible_spatial_probability_cohort & ~dataset.coarse_venue_reference_used).sum()) if len(dataset) else 0,
            'partitions':dataset.groupby('partition').size().to_dict() if len(dataset) else {},
            'player_feature_statuses':dict(Counter(v['status'] for v in features.values())),
            'edition_catalog':events,'metrics_computed':False,'financial_validation':False,'probabilities_modified':False,
            'rest_imputed':False,'later_unknown_locations_skipped':False,
            'source_period_overlap_guard_days':6}
    return dataset,report


def partition(block: dict[str,Any]) -> str:
    """Whole editions and a declared calendar-boundary embargo; no fake hours.

    The 2024 December and cross-year 2025 editions are kept in the dataset but
    quarantined from this first comparison. This is an operational embargo,
    not a claim about the actual last match date.
    """
    year=int(block['tourney_id'].split('-')[0])
    if year==2024 and block['last']<'2024-12-01':return 'development_2024'
    if year==2025 and block['first']>='2025-01-01':return 'exploratory_2025'
    return 'boundary_quarantine'
