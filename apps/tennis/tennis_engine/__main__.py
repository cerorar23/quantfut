import argparse
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description='Local tennis research pipeline')
    sub=parser.add_subparsers(dest='command',required=True)
    dl=sub.add_parser('download')
    dl.add_argument('--root',type=Path,required=True)
    dl.add_argument('--source',choices=['all','tml','mcp'],default='all')
    dl.add_argument('--seed-mcp',type=Path)
    norm=sub.add_parser('normalize')
    norm.add_argument('--root',type=Path,required=True)
    norm.add_argument('--as-of',default='2026-10-16')
    norm.add_argument('--output-root',type=Path,help='Fresh canonical output without replacing the fitted source snapshot')
    fit=sub.add_parser('train')
    fit.add_argument('--root',type=Path,required=True)
    fit.add_argument('--output',type=Path,required=True)
    fit.add_argument('--circuit',choices=['ATP','WTA'],required=True)
    fit.add_argument('--cutoff',required=True)
    fit.add_argument('--since',default='2018-01-01')
    ev=sub.add_parser('evaluate')
    ev.add_argument('--root',type=Path,required=True)
    ev.add_argument('--output',type=Path,required=True)
    ev.add_argument('--circuit',choices=['ATP','WTA'],required=True)
    ev.add_argument('--test-year',type=int,default=2026)
    mev=sub.add_parser('evaluate-markets')
    mev.add_argument('--root',type=Path,required=True)
    mev.add_argument('--output',type=Path,required=True)
    pred=sub.add_parser('predict')
    pred.add_argument('--model',type=Path,required=True)
    pred.add_argument('--player-a',required=True)
    pred.add_argument('--player-b',required=True)
    pred.add_argument('--surface',choices=['Hard','Clay','Grass','Carpet'],default='Hard')
    pred.add_argument('--best-of',type=int,choices=[3,5],default=3)
    pred.add_argument('--deciding-tiebreak',type=int,choices=[7,10],default=7)
    pred.add_argument('--output',type=Path,required=True)
    pred.add_argument('--samples',type=int,default=24)
    args=parser.parse_args()
    if args.command=='download':
        from .ingest import download
        result=download(args.root,args.source,args.seed_mcp)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        if result['failed']: raise SystemExit(1)
    elif args.command=='normalize':
        from .normalize import normalize
        print(json.dumps(normalize(args.root,args.as_of,args.output_root),ensure_ascii=False,indent=2))
    elif args.command=='train':
        from .model import train
        print(json.dumps(train(args.root,args.output,args.circuit,args.cutoff,args.since),indent=2))
    elif args.command=='evaluate':
        from .evaluate import evaluate
        print(json.dumps(evaluate(args.root,args.output,args.circuit,args.test_year),indent=2))
    elif args.command=='evaluate-markets':
        from .evaluate import evaluate_markets
        print(json.dumps(evaluate_markets(args.root,args.output),indent=2))
    elif args.command=='predict':
        from .forecast import forecast
        from .ingest import save_json
        result=forecast(args.model,args.player_a,args.player_b,args.surface,args.best_of,args.deciding_tiebreak,args.samples)
        save_json(args.output,result)
        print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
