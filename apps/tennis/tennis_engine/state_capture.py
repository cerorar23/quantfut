"""Bounded API-Tennis capture and append-only observed state history.

Receipt times describe our observations of the provider, not actual court
events. Unknown latency prevents treating transition brackets as actual start
or finish bounds. Absence from a live feed never creates a terminal result.
"""
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Callable
from uuid import uuid4

import requests

from .operations import now, utc


def state(value: Any) -> str:
    text=str(value or '')
    if re.fullmatch(r'Set [1-5]',text):return 'playing'
    return {'Finished':'completed','Retired':'retired','Walk Over':'walkover',
            'Cancelled':'cancelled','Interrupted':'interrupted','Suspended':'interrupted',
            '1':'scheduled_unverified','':'scheduled_unverified'}.get(text,'unknown')


class StateStore:
    def __init__(self, root: Path):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.root/'states.sqlite',timeout=30)
        self.db.row_factory=sqlite3.Row
        self.db.executescript('''
            PRAGMA foreign_keys=ON;
            CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY, requested_at TEXT NOT NULL, method TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS receipts(id TEXT PRIMARY KEY, received_at TEXT NOT NULL,
                requested_at TEXT NOT NULL, source_path TEXT NOT NULL, sha256 TEXT NOT NULL, method TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS observations(receipt_id TEXT NOT NULL REFERENCES receipts(id),
                event_id TEXT NOT NULL, received_at TEXT NOT NULL, player_a TEXT NOT NULL, player_b TEXT NOT NULL,
                state TEXT NOT NULL, provider_status TEXT NOT NULL, payload TEXT NOT NULL,
                PRIMARY KEY(receipt_id,event_id));
        ''')
        for table in ('requests','receipts','observations'):
            for operation in ('UPDATE','DELETE'):
                self.db.execute(f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{operation} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'append-only capture'); END")
        self.db.commit()

    def reserve(self, method: str, requested_at: str, daily_limit: int) -> str:
        if type(daily_limit) is not int or not 1<=daily_limit<=1000:
            raise ValueError('Explicit local daily request cap from 1 to 1000 required')
        stamp=utc(requested_at).isoformat();identity=uuid4().hex
        self.db.execute('BEGIN IMMEDIATE')
        try:
            n=self.db.execute('SELECT count(*) FROM requests WHERE substr(requested_at,1,10)=?',(stamp[:10],)).fetchone()[0]
            if n>=daily_limit:raise ValueError('Local daily request cap reached')
            self.db.execute('INSERT INTO requests VALUES(?,?,?)',(identity,stamp,method));self.db.commit()
        except Exception:
            self.db.rollback();raise
        return identity

    def ingest(self, receipt: dict[str,Any]) -> int:
        raw=Path(receipt['source_path']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=receipt['sha256']:
            raise ValueError('Response hash differs from receipt')
        received=utc(receipt['received_at']).isoformat()
        requested=utc(receipt['requested_at']).isoformat()
        if requested>received:raise ValueError('Receipt chronology invalid')
        if receipt['method'] not in ('get_fixtures','get_livescore'):
            raise ValueError('Only fixtures and live captures can enter state history')
        data=json.loads(raw)
        if data.get('success')!=1 or not isinstance(data.get('result'),list):
            raise ValueError('Successful fixture response required')
        batch=[];ids=set()
        for row in data['result']:
            key='api_tennis:'+str(row['event_key'])
            if key in ids:raise ValueError('Duplicate event in response')
            ids.add(key)
            a,b=str(row['first_player_key']),str(row['second_player_key'])
            if not a or not b or a==b or a=='None' or b=='None':
                raise ValueError('Distinct provider participant IDs required')
            batch.append((receipt['id'],key,received,a,b,state(row.get('event_status')),
                          str(row.get('event_status','')),json.dumps(row,sort_keys=True)))
        with self.db:
            existing=self.db.execute('SELECT * FROM receipts WHERE id=?',(receipt['id'],)).fetchone()
            if existing:
                if (existing['sha256'],existing['received_at'],existing['requested_at'],existing['method'],existing['source_path'])!=(receipt['sha256'],received,requested,receipt['method'],str(Path(receipt['source_path']).resolve())):
                    raise ValueError('Receipt identity conflict')
                return 0
            self.db.execute('INSERT INTO receipts VALUES(?,?,?,?,?,?)',
                (receipt['id'],received,requested,str(Path(receipt['source_path']).resolve()),receipt['sha256'],receipt['method']))
            self.db.executemany('INSERT INTO observations VALUES(?,?,?,?,?,?,?,?)',batch)
        return len(batch)

    def timeline(self, event_id: str, as_of: str) -> dict[str,Any]:
        until=utc(as_of)
        rows=[dict(r) for r in self.db.execute('SELECT * FROM observations WHERE event_id=? ORDER BY received_at,receipt_id',(event_id,))
              if utc(r['received_at'])<=until]
        changes=[];previous=None
        for row in rows:
            if previous is None or (row['state'],row['player_a'],row['player_b'])!=(previous['state'],previous['player_a'],previous['player_b']):
                changes.append({'from':previous['state'] if previous else None,'to':row['state'],
                    'previous_observation_at':previous['received_at'] if previous else None,
                    'observed_at':row['received_at'],'receipt_id':row['receipt_id']})
            previous=row
        live=[r for r in rows if r['state']=='playing']
        terminal=[r for r in rows if r['state'] in ('completed','retired','walkover','cancelled')]
        return {'event_id':event_id,'as_of':as_of,'n_observations':len(rows),
                'latest':rows[-1] if rows else None,'changes':changes,
                'first_seen_live_at':live[0]['received_at'] if live else None,
                'first_seen_terminal_at':terminal[0]['received_at'] if terminal else None,
                'participant_conflict':len({(r['player_a'],r['player_b']) for r in rows})>1,
                'actual_start':None,'actual_end':None,'provider_latency_upper_bound_seconds':None,
                'timing_quality':'provider_state_observations_only'}

    def summary(self, as_of: str) -> dict[str,Any]:
        ids=[r[0] for r in self.db.execute('SELECT DISTINCT event_id FROM observations ORDER BY event_id')]
        rows=[self.timeline(i,as_of) for i in ids]
        rows=[r for r in rows if r['latest']]
        return {'as_of':as_of,'events':len(rows),'observations':sum(r['n_observations'] for r in rows),
                'states':dict(Counter(r['latest']['state'] for r in rows)),
                'events_seen_live':sum(r['first_seen_live_at'] is not None for r in rows),
                'participant_conflicts':sum(r['participant_conflict'] for r in rows),
                'genuine_actual_times_available':0,'financial_validation':False}

    def load_history(self, as_of: str) -> list:
        """Feed the strict extractor with archived terminal observations.

        Unknown completion lower bounds remain unknown; collecting a transition
        does not silently promote a receipt clock into a verified physical time.
        """
        from .recent_load import api_tennis_history
        result=[]
        latest={}
        for row in self.db.execute('SELECT event_id,received_at,state,receipt_id FROM observations ORDER BY received_at,receipt_id'):
            if utc(row['received_at'])<utc(as_of):latest[row['event_id']]=dict(row)
        for receipt in self.db.execute('SELECT * FROM receipts ORDER BY received_at,id'):
            if utc(receipt['received_at'])<utc(as_of):
                rows=api_tennis_history(Path(receipt['source_path']),receipt['received_at'],receipt['sha256'])
                # Query separately at each decision time. A corrected terminal
                # status must not survive a later live/scheduled observation.
                result.extend(r for r in rows if r.event_id in latest
                    and latest[r.event_id]['receipt_id']==receipt['id'])
        return result


class TennisStateCapture:
    """One bounded request per call; failures consume local reservations.

    The cap counts only this collector, not the provider account's global
    allowance. No retries or redirections, no quotas inferred from HTTP 200.
    """
    def __init__(self, root: Path, key: str, daily_limit: int=24,
                 transport: Callable[...,Any] | None=None):
        if not key:raise ValueError('API-Tennis credential required')
        self.store=StateStore(root);self.key=key;self.daily_limit=daily_limit
        self.transport=transport or requests.get

    def capture(self, method: str, params: dict[str,str]) -> dict[str,Any]:
        allowed={'get_fixtures':{'date_start','date_stop','event_type_key','timezone'},
                 'get_livescore':{'event_type_key','timezone'}}
        if method not in allowed or set(params)-allowed[method] or params.get('timezone')!='UTC':
            raise ValueError('Whitelisted methods/parameters and explicit UTC required')
        if params.get('event_type_key') not in ('265','264','266','267',None):
            raise ValueError('Explicit supported tour type required')
        if method=='get_fixtures':
            start=date.fromisoformat(params['date_start']);stop=date.fromisoformat(params['date_stop'])
            if not 0<=(stop-start).days<=3:raise ValueError('Fixture range limited to four dates')
        started=now();identity=self.store.reserve(method,started,self.daily_limit)
        folder=self.store.root/'originals'/identity;folder.mkdir(parents=True,exist_ok=False)
        receipt={'id':identity,'method':method,'params':params,'requested_at':started,
                 'quota_scope':'local collector only','provider_charge_or_remaining':None}
        try:
            response=self.transport('https://api.api-tennis.com/tennis/',
                params={'method':method,'APIkey':self.key,**params},timeout=(15,60),allow_redirects=False)
        except Exception as exc:
            # Do not expose exception messages: requests embeds credential URLs.
            receipt.update(received_at=now(),error_type=type(exc).__name__)
            (folder/'receipt.json').write_text(json.dumps(receipt,indent=2))
            raise RuntimeError('API-Tennis request failed; reservation retained') from None
        raw=response.content;secret=self.key.encode()
        redacted=secret in raw;raw=raw.replace(secret,b'[REDACTED]')
        path=folder/'response.json'
        with path.open('xb') as stream:stream.write(raw)
        receipt.update(received_at=now(),http_status=response.status_code,
            source_path=str(path.resolve()),sha256=hashlib.sha256(raw).hexdigest(),response_redacted=redacted)
        with (folder/'receipt.json').open('x',encoding='utf-8') as stream:json.dump(receipt,stream,indent=2)
        if response.status_code!=200:raise RuntimeError('API-Tennis returned a non-success HTTP status; original archived')
        count=self.store.ingest(receipt)
        return {'receipt':receipt,'observations_added':count,'summary':self.store.summary(receipt['received_at'])}
