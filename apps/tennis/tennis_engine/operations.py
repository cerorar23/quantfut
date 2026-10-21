"""Bounded Odds API capture and evidence-aware quote inspection. No betting."""
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlencode
from urllib.request import urlopen
from uuid import uuid4


def utc(value):
    if not isinstance(value,str): raise ValueError('A timestamp string with offset is required')
    parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('An explicit UTC offset is required')
    return parsed.astimezone(timezone.utc)


def now():
    return datetime.now(timezone.utc).isoformat()


def quote_gate(event, bookmaker, market, received_at, decision_at, identities_verified,
               fixture=None, max_age_seconds=900):
    """Strict release gate. An estimated future start alone does not verify pre-match."""
    reasons=[]
    try:
        decision=utc(decision_at); received=utc(received_at)
    except (ValueError, TypeError):
        return {'eligible':False,'reasons':['invalid_source_time']}
    if not identities_verified: reasons.append('unverified_identity')
    if received>decision or (decision-received).total_seconds()>max_age_seconds:
        reasons.append('snapshot_unavailable_or_stale')
    try:
        updated=utc(market.get('last_update') or bookmaker['last_update'])
        if updated>received or (decision-updated).total_seconds()>max_age_seconds:
            reasons.append('quote_unavailable_or_stale')
        if utc(event['commence_time'])<=decision: reasons.append('estimated_start_passed')
    except (ValueError, KeyError, TypeError):
        reasons.append('invalid_source_time')
    if not fixture or fixture.get('event_id')!=event['id'] or not fixture.get('evidence'):
        reasons.append('unverified_match_status')
    else:
        try:
            observed=utc(fixture['observed_at'])
            if observed>decision or (decision-observed).total_seconds()>max_age_seconds:
                reasons.append('stale_match_status')
        except (ValueError,TypeError,KeyError):
            reasons.append('invalid_match_status_time')
        if fixture.get('status')!='scheduled' or fixture.get('actual_start'):
            reasons.append('match_started_or_unavailable')
    return {'eligible':not reasons,'reasons':reasons}


def coverage(events):
    """Measure actual inventory; best prices are observational, not executable picks."""
    books=defaultdict(lambda:{'events':set(),'markets':set(),'event_markets':set(),'quotes':0})
    best={}
    for event in events:
        for book in event.get('bookmakers',[]):
            row=books[book['key']]; row['events'].add(event['id'])
            for market in book.get('markets',[]):
                key=market['key']; row['markets'].add(key); row['event_markets'].add((event['id'],key))
                for outcome in market.get('outcomes',[]):
                    price=outcome.get('price')
                    if not isinstance(price,(int,float)) or not math.isfinite(price) or price<=1: continue
                    row['quotes']+=1
                    if key.endswith('_lay'): continue  # Lay liability/commission need a different comparator.
                    identity=(event['id'],key,outcome['name'],outcome.get('description'),outcome.get('point'))
                    record={'event_id':event['id'],'market':key,'selection':outcome['name'],
                            'description':outcome.get('description'),'line':outcome.get('point'),
                            'bookmaker':book['key'],'decimal_odds':price,
                            'last_update':market.get('last_update') or book.get('last_update'),
                            'executable':False,'reason':'Identity, freshness, rules and account availability require validation'}
                    if identity not in best or price>best[identity]['decimal_odds']: best[identity]=record
    ranked=[{'bookmaker':key,'events':len(r['events']),'market_types':sorted(r['markets']),
             'event_markets':len(r['event_markets']),'quotes':r['quotes']} for key,r in books.items()]
    return {'bookmakers':sorted(ranked,key=lambda r:(-r['event_markets'],-r['quotes'],r['bookmaker'])),
            'best_observed_prices':list(best.values()),'all_markets_guaranteed':False}


def select_books(inventory, limit=10):
    """Greedy market coverage, then inventory breadth; at most one credit region-equivalent."""
    available={b['key']:{m['key'] for m in b.get('markets',[])} for b in inventory.get('bookmakers',[])}
    chosen=[];covered=set()
    while available and len(chosen)<limit:
        key=sorted(available,key=lambda k:(-len(available[k]-covered),-len(available[k]),k))[0]
        chosen.append(key); covered.update(available.pop(key))
    # h2h_lay is returned with h2h automatically, not requested as an independent market.
    return chosen,sorted(m for m in covered if not m.endswith('_lay'))


