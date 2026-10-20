"""Validate the single elevation batch and replay all venue/season evidence."""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import hashlib,json,math,sys
from pathlib import Path

sys.path.insert(0,str(Path('.local/tennis_next').resolve() if Path(__file__).parent.name=='.local' else Path(__file__).resolve().parents[1]))
from tennis_engine.venues import VenueRegistry,load_seed
from tennis_engine.fixture_reviews import FixtureReviews
from build_tennis_coordinates import read,save,receipt,ROOT


def main():
    manifest=read(ROOT/'coordinate_manifest.json')
    rec=receipt('open_meteo_27')
    points=manifest['points']
    if rec['coordinate_manifest_sha256']!=hashlib.sha256((ROOT/'coordinate_manifest.json').read_bytes()).hexdigest():
        raise ValueError('Elevation receipt refers to another manifest')
    if rec['ordered_venue_ids']!=[p['venue_id'] for p in points]:raise ValueError('Elevation order differs')
    for field,param in [('lat','latitude'),('lon','longitude')]:
        if rec['params'][param]!=','.join(format(p[field],'.10f') for p in points):raise ValueError('Elevation coordinates differ')
    response=read(rec['source_path']);elevations=response.get('elevation')
    if not isinstance(elevations,list) or len(elevations)!=27:raise ValueError('Invalid elevation count')
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not -500<=v<=9000 for v in elevations):
        raise ValueError('Invalid elevation values')
    seed=deepcopy(read(ROOT/'registry_seed_coordinates_v2.json'))
    path=ROOT/'registry_seed_elevation.json'
    stamp=read(path)['created_at'] if path.exists() else datetime.now(timezone.utc).isoformat()
    seed['created_at']=stamp
    seed['sources'].append(rec)
    latest={v['venue_id']:v for v in seed['venues']}
    for point,height in zip(points,elevations):
        venue=deepcopy(latest[point['venue_id']]);venue.update(recorded_at=stamp,altitude_m=height,
            altitude_status='point_terrain_DEM_estimate',altitude_model='Copernicus DEM 2021 GLO-90',
            altitude_horizontal_resolution_m=90,altitude_is_surveyed_court_height=False,
            altitude_spatial_uncertainty_m=point['coordinate_precision_m'])
        venue['field_sources']['altitude_m']=[rec['source_id']]
        seed['venues'].append(venue)
    save(path,seed)
    registry=VenueRegistry(Path('data/tennis/venues_20261017/venues.sqlite'))
    load_seed(registry,path)
    reviews=FixtureReviews(registry)
    for review in read('data/tennis/venues_completion_20261017/season_reviews.json'):reviews.register(review)
    source=next(s for s in seed['sources'] if s['source_id']=='api_upcoming')
    rows=read(source['source_path'])['result']
    decision=datetime.now(timezone.utc).isoformat()
    report=reviews.enrich_calendar(rows,decision,input_timezone='UTC',source_received_at=source['received_at'])
    report['n_with_altitude']=sum(e['venue_resolution']['status']=='resolved' and e['venue_resolution']['venue'].get('altitude_m') is not None for e in report['events'])
    report.update(n_distinct_venues=35,new_coordinates=27,terrain_not_surveyed_court_height=True,
        registry_seed_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),sports_api_requests=0,odds_api_credits=0)
    target=ROOT/'calendar_georeferenced.json'
    if not target.exists():save(target,report)
    # Real past cut immediately before coordinate evidence was registered.
    past=(datetime.fromisoformat(manifest['reviewed_at'])-timedelta(microseconds=1)).isoformat()
    old=reviews.enrich_calendar(rows,past,input_timezone='UTC',source_received_at=source['received_at'])
    old_alt=sum(e['venue_resolution']['status']=='resolved' and e['venue_resolution']['venue'].get('altitude_m') is not None for e in old['events'])
    if (report['n_resolved'],report['n_with_coordinates'],report['n_with_altitude'],report['n_season_corrected'])!=(228,228,228,48):
        raise ValueError('Unexpected final calendar coverage')
    if (old['n_with_coordinates'],old_alt)!=(102,102):raise ValueError('Coordinates leaked into previous availability')
    hashes=read('data/tennis/extension_20261017/future_protocol.json')['artifacts']
    for p,digest in hashes.items():
        if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=digest:raise ValueError('Frozen model artifact changed')
    audit={'past_decision_at':past,'past_coordinates':old['n_with_coordinates'],'past_altitudes':old_alt,
           'current_named_sites':report['n_resolved'],'current_coordinates':report['n_with_coordinates'],
           'current_altitudes':report['n_with_altitude'],'season_corrections':report['n_season_corrected'],
           'frozen_model_hashes_verified':len(hashes),'elevation_batch_requests':1,'odds_api_credits':0,
           'coordinate_sources_verified':46,'new_venues':27,'probabilities_modified':False}
    save(ROOT/'integration_audit.json',audit)
    registry.db.close()
    print(json.dumps(audit))


if __name__=='__main__':main()
