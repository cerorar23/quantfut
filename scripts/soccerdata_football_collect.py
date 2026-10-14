"""Recuperación histórica optativa: soccerdata 1.9.1 + ZenRows MCP.

Instalar soccerdata en un entorno aislado y definir SOCCERDATA_DIR dentro de
--output. No ejecuta importaciones ni modifica las banderas de las ligas.
"""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path

from qf.ingest.soccerdata_transport import OriginalStore, SourceUnavailable, bind_reader
from qf.ingest.sofascore_history import TOURNAMENTS, normalize_bundle
from qf.ingest.fotmob_import import Matcher, json_write
from football_zenrows_mcp import ZenRowsMCP


def history_reader(store, output):
    # Imports are deliberately optional; production does not need browser deps.
    import pandas as pd
    import soccerdata as sd
    from soccerdata._config import LEAGUE_DICT
    for league in TOURNAMENTS:
        single = league.split('.')[0] in {'ar','br','cl','us','no','se'}
        LEAGUE_DICT[league] = {'Sofascore':league,
            'season_code':'single-year' if single else 'multi-year'}

    class HistoricalSofascore(sd.Sofascore):
        @classmethod
        def _all_leagues(cls):
            return {league:league for league in TOURNAMENTS}

        def read_leagues(self):
            # Explicit custom tournament configuration. Every event's actual
            # tournament, country, teams and final state is validated separately.
            return pd.DataFrame([{'league':league,'league_id':TOURNAMENTS[league]}
                for league in self.leagues]).set_index('league')

        def read_recent_events(self, league, season_id, page=0):
            tid = TOURNAMENTS[league]
            url = f'https://www.sofascore.com/api/v1/unique-tournament/{tid}/season/{season_id}/events/last/{page}'
            data = json.load(self.get(url))
            if not isinstance(data.get('events'),list):
                raise ValueError('invalid_events_response')
            return data['events'], store.used[url]

        def read_event_details(self, event):
            eid = event['id']
            if not isinstance(eid,int) or isinstance(eid,bool) or eid<=0:
                raise ValueError('invalid_event_id')
            base=f'https://www.sofascore.com/api/v1/event/{eid}'
            result, receipts, issues = {}, [], []
            for field in ('statistics','lineups'):
                try:
                    result[field] = json.load(self.get(base+'/'+field))
                    if result[field].get('error'):
                        issues.append({'field':field,'reason':'provider_json_error'})
                        result[field] = None
                    else:
                        receipts.append(store.used[base+'/'+field])
                except Exception as exc:
                    result[field] = None
                    issues.append({'field':field,'reason':type(exc).__name__})
            return result, receipts, issues

    reader=bind_reader(HistoricalSofascore,store,leagues=list(TOURNAMENTS),
        seasons=['2026-2027'],data_dir=Path(output)/'library-cache'/'Sofascore')
    # soccerdata's ordinary season parser and proxy-bound get are retained.
    reader._season_ids=[]  # Custom multi/single-year leagues are queried separately.
    return reader


def import_cached_sources(store, directories):
    """Adopta originales verificados; nunca inventa una recepción nueva."""
    n=0
    for directory in directories:
        # A changed country route is one distinct, bounded attempt. Preserve the
        # prior error in its run; carry forward errors from the same GB route.
        def adopt(url,raw,receipt):
            nonlocal n
            if receipt.get('provider_error') and (receipt.get('parameters') or {}).get('proxy_country')!='GB':
                return
            destination,_=store.paths(url)
            if not destination.exists():
                store.save(url,raw,receipt)
                n+=1
        report_path=Path(directory)/'report.json'
        if report_path.exists():
            report=json.loads(report_path.read_text(encoding='utf-8'))
            for receipt in report.get('receipts',[]):
                if receipt.get('label') and not receipt.get('provider_error'):
                    body=Path(directory)/(receipt['label']+'.body')
                    adopt(receipt['url'],body.read_bytes(),receipt)
        for path in (Path(directory)/'originals').glob('*.receipt.json'):
            receipt=json.loads(path.read_text(encoding='utf-8'))
            raw=gzip.decompress(path.with_name(path.name.replace('.receipt.json','.body.gz')).read_bytes())
            adopt(receipt['url'],raw,receipt)
        for folder in ('responses','detail-responses'):
            for path in (Path(directory)/folder).glob('*.meta.json'):
                receipt=json.loads(path.read_text(encoding='utf-8'))
                body=path.with_name(path.name.removesuffix('.meta.json'))
                raw=gzip.decompress(body.read_bytes())
                url=receipt['url']
                adopt(url,raw,receipt)
    return n


