"""Build a reviewed coordinate manifest from cached originals; no geocoding calls.

Selections are explicit object IDs, not first-result or fuzzy acceptance.
Geometry representatives describe the published complex, not a match court.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path('data/tennis/coordinates_20261018')
OLD = Path('data/tennis/venues_completion_20261017/registry_seed_completed.json')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, value):
    path = Path(path)
    text = json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False)
    if path.exists():
        if read(path) != value:
            raise ValueError(f'Existing artifact differs: {path}')
    else:
        path.write_text(text, encoding='utf-8')


def receipt(folder):
    r = read(ROOT/'originals'/folder/'receipt.json')
    if r.get('http_status') != 200:
        raise ValueError(f'Unsuccessful original: {folder}')
    if hashlib.sha256(Path(r['source_path']).read_bytes()).hexdigest() != r['sha256']:
        raise ValueError(f'Changed original: {folder}')
    return r


def browser_extract(key, url, text):
    """Public place facts transcribed from the observed browser accessibility tree.

    This is a fact extract, explicitly not an archived HTTP response or full DOM.
    No account, history, review authors or other incidental UI are retained.
    """
    folder = ROOT/'originals'/key
    folder.mkdir(exist_ok=True)
    rp = folder/'receipt.json'
    if rp.exists():
        return receipt(key)
    f = folder/'public_fact_extract.json'
    save(f, {'kind':'browser_public_place_fact_extract', 'url':url, 'text':text})
    stamp = datetime.now(timezone.utc).isoformat()
    r = {'source_id':key, 'url':url, 'received_at':stamp,
         'http_status':200, 'http_status_note':'successful browser view; HTTP status not measured',
         'source_path':str(f.resolve()), 'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),
         'evidence_kind':'browser_public_place_fact_extract'}
    save(rp, r)
    return r


def build():
    ROOT.mkdir(exist_ok=True)
    base = read(OLD)
    venues = {v['venue_id']:v for v in base['venues']}
    points = []
    extra_sources = {}

    def add(identity, lat, lon, precision, folder, object_ids, note, *, scope='venue_geometry_representative', extras=()):
        src = receipt(folder)
        extra_sources[src['source_id']] = src
        ids = [src['source_id']]
        for extra in extras:
            r = receipt(extra)
            extra_sources[r['source_id']] = r
            ids.append(r['source_id'])
        ids += venues[identity]['field_sources']['name']
        points.append({'venue_id':identity, 'lat':lat, 'lon':lon,
                       'crs':'EPSG:4326', 'coordinate_scope':scope,
                       'coordinate_precision_m':precision,
                       'precision_interpretation':'conservative spatial representativeness allowance, not surveyed accuracy or statistical confidence interval',
                       'selected_object_ids':object_ids, 'source_ids':list(dict.fromkeys(ids)),
                       'review_note':note, 'actual_court_verified':False})

    def nom(identity, folder, osm_id, precision, note, extras=()):
        src = receipt(folder)
        matches = [r for r in read(src['source_path']) if str(r['osm_id']) == str(osm_id)]
        if len(matches) != 1:
            raise ValueError('Explicit OSM object missing or ambiguous')
        r = matches[0]
        add(identity, float(r['lat']), float(r['lon']), precision, folder,
            [f"{r['osm_type']}/{osm_id}"], note, extras=extras,
            scope='venue_point' if r['osm_type']=='node' else 'venue_geometry_representative')

    def photon(identity, folder, osm_id, precision, note, extras=()):
        src = receipt(folder)
        matches = [r for r in read(src['source_path'])['features'] if str(r['properties']['osm_id']) == str(osm_id)]
        if len(matches) != 1:
            raise ValueError('Explicit Photon object missing or ambiguous')
        r = matches[0]
        lon, lat = r['geometry']['coordinates']
        add(identity, lat, lon, precision, folder, [f"{r['properties']['osm_type']}/{osm_id}"], note, extras=extras)

    def geometry(identity, folder, way_ids, precision, note, extras=()):
        src = receipt(folder)
        t = ET.fromstring(Path(src['source_path']).read_bytes())
        nodes = {n.attrib['id']:(float(n.attrib['lat']),float(n.attrib['lon'])) for n in t.findall('node')}
        ways = {int(w.attrib['id']):w for w in t.findall('way')}
        coords = [nodes[n.attrib['ref']] for wid in way_ids for n in ways[wid].findall('nd')]
        lat = (min(a for a,b in coords)+max(a for a,b in coords))/2
        lon = (min(b for a,b in coords)+max(b for a,b in coords))/2
        add(identity, lat, lon, precision, folder, [f'way/{wid}' for wid in way_ids], note, extras=extras)

    nom('florence_matchball','nominatim_florence_matchball',183326121,300,'Exact named club in Bagno a Ripoli, Via della Massa; primary event venue agrees.')
    nom('fortworth_friedman','nominatim_fortworth_friedman',356844467,300,'Named Friedman Tennis Center on TCU campus, not Fort Worth city centre.')
    nom('cali_farallones','nominatim_refined_cali_farallones',10229626,1100,'Full Club Farallones polygon in Pance; broad club representative, not surveyed tennis courts.')
    geometry('guangzhou_nansha','osm_nansha_bbox',list(range(1428179581,1428179595)),450,
             'Tennis groups adjacent to named Nansha District Gymnasium way/561753033 and Jun Tai Hotel way/1428179580; municipal source identifies this complex. OSM WGS84, not an Amap/Google China coordinate.',extras=('nansha_city',))
    geometry('lisbon_cif','osm_lisbon_bbox_v2',[909202700],450,
             'Named CIF sports centre polygon links cif.org.pt and contains tennis courts; matches official school address Avenida dos Bombeiros.',extras=('official_lisbon_school',))
    geometry('catania_montekatira','osm_catania_bbox_v2',[77438995],250,
             'Named Tennis School Montekatira sports centre with Montecatira/Monte Catira aliases; official booking address Via Cantello 2 agrees.',extras=('official_catania_booking',))
    geometry('jinan_olympic','osm_jinan_bbox_v2',list(range(656197621,656197623))+list(range(656197624,656197631)),650,
             'Tennis court group on east side of Olympic Sports Center next to east indoor gym, not west football stadium. Conservative allowance includes tennis venue buildings; individual court unknown.')
    geometry('bol_zlatnirat','osm_bol_bbox_v2',[97452454,97452469,108927353,108927354,108927355,219584003,1097700910,1097700911,1097700912],400,
             'Main tennis cluster by Bluesun Elaphusa/Borak/Bonaca identified in operator tennis page. Excludes isolated private hotel court way/492865059.',extras=('bol_tennis',))
    geometry('heraklion_lyttos','osm_lyttos_bbox_v2',[907509786],300,
             'Named Lyttos Beach Tennis Academy building within main tennis group; excludes other nearby hotel tennis courts.',extras=('official_lyttos',))
    nom('heraklion_nana','nominatim_refined_heraklion_nana',10132777989,650,
        'Nana Golden Beach hotel complex location; ITF identifies tennis sports club at this resort. Spatial allowance covers adjacent tennis area.',extras=('official_nana',))
    nom('monastir_magic','nominatim_refined_monastir_magic',10077141,500,
        'Skanes Family Resort polygon; ITF Magic Hotel venue identity agrees. Resort representative, not exact court.',extras=('official_skanes',))

    extracts = {
      'browser_ntc':('https://www.google.com/maps/place/Centrul+Na%C8%9Bional+de+Tenis/data=!4m6!3m5!1s0x40c9796946d7ea2b:0x58baa3bf98e55d54!8m2!3d46.9513028!4d28.9044722!16s%2Fg%2F11xw7ynx_3',
        'Centrul National de Tenis; address Spiru Haret 1, Chisinau, Moldova; website ntc.md; phone +373 610 00 830. Selected place pin 46.9513028,28.9044722.'),
      'browser_stara':('https://www.google.com/maps/place/Tennis+Club+%22Avgusta+Trayana%22/data=!4m6!3m5!1s0x40a869954e95517b:0x87eec5ea54d622b5!8m2!3d42.43249!4d25.6126587!16s%2Fg%2F11clyswtt6',
        'Tennis Club Avgusta Trayana; Mitropolit Metodiy Kusev, 6004 Stara Zagora, Bulgaria; website avgustatennis.bg; phone +359 88 555 4403. Selected place pin 42.43249,25.6126587.'),
      'browser_solapur':('https://www.google.com/maps/place/District+Sports+Complex/data=!4m6!3m5!1s0x3bc5da15266e8821:0xf1b0360c595bac1d!8m2!3d17.6543706!4d75.9205683!16s%2Fg%2F11r8cgvx6',
        'District Sports Complex; Krida Sankul, 9, Kumta Naka, Solapur, Maharashtra 413003, India. Selected place pin 17.6543706,75.9205683.'),
      'browser_soho':('https://www.google.com/maps/place/SOHO+Racket+Center/data=!4m6!3m5!1s0x14534956188ac519:0x27652f66f3191b94!8m2!3d27.9618824!4d34.3922957!16s%2Fg%2F11h2hfwqm9',
        'SOHO Racket Center; SOHO square, South Sinai Governorate 46628, Egypt; website soho-sharm.com/sharm-entertainment/tennis-squash-center/; phone +20 10 00109109. Selected place pin 27.9618824,34.3922957.')}
    for key,(url,text) in extracts.items():
        browser_extract(key,url,text)
    add('sharm_soho',27.9618824,34.3922957,300,'browser_soho',['Google place 0x14534956188ac519:0x27652f66f3191b94'],
        'Named racket centre agrees with official SOHO tennis site and main west tennis cluster. Not the Soho Square attraction pin.',scope='venue_point',extras=('soho_tennis','osm_soho_bbox_v2'))
    # Official GPS values are published on the venue websites, independently checked against OSM where available.
    add('szabolcs_hnta',48.2753662870654,22.04319776318043,300,'official_hnta',['official published directions GPS'],
        'Published academy directions GPS; corroborated by OSM relation/11802932.',scope='venue_point',extras=('nominatim_refined_szabolcs_hnta',))
    add('luanda_kikuxi',-9.000391672408247,13.338344114286727,200,'official_kikuxi',['official published GPS'],
        'Published academy GPS and embedded map destination agree within tens of metres.',scope='venue_point')
    geometry('qiandaohu_park','osm_qiandaohu_bbox_v2',[1395103773,1395103774,1395103775,1395103777,1395103778,1395103779,1395103780,1395103781,1395103782],300,
             'Main tennis cluster by Yangguang Road adjacent to Fairfield number619; venue listing identifies park number627. OSM WGS84 used; Amap GCJ02 coordinates not imported.',extras=('qiandaohu_venue',))
    add('solapur_mslta',17.6543706,75.9205683,350,'browser_solapur',['Google place 0x3bc5da15266e8821:0xf1b0360c595bac1d'],
        'District Sports Complex address Kumtha Naka matches ITF and district government; map listing independently has identical location.',scope='venue_point',extras=('official_solapur_official','official_solapur_maplisting'))
    photon('maia_municipal','photon_maia_municipal',160334185,250,'Named Maia tennis complex on Avenida Luis de Camoes, municipality event identity agrees.',extras=('official_maia_visit',))
    nom('mallorca_magaluf','nominatim_refined_mallorca_magaluf',311554861,350,'Named Poliesportiu de Magaluf on Avinguda les Palmeres agrees with event primary site.')
    nom('olbia_terranova','nominatim_refined_olbia_terranova',277337455,250,'Named Stadio del Tennis in Fausto Noce/Terranova complex, not football stadium.')
    nom('roanne_vacheresse','nominatim_roanne_vacheresse',426843792,150,'Named Andre Vacheresse hall in Roanne; current event page uses this hall rather than older Scarabee venue.')
    nom('rovereto_baldresca','nominatim_refined_rovereto_baldresca',910889364,300,'Named Baldresca tennis club on Via Roggia; official Rovereto event contact agrees.',extras=('official_rovereto_contact',))
    add('chisinau_national',46.9513028,28.9044722,350,'browser_ntc',['Google place 0x40c9796946d7ea2b:0x58baa3bf98e55d54'],
        'Named NTC, exact Spiru Haret1 address and official website/phone agree. Rejected unrelated Dacia Boulevard courts.',scope='venue_point',extras=('official_ntc',))
    photon('shenzhen_guangming','photon_shenzhen_guangming',722482734,450,'Named Guangming Qunzhong Sports Center sports polygon at 3115 Guangqiao Road agrees with ITF. Bus stops rejected. OSM WGS84.')
    photon('redding_sunoaks','photon_redding_sunoaks',593625022,250,'Named Sun Oaks Tennis Fitness on Argyle Road; official address3452Argyle agrees.',extras=('official_sun_oaks',))
    nom('quebec_avantage','nominatim_refined_quebec_avantage',3222666969,250,'Named Club Avantage sports centre on Rue Bouvier, Quebec; ITF club address agrees.')
    geometry('pula_fortevillage','osm_pula_bbox_v2',[296379170,296379914],650,
             'Mapped tennis pitches in Forte Village resort beside named resort hotels and mapped resort area. Conservative complex representative; hotel/neighbourhood centroid not used as court.')
    geometry('stara_avgusta','osm_stara_bbox_v2',[75849466],250,
             'Municipal tennis sports-centre polygon; selected Google club, official website and phone match. Rejects street named Avgusta Trayana and isolated eastern tennis pitch.',extras=('browser_stara','official_stara_contact'))

    expected = {k for k,v in venues.items() if v.get('lat') is None}
    if len(points)!=27 or {p['venue_id'] for p in points}!=expected:
        raise ValueError('Coordinate manifest does not exactly cover 27 pending venues')
    if (ROOT/'coordinate_manifest.json').exists():
        old = read(ROOT/'coordinate_manifest.json')
        stamp = old['reviewed_at']
    else:
        stamp = datetime.now(timezone.utc).isoformat()
    manifest = {'schema':'tennis-reviewed-coordinates-v1','reviewed_at':stamp,
                'base_seed_sha256':hashlib.sha256(OLD.read_bytes()).hexdigest(),
                'points':points,'rejected_candidates':['Shenzhen sports-centre bus stops','Stara Avgusta Trayana street','Chisinau Dacia Boulevard unnamed tennis courts','Jinan west football stadium','Google map viewport coordinates','China GCJ02 positions without WGS84 verification'],
                'probabilities_modified':False}
    save(ROOT/'coordinate_manifest.json',manifest)
    save(ROOT/'coordinate_sources.json',list(extra_sources.values()))
    result = deepcopy(base)
    result['sources'] += list(extra_sources.values())
    result['coordinate_manifest_sha256'] = hashlib.sha256((ROOT/'coordinate_manifest.json').read_bytes()).hexdigest()
    for point in points:
        venue = deepcopy(venues[point['venue_id']])
        for field in ('lat','lon','coordinate_scope','coordinate_precision_m'):
            venue[field]=point[field]
            venue['field_sources'][field]=point['source_ids']
        venue['field_sources']['coordinates']=point['source_ids']
        venue.update(recorded_at=stamp,coordinate_status='reviewed_source_backed',coordinate_crs='EPSG:4326',
                     coordinate_review_note=point['review_note'],altitude_status='awaiting_point_elevation')
        result['venues'].append(venue)
    save(ROOT/'registry_seed_coordinates_v2.json',result)
    print(json.dumps({'points':len(points),'sources_added':len(extra_sources),'venue_revisions':len(result['venues']),'reviewed_at':stamp}))


if __name__=='__main__':
    build()
