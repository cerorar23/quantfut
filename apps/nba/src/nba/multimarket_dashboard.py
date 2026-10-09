"""Independent sealed extension, reusing verified official receipts read-only."""
from datetime import UTC, datetime
import json
import math
from pathlib import Path

from .audit import digest
from .dashboard import Dashboard, Server, handler, journal, worker_path
from .paper import official_game

STAT = dict(player_points='points', player_rebounds='reboundsTotal', player_assists='assists',
            player_threes='threePointersMade', player_steals='steals', player_blocks='blocks')


def score_game(game, forecasts, mapping):
    """No missing-player zeros; additional counts must reconcile with their team."""
    if (game['gameId'] != mapping['nba_game_id'] or game['gameStatus'] != 3
            or datetime.fromisoformat(game['gameTimeUTC'].replace('Z','+00:00')) != datetime.fromisoformat(mapping['tipoff_utc'])):
        raise ValueError('extension result identity/time mismatch')
    teams = {game[s]['teamId']: game[s] for s in ('homeTeam','awayTeam')}
    if set(teams) != {mapping['home_nba_team_id'],mapping['away_nba_team_id']}:
        raise ValueError('extension team identity mismatch')
    players = {}
    # A single missing extra statistic blocks that market, not the original pilot.
    valid = {}
    for market, stat in STAT.items():
        valid[market] = True
        for team in teams.values():
            counts=[p.get('statistics',{}).get(stat) for p in team['players'] if p.get('played') == '1']
            total=team.get('statistics',{}).get(stat)
            if type(total) is not int or total<0 or any(type(v) is not int or v<0 for v in counts) or sum(counts)!=total:
                valid[market]=False
    for tid,team in teams.items():
        for p in team['players']:
            if p['personId'] in players: raise ValueError('duplicate extension official player')
            players[p['personId']] = (tid,p)
    scores={tid:team.get('statistics',{}).get('points') for tid,team in teams.items()}
    if any(type(v) is not int or v<0 for v in scores.values()) or len(set(scores.values()))!=2 or not valid['player_points']:
        raise ValueError('final team scores do not reconcile')
    outcomes={}
    for f in forecasts:
        key=(f['player_id'],f['market']);actual=None;status='evaluated'
        if f['market'] in STAT:
            pair=players.get(f['player_id'])
            if pair is None or pair[0] != f['team_id']:
                status='validation_hold'
            elif pair[1].get('played')=='0': status='dnp'
            elif pair[1].get('played')!='1' or not valid[f['market']]: status='validation_hold'
            else: actual=pair[1]['statistics'][STAT[f['market']]]
        elif f['market']=='winner': actual=int(scores[mapping['home_nba_team_id']]>scores[mapping['away_nba_team_id']])
        elif f['market']=='team_points': actual=scores[f['team_id']]
        elif f['market']=='game_total': actual=sum(scores.values())
        else: raise ValueError('unknown sealed extension market')
        outcomes[key]=dict(status=status,actual=actual)
    return outcomes


class MultiDashboard:
    def __init__(self, original, bundle_folder):
        self.original=original;self.folder=Path(bundle_folder)
        self.seal=digest(self.folder/'bundle.seal.json')
        self.bundle=self.load()
        if 'model_sha256' in self.bundle and digest(self.folder/'model.json')!=self.bundle['model_sha256']:
            raise ValueError('extension model changed')
        if self.bundle['original_plan_sha256'] != original.plan_hash:
            raise ValueError('extension linked to different original plan')
        mapping={m['provider_event_id']:m for m in original.plan['mappings']}
        seen=set()
        for f in self.bundle['forecasts']:
            m=mapping[f['event_id']];key=(f['event_id'],f['player_id'],f['market'])
            if key in seen or f['nba_game_id']!=m['nba_game_id']:
                raise ValueError('duplicate or foreign extension forecast')
            seen.add(key)
            seal=datetime.fromisoformat(f['sealed_at_utc']);tip=datetime.fromisoformat(m['tipoff_utc'])
            if seal>=tip or f['last_feature_date']>=seal.date().isoformat():
                raise ValueError('extension forecast after target/feature date')
            if f['market'] in STAT and f['player_id'] not in m['players']:
                raise ValueError('extension player outside original verified mapping')
            if not all(math.isfinite(f[k]) for k in ('estimate','line','probability_over','probability_under')) or (
                    not 0<=f['probability_over']<=1 or abs(f['probability_over']+f['probability_under']-1)>1e-8):
                raise ValueError('invalid extension probability')

    def load(self):
        if digest(self.folder/'bundle.seal.json')!=self.seal: raise ValueError('extension seal changed')
        seal=json.loads((self.folder/'bundle.seal.json').read_bytes())
        if digest(self.folder/'bundle.json')!=seal['sha256']: raise ValueError('extension bundle changed')
        return json.loads((self.folder/'bundle.json').read_bytes())

    def data(self):
        bundle=self.load();data=self.original.data();now=datetime.now(UTC)
        payloads=journal(self.original.paper/'state.sqlite')
        results=[]
        for m in self.original.plan['mappings']:
            forecasts=[f for f in bundle['forecasts'] if f['event_id']==m['provider_event_id']]
            event=next(e for e in data['events'] if e['event_id']==m['provider_event_id']);outcomes={}
            scored=[p for p in payloads if p.get('status')=='scored' and p.get('plan_sha256')==self.original.plan_hash and p.get('event_id')==m['provider_event_id']]
            if event['status']=='evaluated' and len(scored)==1:
                try:
                    # Independently revalidate the entire original receipt/evaluation chain.
                    self.original.verify_outcomes(scored[0],m,now)
                    folder=worker_path(self.original.paper,scored[0]['evaluation']).parent/'received'
                    if digest(folder/'receipt.json')!=scored[0]['metrics']['receipt_sha256']:
                        raise ValueError('extension receipt linkage changed')
                    receipt=json.loads((folder/'receipt.json').read_bytes())
                    raw=folder/receipt['raw_file']
                    if receipt['raw_sha256']!=scored[0]['metrics']['raw_sha256'] or digest(raw)!=receipt['raw_sha256']:
                        raise ValueError('extension receipt changed')
                    outcomes=score_game(official_game(raw.read_bytes(),receipt),forecasts,m)
                except (ValueError,KeyError,TypeError,IndexError):
                    outcomes={(f['player_id'],f['market']):dict(status='validation_hold',actual=None) for f in forecasts}
            for f in forecasts:
                # PMFs and local provenance paths stay private; public fields are explicit.
                row={k:f[k] for k in ('event_id','nba_game_id','player_id','player','market','market_label','estimate',
                     'range_low','range_high','line','probability_over','probability_under','sealed_at_utc',
                     'conditional_participation','last_feature_date','reference')}
                row['result']=outcomes.get((f['player_id'],f['market']),dict(status=event['status'],actual=None))
                row['actionable']=False;results.append(row)
        return dict(data, extension=dict(version=bundle['version'],created_at_utc=bundle['created_at_utc'],
            predictions=results,comparison=bundle['comparison'],original_pilot_unchanged=True,
            totals=dict(predictions=len(results),evaluated=sum(r['result']['status']=='evaluated' for r in results),
                        dnp=sum(r['result']['status']=='dnp' for r in results))))


def main():
    original=Dashboard('apps/nba/.local/normalized/nba_f6_run66_20261008/lifecycle','/paper-data','/capture-data','/operations-data')
    Server(('0.0.0.0',8080),handler(MultiDashboard(original,'/app/public-bundle'),'/app/web')).serve_forever()


if __name__=='__main__': main()
