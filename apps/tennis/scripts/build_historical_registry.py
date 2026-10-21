"""Build exact edition links from archived annual directories and edition notes."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re,unicodedata,argparse
import pandas as pd

ROOT=Path('data/tennis/historical_venues_20261018');ORIG=ROOT/'originals'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--config',type=Path,required=True)
CONFIG=parser.parse_args().config
def norm(t):return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',t).encode('ascii','ignore').decode().lower())
sources={};venues={};links={};reviews=[]
def source(folder):
    r=json.loads((ORIG/folder/'receipt.json').read_text())
    assert r['http_status']==200,(folder,r['http_status'])
    assert hashlib.sha256(Path(r['source_path']).read_bytes()).hexdigest()==r['sha256']
    sources[r['source_id']]=r;return r['source_id']

# Reviewed OSM object IDs: candidate order is never an identity rule.
normal='qtc:517533462 memorial:266282674 asb:1274535561 melbourne:220550128 sudfrance:114965156 marseille:231935931 ahoy:2788817376 baltc:53183618 delray:3369747254 jockey:15018420 cabo:1415169347 dubai:1110956736 indianwells:18810425 hardrock:171419981 estoril:91026888 riveroaks:123419610 montecarlo:1264875621 rctb:120291810 iphitos:241941631 nastase:23731450 foro:938775337 geneva:45770172 roland:39316077 autotron:12031461138 owl:33711828 queens:55149713 newport:366690870 iga:2676968 sobeys:612276897 cincy:654094498 usta:663795041 sichuan:1561457689 uber:25007895 chase:579646390 ariake:541648366 beijing:48050631 shanghai:126723499 lotto:30800728 almaty:10082036 stockholm:4880577 basel:38859151 vienna:6802681 accor:252506849 defense:14479234 metz:544572370 belgrade:146854025'
photon='victoria:962060333 ford:518594979 khalifa:154915951 gnp:1110609310 caja:1095415226 teteor:4077207 weissenhof:29841988 aeltc:4268203 rothenbaum:136964940 rockcreek:1028703073 wake:1028563434 turin:41753512 jeddah:504162355'
refined='kitz:11126224 hangzhou:9874418 athens:5855718221'
accepted={}
for prefix,text in [('geo',normal),('photon',photon),('refined',refined)]:
    for pair in text.split():
        k,identity=pair.split(':');accepted[k]=(prefix,identity)
accepted.update({k:('geo',i) for k,i in {
    'sonoma':'158890883','porsche':'1069797443','romai':'1316672789',
}.items()})
# Extend only after a separate human-readable candidate review.
extra=CONFIG/'reviewed_osm_objects.json'
if extra.exists():accepted.update({k:tuple(v) for k,v in json.loads(extra.read_text()).items()})

specs={}
for line in (CONFIG/'atp_specs.txt').read_text().splitlines():
    key,name,city,country,zone,codes,fragment=line.split('|');specs[key]=(name,city,country,zone,codes,fragment)
for key,(name,city,country,zone) in json.loads((CONFIG/'wta_specs.json').read_text()).items():
    specs[key]=(name,city,country,zone,'','')
for key,(name,city,country,zone,codes,fragment) in specs.items():
    v={'venue_id':key,'name':name,'city':city,'country':country,'timezone':zone,'lat':None,'lon':None,
       'altitude_m':None,'coordinate_sources':[],'altitude_sources':[],
       'coordinate_status':'not_yet_verified','altitude_scope':'terrain_DEM_not_measured_court'}
    if key in accepted:
        prefix,identity=accepted[key];folder=prefix+'_'+key;sid=source(folder)
        raw=json.loads((ORIG/folder/'response.json').read_text(encoding='utf8'))
        if prefix=='photon':
            p=next(x for x in raw['features'] if str(x['properties']['osm_id'])==identity)
            lon,lat=p['geometry']['coordinates'];feature=p['properties']
        else:
            matches=[x for x in raw if str(x['osm_id'])==identity]
            assert len(matches)==1,(key,identity,[str(x['osm_id']) for x in raw])
            p=matches[0];lat,lon=float(p['lat']),float(p['lon']);feature={k:p.get(k) for k in ['osm_type','osm_id','name','type','namedetails']}
        allowance={'jockey':1500,'riveroaks':2000,'teteor':1200,'jeddah':2000,'autotron':800,'wake':800,'ariake':800,'aeltc':800,'hardrock':900}.get(key,600)
        v.update(lat=lat,lon=lon,coordinate_sources=[sid],coordinate_scope='venue_geometry_representative',coordinate_precision_m=allowance,coordinate_status='reviewed_OSM_object',coordinate_feature=feature)
    venues[key]=v

# Physical points can be reused; historical edition bindings cannot.
old=json.loads(Path('data/tennis/coordinates_20261018/registry_seed_elevation.json').read_text())
oldv={v['venue_id']:v for v in old['venues']};olds={s['source_id']:s for s in old['sources']}
for key,oldkey in {'brussels':'brussels_p12','guangzhou':'guangzhou_nansha','ningbo':'ningbo_yinzhou','osaka':'osaka_utsubo','monastir':'monastir_magic','wuhan':'wuhan_optics'}.items():
    v=oldv[oldkey];fs=v['field_sources']
    coordinate_sources=list(dict.fromkeys(fs.get('coordinates',[])+fs.get('lat',[])+fs.get('lon',[])))
    altitude_sources=fs.get('altitude_m',[])
    # field_sources is a list of source IDs per audited field.
    assert isinstance(coordinate_sources,list)
    for sid in coordinate_sources+altitude_sources:sources[sid]=olds[sid]
    venues[key]={k:v.get(k) for k in ['name','city','country','timezone','lat','lon','coordinate_scope','coordinate_precision_m','coordinate_feature','altitude_m','altitude_scope']}
    venues[key].update(venue_id=key,coordinate_sources=coordinate_sources,altitude_sources=altitude_sources,
                       coordinate_status='same_physical_venue_reused_no_edition_inheritance')

rawtargets={}
for year in (2024,2025):
    for circuit,suffix in [('ATP',''),('WTA','_wta')]:
        raw=pd.read_csv(Path('data/tennis/full_20261016/tml/originals')/f'{year}{suffix}.csv',dtype=str)
        rawtargets[circuit,year]=set(raw.tourney_id)
def bind(circuit,year,code,key,sids,fact,page=None):
    tid=f'{year}-{code}'
    if tid not in rawtargets[circuit,year]:return
    identity=f'{circuit}:tour:{tid}';assert identity not in links,identity
    links[identity]={'circuit':circuit,'phase':'tour','tourney_id':tid,'venue_id':key,'evidence_season':year,
                     'edition_sources':sids,'edition_fact':fact,'pdf_page':page,'reconstruction_only':True}
overrides={(2025,'ford'):'dallas_2025',(2025,'brussels'):'brussels_2025',
           (2024,'hangzhou'):'hangzhou_2024',(2024,'belgrade'):'belgrade_2024',(2025,'athens'):'athens_2025'}
shared={'qtc':'800','memorial':'2014','melbourne':'901','indianwells':'609','hardrock':'902','caja':'1038','foro':'709','roland':'903','aeltc':'904','usta':'905','autotron':'822','devonshire':'710','cincy':'1017','rockcreek':'1045'}
for year in (2024,2025):
    pages=json.loads((ROOT/f'guide_{year}_directory_extract.json').read_text());sid=source(f'atp_guide_{year}')
    for key,(_,_,_,_,codes,fragment) in specs.items():
        for code in filter(None,codes.split(',')):
            if '@' in code:
                code,only=code.split('@')
                if int(only)!=year:continue
            if code=='96':continue  # Olympic edition has independent ITF evidence below.
            if f'{year}-{code}' not in rawtargets['ATP',year]:continue
            if (year,key) in overrides:
                evidence=source(overrides[year,key]);page=None;fact='Edition-specific historical correction: '+venues[key]['name']
            else:
                query={'queens':'SITE The Queen','beijing':'Beijing, China'}.get(key,fragment)
                candidates=[p for p in pages if norm(query) in norm(p['text'])] if fragment!='OVERRIDE' else []
                if len(candidates)!=1:
                    reviews.append({'year':year,'key':key,'reason':'annual_site_fragment_not_unique','fragment':fragment});continue
                evidence=sid;page=candidates[0]['pdf_page'];fact=fragment
            bind('ATP',year,code,key,[evidence],fact,page)
            if key in shared:
                # The same-year directory must explicitly identify a combined event,
                # except the shared Grand Slam event itself.
                p=next((p for p in pages if p['pdf_page']==page),None)
                position=norm(p['text']).find(norm(fragment)) if p else -1
                before=norm(p['text'])[:position][-350:] if p else ''
                if key in ('melbourne','roland','aeltc','usta') or 'atptourwtacombinedevent' in before:
                    bind('WTA',year,shared[key],key,[evidence],fact+'; same-year combined event/Grand Slam',page)
                else:reviews.append({'year':year,'key':key,'reason':'WTA_shared_venue_requires_independent_confirmation'})

# Edition notes: never extend a fact from one season to the other.
wta={
'2024-1023':'guangzhou','2024-1039':'sonoma','2024-1051':'porsche','2024-1074':'victoria',
'2024-1077':'jiujiang','2024-2036':'romai','2024-2040':'nautica','2024-2072':'monastir',
'2024-2092':'ningbo','2024-405':'osaka','2024-406':'strasbourg','2024-806':'sobeys','2024-894':'bogota',
'2025-1020':'beijing','2025-1074':'victoria','2025-1077':'jiujiang','2025-2075':'guadalajara',
'2025-2092':'ningbo','2025-804':'charleston','2025-1005':'rabat','2025-1075':'wuhan',
'2025-1080':'nottingham','2025-1082':'prague','2025-1111':'queens','2025-1139':'villa',
'2025-2012':'berlin','2025-2017':'homburg','2025-2042':'rothenbaum','2025-2063':'ciric','2025-2082':'westwood'}
for tid,key in wta.items():
    year,code=map(int,tid.split('-'));sid=source(f'wta_{year}_{code}')
    bind('WTA',year,str(code),key,[sid],'Venue field in edition-specific WTA preview; PDF first-page review',1)
for circuit,code in [('ATP','96'),('WTA','650')]:
    bind(circuit,2024,code,'roland',[source('olympics_2024')],'Paris 2024 Olympic Tennis Event: Roland Garros')

# Load only independently collected DEM values at the accepted exact points.
dem=ROOT/'originals/historical_elevation/receipt.json'
if dem.exists():
    sid=source('historical_elevation');rec=json.loads(dem.read_text());values=json.loads(Path(rec['source_path']).read_bytes())['elevation']
    for key,height in zip(rec['venue_ids'],values,strict=True):
        assert [venues[key]['lat'],venues[key]['lon']]==rec['venue_coordinates'][key]
        venues[key].update(altitude_m=height,altitude_sources=[sid],altitude_scope='OpenMeteo_Copernicus_GLO90_terrain_at_representative_point')

used={l['venue_id'] for l in links.values()}
registry={'schema':'tennis-historical-venue-links-v1','historical_reconstruction':True,'genuine_asof_validation':False,
          'created_at':datetime.now(timezone.utc).isoformat(),'sources':list(sources.values()),
          'venues':[v for k,v in venues.items() if k in used],'links':list(links.values()),
          'review_queue':reviews,'rest_imputed':False,'2026_edition_links_inherited':0,
          'coordinate_precision_note':'Conservative spatial representativeness allowance, not surveyed error or confidence interval',
          'excluded_multivenue_events':['United Cup','Davis Cup','Billie Jean King Cup']}
(ROOT/'registry.json').write_text(json.dumps(registry,indent=2,ensure_ascii=True))
print(json.dumps({'links':len(links),'venues':len(used),'georeferenced':sum(v.get('lat') is not None for k,v in venues.items() if k in used),'review_queue':reviews},indent=2))

