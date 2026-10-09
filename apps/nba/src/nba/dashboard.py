"""Read-only public projection of the sealed pilot and received official results."""
from datetime import UTC,datetime
import hashlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import math
from pathlib import Path
import sqlite3
import threading
import time

from .audit import canonical,digest
from .context import utc
from .paper import official_game
from .paper_followup import load_cohort,portable_path,verify_plan

MARKETS={'player_points':'Puntos','player_rebounds':'Rebotes','player_assists':'Asistencias'}
STAT={'player_points':'points','player_rebounds':'reboundsTotal','player_assists':'assists'}


def journal(path):
    """No schema initialization or writes from a web request."""
    previous='0'*64;count=0;payloads=[]
    with sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True) as db:
        for seq,received,kind,payload,prev,hashed in db.execute('SELECT * FROM events ORDER BY seq'):
            count+=1
            event=dict(seq=seq,received_at=received,kind=kind,payload=payload,previous_hash=prev)
            if seq!=count or prev!=previous or hashlib.sha256(canonical(event).encode()).hexdigest()!=hashed:
                raise ValueError('paper journal integrity failed')
            previous=hashed
            if kind=='job_result':payloads.append(json.loads(payload))
    return payloads


def worker_path(root,value):
    name=str(value).replace('\\','/')
    if not name.startswith('/data/') or '..' in Path(name).parts:raise ValueError('unsafe worker result path')
    target=Path(root)/name.removeprefix('/data/')
    if not target.resolve().is_relative_to(Path(root).resolve()):raise ValueError('unsafe worker result path')
    return target


def quantile(pmf,q):
    total=0
    for value,p in enumerate(pmf):
        total+=p
        if total>=q:return value
    raise ValueError('incomplete prediction distribution')


def observation(path,now,max_age):
    try:
        raw=json.loads(Path(path).read_bytes());stamp=raw.get('at_utc',raw.get('as_of'))
        age=(now-utc(stamp)).total_seconds()
        state=raw['state'] if -5<=age<=max_age else 'stale'
        if raw['state'] in ('completed','deadline_exhausted','validation_error','clock_hold') and age>=-5:state=raw['state']
        return dict(state=state,updated_at_utc=stamp)
    except Exception:return dict(state='unavailable',updated_at_utc=None)


