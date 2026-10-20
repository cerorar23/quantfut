"""Current engine CLI: forecast one match in every market, or seal/evaluate through the frozen v8 study."""
import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    f = sub.add_parser('forecast')
    f.add_argument('--circuit', choices=['ATP', 'WTA'], required=True)
    f.add_argument('--player-a', required=True)
    f.add_argument('--player-b', required=True)
    f.add_argument('--surface', choices=['Hard', 'Clay', 'Grass'], required=True)
    f.add_argument('--date', required=True, help='Match day (YYYY-MM-DD)')
    f.add_argument('--best-of', type=int, choices=[3, 5], default=3)
    f.add_argument('--deciding-tiebreak', type=int, choices=[7, 10], default=7)
    f.add_argument('--odds-a', type=float, help='Decimal pre-match odds for player A (optional, typed by hand)')
    f.add_argument('--odds-b', type=float, help='Decimal pre-match odds for player B')
    f.add_argument('--output', type=Path)
    f.add_argument('--config', type=Path)
    for name in ('seal', 'evaluate'):
        sub.add_parser(name, add_help=False)
    args, rest = parser.parse_known_args()
    if args.command in ('seal', 'evaluate'):
        from tennis_core_v8.__main__ import main as current
        sys.argv = ['tennis_core_v8', args.command, *rest]
        return current()
    from . import Motor, CONFIG
    result = Motor(args.config or CONFIG).forecast(args.circuit, args.player_a, args.player_b, args.surface, args.date,
                                                     args.best_of, args.deciding_tiebreak,
                                                     (args.odds_a, args.odds_b) if args.odds_a or args.odds_b else None)
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        with Path(args.output).open('x', encoding='utf-8') as handle:
            handle.write(text)
    w = result['winner']
    print(f"{result['players'][0]} vs {result['players'][1]}: gana A {w['final_winner']:.1%} (Markov crudo {w['markov_winner']:.1%}; fuente {w['source']})")
    for row in result['markets'][:12]:
        c, p = row['contract'], row['probabilities']
        print(' ', c['kind'], c.get('selection'), c.get('line') if c.get('line') is not None else '', f"{p.get('win', 0):.1%}")


if __name__ == '__main__':
    main()