def assemble_cached(output, snapshot_path, pilot=None, cached=()):
    """Consolida respuestas recibidas sin red, usando el lector ampliado.

    Incluye pilotos previos autorizados; conserva versiones por hash en vez de
    sustituir un error posterior por una respuesta exitosa anterior en caché.
    """
    output=Path(output);prepared=output/'prepared'
    if prepared.exists():
        raise ValueError('prepared_archive_already_exists')
    prepared.mkdir()
    originals={}
    paths=[p for directory in [output,*map(Path,cached)]
           for p in (directory/'originals').glob('*.receipt.json')]
    for path in paths:
        receipt=json.loads(path.read_text(encoding='utf-8'))
        raw=gzip.decompress(path.with_name(path.name.replace('.receipt.json','.body.gz')).read_bytes())
        if hashlib.sha256(raw).hexdigest()!=receipt['sha256']:
            raise ValueError('original_hash_mismatch')
        if receipt.get('provider_error'):continue
        try:value=json.loads(raw)
        except ValueError:continue
        if value.get('error'):continue
        originals.setdefault(receipt['url'],(raw,receipt))
    if pilot:
        pilot=Path(pilot)
        report=json.loads((pilot/'report.json').read_text(encoding='utf-8'))
        for receipt in report['receipts']:
            raw=(pilot/(receipt['label']+'.body')).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=receipt['sha256']:
                raise ValueError('pilot_original_hash_mismatch')
            if not receipt.get('provider_error'):
                originals.setdefault(receipt['url'],(raw,receipt))
    class ReplayStore(OriginalStore):
        def load(self,url):
            if url not in originals:
                raise SourceUnavailable('offline_response_unavailable')
            raw,receipt=originals[url]
            self.used[url]=receipt
            return raw,receipt
    store=ReplayStore(prepared/'unused',lambda _:None)
    reader=history_reader(store,output)
    inverse={tid:l for l,tid in TOURNAMENTS.items()};inverse[11621]='mx.liga_mx'
    events={};issues=[]
    for url,(raw,receipt) in originals.items():
        value=json.loads(raw)
        for event in value.get('events',[]):
            tid=(event.get('tournament',{}).get('uniqueTournament') or {}).get('id')
            if tid not in inverse or (event.get('status') or {}).get('type')!='finished':continue
            eid=str(event['id'])
            events.setdefault(eid,(inverse[tid],event,receipt))
    archive=prepared/'archive'/'raw'/'matches';archive.mkdir(parents=True)
    http=prepared/'http-originals';http.mkdir()
    rows=[]
    for eid,(league,event,calendar) in events.items():
        details,receipts,errors=reader.read_event_details(event)
        # A verified final calendar also contains an original result. Preserve
        # it even when details are unavailable; missing metrics remain NULL.
        raw=json.dumps({'event':event,**details},ensure_ascii=False,allow_nan=False).encode()
        receipts=[calendar,*receipts]
        meta={'provider':'sofascore','reader':'soccerdata 1.9.1 HistoricalSofascore',
            'captured_at':max(r['received_at'] for r in receipts),
            'sha256':hashlib.sha256(raw).hexdigest(),'receipts':receipts}
        try:row=normalize_bundle(league,raw,meta)
        except ValueError as exc:
            issues.append({'event':eid,'reason':str(exc)});continue
        (archive/(eid+'.json.gz')).write_bytes(gzip.compress(raw))
        json_write(archive/(eid+'.json.gz.meta.json'),meta)
        for receipt in receipts:
            source_raw=originals[receipt['url']][0]
            (http/(receipt['sha256']+'.body.gz')).write_bytes(gzip.compress(source_raw))
        rows.append(row)
    with gzip.open(prepared/'normalized.jsonl.gz','wt',encoding='utf-8') as handle:
        for row in rows:handle.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n')
    snapshot=json.loads(Path(snapshot_path).read_text(encoding='utf-8'))
    snapshot['matches']=[dict(m,status=m.get('status','finished')) for m in snapshot['matches']]
    json_write(prepared/'database-matching.json',snapshot)
    from collections import Counter
    result={'original_bundles':len(rows),'by_league':dict(Counter(r['league_id'] for r in rows)),
        'xg_pairs':sum(r['home_xg'] is not None and r['away_xg'] is not None for r in rows),
        'lineups':sum(len(r['lineups']) for r in rows),'players':sum(len(r['players']) for r in rows),
        'absences':sum(len(r['absences']) for r in rows),'issues':issues,'network_requests':0}
    json_write(prepared/'assembly.json',result)
    print(json.dumps(result),flush=True)
    return result


