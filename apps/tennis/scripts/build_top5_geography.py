"""Apply five reviewed venue references to a new historical registry, offline.

Edition bindings and existing coordinates are immutable. The broad Yucatan
reference is explicitly a complex point, not an assumed historical court.
"""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,re,hashlib,argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tennis_engine.context import haversine_km
from tennis_engine.historical_dataset import load_historical_registry

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--stage',choices=('coordinates','final'),default='final')
args=parser.parse_args()
root=Path('data/tennis/historical_geography_top5_20261018');orig=root/'originals'
parent=Path('data/tennis/historical_coverage_20261018/registry.json')
reg=load_historical_registry(parent);original=json.loads(parent.read_text())
sources={s['source_id']:s for s in reg['sources']};sites={v['venue_id']:v for v in reg['venues']}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
reviews=[]

def source(key):
    r=json.loads((orig/key/'receipt.json').read_text())
    if r.get('http_status')!=200:raise ValueError('Only successful archived evidence is accepted: '+key)
    if sha(r['source_path'])!=r['sha256']:raise ValueError('Source hash differs: '+key)
    if 'openstreetmap.org' in r['url']:r.update(attribution='OpenStreetMap contributors, ODbL',crs='EPSG:4326')
    sources[r['source_id']]=r
    return r['source_id'],Path(r['source_path']).read_bytes()

def add(key,lat,lon,precision,scope,keys,reason,feature,crosscheck):
    assert key in sites and sites[key].get('lat') is None
    assert -90<=lat<=90 and -180<=lon<=180 and precision>0
    ids=[source(k)[0] for k in keys]
    distance=None if crosscheck is None else haversine_km((lat,lon),crosscheck)*1000
    if distance is not None:assert distance<precision,(key,distance,precision)
    sites[key].update(lat=lat,lon=lon,coordinate_precision_m=precision,coordinate_scope=scope,
        coordinate_sources=ids,coordinate_status='reviewed_top5_historical_extension',
        coordinate_feature=feature,coordinate_reference_note=reason)
    reviews.append(dict(venue_id=key,latitude=lat,longitude=lon,precision_m=precision,
        coordinate_scope=scope,coordinate_sources=ids,reason=reason,feature=feature,
        corroborating_point=None if crosscheck is None else list(crosscheck),corroborating_distance_m=distance,
        corroboration_method='coordinate_comparison' if crosscheck is not None else 'operator_identity_and_named_geographic_object'))

# Hua Hin: the actual place point in the map embedded by the arena, not viewport.
_,raw=source('owner_huahin_map');text=raw.decode('utf8',errors='replace')
assert 'Arena Hua Hin' in text and '77110' in text
points=set(re.findall(r'\[(12\.[0-9]+),(99\.[0-9]+)\]',text));assert len(points)==1
lat,lon=map(float,next(iter(points)))
_,raw=source('osm_huahin_area');data=json.loads(raw)
arena=next(o for o in data['elements'] if o['type']=='way' and o['id']==1068701726)
assert arena['tags']['sport']=='tennis' and arena['tags']['website']=='https://arenahuahin.com/'
nodes={o['id']:o for o in data['elements'] if o['type']=='node'}
coords=[nodes[i] for i in set(arena['nodes'])]
check=(sum(p['lat'] for p in coords)/len(coords),sum(p['lon'] for p in coords)/len(coords))
add('huahin',lat,lon,500,'venue_point',['owner_huahin_net','owner_huahin_map','osm_huahin_area'],
    'Arena owner embeds this place point; same-named OSM tennis complex links to that owner. Historical season bindings remain unchanged.',
    {'owner_map_place_point':True,'osm_way':1068701726},check)

# Yucatan: the owner's compound pin is deliberately broad. The mapped tennis
# area is a cross-check, not a claim about the court position in 2024/2025.
sid,raw=source('owner_merida_map');url=sources[sid]['final_url']
m=re.search(r'!3d([0-9.]+)!4d(-[0-9.]+)',url);assert m and 'Yucatan+Country+Club' in url
lat,lon=map(float,m.groups())
_,raw=source('osm_merida_area');data=json.loads(raw)
tennis=next(o for o in data['elements'] if o['type']=='way' and o['id']==1359255118)
assert tennis['tags']['sport']=='tennis' and tennis['tags']['name']=='Merida Open Akron'
nodes={o['id']:o for o in data['elements'] if o['type']=='node'};coords=[nodes[i] for i in set(tennis['nodes'])]
check=(sum(p['lat'] for p in coords)/len(coords),sum(p['lon'] for p in coords)/len(coords))
add('merida',lat,lon,1800,'venue_point',['owner_merida_net','owner_merida_map','osm_merida_area'],
    'Owner-linked Yucatan Country Club compound reference. Not the village node and not a surveyed historical court. 1800m allowance covers the separately mapped tennis area; coarse-reference sensitivity must exclude it.',
    {'owner_map_place_point':True,'osm_tennis_area_crosscheck':1359255118,'complex_reference':True},check)

