"""Consolidate the complete manually reviewed geography queue, offline.

No candidate geocoder result is auto-approved. IDs, map geometries and literal
published points are checked against immutable source receipts. An ambiguous
historical campus stays missing; aliases retain separate edition bindings.
"""
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import argparse, copy, hashlib, json, math, sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tennis_engine.historical_dataset import load_historical_registry
from tennis_engine.context import haversine_km

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--stage',choices=['coordinates','final'],default='final')
args=p.parse_args()
root=Path('data/tennis/historical_geography_complete_20261018')
parent=Path('data/tennis/historical_geography_batch3_20261018/registry.json')
sha=lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
reg=load_historical_registry(parent);before=copy.deepcopy(reg)
sites={v['venue_id']:v for v in reg['venues']};sources={s['source_id']:s for s in reg['sources']}
reviews=json.loads((root/'reviewed_locations.json').read_text(encoding='utf8'))
assert len(reviews)==73 and len({r['venue_id'] for r in reviews})==73
assert {r['venue_id'] for r in reviews}=={v['venue_id'] for v in reg['venues'] if v.get('lat') is None}

def source(key):
    rec=json.loads((root/'originals'/key/'receipt.json').read_text(encoding='utf8'))
    assert rec.get('http_status')==200 or rec.get('retrieval_method')=='web_search_extract_of_operator_page',key
    assert sha(rec['source_path'])==rec['sha256'],key
    if rec['source_id'] in sources:assert sources[rec['source_id']]==rec
    sources[rec['source_id']]=rec
    return rec['source_id'],Path(rec['source_path']).read_bytes(),rec

resolved=[];pending=[]
for review in reviews:
    key=review['venue_id'];v=sites[key]
    if 'alias_of' in review:pending.append(review);continue
    ids=[source(k)[0] for k in review.get('additional_sources',[])]
    if review['method']=='unresolved_historical_campus':
        v.update(coordinate_status='reviewed_historical_campus_ambiguous',coordinate_reference_note=review['note'],
            unresolved_candidate_venues=review['candidate_venues'],identity_review_sources=ids)
        continue
    sid,raw,receipt=source(review['source_key']);ids.insert(0,sid)
    method=review['method'];feature={'method':method};scope='venue_geometry_representative'
    if method=='nominatim':
        candidates=[x for x in json.loads(raw) if x['osm_id']==review['osm_id']]
        assert len(candidates)==1,(key,'non-unique object')
        place=candidates[0]
        assert place.get('category',place.get('class')) not in ['highway','place','boundary'],(key,'not a venue')
        point=(float(place['lat']),float(place['lon']))
        feature.update(osm_id=place['osm_id'],osm_type=place['osm_type'],name=place.get('name'),provider_representative_point=True)
    elif method=='photon':
        data=json.loads(raw);candidates=[x for x in data['features'] if x['properties']['osm_id']==review['osm_id']]
        assert len(candidates)==1,(key,'non-unique photon object')
        place=candidates[0];coords=place['geometry']['coordinates'];assert place['geometry']['type']=='Point'
        assert place['properties']['osm_key'] not in ['highway','place','boundary'],(key,'not a venue')
        point=(coords[1],coords[0]);feature.update(osm_id=review['osm_id'],properties=place['properties'],provider_representative_point=True)
    elif method=='osm_geometry':
        data=json.loads(raw);obj=next(x for x in data['elements'] if x['type']==review['osm_type'] and x['id']==review['osm_id'])
        for k,val in review['required_tags'].items():assert obj['tags'][k]==val,(key,k)
        if obj['type']=='node':point=(obj['lat'],obj['lon'])
        else:
            assert obj['type']=='way';nodes={e['id']:e for e in data['elements'] if e['type']=='node'}
            pts=[nodes[n] for n in set(obj['nodes'])]
            point=tuple((min(x[k] for x in pts)+max(x[k] for x in pts))/2 for k in ['lat','lon'])
            radius=max(haversine_km(point,(x['lat'],x['lon']))*1000 for x in pts)
            assert radius<review['precision_m'],(key,'geometry exceeds allowance',radius)
            feature['geometry_radius_m']=radius
        if review.get('corroborating_relation'):
            relation=next(e for e in data['elements'] if e['type']=='relation' and e['id']==review['corroborating_relation'])
            assert relation.get('tags',{}).get('name');feature['corroborating_relation']=relation['id']
        feature.update(osm_id=obj['id'],osm_type=obj['type'],tags=obj.get('tags'),representative_method='native_node_or_bbox_midpoint')
    elif method=='official_point':
        assert review['point_pattern'] in raw.decode('utf8',errors='replace') or review['point_pattern'] in receipt.get('final_url',''),(key,'literal point not found')
        point=(review['lat'],review['lon']);scope='venue_point';feature['published_point_literal']=review['point_pattern']
    else:raise ValueError(method)
    ZoneInfo(review['timezone']);assert all(math.isfinite(c) for c in point)
    v.update(lat=point[0],lon=point[1],timezone=review['timezone'],coordinate_precision_m=review['precision_m'],
        coordinate_scope=scope,coordinate_sources=list(dict.fromkeys(ids)),coordinate_status='reviewed_complete_historical_extension',
        coordinate_feature=feature,coordinate_reference_note=review['note'])
    resolved.append(key)