class Capture:
    def __init__(self, root, api_key, cap=0, account_reserve=6000, transport=None, clock=now):
        if cap<0 or account_reserve<0: raise ValueError('Nonnegative credit limits required')
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
        self.key=api_key; self.cap=cap; self.reserve=account_reserve
        self.transport=transport or self._transport
        self.clock=clock
        self.db=sqlite3.connect(self.root/'credits.sqlite',timeout=30)
        self.db.execute('CREATE TABLE IF NOT EXISTS charges(id TEXT PRIMARY KEY,month TEXT,cost INTEGER,state TEXT)')
        if 'actual_cost' not in {r[1] for r in self.db.execute('PRAGMA table_info(charges)')}:
            self.db.execute('ALTER TABLE charges ADD COLUMN actual_cost INTEGER')
        self.db.commit()
        self.remaining=None

    def _transport(self, path, params):
        url='https://api.the-odds-api.com/v4/'+path+'?'+urlencode({**params,'apiKey':self.key})
        # Do not propagate exceptions containing URLs/API keys, and never retry silently.
        try:
            with urlopen(url,timeout=30) as response:
                raw=response.read(20_000_001)
                if len(raw)>20_000_000: raise ValueError('Response too large')
                headers={k:response.headers.get(k) for k in ('x-requests-last','x-requests-remaining','x-requests-used')}
                return raw,headers
        except Exception:
            raise RuntimeError('Odds API request failed; reserved credits retained; key redacted') from None

    def request(self, path, params=None):
        params=dict(params or {})
        if set(params)-{'regions','bookmakers','markets','oddsFormat','dateFormat','date'}:
            raise ValueError('Unsupported parameters; credentials are never persisted')
        sports=path=='sports'
        historical=path.startswith('historical/')
        match=re.fullmatch(r'(?:historical/)?sports/(tennis_(?:atp|wta)_[a-z0-9_]+)/(events|odds)(?:/([a-zA-Z0-9_-]+)/(?P<kind>markets|odds))?',path)
        if not sports and not match: raise ValueError('Only tennis endpoints are supported')
        if match and match.group('kind') and match.group(2)!='events': raise ValueError('Invalid event endpoint')
        kind='sports' if sports else match.group('kind') or match.group(2)
        if historical:
            if 'date' not in params or utc(params['date'])>utc(self.clock()):
                raise ValueError('Historical requests need a non-future date with offset')
        elif 'date' in params:raise ValueError('Date parameter is restricted to historical endpoints')
        free=not historical and (sports or kind=='events')
        def items(key):
            values=params.get(key,'').split(',') if params.get(key) else []
            if any(not re.fullmatch('[a-z0-9_]+',v) for v in values) or len(set(values))!=len(values):
                raise ValueError('Invalid or duplicate request keys')
            return values
        markets=items('markets'); books=items('bookmakers'); regions=items('regions')
        if not free and kind!='events' and not (books or regions): raise ValueError('Choose bookmakers or regions')
        if kind=='odds' and not markets: raise ValueError('Explicit markets required')
        if kind=='odds' and not match.group('kind') and set(markets)-{'h2h','spreads','totals'}:
            raise ValueError('Additional markets require event odds endpoint')
        units=math.ceil(len(books)/10) if books else len(regions)
        cost=0 if free else 1 if kind in ('events','markets') else (10 if historical else 1)*units*len(markets)
        started=self.clock(); identity=uuid4().hex
        self.db.execute('BEGIN IMMEDIATE')
        try:
            spent=self.db.execute('SELECT coalesce(sum(cost),0) FROM charges WHERE month=?',(started[:7],)).fetchone()[0]
            if cost and (spent+cost>self.cap or self.remaining is None or self.remaining-cost<self.reserve):
                raise ValueError('Credit limit: refresh free catalog, preserve shared reserve, or configure a bounded cap')
            self.db.execute('INSERT INTO charges(id,month,cost,state) VALUES (?,?,?,?)',(identity,started[:7],cost,'reserved'))
            self.db.commit()
        except Exception:
            self.db.rollback(); raise
        self.remaining=None  # A failed request can have consumed credits; refresh before another paid call.
        raw,headers=self.transport(path,params)
        received=self.clock()
        # Persist each original before parsing it. A malformed response still has a receipt.
        folder=self.root/'snapshots'/identity; folder.mkdir(parents=True)
        (folder/'response.json').write_bytes(raw)
        receipt={'snapshot_id':identity,'path':path,'parameters':params,'requested_at':started,'received_at':received,
                 'sha256':hashlib.sha256(raw).hexdigest(),'headers':headers,'reserved_credits':cost,
                 'estimated_start_is_market_close':False}
        (folder/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        try:
            actual=int(headers['x-requests-last']); remaining=int(headers['x-requests-remaining'])
            if actual<0 or remaining<0: raise ValueError()
        except (ValueError,TypeError,KeyError):
            self.remaining=None
            raise ValueError('Missing or invalid quota headers; reservation retained') from None
        self.remaining=remaining
        with self.db:
            self.db.execute('UPDATE charges SET cost=?,state=?,actual_cost=? WHERE id=?',(max(cost,actual),'captured',actual,identity))
        if actual>cost:
            self.remaining=None
            raise ValueError('Provider charged beyond estimate; stop and inspect receipt')
        return json.loads(raw),receipt

    def budget_report(self, month):
        rows=self.db.execute('SELECT id,cost,state,actual_cost FROM charges WHERE month=?',(month,)).fetchall()
        actual=0;unknown=0
        for identity,cost,state,charged in rows:
            if charged is None:
                receipt=self.root/'snapshots'/identity/'receipt.json'
                try:
                    charged=int(json.loads(receipt.read_text())['headers']['x-requests-last'])
                    if charged<0: raise ValueError()
                except (OSError,ValueError,TypeError,KeyError):
                    unknown+=1;continue
            actual+=charged
        return {'month':month,'reserved_accounting_total':sum(r[1] for r in rows),
                'confirmed_actual_credits':actual,'requests_with_unknown_charge':unknown,
                'shared_account_remaining':self.remaining,'shared_account_reserve':self.reserve,
                'coordination_limit':'Local ledger only; other account consumers can spend concurrently'}


def discover(root, api_key, cap=0, account_reserve=6000, regions='eu,uk,us,us2,au', max_events=2):
    """One bounded inventory run. No scheduler and no claim of exhaustive coverage."""
    client=Capture(root,api_key,cap,account_reserve)
    sports,_=client.request('sports')
    report={'captured_at':now(),'sports':[],'events':[],'inventories':[],'quotes':[],'quote_receipts':{},
            'status':'catalog_only','coverage_scope':'Current provider events and selected regions; bounded sample'}
    for sport in sports:
        if sport.get('group')!='Tennis' or not re.match(r'tennis_(atp|wta)_',sport['key']): continue
        report['sports'].append(sport['key'])
        events,_=client.request('sports/'+sport['key']+'/events')
        report['events'].extend(events)
    eligible=[e for e in report['events'] if utc(e['commence_time'])>utc(now())]
    # Start with one event per circuit before taking extra events from the same circuit.
    seen=set();first=[];rest=[]
    for event in eligible:
        circuit=event['sport_key'].split('_')[1]
        (rest if circuit in seen else first).append(event);seen.add(circuit)
    eligible=first+rest
    for event in eligible[:max_events]:
        if not cap: break
        path='sports/'+event['sport_key']+'/events/'+event['id']
        try:
            inventory,_=client.request(path+'/markets',{'regions':regions})
            report['inventories'].append(inventory)
            books,markets=select_books(inventory)
            if markets:
                # Select up to ten books spanning observed markets to avoid five-region pricing.
                quoted,receipt=client.request(path+'/odds',{'bookmakers':','.join(books),'markets':','.join(markets),'oddsFormat':'decimal'})
                report['quotes'].append(quoted)
                report['quote_receipts'][event['id']]=receipt
        except ValueError as error:
            report['stop_reason']=str(error); break
    report['status']='captured' if report['quotes'] else 'no_current_quotes_captured'
    report['coverage']=coverage(report['quotes']);report['remaining_credits']=client.remaining
    report['reserved_credits']=client.db.execute('SELECT coalesce(sum(cost),0) FROM charges').fetchone()[0]
    target=Path(root)/('coverage_'+uuid4().hex+'.json')
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return {**report,'report_path':str(target)}
