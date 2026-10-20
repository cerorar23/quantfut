"""Versioned, offline five-venue extension with explicit geographic allowances.

Run from the data workspace; preserve all historical edition bindings. Biel is
a National Performance Centre compound reference, not a surveyed arena court.
Taipei operator evidence is explicitly a search extract rather than raw HTML.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, re, sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tennis_engine.context import haversine_km
from tennis_engine.historical_dataset import load_historical_registry

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--stage', choices=['coordinates','final'], default='final')
args=p.parse_args()
root=Path('data/tennis/historical_geography_batch3_20261018')
parent=Path('data/tennis/historical_geography_batch2_20261018/registry.json')
sha=lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
reg=load_historical_registry(parent)
before=json.loads(parent.read_text(encoding='utf8'))
sites={v['venue_id']:v for v in reg['venues']}
sources={s['source_id']:s for s in reg['sources']}
reviews=[]

def source(key):
    receipt=json.loads((root/'originals'/key/'receipt.json').read_text(encoding='utf8'))
    assert receipt.get('http_status')==200 or receipt.get('retrieval_method')=='web_search_extract_of_operator_page'
    assert sha(receipt['source_path'])==receipt['sha256']
    sources[receipt['source_id']]=receipt
    return receipt['source_id'], Path(receipt['source_path']).read_bytes()

def geometry(key, identity):
    _,raw=source(key);data=json.loads(raw)
    way=next(x for x in data['elements'] if x['type']=='way' and x['id']==identity)
    nodes={x['id']:x for x in data['elements'] if x['type']=='node'}
    points=[nodes[i] for i in set(way['nodes'])]
    centre=((min(x['lat'] for x in points)+max(x['lat'] for x in points))/2,
            (min(x['lon'] for x in points)+max(x['lon'] for x in points))/2)
    return way, centre

def add(key,point,precision,keys,note,feature,check=None,scope='venue_geometry_representative'):
    assert sites[key]['lat'] is None
    ids=[source(k)[0] for k in keys]
    distance=None if check is None else 1000*haversine_km(point,check)
    assert distance is None or distance<precision
    sites[key].update(lat=point[0],lon=point[1],coordinate_precision_m=precision,
        coordinate_scope=scope,coordinate_sources=ids,coordinate_status='reviewed_batch3_historical_extension',
        coordinate_feature=feature,coordinate_reference_note=note)
    reviews.append(dict(venue_id=key,point=list(point),precision_m=precision,sources=ids,
        reason=note,feature=feature,corroborating_point=check,corroborating_distance_m=distance))


# Reviewed venue-specific evidence follows.
_,raw=source('taipei_reader');assert '208' in raw.decode('utf8')
way,point=geometry('taipei_area',189781451)
assert way['tags']['sport']=='tennis' and way['tags']['addr:housenumber']=='208'
assert way['tags']['wikidata']=='Q10914205'
key='team_56b54517-3b88-40b7-afe0-d1b5999702fe'
sites[key]['timezone']='Asia/Taipei'
add(key,point,500,['taipei_reader','taipei_area'],
    'Native WGS84 geometry of the tennis sports centre at Minquan East Road section 6, number 208. Operator search extract confirms address; direct requests failed TLS/connection and are not accepted evidence. Bicycle rental station with same name rejected. Reference covers complex, not surveyed historical court.',
    {'osm_way':189781451,'representative_method':'outer_ring_bbox_midpoint','timezone_verified':'Asia/Taipei','complex_reference':True})

_,raw=source('bologna_government');assert b'2025' in raw and b'37' in raw
_,raw=source('bologna_federation');assert b'2025' in raw and b'37' in raw
way,point=geometry('bologna_area',41260142)
assert way['tags']['alt_name']=='Padiglione 37' and way['tags']['name']=='Virtus Arena'
add('team_b2e8ba1c-02c3-4197-9327-b7576dca3609',point,500,
    ['bologna_government','bologna_federation','bologna_area'],
    'BolognaFiere pavilion 37 venue geometry, temporarily converted from Virtus Arena for the 2025 Davis Cup Finals. Federation and regional authority identify the 2025 event site and pavilions 36/37. Not Unipol Arena in Casalecchio and not the new pavilion planned for 2026. No historic edition links changed.',
    {'osm_way':41260142,'representative_method':'outer_ring_bbox_midpoint','pavilion':'37','season_context':2025})

_,raw=source('manchester_owner');text=raw.decode('utf8')
assert 'Victoria Station' in text and 'M3 1AR' in text
_,raw=source('manchester_geo');p=next(x for x in json.loads(raw) if x['osm_type']=='way' and x['osm_id']==354135390)
assert p['name']=='AO Arena' and p['address']['postcode']=='M3 1AR' and p['extratags']['website']=='https://www.ao-arena.com/'
add('manchester_ao',(float(p['lat']),float(p['lon'])),500,['manchester_owner','manchester_geo'],
    'Named AO Arena stadium geometry whose website and postcode agree with the operator at Manchester Victoria Station. Not the railway station centroid or another Manchester arena.',
    {'osm_way':354135390,'provider_representative_point':True})

_,raw=source('vilnius_owner');assert 'SEB arena' in raw.decode('utf8')
_,raw=source('vilnius_city');text=raw.decode('utf8')
assert 'https://www.google.com/maps/dir//54.70699120,25.23477640' in text
_,raw=source('vilnius_geo');p=next(x for x in json.loads(raw) if x['osm_type']=='way' and x['osm_id']==199382037)
assert p['name']=='SEB Arena' and p['address']['house_number']=='7' and p['extratags']['sport']=='tennis'
key='team_b1c9a351-5fdd-4ef8-a577-a17068d9d9a2';sites[key]['timezone']='Europe/Vilnius'
add(key,(54.70699120,25.23477640),500,['vilnius_owner','vilnius_city','vilnius_geo'],
    'Go Vilnius publishes this venue map point for SEB Arena central court at Azuolyno 7; named OSM tennis complex agrees on address. It includes hotel facilities, so the municipality arena reference is retained rather than claiming the OSM centroid is the exact court. Not Arena Vilnius or Bernardinu courts.',
    {'municipal_outbound_map_point':True,'osm_way':199382037,'timezone_verified':'Europe/Vilnius'},
    (float(p['lat']),float(p['lon'])),scope='venue_point')

_,raw=source('biel_owner');text=raw.decode('utf8');assert 'Roger-Federer-Allee 1' in text and 'Event-Arena' in text
_,raw=source('biel_arena');text=raw.decode('utf8');assert '2017' in text and 'Swiss Tennis Arena' in text
way,point=geometry('biel_area',213588055)
assert way['tags']['addr:housenumber']=='1' and way['tags']['addr:street']=='Roger-Federer-Allee' and way['tags']['sport']=='tennis'
key='team_71d6081c-de61-4c06-80dd-774e65674b34';sites[key]['timezone']='Europe/Zurich'
add(key,point,600,['biel_owner','biel_arena','biel_contact','biel_area'],
    'Reference to the National Performance Centre compound at Roger-Federer-Allee 1; operator explicitly places its event arena within the centre. Geometry represents the named tennis training hall, not a separately verified event-arena footprint. 600m allowance retains that uncertainty. Nearby Swiss Tennis bus stop and Tissot Arena rejected.',
    {'osm_way':213588055,'representative_method':'outer_ring_bbox_midpoint','complex_reference':True,'arena_footprint_verified':False,'timezone_verified':'Europe/Zurich'})

expected={r['venue_id'] for r in reviews};assert len(expected)==5
if args.stage=='final':
    sid,raw=source('elevation');receipt=sources[sid];heights=json.loads(raw)['elevation']
    assert len(heights)==len(receipt['venue_ids'])==5 and set(receipt['venue_ids'])==expected
    for key,height in zip(receipt['venue_ids'],heights,strict=True):
        assert receipt['venue_coordinates'][key]==[sites[key]['lat'],sites[key]['lon']]
        sites[key].update(altitude_m=height,altitude_sources=[sid],altitude_scope='OpenMeteo_Copernicus_GLO90_terrain_at_representative_point')
assert reg['links']==before['links'] and reg['match_links']==before['match_links']
assert {v['venue_id'] for v in before['venues'] if v!=sites[v['venue_id']]}==expected
reg.update(created_at=datetime.now(timezone.utc).isoformat(),sources=list(sources.values()),
    parent_registry_sha256=sha(parent),parent_registry_path=str(parent.resolve()),
    reconstruction_extension='five_priority_venues_batch3_20261018',geography_review=reviews)
output=root/('registry_pre_elevation.json' if args.stage=='coordinates' else 'registry.json')
assert not output.exists(),'Immutable registry already exists'
output.write_text(json.dumps(reg,indent=2),encoding='utf8');load_historical_registry(output)
if args.stage=='final':(root/'coordinate_review.json').write_text(json.dumps(reviews,indent=2),encoding='utf8')
print(json.dumps(dict(stage=args.stage,reviewed=reviews)))
