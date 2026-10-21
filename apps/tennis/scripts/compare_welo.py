"""Offline historical benchmark, explicitly experimental."""
import argparse
import json
from pathlib import Path
from tennis_engine.weighted_elo import compare_weighted_elo


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--improvements-root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--circuit',choices=['ATP','WTA'],required=True)
    a=p.parse_args()
    report=compare_weighted_elo(a.root,a.improvements_root,a.output,a.circuit)
    print(json.dumps({'circuit':a.circuit,'n_common':report['n_common'],'metrics':{
        k:{m:v[m] for m in ('log_loss','brier','ece')} for k,v in report['metrics'].items()}}))


if __name__=='__main__':main()