# Seoul: stadium multipolygon geometry, rather than an Olympic Park-wide pin.
_,raw=source('osm_seoul_area');data=json.loads(raw)
rel=next(o for o in data['elements'] if o['type']=='relation' and o['id']==8679966)
assert rel['tags']['sport']=='tennis' and rel['tags']['addr:housenumber']=='424'
nodes={o['id']:o for o in data['elements'] if o['type']=='node'};ways={o['id']:o for o in data['elements'] if o['type']=='way'}
ids={i for member in rel['members'] if member['type']=='way' and member['role']=='outer' for i in ways[member['ref']]['nodes']}
coords=[nodes[i] for i in ids]
lat=(min(p['lat'] for p in coords)+max(p['lat'] for p in coords))/2
lon=(min(p['lon'] for p in coords)+max(p['lon'] for p in coords))/2
_,raw=source('seoul_wikidata');claims=json.loads(raw)['entities']['Q7451681']['claims']['P625']
assert len(claims)==1
point=claims[0]['mainsnak']['datavalue']['value'];assert point['globe']=='http://www.wikidata.org/entity/Q2'
add('seoul',lat,lon,500,'venue_geometry_representative',['owner_seoul_net','osm_seoul_area','seoul_wikidata'],
    'Representative bounding-box centre of the mapped tennis stadium. Official operator address matches; the structured venue point corroborates this facility, not the whole park.',
    {'osm_relation':8679966,'representative_method':'outer_ring_bbox_midpoint','corroborating_wikidata':'Q7451681'},(point['latitude'],point['longitude']))

# Abu Dhabi: tennis stadium, explicitly not the nearby football stadium.
_,raw=source('geo_zayed_net');points=json.loads(raw)
point=next(p for p in points if p['osm_type']=='way' and p['osm_id']==93051899)
assert point['extratags']['sport']=='tennis' and point['namedetails']['name:en']=='Abu Dhabi International Tennis Centre'
lat,lon=float(point['lat']),float(point['lon'])
assert 24.412<lat<24.416 and 54.458<lon<54.461
add('zayed',lat,lon,500,'venue_geometry_representative',['owner_zayed_net','geo_zayed_net'],
    'Named OSM tennis stadium and operator description of the International Tennis Centre; football stadium coordinates rejected.',
    {'osm_way':93051899,'sport':'tennis','provider_representative_point':True},None)

# Malaga: explicit government GeoCoordinates, corroborated by stadium geometry.
_,raw=source('government_carpena_net');text=raw.decode('utf8')
assert 'GeoCoordinates' in text and 'Mart' in text
lat=float(re.search(r'"latitude":\s*"([0-9.]+)"',text)[1]);lon=float(re.search(r'"longitude":\s*"(-[0-9.]+)"',text)[1])
_,raw=source('carpena_geo');point=next(p for p in json.loads(raw) if p['osm_type']=='way' and p['osm_id']==1235193701)
assert point['type']=='stadium'
add('martin_carpena',lat,lon,400,'venue_point',['government_carpena_net','carpena_geo'],
    'Regional government publishes the arena GeoCoordinates; named stadium object corroborates them. The similarly named taxi rank is rejected.',
    {'government_geo_coordinates':True,'osm_way':1235193701},(float(point['lat']),float(point['lon'])))

expected={'huahin','merida','seoul','zayed','martin_carpena'}
assert {r['venue_id'] for r in reviews}==expected
if args.stage=='final':
    sid,raw=source('elevation');receipt=sources[sid];heights=json.loads(raw)['elevation']
    assert len(heights)==len(receipt['venue_ids'])==5 and set(receipt['venue_ids'])==expected
    for key,height in zip(receipt['venue_ids'],heights,strict=True):
        assert receipt['venue_coordinates'][key]==[sites[key]['lat'],sites[key]['lon']]
        sites[key].update(altitude_m=height,altitude_sources=[sid],altitude_scope='OpenMeteo_Copernicus_GLO90_terrain_at_representative_point')
assert reg['links']==original['links'] and reg['match_links']==original['match_links']
before={v['venue_id']:v for v in original['venues']}
assert {k for k in sites if sites[k]!=before[k]}==expected
reg.update(created_at=datetime.now(timezone.utc).isoformat(),sources=list(sources.values()),
    parent_registry_sha256=sha(parent),parent_registry_path=str(parent.resolve()),
    reconstruction_extension='five_priority_venues_20261018',geography_review=reviews)
name='registry_pre_elevation.json' if args.stage=='coordinates' else 'registry.json'
path=root/name
if path.exists():raise ValueError('Registry version already exists; preserve the published artifact')
path.write_text(json.dumps(reg,indent=2))
load_historical_registry(path)
if args.stage=='final':(root/'coordinate_review.json').write_text(json.dumps(reviews,indent=2))
print(json.dumps({'stage':args.stage,'coordinate_count':sum(v.get('lat') is not None for v in sites.values()),'reviewed':reviews},indent=2))
