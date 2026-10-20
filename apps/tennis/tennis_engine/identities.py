"""Provider identities are evidence-backed; fuzzy scores only rank candidates."""
from difflib import SequenceMatcher
import sqlite3
import unicodedata
from pathlib import Path
from datetime import datetime, timezone


def normalized(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', value).casefold()
                           if not unicodedata.combining(c) and (c.isalnum() or c.isspace())).split())


class Registry:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS names(circuit TEXT, player_id TEXT, name TEXT,
                PRIMARY KEY(circuit,player_id,name));
            CREATE TABLE IF NOT EXISTS bindings(provider TEXT,circuit TEXT,external_key TEXT,
                player_id TEXT,evidence TEXT,reviewer TEXT,verified_at TEXT,
                PRIMARY KEY(provider,circuit,external_key));
        ''')

    def seed(self, frame):
        with self.db:
            for side in ('winner', 'loser'):
                rows = frame[['circuit', side+'_id', side+'_name']].drop_duplicates()
                self.db.executemany('INSERT OR IGNORE INTO names VALUES (?,?,?)', rows.itertuples(index=False, name=None))
        return self.db.execute('SELECT count(DISTINCT player_id) FROM names').fetchone()[0]

    def bind(self, provider, circuit, external_key, player_id, evidence, reviewer):
        if not all(isinstance(x, str) and x.strip() for x in (provider,circuit,external_key,player_id,evidence,reviewer)):
            raise ValueError('Provider identity, evidence and reviewer are required')
        if not self.db.execute('SELECT 1 FROM names WHERE circuit=? AND player_id=?', (circuit,player_id)).fetchone():
            raise ValueError('Unknown player in circuit')
        current = self.resolve(provider,circuit,external_key)
        if current:
            if current != player_id:
                raise ValueError('Conflicting binding; explicit audited migration required')
            return current
        with self.db:
            self.db.execute('INSERT INTO bindings VALUES (?,?,?,?,?,?,?)',
                (provider,circuit,external_key,player_id,evidence,reviewer,datetime.now(timezone.utc).isoformat()))
        return player_id

    def resolve(self, provider, circuit, external_key):
        row = self.db.execute('SELECT player_id FROM bindings WHERE provider=? AND circuit=? AND external_key=?',
                             (provider,circuit,external_key)).fetchone()
        return row[0] if row else None

    def candidates(self, circuit, name, limit=5):
        scores = {}
        for pid, alias in self.db.execute('SELECT player_id,name FROM names WHERE circuit=?', (circuit,)):
            score = SequenceMatcher(None, normalized(name), normalized(alias)).ratio()
            if pid not in scores or score > scores[pid]['similarity']:
                scores[pid] = {'player_id':pid,'name':alias,'similarity':round(score,4)}
        return sorted(scores.values(), key=lambda x:(-x['similarity'],x['player_id']))[:limit]


def reconcile(events, registry):
    results=[]
    for event in events:
        circuit='ATP' if event['sport_key'].startswith('tennis_atp_') else 'WTA' if event['sport_key'].startswith('tennis_wta_') else None
        if not circuit:
            raise ValueError('Unsupported circuit')
        players=[]
        for side in ('home_team','away_team'):
            name=event[side]
            pid=registry.resolve('the_odds_api',circuit,'name:'+name)
            players.append({'source_name':name,'player_id':pid,
                'candidates':[] if pid else registry.candidates(circuit,name)})
        valid=all(p['player_id'] for p in players) and players[0]['player_id']!=players[1]['player_id']
        results.append({'event_id':event['id'],'players':players,'identities_verified':bool(valid),
                        'commence_time':event['commence_time'],'actual_start_verified':False})
    return results
