"""Link historical prop quotes (props_history.load rows) to box-score players of the same game.

Matching is by name inside that game's roster only: exact `name_key`, then the same key without a Jr/Sr/II-IV
suffix when that is unique in the roster. A known player with no box row that game keeps the quote with no outcome (`no_box_row`); anything else stays
unmatched and is counted, never guessed.
The realised stat is attached for training; it is the outcome, not a pre-game feature.
"""
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
import re

from .context import name_key

STAT = dict(player_points='points', player_rebounds='rebounds', player_assists='assists', player_threes='threes')
SUFFIX = re.compile(r'\s(jr|sr|ii|iii|iv)$')
# Provider spelling -> box-score spelling; each pair checked against players.jsonl.gz on 2026-10-24 (the match is still
# restricted to the game's roster, so an alias cannot attach a quote to someone who did not play that game).
ALIASES = {name_key(k): name_key(v) for k, v in {
    'Carlton Carrington': 'Bub Carrington', 'Nicolas Claxton': 'Nic Claxton', 'Herb Jones': 'Herbert Jones',
    'Ron Holland': 'Ronald Holland II', 'Vincent Williams Jr': 'Vince Williams Jr.', 'Moe Wagner': 'Moritz Wagner',
    'B.J. Boston Jr': 'Brandon Boston', 'James Huff': 'Jay Huff', 'Kenyon Martin Jr.': 'KJ Martin'}.items()}


def rosters(players):
    """game_id -> (exact index, suffix-stripped index); a key shared by two players is marked None."""
    games = defaultdict(lambda: ({}, {}))
    for p in players:
        exact, loose = games[str(p['game_id'])]
        for index, key in ((exact, name_key(p['name'])), (loose, SUFFIX.sub('', name_key(p['name'])))):
            index[key] = None if key in index else p
    return games


def link(rows, players):
    index, out, stats, unmatched = rosters(players), [], Counter(), Counter()
    ids = defaultdict(set)
    for p in players:
        ids[name_key(p['name'])].add(p['player_id'])
    for row in rows:
        exact, loose = index.get(row['game_id'], ({}, {}))
        key = ALIASES.get(name_key(row['player']), name_key(row['player']))
        found, how = exact.get(key), 'exact'
        if found is None:
            found, how = loose.get(SUFFIX.sub('', key)), 'suffix'
        if found is None and len(ids.get(key, ())) == 1:
            # a known player with no box row in this game (inactive / did not play): keep the quote, no outcome
            stats['no_box_row'] += 1
            out.append(row | dict(player_id=next(iter(ids[key])), team_id=None, participated=None, minutes=None, actual=None))
            continue
        if found is None:
            stats['unmatched'] += 1
            unmatched[row['player']] += 1
            continue
        stats[how] += 1
        out.append(row | dict(player_id=found['player_id'], team_id=found['team_id'], participated=found['participated'],
                              minutes=found['minutes'], actual=found[STAT[row['market']]]))
    return out, dict(stats), unmatched


def read_players(path):
    with gzip.open(path, 'rt', encoding='utf8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--players', required=True, type=Path)
    parser.add_argument('--odds', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    a = parser.parse_args()
    rows, stats, unmatched = link(read_players(a.odds), read_players(a.players))
    with gzip.open(a.output, 'wt', encoding='utf8') as stream:
        stream.writelines(json.dumps(r) + '\n' for r in rows)
    print(json.dumps(dict(linked=len(rows), **stats, top_unmatched=unmatched.most_common(15))))


if __name__ == '__main__':
    main()