# Dependencies may refer to another newly reviewed venue. Resolve topologically.
while pending:
    progressed=False
    for review in list(pending):
        target=sites[review['alias_of']]
        if target.get('lat') is None:continue
        v=sites[review['venue_id']]
        fields=['lat','lon','timezone','altitude_m','coordinate_scope','coordinate_precision_m','coordinate_sources','altitude_sources','altitude_scope']
        for field in fields:
            if field in target:v[field]=copy.deepcopy(target[field])
        v['coordinate_sources']=list(dict.fromkeys(v['coordinate_sources']+[source(k)[0] for k in review.get('additional_sources',[])]))
        v.update(coordinate_status='reviewed_complete_historical_alias',coordinate_reference_note=review['note'],
            coordinate_feature={'alias_of':review['alias_of'],'identity_relation':review['identity_relation']})
        pending.remove(review);progressed=True
    assert progressed,'Alias cycle or unresolved dependency'

if args.stage=='final':
    sid,raw,receipt=source('elevation');heights=json.loads(raw)['elevation']
    assert receipt['venue_ids']==resolved and len(heights)==len(resolved)
    for key,height in zip(resolved,heights,strict=True):
        assert receipt['venue_coordinates'][key]==[sites[key]['lat'],sites[key]['lon']]
        sites[key].update(altitude_m=height,altitude_sources=[sid],altitude_scope='OpenMeteo_Copernicus_GLO90_terrain_at_representative_point')
    # Refresh heights on aliases only after all new reference points have heights.
    aliases=[r for r in reviews if 'alias_of' in r]
    for _ in range(len(aliases)+1):
        for r in aliases:
            v=sites[r['venue_id']];target=sites[r['alias_of']]
            for field in ['altitude_m','altitude_sources','altitude_scope']:v[field]=copy.deepcopy(target[field])
    assert all(v['altitude_m'] is not None for v in sites.values() if v.get('lat') is not None)
assert reg['links']==before['links'] and reg['match_links']==before['match_links']
reg.update(created_at=datetime.now(timezone.utc).isoformat(),sources=list(sources.values()),
    parent_registry_sha256=sha(parent),parent_registry_path=str(parent.resolve()),
    reconstruction_extension='complete_queue_review_20261018',geography_review=reviews,
    georeferencing_policy='No arbitrary hours or city centroids. Unresolved historical campus remains unavailable.',
    elevation_request_venue_order=resolved)
output=root/('registry_pre_elevation.json' if args.stage=='coordinates' else 'registry.json')
assert not output.exists(),'Immutable registry already exists'
output.write_text(json.dumps(reg,indent=2,ensure_ascii=False),encoding='utf8');load_historical_registry(output)
if args.stage=='final':(root/'coordinate_review.json').write_text(json.dumps(reviews,indent=2),encoding='utf8')
print(json.dumps(dict(stage=args.stage,reviewed=len(reviews),new_points=len(resolved),georeferenced=sum(v.get('lat') is not None for v in sites.values()),unresolved=[v['venue_id'] for v in sites.values() if v.get('lat') is None])))
