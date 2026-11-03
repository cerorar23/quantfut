"""RUN071 + the new box-score columns of the extended dataset (nba_live14b_protocol.json).

No row, game or season type is added or removed: each RUN071 player row takes tov, fga, fta and oreb of the same (game, player, team)
in the extended dataset, and each game the possessions_estimate of its sides. A row or game missing there keeps None."""
import gzip
import json
from pathlib import Path

from .audit import digest, write_json

COLUMNS = ('tov', 'fga', 'fta', 'oreb')
SAME = ('points', 'rebounds', 'assists', 'threes', 'steals', 'blocks')


def enrich_players(base, extra):
    index = {}
    for r in extra:
        k = (r['game_id'], r['player_id'], r['team_id'])
        if k in index:
            raise ValueError(f'duplicate extended row {k}')
        index[k] = r
    out = []
    for r in base:
        e = index.get((r['game_id'], r['player_id'], r['team_id']))
        if e is not None:
            bad = [k for k in SAME if r.get(k) != e.get(k)]
            if bad:
                raise ValueError(f'extended row disagrees with RUN071 on {bad}: {r["game_id"]} {r["player_id"]}')
        out.append(dict(r, **{k: None if e is None else e[k] for k in COLUMNS}))
    return out


def enrich_games(base, extra):
    index = {g['game_id']: g for g in extra}
    out = []
    for g in base:
        e = index.get(g['game_id'])
        g = dict(g)
        for side in ('home', 'away'):
            if e is not None and (e[side]['team_id'] != g[side]['team_id'] or e[side]['points'] != g[side]['points']):
                raise ValueError(f'extended game disagrees with RUN071: {g["game_id"]}')
            g[side] = dict(g[side], possessions_estimate=None if e is None else e[side].get('possessions_estimate'))
        out.append(g)
    return out


def read_rows(path):
    with gzip.open(path, 'rt', encoding='utf8') as f:
        return [json.loads(line) for line in f]


def build(run71, extended, output):
    run71, extended, output = Path(run71), Path(extended), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    players = enrich_players(read_rows(run71 / 'players.jsonl.gz'), read_rows(extended / 'players.jsonl.gz'))
    games = enrich_games(json.loads((run71 / 'games.json').read_bytes()), json.loads((extended / 'games.json').read_bytes()))
    text = ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in players)
    with open(output / 'players.jsonl.gz', 'wb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', mtime=0) as gz:
        gz.write(text.encode('utf8'))
    (output / 'games.json').write_text(json.dumps(games, ensure_ascii=False), encoding='utf8', newline='\n')
    (output / 'coverage.json').write_bytes((run71 / 'coverage.json').read_bytes())
    missing = {}
    for r in players:
        missing[r['season']] = missing.get(r['season'], 0) + (r['tov'] is None)
    summary = dict(protocol='apps/nba/nba_live14b_protocol.json', player_rows=len(players),
                   without_columns=sum(missing.values()), without_columns_by_season=dict(sorted(missing.items())),
                   games=len(games), games_without_possessions=sum(g['home']['possessions_estimate'] is None for g in games),
                   season_types=sorted({r['season_type'] for r in players}),
                   sources={f'{a}_{n}': digest(d / n) for a, d in (('run71', run71), ('extended', extended))
                            for n in ('players.jsonl.gz', 'games.json')},
                   outputs={n: digest(output / n) for n in ('players.jsonl.gz', 'games.json', 'coverage.json')})
    write_json(output.parent / 'build.json', summary)
    return summary


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('--run71', '--extended', '--output'):
        parser.add_argument(name, required=True)
    a = parser.parse_args()
    print(json.dumps(build(a.run71, a.extended, a.output), indent=2))


if __name__ == '__main__':
    main()