def collect(root, output, snapshot_path, cached, max_requests=70):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    os.environ['SOCCERDATA_DIR']=str(output/'library-cache')
    os.environ['SOCCERDATA_LOGLEVEL']='ERROR'
    snapshot=json.loads(Path(snapshot_path).read_text(encoding='utf-8'))
    snapshot['matches']=[dict(m,status=m.get('status','finished')) for m in snapshot['matches']]
    client=ZenRowsMCP(root,max_requests=max_requests)
    store=OriginalStore(output/'originals',client.scrape)
    issues=[];events={};rows=[]
    try:
        json_write(output/'account-before-collect.json',client.usage())
        adopted=import_cached_sources(store,cached)
        print(json.dumps({'adopted_originals':adopted}),flush=True)
        reader=history_reader(store,output)
        # Cache-aware recent calendars: prioritize the twelve leagues lacking
        # models, then the remaining enabled leagues. The importer never enables.
        flags={l['league_id']:l for l in snapshot['leagues']}
        order=sorted((l for l in TOURNAMENTS if l in flags and flags[l].get('active',True)),
                     key=lambda l:(flags[l]['model_enabled'],l))
        for league in order:
            tid=TOURNAMENTS[league]
            url=f'https://www.sofascore.com/api/v1/unique-tournament/{tid}/seasons'
            try:
                seasons=json.load(reader.get(url))['seasons']
                selected=[s for s in seasons if str(s.get('year')) in {'26/27','2026','2026/2027'}]
                if len(selected)!=1:
                    raise ValueError('current_season_not_unique')
                found,receipt=reader.read_recent_events(league,selected[0]['id'])
                for event in found:
                    if (event.get('status') or {}).get('type')!='finished':continue
                    raw=json.dumps({'event':event,'statistics':None,'lineups':None},ensure_ascii=False,allow_nan=False).encode()
                    meta={'captured_at':receipt['received_at'],'sha256':hashlib.sha256(raw).hexdigest(),'receipts':[receipt]}
                    row=normalize_bundle(league,raw,meta)
                    events[str(event['id'])]=(league,event,receipt,row)
                print(json.dumps({'league':league,'finished':len(found),'requests':client.calls}),flush=True)
            except Exception as exc:
                issues.append({'league':league,'stage':'calendar','reason':type(exc).__name__,'message':str(exc)[:180]})
        matcher=Matcher(snapshot,[v[3] for v in events.values()],provider='sofascore')
        by_id={m['match_id']:m for m in snapshot['matches']}
        priority=[]
        for eid,(league,event,receipt,row) in events.items():
            decision=matcher.match(row)
            old=by_id.get(decision['match_id'])
            missing=bool(old and old['home_xg'] is None and old['away_xg'] is None)
            recent=event['startTimestamp']>=datetime(2026,10,4,tzinfo=timezone.utc).timestamp()
            if missing or recent or decision['mapping_status']=='created':
                priority.append((not missing,flags[league]['model_enabled'],not recent,-event['startTimestamp'],eid))
        priority.sort()
        archive=output/'archive'/'raw'/'matches';archive.mkdir(parents=True,exist_ok=True)
        for *_,eid in priority:
            league,event,calendar,row=events[eid]
            if client.calls>=max_requests or client.remaining_floor<client.reserve+25:
                issues.append({'stage':'details','reason':'bounded_budget_reached','pending_events':len(priority)-len(rows)})
                break
            details,receipts,errors=reader.read_event_details(event)
            issues.extend(dict(eid=eid,league=league,stage='details',**i) for i in errors)
            if not receipts:continue
            bundle={'event':event,**details}
            raw=json.dumps(bundle,ensure_ascii=False,allow_nan=False).encode()
            receipts=[calendar,*receipts]
            meta={'provider':'sofascore','reader':'soccerdata 1.9.1 HistoricalSofascore',
                'captured_at':max(r['received_at'] for r in receipts),'sha256':hashlib.sha256(raw).hexdigest(),'receipts':receipts}
            normalized=normalize_bundle(league,raw,meta)
            if normalized['home_xg'] is None and not normalized['lineups'] and not normalized['players']:
                continue
            (archive/(eid+'.json.gz')).write_bytes(gzip.compress(raw))
            json_write(archive/(eid+'.json.gz.meta.json'),meta)
            rows.append(normalized)
            print(json.dumps({'event':eid,'league':league,'xg':normalized['home_xg'] is not None,
                'players':len(normalized['players']),'requests':client.calls}),flush=True)
        with gzip.open(output/'normalized.jsonl.gz','wt',encoding='utf-8') as handle:
            for row in rows:handle.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n')
        json_write(output/'database-matching.json',snapshot)
        json_write(output/'collection.json',{'events_found':len(events),'events_targeted':len(priority),
            'original_bundles':len(rows),'xg_pairs':sum(r['home_xg'] is not None and r['away_xg'] is not None for r in rows),
            'lineups':sum(len(r['lineups']) for r in rows),'players':sum(len(r['players']) for r in rows),
            'absences':sum(len(r['absences']) for r in rows),'requests':client.calls,'issues':issues})
    finally:
        try:json_write(output/'account-after-collect.json',client.usage())
        finally:client.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--snapshot',type=Path,required=True)
    p.add_argument('--cache',type=Path,action='append',default=[])
    p.add_argument('--max-requests',type=int,default=70)
    p.add_argument('--assemble-only',action='store_true')
    p.add_argument('--pilot',type=Path)
    args=p.parse_args()
    if args.assemble_only:
        os.environ['SOCCERDATA_DIR']=str(args.output/'library-cache')
        os.environ['SOCCERDATA_LOGLEVEL']='ERROR'
        assemble_cached(args.output,args.snapshot,args.pilot,args.cache)
    else:
        collect(Path.cwd(),args.output,args.snapshot,args.cache,args.max_requests)
