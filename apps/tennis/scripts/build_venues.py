"""Build/replay a reviewed edition-aware registry from archived sources only."""
import argparse
from collections import Counter
import hashlib,json
from pathlib import Path

from tennis_engine.context import haversine_km
from tennis_engine.operations import now
from tennis_engine.venues import VenueRegistry,load_seed


def build_seed(root: Path,probe: Path) -> dict:
    sources=[]
    for receipt in json.loads((root/'research_manifest.json').read_text(encoding='utf-8')):
        if receipt.get('http_status')==200:sources.append(receipt)
    for name in ('osm_venues','osm_ningbo'):
        receipt=json.loads((root/'originals'/name/'receipt.json').read_text(encoding='utf-8'))
        if receipt['http_status']!=200:raise ValueError('Successful mapped geometry source required')
        sources.append(receipt)
    manifest={r['label']:r for r in json.loads((probe/'manifest.json').read_text())}
    for name in ('tournaments','upcoming'):
        r=manifest[name]
        sources.append({'source_id':'api_'+name,'url':'https://api.api-tennis.com/tennis/',
            'method':r['method'],'received_at':r['received_at'],'source_path':str((probe/(name+'.json')).resolve()),
            'sha256':r['sha256'],'parameters_without_credentials':r['params']})
    for source in sources:
        if hashlib.sha256(Path(source['source_path']).read_bytes()).hexdigest()!=source['sha256']:
            raise ValueError('Source archive changed')
    points={p['venue_id']:p for p in json.loads((root/'reviewed_points.json').read_text())}
    catalog={str(t['tournament_key']):t for t in json.loads((probe/'tournaments.json').read_bytes())['result']}
    fixture_rows=json.loads((probe/'upcoming.json').read_bytes())['result']
    types={str(r['tournament_key']):r['event_type_type'] for r in fixture_rows}
    stamp=now()
    specifications=[
        ('almaty_arena','Almaty Arena','Almaty','KZ','Asia/Almaty','almaty',True,'api_tournaments'),
        ('lyon_ldlc','LDLC Arena','Decines-Charpieu','FR','Europe/Paris','lyon',True,'api_tournaments'),
        ('brussels_p12','ING Arena / Palais 12','Brussels','BE','Europe/Brussels','brussels',True,'api_tournaments'),
        ('brussels_p5','Brussels Expo / Palais 5','Brussels','BE','Europe/Brussels','brussels',True,'api_tournaments'),
        ('shanghai_qizhong','Qizhong Tennis Center','Shanghai','CN','Asia/Shanghai','shanghai',None,None),
        ('wuhan_optics','Optics Valley International Tennis Center','Wuhan','CN','Asia/Shanghai','wuhan',False,'wuhan'),
        ('ningbo_yinzhou','Ningbo Yinzhou Tennis Center','Ningbo','CN','Asia/Shanghai','ningbo',False,'ningbo'),
        ('osaka_utsubo','Morita Tennis Center Utsubo','Osaka','JP','Asia/Tokyo','osaka_wta',False,'osaka_wta'),
    ]
    timezone_table=Path(next(s for s in sources if s['source_id']=='iana_zones')['source_path']).read_text()
    venues=[]
    for identity,name,city,country,timezone,official,indoor,indoor_source in specifications:
        if not any(timezone in line.split() for line in timezone_table.splitlines() if not line.startswith('#')):
            raise ValueError('Timezone not present in archived IANA table')
        p=points[identity]
        precision=250.
        if 'osm_id' in p:
            payload=json.loads((root/'originals'/p['source_id']/'response.json').read_bytes())
            element=next(e for e in payload['elements'] if e['id']==p['osm_id'] and e['type']==p['osm_type'])
            geometry=element.get('geometry',[])+[x for m in element.get('members',[]) for x in m.get('geometry',[])]
            precision=max(100.,haversine_km((min(x['lat'] for x in geometry),min(x['lon'] for x in geometry)),
                                      (max(x['lat'] for x in geometry),max(x['lon'] for x in geometry)))*500)
        fields={'name':[official],'city':[official],'country':[official],'timezone':['iana_zones'],
                'coordinates':[p['source_id']]}
        if indoor is not None:fields['indoor']=[indoor_source]
        venues.append({'venue_id':identity,'name':name,'city':city,'country':country,'timezone':timezone,
            'lat':p['lat'],'lon':p['lon'],'coordinate_scope':'venue_geometry_representative' if 'osm_id' in p else 'venue_point',
            'coordinate_precision_m':round(precision,1),'coordinate_feature':p,
            'altitude_m':None,'altitude_status':'not_verified','indoor':indoor,
            'indoor_scope':'published_tournament_classification_not_live_roof_state',
            'roof_state_at_match':None,'recorded_at':stamp,'field_sources':fields})
    # These are explicit reviewed aliases, never inferred from matching city strings.
    editions=[
        ('atp:almaty:2026',['11851','11853'],'Almaty','almaty_arena','2026-10-17','2026-10-26','almaty'),
        ('atp:lyon:2026',['14763'],'Lyon (France) - Qualification','lyon_ldlc','2026-10-18','2026-10-26','lyon'),
        ('atp:brussels:2026',['3669','9159'],'Brussels','brussels_p12','2026-10-17','2026-10-23','brussels'),
        ('atp:brussels:2026',['3669','9159'],'Brussels','brussels_p5','2026-10-23','2026-10-26','brussels'),
        ('atp:shanghai:2026',['1667','8656'],'Shanghai','shanghai_qizhong','2026-10-05','2026-10-19','shanghai_government'),
        ('wta:wuhan:2026',['2236','8696'],'Wuhan','wuhan_optics','2026-10-12','2026-10-19','wuhan'),
        ('wta:ningbo:2026',['10180','10186'],'Ningbo','ningbo_yinzhou','2026-10-18','2026-10-26','ningbo'),
        ('wta:osaka:2026',['1666','8657'],'Osaka','osaka_utsubo','2026-10-17','2026-10-26','osaka'),
    ]
    bindings=[];venue_index={v['venue_id']:v for v in venues}
    for edition,identities,name,venue_id,start,end,source in editions:
        for identity in identities:
            t=catalog[identity]
            if t['tournament_name']!=name or t['event_type_type']!=types[identity] or not t['tournament_sourface'].startswith('Hard'):
                raise ValueError('Reviewed provider alias no longer matches catalog')
            bindings.append({'binding_id':'api_tennis:'+identity+':2026:'+start,'provider':'api_tennis',
                'provider_tournament_id':identity,'provider_event_type':types[identity],'season':'2026','edition_id':edition,
                'venue_id':venue_id,'valid_from':start,'valid_until':end,'timezone':venue_index[venue_id]['timezone'],
                'surface':'Hard','surface_sources':['api_tournaments'],'sources':[source,'api_upcoming','api_tournaments'],
                'recorded_at':stamp,'scope':'published_primary_tournament_site_not_confirmed_individual_court'})
    return {'schema':'tennis-venue-seed-v1','created_at':stamp,'sources':sources,'venues':venues,'bindings':bindings,
            'attribution':'Geometry: OpenStreetMap contributors, ODbL 1.0; LDLC coordinates: official venue structured data.',
            'osm_license_url':'https://www.openstreetmap.org/copyright',
            'limits':['No court-specific roof observation.','No surveyed altitude verified.',
                      'Metadata received now cannot backfill past forecast availability.',
                      'Coordinate precision is a conservative footprint scale, not a survey accuracy certificate.']}


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--probe-root',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    if args.report.exists():raise ValueError('Use a new report path')
    seed_path=args.root/'registry_seed.json'
    if not seed_path.exists():
        seed=build_seed(args.root,args.probe_root)
        with seed_path.open('x',encoding='utf-8') as stream:json.dump(seed,stream,indent=2,ensure_ascii=False)
    registry=VenueRegistry(args.root/'venues.sqlite');counts=load_seed(registry,seed_path)
    manifest={r['label']:r for r in json.loads((args.probe_root/'manifest.json').read_text())}
    raw=(args.probe_root/'upcoming.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=manifest['upcoming']['sha256'] or manifest['upcoming']['params'].get('timezone')!='UTC':
        raise ValueError('UTC fixture archive/receipt mismatch')
    rows=json.loads(raw)['result'];report=registry.enrich_calendar(rows,now(),input_timezone='UTC',
                      source_received_at=manifest['upcoming']['received_at'])
    primary=[r for r in report['events'] if r['event_type'] in ('Atp Singles','Atp Doubles','Wta Singles','Wta Doubles')]
    unresolved=Counter((r['tournament_name'],str(r['season']),r['event_type']) for r in report['events']
                       if r['venue_resolution']['status']!='resolved')
    report.update({'registry_counts':counts,'primary_tour_matches':len(primary),
        'primary_tour_resolved':sum(r['venue_resolution']['status']=='resolved' for r in primary),
        'provider_season_flags':sum(bool(r['review_flags']) for r in report['events']),
        'unresolved_groups':[{'name':k[0],'season':k[1],'type':k[2],'matches':v} for k,v in sorted(unresolved.items())],
        'input_sha256':hashlib.sha256(raw).hexdigest(),'registry_seed_sha256':hashlib.sha256(seed_path.read_bytes()).hexdigest(),
        'implementation_sha256':hashlib.sha256(Path(__import__('tennis_engine.venues',fromlist=['__file__']).__file__).read_bytes()).hexdigest(),
        'paid_api_requests':0})
    args.report.parent.mkdir(parents=True,exist_ok=True)
    with args.report.open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2,ensure_ascii=False)
    print(json.dumps({k:report[k] for k in ('n_total','n_resolved','n_with_coordinates','primary_tour_matches',
                                         'primary_tour_resolved','provider_season_flags','registry_counts')}))


if __name__=='__main__':main()
