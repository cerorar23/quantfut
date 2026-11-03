"""v1 player-prop probabilities against the US books' no-vig probabilities at the quoted lines.

Research only (protocol: nba_props_vs_market_protocol.json, frozen before running). Needs props_link output."""
from collections import defaultdict, deque
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize_scalar
from scipy.special import expit, logit

from . import multimarket as m1
from . import multimarket_v12 as v12
from .audit import digest, write_json

STAT = dict(player_points='points', player_rebounds='rebounds', player_assists='assists', player_threes='threes')
OVERROUND = (-.02, .25)


def units(rows):
    """Quotes with a realised outcome -> one row per (game, player, market, line) with the consensus no-vig over."""
    groups, drops = defaultdict(list), defaultdict(int)
    for r in rows:
        if r['actual'] is None or not r['participated'] or not r['minutes'] or r['minutes'] <= 0:
            drops['no_outcome_or_dnp'] += 1
            continue
        if r['over'] <= 1 or r['under'] <= 1:
            drops['bad_price'] += 1
            continue
        inv_o, inv_u = 1 / r['over'], 1 / r['under']
        if not OVERROUND[0] <= inv_o + inv_u - 1 <= OVERROUND[1]:
            drops['overround_out_of_range'] += 1
            continue
        groups[(r['game_id'], r['player_id'], r['market'], r['line'])].append((logit(inv_o / (inv_o + inv_u)), r))
    out = []
    for (game, player, market, line), items in groups.items():
        first = items[0][1]
        if first['actual'] == line:
            drops['push'] += 1
            continue
        out.append(dict(game_id=game, player_id=player, market=market, line=line, books=len(items),
                        market_p=float(expit(np.mean([v for v, _ in items]))), y=int(first['actual'] > line),
                        minutes_to_tipoff=first['minutes_to_tipoff']))
    return out, dict(drops)


def attach_model(units_, players, protocol):
    """Replay box rows by date (a date's forecasts precede its outcomes) and price each unit at its own line."""
    need = defaultdict(list)
    for u in units_:
        need[(u['game_id'], u['player_id'])].append(u)
    local = dict(history_window=20, min_history=10, history_max_days=370, prior_minutes=90,
                 empirical_weight=protocol['model']['empirical_weight'], player_prior_rates=protocol['player_prior_rates'])
    histories, days, skipped = defaultdict(lambda: deque(maxlen=20)), defaultdict(list), defaultdict(int)
    for r in players:
        days[r['date']].append(r)
    priced = []
    for day in sorted(days):
        for r in days[day]:
            wanted = need.get((str(r['game_id']), r['player_id']))
            if not wanted:
                continue
            history = m1.eligible(histories[r['player_id']], day, local)
            if len(history) < local['min_history']:
                skipped['insufficient_history'] += len(wanted)
                continue
            parameters = {}
            for u in wanted:
                stat = STAT[u['market']]
                parameters.setdefault(stat, m1.player_parameters(history, stat, local))
                priced.append(dict(u, date=day, season=m1.season_label(day),
                                   model_p=m1.player_over(parameters[stat], u['line'], local)))
        for r in days[day]:
            if r['participated'] and r['minutes'] > 0:
                histories[r['player_id']].append(r)
    return priced, dict(skipped)


def _logits(rows):
    clip = lambda p: np.clip(p, 1e-6, 1 - 1e-6)
    return logit(clip([r['model_p'] for r in rows])), logit(clip([r['market_p'] for r in rows]))


def information_weight(rows):
    """c in logit(p) = lk + c (lm - lk), maximum likelihood; cluster-robust (by date) standard error."""
    y, (lm, lk) = np.asarray([r['y'] for r in rows], float), _logits(rows)
    d = lm - lk
    nll = lambda c: float(np.sum(np.logaddexp(0, lk + c * d) - y * (lk + c * d)))
    c = float(minimize_scalar(nll, bounds=(-1., 3.), method='bounded').x)
    p = expit(lk + c * d)
    information = float(np.sum(p * (1 - p) * d * d))
    scores = defaultdict(float)
    for r, s in zip(rows, (y - p) * d):
        scores[r['date']] += s
    se = float(np.sqrt(sum(v * v for v in scores.values())) / information)
    return dict(c=c, ci95=[c - 1.96 * se, c + 1.96 * se], se=se)