class Dashboard:
    def __init__(self,plan_folder,paper_data,capture_data=None,operations_data=None):
        self.plan_folder=Path(plan_folder);self.plan=verify_plan(plan_folder)
        self.plan_hash=digest(self.plan_folder/'plan.json');self.groups=load_cohort(self.plan['cohort_path'])
        self.paper=Path(paper_data);self.capture=Path(capture_data) if capture_data else None
        self.operations=Path(operations_data) if operations_data else None
        self.lock=threading.Lock();self.cached=None;self.cached_at=0

    def verify_outcomes(self,payload,mapping,now):
        folder=worker_path(self.paper,payload['evaluation']);seal=json.loads((folder/'seal.json').read_bytes())
        if set(seal['files'])!={'outcomes.json','result.json'}:raise ValueError('unexpected evaluation files')
        for name,hashed in seal['files'].items():
            if digest(folder/name)!=hashed:raise ValueError('evaluation changed')
        result=json.loads((folder/'result.json').read_bytes())
        if result!=payload['metrics'] or result['event_id']!=mapping['provider_event_id'] or result['nba_game_id']!=mapping['nba_game_id']:
            raise ValueError('evaluation linkage failed')
        expected=self.groups[mapping['provider_event_id']]
        if digest(portable_path(expected[0]['registration'])/'seal.json')!=result['registration_seal_sha256']:
            raise ValueError('evaluation registration changed')
        receipt_path=folder.parent/'received/receipt.json';receipt=json.loads(receipt_path.read_bytes())
        if digest(receipt_path)!=result['receipt_sha256'] or receipt['raw_sha256']!=result['raw_sha256']:
            raise ValueError('official receipt changed')
        if receipt['raw_file'] not in ('boxscore.json','boxscore.html') or receipt['http_status']!=200:
            raise ValueError('official result not received')
        raw_path=receipt_path.parent/receipt['raw_file']
        if digest(raw_path)!=receipt['raw_sha256'] or not utc(mapping['tipoff_utc'])<utc(receipt['first_received_at_utc'])<=now:
            raise ValueError('official result hash/time invalid')
        game=official_game(raw_path.read_bytes(),receipt)
        if (game['gameId']!=mapping['nba_game_id'] or game['gameStatus']!=3 or utc(game['gameTimeUTC'])!=utc(mapping['tipoff_utc'])
            or any(game[side]['teamCity']+' '+game[side]['teamName']!=mapping[field] for side,field in [('homeTeam','home_team'),('awayTeam','away_team')])):
            raise ValueError('official result scope mismatch')
        players={}
        for team in (game['homeTeam'],game['awayTeam']):
            for p in team['players']:
                if p['personId'] in players:raise ValueError('duplicate official player')
                players[p['personId']]=p
        outcomes=json.loads((folder/'outcomes.json').read_bytes());seen=set();projected={}
        forecasts={(f['player_id'],f['market']):f for f in expected}
        for row in outcomes:
            key=(row['player_id'],row['market']);f=forecasts.get(key)
            if key in seen or f is None or row['event_id']!=mapping['provider_event_id'] or row['nba_game_id']!=mapping['nba_game_id']:
                raise ValueError('outcome outside cohort')
            if row['sealed_at_utc']!=f['sealed_at_utc'] or row['official_result_sha256']!=receipt['raw_sha256']:
                raise ValueError('outcome identity changed')
            player=players[row['player_id']];played=player['played']=='1'
            if player['played'] not in ('0','1') or type(row['played']) is not bool or row['played']!=played:
                raise ValueError('outcome participation changed')
            actual=player['statistics'][STAT[row['market']]] if played else None
            if played and (type(actual) is not int or actual<0 or row['actual']!=actual):raise ValueError('outcome count changed')
            if not played and row.get('actual') is not None:raise ValueError('DNP is not zero count')
            seen.add(key)
            projected[key]=dict(status='evaluated' if played else 'dnp',actual=actual,
                received_at_utc=receipt['first_received_at_utc'],official_source_url=receipt['url'])
        if seen!=set(forecasts):raise ValueError('missing cohort outcomes')
        return projected

    def snapshot(self,now=None):
        cut=now or datetime.now(UTC);events=[];units=[];problems=0
        # Recheck the small cohort files; never publish a changed prediction.
        plan=verify_plan(self.plan_folder)
        if digest(self.plan_folder/'plan.json')!=self.plan_hash:raise ValueError('original plan changed')
        payloads=[p for p in journal(self.paper/'state.sqlite') if p.get('plan_sha256')==self.plan_hash]
        for mapping in plan['mappings']:
            event=mapping['provider_event_id'];results=[p for p in payloads if p.get('event_id')==event]
            scored=[p for p in results if p.get('status')=='scored'];outcomes={}
            status='pending' if cut<utc(mapping['tipoff_utc']) else 'awaiting_result'
            if scored:
                try:
                    if len(scored)!=1:raise ValueError('ambiguous result')
                    outcomes=self.verify_outcomes(scored[0],mapping,cut);status='evaluated'
                except Exception:status='validation_hold';problems+=1
            elif any(p.get('status') in ('source_or_validation_failure','missed_window','run_limit_requires_review') and ':result:' in p.get('job_id','') for p in results):
                status='result_unavailable'
            events.append(dict(event_id=event,nba_game_id=mapping['nba_game_id'],home_team=mapping['home_team'],away_team=mapping['away_team'],
                tipoff_utc=mapping['tipoff_utc'],official_url=mapping['official_url'],status=status))
            for f in self.groups[event]:
                ref=f['reference_quote'];entry=f['hypothetical_entry'];pmf=f['candidate']['pmf']
                outcome=outcomes.get((f['player_id'],f['market']),dict(status=status,actual=None))
                row=dict(event_id=event,nba_game_id=mapping['nba_game_id'],player_id=f['player_id'],player=f['name'],
                    market=f['market'],market_label=MARKETS[f['market']],estimate=f['candidate_mean'],
                    range_low=quantile(pmf,.1),range_high=quantile(pmf,.9),line=ref['line'],
                    probability_over=f['probabilities']['over'],probability_under=f['probabilities']['under'],
                    sealed_at_utc=f['sealed_at_utc'],quote_received_at_utc=ref['first_received_at_utc'],
                    recorded_book=ref['book'],recorded_over_decimal=ref['over_decimal'],recorded_under_decimal=ref['under_decimal'],
                    paper_selection=bool(entry['selected']),paper_side=entry['side'] if entry['selected'] else None,
                    result=outcome,availability='unknown',actionable=False)
                if not all(math.isfinite(row[k]) for k in ('estimate','line','probability_over','probability_under')):
                    raise ValueError('nonfinite public prediction')
                units.append(row)
        return dict(as_of=cut.isoformat(),scope='research_pilot',events=events,predictions=units,
            totals=dict(predictions=len(units),players=len({r['player_id'] for r in units}),events=len(events),
                evaluated=sum(r['result']['status']=='evaluated' for r in units),dnp=sum(r['result']['status']=='dnp' for r in units),validation_holds=problems),
            health=dict(pilot=observation(self.paper/'health.json',cut,120),
                capture=observation(self.capture/'health.json',cut,1800) if self.capture else dict(state='unavailable',updated_at_utc=None),
                alerts=observation(self.operations/'status.json',cut,90) if self.operations else dict(state='unavailable',updated_at_utc=None)),
            production_ready=False,actionable=False)

    def data(self):
        with self.lock:
            if self.cached is None or time.monotonic()-self.cached_at>=15:
                self.cached=self.snapshot();self.cached_at=time.monotonic()
            return self.cached


