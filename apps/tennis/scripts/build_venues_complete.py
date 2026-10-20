"""Replay manually reviewed venue editions and event-specific season corrections.

Network collection is separate. Sources may be archived HTTP bytes or explicitly
labelled web-tool extracts. Failed/challenge responses never become evidence.
"""
import argparse
from copy import deepcopy
import hashlib,json
from pathlib import Path

from tennis_engine.fixture_reviews import FixtureReviews,fixture_digest
from tennis_engine.operations import now
from tennis_engine.venues import VenueRegistry,load_seed


def write_new(path,value):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False)


def build(root: Path,base_path: Path,probe: Path) -> dict:
    seed=deepcopy(json.loads(base_path.read_text(encoding='utf-8')))
    specs=json.loads((root/'reviewed_editions.json').read_text(encoding='utf-8'))
    receipts={s['source_id']:s for s in seed['sources']}
    for receipt_path in sorted((root/'originals').glob('*/receipt.json')):
        receipt=json.loads(receipt_path.read_text())
        if receipt.get('http_status')!=200:continue
        raw=Path(receipt['source_path']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=receipt['sha256']:raise ValueError('Changed source')
        text=raw.decode('utf-8',errors='replace')
        if any(marker in text for marker in ('Incapsula','Request unsuccessful')) and len(raw)<5000:continue
        if not text.strip():continue
        receipts[receipt['source_id']]=receipt
    for receipt in json.loads((root/'web_sources.json').read_text()):
        if hashlib.sha256(Path(receipt['source_path']).read_bytes()).hexdigest()!=receipt['sha256']:
            raise ValueError('Changed web extract')
        receipts[receipt['source_id']]=receipt
    stamp=now();seed['created_at']=stamp
    rows=json.loads((probe/'upcoming.json').read_bytes())['result']
    catalog={str(t['tournament_key']):t for t in json.loads((probe/'tournaments.json').read_bytes())['result']}
    seen=set();venues={v['venue_id']:v for v in seed['venues']};reviewed_groups=[]
    for spec in specs:
        for sid in spec['sources']:
            if sid not in receipts:raise ValueError('Missing successful reviewed evidence: '+sid)
        identity=spec['venue_id']
        if identity not in venues:
            fields={k:spec['sources'] for k in ('name','city','country')}
            fields['timezone']=['iana_zones']
            if spec['indoor'] is not None:fields['indoor']=spec['sources']
            venues[identity]={'venue_id':identity,'name':spec['name'],'city':spec['city'],
                'country':spec['country'],'timezone':spec['timezone'],'address':spec.get('address'),
                'lat':None,'lon':None,'coordinate_status':'not_verified','altitude_m':None,
                'altitude_status':'requires_verified_coordinates','indoor':spec['indoor'],
                'roof_state_at_match':None,'recorded_at':stamp,'field_sources':fields,
                'scope':'published_tournament_primary_site_not_individual_court'}
        for provider_id,expected_name in spec['aliases']:
            if provider_id in seen:raise ValueError('Provider alias specified twice')
            seen.add(provider_id)
            subset=[r for r in rows if str(r['tournament_key'])==provider_id]
            if not subset or any(r['tournament_name']!=expected_name for r in subset):
                raise ValueError('Provider name/ID changed')
            if catalog[provider_id]['tournament_name']!=expected_name:raise ValueError('Catalog mismatch')
            kinds={r['event_type_type'] for r in subset}
            if len(kinds)!=1 or next(iter(kinds))!=catalog[provider_id]['event_type_type']:
                raise ValueError('Provider discipline mismatch')
            kind=next(iter(kinds))
            if ('Women' in kind)!=spec['women']:raise ValueError('Sex/edition mismatch')
            binding={'binding_id':'api_tennis:'+provider_id+':reviewed:2026','provider':'api_tennis',
                'provider_tournament_id':provider_id,'provider_event_type':kind,'season':'2026',
                'edition_id':spec['edition_id'],'venue_id':identity,'valid_from':spec['valid_from'],
                'valid_until':spec['valid_until'],'timezone':spec['timezone'],'surface':spec['surface'],
                'sources':spec['sources']+['api_upcoming','api_tournaments'],
                'surface_sources':spec['sources'] if spec['surface'] is not None else [],
                'recorded_at':stamp,'scope':'published_primary_site_not_confirmed_individual_court'}
            seed['bindings'].append(binding)
            reviewed_groups.append({'provider_id':provider_id,'name':expected_name,'event_type':kind,
                'edition_id':spec['edition_id'],'venue_id':identity,'n_matches':len(subset),
                'sources':spec['sources'],'official_date_scope':[spec['valid_from'],spec['valid_until']]})
    seed['venues']=list(venues.values());seed['sources']=list(receipts.values())
    seed['limits'].append('New named venues without verified coordinate pairs cannot supply distances, altitude or weather.')
    seed['reviewed_groups']=reviewed_groups
    return seed


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--base-seed',type=Path,required=True);parser.add_argument('--probe-root',type=Path,required=True)
    parser.add_argument('--registry',type=Path,required=True);parser.add_argument('--report',type=Path,required=True)
    a=parser.parse_args()
    if a.report.exists():raise ValueError('Report is immutable; choose a new path')
    path=a.root/'registry_seed_completed.json'
    if not path.exists():write_new(path,build(a.root,a.base_seed,a.probe_root))
    seed=json.loads(path.read_text(encoding='utf-8'));registry=VenueRegistry(a.registry);load_seed(registry,path)
    raw=(a.probe_root/'upcoming.json').read_bytes()
    original=json.loads(raw)['result'];manifest={r['label']:r for r in json.loads((a.probe_root/'manifest.json').read_text())}
    if hashlib.sha256(raw).hexdigest()!=manifest['upcoming']['sha256'] or manifest['upcoming']['params'].get('timezone')!='UTC':
        raise ValueError('Changed or non-UTC calendar input')
    review_path=a.root/'season_reviews.json'
    if not review_path.exists():
        corrections=[]
        for row in original:
            if str(row['tournament_season'])==row['event_date'][:4]:continue
            groups=[g for g in seed['reviewed_groups'] if g['provider_id']==str(row['tournament_key'])]
            if len(groups)!=1:raise ValueError('Season discrepancy needs exactly one reviewed edition')
            g=groups[0]
            # Explicit reviewed groups only, not a generic year-from-date correction.
            if (g['provider_id'],str(row['tournament_season'])) not in {('2440','2025'),('7332','2025'),('2756','2025'),('2759','2025')}:
                raise ValueError('Unreviewed season discrepancy')
            corrections.append({'review_id':'api_tennis:'+str(row['event_key'])+':season','provider':'api_tennis',
                'provider_event_id':str(row['event_key']),'input_sha256':fixture_digest(row),'input_source_id':'api_upcoming',
                'field':'tournament_season','before':'2025','after':'2026','action':'correct',
                'recorded_at':now(),'sources':g['sources'],
                'reason':'Reviewed 2026 edition '+g['edition_id']+' and published date window; provider tournament ID and discipline retained. This does not authenticate the individual fixture schedule.'})
        write_new(review_path,corrections)
    reviews=FixtureReviews(registry)
    for correction in json.loads(review_path.read_text()):reviews.register(correction)
    decision=now();report=reviews.enrich_calendar(original,decision,input_timezone='UTC',source_received_at=manifest['upcoming']['received_at'])
    report.update(input_sha256=hashlib.sha256(raw).hexdigest(),registry_seed_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        reviews_sha256=hashlib.sha256(review_path.read_bytes()).hexdigest(),n_named_venues=len(seed['venues']),
        n_bindings=len(seed['bindings']),reviewed_groups=seed['reviewed_groups'],
        n_with_altitude=sum(e['venue_resolution']['status']=='resolved' and e['venue_resolution']['venue'].get('altitude_m') is not None for e in report['events']),
        sports_api_requests=0,probabilities_modified=False,
        code_sha256={p:hashlib.sha256(Path(__import__('tennis_engine.'+p,fromlist=['__file__']).__file__).read_bytes()).hexdigest() for p in ['venues','fixture_reviews']})
    write_new(a.report,report);registry.db.close()
    print(json.dumps({k:report[k] for k in ['n_total','n_resolved','n_with_coordinates','n_with_altitude','n_season_corrected','n_season_unresolved','n_named_venues','n_bindings']}))


if __name__=='__main__':main()
