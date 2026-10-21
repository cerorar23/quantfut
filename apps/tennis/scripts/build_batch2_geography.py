"""Versioned, offline five-venue extension with explicit geographic allowances.

Run from the data workspace; preserve all historical edition bindings. Palermo
is a compound reference inferred from its operator address and mapped tennis
complex, not a surveyed historical court. Reader extracts are identified as such.
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
root=Path('data/tennis/historical_geography_batch2_20261018')
parent=Path('data/tennis/historical_geography_top5_20261018/registry.json')
sha=lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
reg=load_historical_registry(parent)
before=json.loads(parent.read_text(encoding='utf8'))
sites={v['venue_id']:v for v in reg['venues']}
sources={s['source_id']:s for s in reg['sources']}
reviews=[]

def source(key):
    receipt=json.loads((root/'originals'/key/'receipt.json').read_text(encoding='utf8'))
    assert receipt.get('http_status')==200 or receipt.get('retrieval_method')=='web_reader_extract_with_observed_outbound_link'
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
        coordinate_scope=scope,coordinate_sources=ids,coordinate_status='reviewed_batch2_historical_extension',
        coordinate_feature=feature,coordinate_reference_note=note)
    reviews.append(dict(venue_id=key,point=list(point),precision_m=precision,sources=ids,
        reason=note,feature=feature,corroborating_point=check,corroborating_distance_m=distance))

_,raw=source('chennai_owner');text=raw.decode('utf8')
assert 'Chennai+Tennis+Stadium' in text and '!3d13.056551!4d80.2389454' in text
way,check=geometry('chennai_area',23186312)
assert way['tags']['sport']=='tennis' and way['tags']['wikidata']=='Q3533459'
add('chennai',(13.056551,80.2389454),500,['chennai_owner','chennai_map','chennai_area'],
    'Tennis association links this stadium place point, not the hockey stadium or the map viewport. Named OSM tennis stadium corroborates the facility; historical edition unchanged.',
    {'owner_place_point':True,'osm_way':23186312},check,scope='venue_point')

_,raw=source('palermo_owner');text=raw.decode('utf8')
assert "Viale dell'Olimpo, 5" in text and '90149 Palermo' in text
way,point=geometry('palermo_area',262811284)
assert way['tags']['leisure']=='sports_centre'
_,raw=source('palermo_area');data=json.loads(raw)
assert any(x.get('tags',{}).get('name')=="Viale dell'Olimpo" for x in data['elements'])
assert all(next(x for x in data['elements'] if x['type']=='way' and x['id']==i)['tags']['sport']=='tennis' for i in range(631280385,631280398))
assert any(x.get('tags',{}).get('name')=='Country Discoclub' for x in data['elements'])
add('palermo',point,750,['palermo_owner','palermo_home','palermo_area'],
    'Compound reference: operator address Viale dell Olimpo 5 is matched to the mapped sports compound with clustered tennis courts and Country Discoclub on that street. OSM compound has no name tag; identity is a reviewed geographic inference, not an exact historical court position. Wrong Addaura beach resort and generic city points rejected.',
    {'osm_way':262811284,'identity_method':'operator_address_and_tennis_compound_context','complex_reference':True,'named_osm_object':False})

_,raw=source('riyadh_reader');text=raw.decode('utf8')
assert '24.727892296786052%2C46.6221849' in text and 'King Saud University Indoor Arena' in text
way,check=geometry('riyadh_area',667480100)
assert way['tags']['name:en']=='King Saud University Indoor Arena'
add('riyadh',(24.727892296786052,46.6221849),500,['riyadh_wta','riyadh_reader','riyadh_area'],
    'Official WTA links to webook; reader-observed arena outbound map query supplies this point. The map itself was not fetched successfully. Allowance covers the difference from named indoor arena geometry; Al-Awwal football stadium and swimming pool rejected. HTTP200 challenge page is not evidence.',
    {'official_outbound_map_point':True,'osm_way':667480100,'map_target_loaded':False},check,scope='venue_point')

_,raw=source('hengqin_geo');point=next(x for x in json.loads(raw) if x['osm_type']=='way' and x['osm_id']==435045112)
assert point['extratags']['sport']=='tennis' and 'Hengqin International Tennis Center' in str(point)
key='team_179e9596-3f85-4976-8e88-bfa8d59fe7ce'
sites[key]['timezone']='Asia/Shanghai'
add(key,(float(point['lat']),float(point['lon'])),600,['hengqin_owner','hengqin_geo'],
    'Named native WGS84 OSM tennis compound corroborated by Huafa operator address in Hengqin, Zhuhai. Mainland China IANA timezone filled explicitly. Historical Davis Cup group venue link remains unchanged; no Chinese GCJ02 point used.',
    {'osm_way':435045112,'timezone_verified':'Asia/Shanghai','complex_reference':True})

_,raw=source('shenzhen_reader');assert '3001' in raw.decode('utf8')
way,point=geometry('shenzhen_area',665408865)
assert way['tags']['name']=='\u6df1\u5733\u6e7e\u4f53\u80b2\u9986' and way['tags']['sport']=='multi'
complex_way,check=geometry('shenzhen_area',542049855)
assert complex_way['tags']['addr:housenumber']=='3001'
add('bjkc_shenzhen_bay',point,500,['shenzhen_reader','shenzhen_geo','shenzhen_area'],
    'Bounding-box centre of the named Shenzhen Bay indoor gymnasium, not its football stadium, pool or public tennis courts. Municipal source confirms complex address 3001 Binhai Avenue; existing ITF 2025 venue evidence identifies the arena. Government HTML request failed TLS; source is explicitly a web-reader extract.',
    {'osm_way':665408865,'parent_osm_way':542049855,'representative_method':'outer_ring_bbox_midpoint'},check)

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
    reconstruction_extension='five_priority_venues_batch2_20261018',geography_review=reviews)
output=root/('registry_pre_elevation.json' if args.stage=='coordinates' else 'registry.json')
assert not output.exists(),'Immutable registry already exists'
output.write_text(json.dumps(reg,indent=2),encoding='utf8');load_historical_registry(output)
if args.stage=='final':(root/'coordinate_review.json').write_text(json.dumps(reviews,indent=2),encoding='utf8')
print(json.dumps(dict(stage=args.stage,reviewed=reviews)))
