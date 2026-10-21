"""Daily producer for live v1.3 cohorts: collect official results, then seal today's games after the afternoon report.

Meant to run every ~10 minutes from cron; every decision is taken here, in Eastern time, so the host timezone is irrelevant.
"""
from datetime import UTC, datetime, time
import json
from pathlib import Path

from . import multimarket as m1
from . import multimarket_v13_live as live

SEAL_AFTER = time(17, 35)  # Eastern: after the 17:30 injury report, before the evening tipoffs
ROOT = Path(__file__).parents[2]


def run(now, cohorts, model, data, first_day, get=live.http_get):
    """Returns a status dict; raises only on unexpected failures (so cron mail/log shows them)."""
    cohorts, status = Path(cohorts), dict(at_utc=now.isoformat(), results={}, sealed=None)
    for folder in sorted(p.parent for p in cohorts.glob('*/bundle.seal.json')):
        status['results'][folder.name] = live.capture_results(folder, now, get)
    local = now.astimezone(live.EASTERN)
    day = local.date().isoformat()
    if local.time() < SEAL_AFTER or (cohorts / day).exists():
        return status
    protocol_path = ROOT / 'multimarket_v13_live_protocol.json'
    protocol = dict(json.loads(protocol_path.read_bytes()), _path=str(protocol_path))
    v12_protocol = json.loads((ROOT / 'multimarket_v12_protocol.json').read_bytes())
    data = Path(data)
    players, games = m1.read_rows(data / 'players.jsonl.gz'), json.loads((data / 'games.json').read_bytes())
    try:
        status['sealed'] = live.seal(model, cohorts / day, day, players, games, protocol, v12_protocol, now=now, get=get,
                                     first_completed_day=first_day, exclude=live.sealed_games(cohorts))
    except ValueError as error:
        if str(error) != 'no games left to seal for this date':
            raise
        status['sealed'] = 'no_games_left'
    return status


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohorts', default='/live13/cohorts')
    parser.add_argument('--model', default='/live13/model')
    parser.add_argument('--data', default='/live13/data')
    parser.add_argument('--first-day', default='2026-10-20')
    a = parser.parse_args()
    print(json.dumps(run(datetime.now(UTC), a.cohorts, a.model, a.data, a.first_day), default=str))


if __name__ == '__main__':
    main()