def handler(dashboard,static):
    assets={'/nba':('index.html','text/html; charset=utf-8'),'/nba/':('index.html','text/html; charset=utf-8'),
        '/nba/styles.css':('styles.css','text/css; charset=utf-8'),'/nba/app.js':('app.js','text/javascript; charset=utf-8')}
    class Handler(BaseHTTPRequestHandler):
        server_version='QuantNBA'
        sys_version=''
        def do_GET(self):self.respond(False)
        def do_HEAD(self):self.respond(True)
        def do_POST(self):
            # Drain only a small declared body so rejected POSTs close cleanly.
            try:amount=int(self.headers.get('Content-Length','0'))
            except ValueError:amount=0
            if 0<amount<=4096:self.rfile.read(amount)
            self.send_error(405)
        def respond(self,head):
            path=self.path.split('?',1)[0];status=200
            try:
                if path=='/nba/api/data':
                    body=json.dumps(dashboard.data(),allow_nan=False,ensure_ascii=False).encode();content_type='application/json; charset=utf-8'
                elif path in assets:
                    name,content_type=assets[path];body=(Path(static)/name).read_bytes()
                else:status=404;body=b'No encontrado';content_type='text/plain; charset=utf-8'
            except Exception:
                status=503;body=json.dumps(dict(detail='Los datos no se pudieron verificar. Intenta de nuevo más tarde.'),ensure_ascii=False).encode()
                content_type='application/json; charset=utf-8'
            self.send_response(status);self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('X-Frame-Options','DENY');self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            if not head:self.wfile.write(body)
        def log_message(self,*args):pass
    return Handler


class Server(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,*args,**kwargs):
        self.slots=threading.BoundedSemaphore(16)
        super().__init__(*args,**kwargs)
    def get_request(self):
        request,address=super().get_request();request.settimeout(10);return request,address
    def process_request(self,request,address):
        if not self.slots.acquire(blocking=False):
            try:request.sendall(b'HTTP/1.0 503 Service Unavailable\r\nContent-Length: 0\r\nConnection: close\r\n\r\n')
            finally:self.shutdown_request(request)
            return
        try:super().process_request(request,address)
        except Exception:self.slots.release();raise
    def process_request_thread(self,request,address):
        try:super().process_request_thread(request,address)
        finally:self.slots.release()


def main():
    dashboard=Dashboard('apps/nba/.local/normalized/nba_f6_run66_20261008/lifecycle','/paper-data','/capture-data','/operations-data')
    server=Server(('0.0.0.0',8080),handler(dashboard,'/app/web'))
    server.serve_forever()


if __name__=='__main__':main()
