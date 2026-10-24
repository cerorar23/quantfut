"""Daily producer for live v1.3 cohorts: collect official results, then seal each game shortly before its own tipoff.

Meant to run every ~10 minutes from cron; every decision is taken here, in Eastern time, so the host timezone is irrelevant.
A game is sealed in the first run that finds its tipoff inside SEAL_LEAD, together with any other game in that window,
so afternoon games are covered and every game gets the newest report that can still count (>= 60 min before tipoff).
"""
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

from . import multimarket as m1
from . import multimarket_v13_live as live

SEAL_LEAD = (timedelta(minutes=65), timedelta(minutes=90))  # seal when the tipoff is this far ahead; two cron runs fit
SCHEDULE_TTL = timedelta(hours=2)  # the day's tipoffs are read again after this long
ROOT = Path(__file__).parents[2]


def schedule(day, now, cache, get):
    """game id -> tipoff of the day's games not started, from the official pages; kept in the cache for SCHEDULE_TTL."""
    path = Path(cache) / 'schedule' / f'{day}.json'
    if path.is_file():
        stored = json.loads(path.read_bytes())
        if now - datetime.fromisoformat(stored['fetched_at_utc']) < SCHEDULE_TTL:
            return stored['games']
    games = {m['nba_game_id']: m['tipoff_utc'] for m in live.upcoming(day, now, get)}
    live.store(cache, 'schedule', day, dict(fetched_at_utc=now.isoformat(), games=games))
    return games


def run(now, cohorts, model, data, first_day, cache, get=live.http_get, clock=None):
    """Returns a status dict; raises only on unexpected failures (so cron mail/log shows them).

    `now` is when the run starts and drives every decision; `clock` stamps receipts and the seal (default: `now`)."""
    cohorts, status = Path(cohorts), dict(at_utc=now.isoformat(), results={}, sealed=None)
    for folder in sorted(p.parent for p in cohorts.glob('*/bundle.seal.json')):
        status['results'][folder.name] = live.capture_results(folder, now, get)
    local = now.astimezone(live.EASTERN)
    day = local.date().isoformat()
    sealed = live.sealed_games(cohorts)
    due = [g for g, tip in schedule(day, now, cache, get).items()
           if g not in sealed and SEAL_LEAD[0] < datetime.fromisoformat(tip) - now <= SEAL_LEAD[1]]
    if not due:
        return status
    protocol_path = ROOT / 'multimarket_v13_live_protocol.json'
    protocol = dict(json.loads(protocol_path.read_bytes()), _path=str(protocol_path))
    v12_protocol = json.loads((ROOT / 'multimarket_v12_protocol.json').read_bytes())
    data = Path(data)
    players, games = m1.read_rows(data / 'players.jsonl.gz'), json.loads((data / 'games.json').read_bytes())
    try:
        status['sealed'] = live.seal(model, cohorts / f"{day}_{local:%H%M}", day, players, games, protocol, v12_protocol, now=now,
                                     get=get, first_completed_day=first_day, exclude=sealed, cache=cache, clock=clock, lead=SEAL_LEAD)
    except ValueError as error:
        if str(error) != 'no games left to seal for this date':
            raise
        status['sealed'] = 'no_games_left'  # the fresh pages moved or started every game the cached schedule had due
    return status


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohorts', default='/live13/cohorts')
    parser.add_argument('--model', default='/live13/model')
    parser.add_argument('--data', default='/live13/data')
    parser.add_argument('--cache', default='/live13/cache', help='finished games and the day schedule, kept between runs')
    parser.add_argument('--first-day', default='2026-10-20')
    a = parser.parse_args()
    clock = lambda: datetime.now(UTC)
    print(json.dumps(run(clock(), a.cohorts, a.model, a.data, a.first_day, a.cache, clock=clock), default=str))


if __name__ == '__main__':
    main()