def blend(rows, c):
    lm, lk = _logits(rows)
    return expit(lk + c * (lm - lk))


def compare(rows, protocol):
    y = [r['y'] for r in rows]
    model, loss_m = v12.metrics(y, [r['model_p'] for r in rows])
    market, loss_k = v12.metrics(y, [r['market_p'] for r in rows])
    diff = loss_m - loss_k
    half, _ = v12.metrics(y, blend(rows, .5))
    stats = protocol['stats']
    return dict(model=model, market=market, blend_5050=half, information_weight=information_weight(rows),
                paired_brier_difference=float(diff.mean()),
                ci95_date_bootstrap=v12.date_bootstrap([r['date'] for r in rows], diff, stats['bootstrap'], stats['seed']),
                mean_books=float(np.mean([r['books'] for r in rows])))


def evaluate(units_, players, protocol):
    priced, skipped = attach_model(units_, players, protocol)
    seasons = protocol['seasons']
    report = dict(skipped=skipped, markets={}, units=len(priced))
    final = {}
    for market in protocol['markets']:
        per = {s: [r for r in priced if r['market'] == market and r['season'] == s] for s in seasons}
        entry = dict(seasons={s: compare(rows, protocol) for s, rows in per.items() if len(rows) >= 200})
        if all(s in entry['seasons'] for s in seasons):
            first, second = per[seasons[0]], per[seasons[1]]
            c = entry['seasons'][seasons[0]]['information_weight']['c']
            wf, _ = v12.metrics([r['y'] for r in second], blend(second, c))
            entry['walk_forward'] = dict(c_from_first=c, blend=wf, market=entry['seasons'][seasons[1]]['market'])
            both = information_weight(first + second)
            final[market] = dict(c_first_season=c, c_both_seasons=both['c'], ci95_both=both['ci95'], rows=len(first) + len(second))
            low = [entry['seasons'][s]['information_weight']['ci95'][0] > 0 for s in seasons]
            entry['adds_information'] = bool(all(low) and wf['brier'] < entry['walk_forward']['market']['brier'])
            entry['better_than_market'] = bool(all(entry['seasons'][s]['ci95_date_bootstrap'][1] < 0 for s in seasons))
        report['markets'][market] = entry
    return report, final


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True, help='dir with players.jsonl.gz')
    parser.add_argument('--linked', required=True, type=Path, help='props_linked.jsonl.gz from nba.props_link')
    parser.add_argument('--protocol', required=True)
    parser.add_argument('--v12-protocol', required=True)
    parser.add_argument('--output', required=True, type=Path, help='folder holding protocol_frozen.json')
    a = parser.parse_args()
    if json.loads((a.output / 'protocol_frozen.json').read_bytes())['sha256'] != digest(a.protocol):
        raise ValueError('protocol changed after it was frozen')
    protocol = json.loads(Path(a.protocol).read_bytes())
    protocol['player_prior_rates'] = json.loads(Path(a.v12_protocol).read_bytes())['player_prior_rates']
    from .props_link import read_players
    rows, drops = units(read_players(a.linked))
    report, final = evaluate(rows, m1.read_rows(Path(a.data) / 'players.jsonl.gz'), protocol)
    report['drops'] = drops
    write_json(a.output / 'props_market_comparison.json', report)
    write_json(a.output / 'props_blend.json', dict(research_prior=True, promoted=False, markets=final))
    print(json.dumps({m: dict(adds_information=e.get('adds_information'), better_than_market=e.get('better_than_market'))
                      for m, e in report['markets'].items()} | dict(units=report['units']), allow_nan=False))


if __name__ == '__main__':
    main()
