"""Extend the historical registry with reviewed season and tie evidence."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re,html,unicodedata
ROOT=Path('data/tennis/historical_coverage_20261018');ORIG=ROOT/'originals'
old=Path('data/tennis/historical_venues_20261018/registry.json')
reg=json.loads(old.read_text());sources={x['source_id']:x for x in reg['sources']};venues={x['venue_id']:x for x in reg['venues']}
links={(x['circuit'],x['phase'],x['tourney_id']):x for x in reg['links']}
def source(key):
    path=ORIG/key/'receipt.json'
    if key.startswith('legacy/'):
        path=Path('data/tennis/historical_venues_20261018/originals')/key.removeprefix('legacy/')/'receipt.json'
    elif not path.exists():path=Path('data/tennis/historical_venues_20261018/originals')/key/'receipt.json'
    r=json.loads(path.read_text());assert r.get('http_status')==200,(key,r)
    assert hashlib.sha256(Path(r['source_path']).read_bytes()).hexdigest()==r['sha256']
    sources[r['source_id']]=r;return r['source_id']
def web_source(key,filename,url):
    f=ROOT/filename;receipt=ROOT/'web_reader_receipts.json'
    saved=json.loads(receipt.read_text()) if receipt.exists() else {}
    r=saved.get(key) or {'source_id':key,'url':url,'source_path':str(f.resolve()),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),
        'received_at':datetime.now(timezone.utc).isoformat(),'retrieval_method':'web_reader_extract','raw_pdf_archived':False}
    assert hashlib.sha256(f.read_bytes()).hexdigest()==r['sha256']
    saved[key]=r;receipt.write_text(json.dumps(saved,indent=2))
    sources[key]=r;return key
def add_site(key,name,city,country,zone=None):
    if key not in venues:venues[key]=dict(venue_id=key,name=name,city=city,country=country,timezone=zone,lat=None,lon=None,altitude_m=None,
        coordinate_sources=[],altitude_sources=[],coordinate_status='not_yet_verified',altitude_scope='terrain_DEM_not_measured_court')
def bind(year,code,venue,sids,fact,circuit='WTA',**extra):
    identity=(circuit,'tour',f'{year}-{code}');assert identity not in links,identity
    links[identity]=dict(circuit=circuit,phase='tour',tourney_id=identity[2],venue_id=venue,evidence_season=year,edition_sources=sids,
                        edition_fact=fact,reconstruction_only=True,**extra)

specs=json.loads((ROOT/'new_venue_candidates_specs.json').read_text())
zones={'hobart':'Australia/Hobart','linz':'Europe/Vienna','zayed':'Asia/Dubai','cluj':'Europe/Bucharest','barnes':'America/Los_Angeles',
       'rouen':'Europe/Paris','huahin':'Asia/Bangkok','merida':'America/Merida','riyadh':'Asia/Riyadh','chennai':'Asia/Kolkata',
       'singapore':'Asia/Singapore','palermo':'Europe/Rome','birmingham':'Europe/London','seoul':'Asia/Seoul'}
for key,zone in zones.items():
    v=specs[key];add_site(key,v['name'],v['city'],v['country'],zone)
mapping={'1050':'hobart','528':'linz','2088':'zayed','2050':'cluj','1003':'khalifa','718':'dubai','2074':'barnes','2066':'rouen',
    '1005':'rabat','2012':'berlin','2017':'homburg','2063':'ciric','1082':'prague','1045':'rockcreek','2075':'guadalajara',
    '1121':'huahin','1020':'beijing','2085':'merida','808':'riyadh','894':'bogota','1051':'porsche','806':'iga','1039':'sonoma',
    '405':'osaka','1023':'guangzhou','1056':'ariake','1148':'chennai'}
for record in json.loads((ROOT/'wta_found.json').read_text()):
    year,code=record['edition_id'].split('-');key=mapping[code];r=record['source'];sources[r['source_id']]=r
    bind(int(year),code,key,[r['source_id']],record['venue_lines'][0],evidence_grade='official_season_preview')

manual={
'2024-1049':('asb','auckland2024','ASB Classic 2024 at ASB Tennis Arena'),
'2024-2082':('westwood','atx2024','2024 ATX Open at Westwood Country Club'),
'2024-804':('charleston','charleston2024','2024 event at Live to Play Daniel Island, home of Credit One Stadium'),
'2024-1080':('nottingham','lta_grass2024','2024 grass-season media guide: Nottingham Tennis Centre'),
'2024-1052':('birmingham','lta_grass2024','2024 grass-season media guide: Edgbaston Priory Club'),
'2024-1024':('seoul','seoul2024_edition','2024 Korea Open structured edition explicitly located at Q7451681; corroborated by official 2024 page'),
'2024-1075':('wuhan','wuhan2024','October 2024 draw announcement at Optics Valley International Tennis Center'),
'2024-1056':('ariake','tokyo2024','Tokyo metropolitan government fiscal-year-2024 archive: Toray tournament at Ariake Coliseum'),
'2025-1049':('asb','auckland2025','2025 ASB Classic ticket terms: ASB Tennis Arena December 30 2024 to January 11 2025'),
'2025-1055':('singapore','singapore2025','January 2025 organiser release: Kallang Tennis Hub, January 27-February 2; TML ID retained'),
'2025-2085':('merida','merida2025','January 2025 organiser announcement: Yucatan Country Club'),
'2025-406':('strasbourg','strasbourg2025_interview','2025 organiser interview: Tennis Club de Strasbourg renovations'),
'2025-1024':('seoul','seoul2025','September 2025 WTA announcement: Seoul Olympic Park Tennis Center')}
for tid,(key,src,fact) in manual.items():
    year,code=tid.split('-');sid=source(src);sids=[sid]
    grade='official_season_source'
    if src=='seoul2024_edition':sids.append(source('seoul2024_official'));grade='official_season_page_and_structured_edition_corroboration'
    if src=='strasbourg2025_interview':grade='firsthand_organiser_interview'
    bind(int(year),code,key,sids,fact,evidence_grade=grade)
for tid,key,url in [('2024-466','palermo','https://wtafiles.wtatennis.com/pdf/matchnotes/2024/466_P.pdf'),
                    ('2025-2040','nautica','https://wtafiles.wtatennis.com/pdf/matchnotes/2025/2040_P.pdf')]:
    y,code=tid.split('-');sid=web_source('coverage_web_'+tid,'web_reader_wta.json',url)
    bind(int(y),code,key,[sid],'Venue field in archived web-reader extraction of edition-specific official PDF',evidence_grade='official_preview_web_reader_extract')
sid=web_source('coverage_web_huahin2024','web_reader_huahin.json','https://thai.tourismthailand.org/Articles/thailand-open-2024')
bind(2024,'1096','huahin',[sid],'Tourism Authority of Thailand January 18 2024 announcement: Arena Hua Hin, January 29-February 4',evidence_grade='government_season_article_web_reader_extract')

# Reviewed object IDs: reject company offices, parking, villages and homonyms.
approved_ids='1332611895 636288920 1274535561 673174982 1141856882 2676968 713458589 617665891 3781106 552156654 229102705 5646897 221151032 382210548 529469197 872343226 110616292 220474821 320617666 4356481857 19913562 146348530 81318842 1205396662 35842070 100876286 391594117 118762477 1191239201 25446687 11500914669 12552234990 191296414 553574575 1113005905 794212198 3369747254 449590605 137725849 10891178 598236198 745521408 10399036 15280511 210654887 610927073 133751858 1436148795 89430799'.split()
country_zones={'Vietnam':'Asia/Ho_Chi_Minh','Uzbekistan':'Asia/Tashkent','New Zealand':'Pacific/Auckland','Finland':'Europe/Helsinki',
'Netherlands':'Europe/Amsterdam','Canada':'America/Toronto','Sweden':'Europe/Stockholm','El Salvador':'America/El_Salvador',
'Argentina':'America/Argentina/Cordoba','Bulgaria':'Europe/Sofia','Croatia':'Europe/Zagreb','Togo':'Africa/Lome','Paraguay':'America/Asuncion',
'Malaysia':'Asia/Kuala_Lumpur','Bolivia':'America/La_Paz','Italy':'Europe/Rome','Spain':'Europe/Madrid','Romania':'Europe/Bucharest',
'Cyprus':'Asia/Nicosia','Poland':'Europe/Warsaw','Serbia':'Europe/Belgrade','Belgium':'Europe/Brussels','Norway':'Europe/Oslo','Austria':'Europe/Vienna',
'Denmark':'Europe/Copenhagen','France':'Europe/Paris','Zimbabwe':'Africa/Harare','Kazakhstan':'Asia/Almaty','Benin':'Africa/Porto-Novo',
'Slovenia':'Europe/Ljubljana','Ecuador':'America/Guayaquil','Peru':'America/Lima','Hungary':'Europe/Budapest','Australia':'Australia/Sydney','USA':'America/New_York','United States':'America/New_York'}
def point(key,lat,lon,sids,allowance=600,feature=None):
    assert venues[key]['timezone'],key
    venues[key].update(lat=float(lat),lon=float(lon),coordinate_sources=sids,coordinate_scope='venue_geometry_representative',
        coordinate_precision_m=allowance,coordinate_status='reviewed_physical_venue_or_published_venue_map',coordinate_feature=feature)
review=json.loads((ROOT/'team_links_review.json').read_text())
for record in review['links']:
    ed,t=record['edition'],record['official_tie'];v=t['venue'];key='team_'+v['id'];co=v.get('country',{}).get('name','')
    zone=country_zones.get(co)
    if co=='Canada' and v.get('city')=='Halifax':zone='America/Halifax'
    add_site(key,v['name'],v.get('city'),co,zone)
    identity=(ed['circuit'],'tour',ed['tourney_id']);assert identity not in links
    links[identity]=dict(circuit=ed['circuit'],phase='tour',tourney_id=ed['tourney_id'],venue_id=key,evidence_season=t['year'],
        edition_sources=[source('dc_draws_'+str(t['year']))],edition_fact='Official ITF bilateral tie: '+t['event_name'],
        official_tie_id=t['tie_id'],competition_group_id='ATP:ITF-tie:'+t['tie_id'],country_pair=[t['home'],t['away']],
        official_event_start_day=t['start'],reconstruction_only=True)
for record in json.loads((ROOT/'new_venue_candidates.json').read_text()):
    key=record['key']
    if key not in venues:continue
    accepted=[p for p in record['points'] if str(p['osm_id']) in approved_ids]
    if len(accepted)!=1:continue
    p=accepted[0];r=record['source'];sources[r['source_id']]=r
    point(key,p['lat'],p['lon'],[r['source_id']],1200 if p.get('type')=='golf_course' else 700,
          {k:p.get(k) for k in ['osm_type','osm_id','name','type','display_name']})

# Independent evidence for the original seventeen missing physical points.
for key in ['devonshire','bastad','gstaad']:
    sid=source('wikidata_'+key);r=sources[sid];d=json.loads(Path(r['source_path']).read_bytes())
    entity=next(iter(d['entities'].values()));coords=entity['claims']['P625'][0]['mainsnak']['datavalue']['value']
    point(key,coords['latitude'],coords['longitude'],[sid],500,{'wikidata_id':entity['id']})
sid=source('wikidata_extra_venues');d=json.loads(Path(sources[sid]['source_path']).read_bytes())
for key,qid in [('guadalajara','Q5156398'),('prague','Q12058625')]:
    c=d['entities'][qid]['claims']['P625'][0]['mainsnak']['datavalue']['value']
    point(key,c['latitude'],c['longitude'],[sid],500,{'wikidata_id':qid})
for key in ['smu','mallorca']:
    folder='smu_official_map' if key=='smu' else 'mallorca_map';sid=source(folder);url=sources[sid]['url']
    m=re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)',url);assert m
    point(key,*m.groups(),[sid,source(key+'_official')],600,{'method':'official venue links to this map; viewport/address representative, not court pin'})
for key in ['marrakech','bogota']:
    sid=source('waze_'+key);text=Path(sources[sid]['source_path']).read_text(encoding='utf8')
    m=re.search(r'"latitude":(-?\d+\.\d+),"longitude":(-?\d+\.\d+)',text);assert m
    point(key,*m.groups(),[sid],600,{'method':'named place structured GeoCoordinates, not map viewport'})
sid=source('prague_map');url=sources[sid]['url'];m=re.search(r'x=(-?\d+\.\d+)&y=(-?\d+\.\d+)',url);assert m
point('prague',m[2],m[1],[sid,source('prague_contact'),source('wikidata_extra_venues')],500)
sid=source('homburg_osm');p=json.loads(Path(sources[sid]['source_path']).read_bytes())['elements'][0]
point('homburg',p['lat'],p['lon'],[sid,source('homburg_city')],500,{'method':'official club address matches OSM house number 20, postcode 61348'})
sid=source('geo_ciric');raw=json.loads(Path(sources[sid]['source_path']).read_bytes());p=next(p for p in raw if p['osm_id']==1415200131)
point('ciric',p['lat'],p['lon'],[sid],600,{'osm_id':1415200131})
for key,folder,way_id in [('santiago','santiago_osm',1418182801),('umag','umag_osm',1416830841)]:
    sid=source(folder);data=json.loads(Path(sources[sid]['source_path']).read_bytes())['elements']
    way=next(x for x in data if x['type']=='way' and x['id']==way_id)
    nodes={x['id']:x for x in data if x['type']=='node'};points=[nodes[n] for n in set(way['nodes'])]
    lat=(min(x['lat'] for x in points)+max(x['lat'] for x in points))/2
    lon=(min(x['lon'] for x in points)+max(x['lon'] for x in points))/2
    point(key,lat,lon,[sid],600,{'osm_id':way_id,'method':'reviewed venue footprint bounds representative'})
sid=source('atlanta_address');data=json.loads(Path(sources[sid]['source_path']).read_bytes());p=next(x for x in data if x['osm_id']==1211153871)
point('atlanta',p['lat'],p['lon'],[sid,source('atlanta_faq')],600,{'osm_id':1211153871,'method':'Pinnacle Lot address identified by venue owner, not generic Atlantic Station neighborhood'})
sid=source('legacy/geo_kempes');data=json.loads(Path(sources[sid]['source_path']).read_bytes());p=next(x for x in data if x['osm_id']==154248210)
point('kempes',p['lat'],p['lon'],[sid,'atp_guide_2024'],1800,{'osm_id':154248210,'method':'Kempes complex reference point; temporary tennis courts adjacent to stadium, not surveyed court coordinates'})
sid=source('geo_nautica');data=json.loads(Path(sources[sid]['source_path']).read_bytes());p=next(x for x in data if x['osm_id']==966617750)
point('nautica',p['lat'],p['lon'],[sid,source('nautica_owner')],700,{'osm_id':966617750,'method':'Jacobs Pavilion at Nautica; organiser confirms tennis venue, temporary court footprint not individually surveyed'})
sid=source('jiujiang_osm_area');data=json.loads(Path(sources[sid]['source_path']).read_bytes())['elements']
p=next(x for x in data if x['type']=='node' and x['id']==2691079690)
point('jiujiang',p['lat'],p['lon'],[sid,source('jiujiang_complex')],1600,
      {'osm_id':2691079690,'method':'named Jiujiang Sports Center WGS84 reference; dated 2024 local report places International Tennis Center inside this complex; not an individual court coordinate',
       'rejected_alternative':'Trip.com explicitly marks its point GCJ02; it is not copied as WGS84'})

# Additional reviewed points are independent, explicit choices with receipts.
extra=ROOT/'reviewed_extra_points.json'
if extra.exists():
    for p in json.loads(extra.read_text()):
        point(p['venue_id'],p['lat'],p['lon'],[source(k) for k in p['source_folders']],p['allowance_m'],p.get('feature'))

from coverage_team_completion import extend
reg=extend(reg,source,add_site,bind,venues,links,ROOT)
sid=source('perth_rac_geo');p=next(x for x in json.loads(Path(sources[sid]['source_path']).read_bytes()) if x['osm_id']==150405797)
point('perth_rac',p['lat'],p['lon'],[sid],600,{'osm_id':150405797})
# Aliases concern the same physical facility, with independent season/tie links.
def namekey(s):return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',s or '').encode('ascii','ignore').decode().lower())
aliases={'asbtennisarena':'asb','igastadium':'iga','stadeiga':'iga','delraybeachtenniscenter':'delray',
         'theroyaltennishall':'stockholm','royaltennishall':'stockholm','kungligatennishallen':'stockholm',
         'victoriaparktennisstadium':'victoria','ariakecolosseum':'ariake','ariakecoliseum':'ariake',
         'clubsonoma':'sonoma','kenrosewallarena':'sydney_kenrosewall'}
for key,v in venues.items():
    other=aliases.get(namekey(v['name']))
    if other and other!=key and v.get('lat') is None and venues[other].get('lat') is not None:
        known=venues[other]
        v.update({k:known.get(k) for k in ['timezone','lat','lon','coordinate_scope','coordinate_precision_m','coordinate_sources','altitude_m','altitude_sources','coordinate_feature']})
        v['coordinate_status']='same_physical_venue_alias_reviewed'

reg.update(created_at=datetime.now(timezone.utc).isoformat(),parent_registry_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),
           venues=list(venues.values()),links=list(links.values()),sources=list(sources.values()),
           excluded_multivenue_events=[],reconstruction_extension='coverage_20261018',
           original_pending_wta_editions_linked=52,initial_team_review_queue=review['unresolved'],
           team_review=reg['team_review_summary']['unresolved_match_locations'])
# DEM enrichment is optional until the finite batch has been received.
receipt=ORIG/'elevation/receipt.json'
if receipt.exists():
    sid=source('elevation');r=sources[sid];values=json.loads(Path(r['source_path']).read_bytes())['elevation']
    for key,height in zip(r['venue_ids'],values,strict=True):
        assert [venues[key]['lat'],venues[key]['lon']]==r['venue_coordinates'][key]
        venues[key].update(altitude_m=height,altitude_sources=[sid],altitude_scope='OpenMeteo_Copernicus_GLO90_terrain_at_representative_point')
    reg['sources']=list(sources.values())
(ROOT/'registry.json').write_text(json.dumps(reg,indent=2))
print(json.dumps({'links':len(links),'venues':len(venues),'georeferenced':sum(v.get('lat') is not None for v in venues.values()),
                  'original_17_pending':[k for k in ['kempes','smu','santiago','marrakech','mallorca','devonshire','bastad','gstaad','atlanta','umag','jiujiang','nautica','bogota','guadalajara','prague','homburg','ciric'] if venues[k].get('lat') is None]},indent=2))
