"""Explicit local operational/research commands; no daemon or publication."""
import argparse
import json
import os
from pathlib import Path
from .ingest import save_json


def main():
    parser=argparse.ArgumentParser(description='Tennis capture, identities, settlement and research')
    sub=parser.add_subparsers(dest='command',required=True)
    seed=sub.add_parser('seed-identities');seed.add_argument('--root',type=Path,required=True);seed.add_argument('--db',type=Path,required=True)
    bind=sub.add_parser('bind-identity')
    for name in ('db','circuit','source-name','player-id','evidence','reviewer'): bind.add_argument('--'+name,required=True)
    resolve=sub.add_parser('reconcile');resolve.add_argument('--db',required=True);resolve.add_argument('--events',type=Path,required=True);resolve.add_argument('--output',type=Path,required=True)
    discovery=sub.add_parser('discover');discovery.add_argument('--root',type=Path,required=True)
    discovery.add_argument('--credit-cap',type=int);discovery.add_argument('--account-reserve',type=int)
    discovery.add_argument('--policy',type=Path)
    discovery.add_argument('--regions',default='eu,uk,us,us2,au');discovery.add_argument('--max-events',type=int,default=2)
    settle=sub.add_parser('settle');settle.add_argument('--bets',type=Path,required=True);settle.add_argument('--output',type=Path,required=True)
    pool=sub.add_parser('pool');wf=sub.add_parser('walk-forward')
    for command in (pool,wf):
        command.add_argument('--root',type=Path,required=True);command.add_argument('--output',type=Path,required=True)
        command.add_argument('--circuit',choices=['ATP','WTA'],required=True)
    wf.add_argument('--start',required=True);wf.add_argument('--end',required=True);wf.add_argument('--pool',type=Path)
    hybrid=sub.add_parser('predict-hybrid')
    for name in ('root','model','pool','output'): hybrid.add_argument('--'+name,type=Path,required=True)
    hybrid.add_argument('--player-a',required=True);hybrid.add_argument('--player-b',required=True)
    hybrid.add_argument('--surface',choices=['Hard','Clay','Grass','Carpet'],required=True)
    hybrid.add_argument('--best-of',type=int,choices=[3,5],default=3)
    hybrid.add_argument('--deciding-tiebreak',type=int,choices=[7,10],default=7)
    shadow=sub.add_parser('shadow',help='Seal a prospective plan; paid odds only in due verified windows')
    for name in ('data-root','models-root','pools-root','operations-root','identity-db','tournament-config'):
        shadow.add_argument('--'+name,type=Path,required=True)
    shadow.add_argument('--fixture-file',type=Path)
    shadow.add_argument('--credit-cap',type=int)
    shadow.add_argument('--account-reserve',type=int)
    shadow.add_argument('--policy',type=Path)
    shadow.add_argument('--calibration-root',type=Path)
    shadow.add_argument('--refresh-official',action='store_true')
    shadow.add_argument('--regions',default='eu,uk')
    shadow.add_argument('--capture-odds',action='store_true')
    audit_cmd=sub.add_parser('audit',help='Offline data/model/receipt audit; no paid API calls')
    for name in ('root','operations-root','output'): audit_cmd.add_argument('--'+name,type=Path,required=True)
    dyn=sub.add_parser('dynamic-experiment');dyn.add_argument('--canonical-root',type=Path,required=True)
    dyn.add_argument('--baseline-root',type=Path,required=True);dyn.add_argument('--output',type=Path,required=True)
    dyn.add_argument('--circuit',choices=['ATP','WTA'],required=True)
    der=sub.add_parser('calibrate-derivatives')
    for name in ('root','output'):der.add_argument('--'+name,type=Path,required=True)
    der.add_argument('--circuit',choices=['ATP','WTA'],required=True)
    der.add_argument('--training-cache',type=Path)
    hist=sub.add_parser('historical')
    hist.add_argument('--root',type=Path,required=True);hist.add_argument('--policy',type=Path,required=True)
    hist.add_argument('--sport',required=True);hist.add_argument('--date',required=True)
    hist.add_argument('--bookmakers',default='pinnacle');hist.add_argument('--markets',default='h2h,spreads,totals')
    hist.add_argument('--credit-cap',type=int);hist.add_argument('--account-reserve',type=int)
    prospect=sub.add_parser('evaluate-prospective')
    for name in ('operations-root','results','output'):prospect.add_argument('--'+name,type=Path,required=True)
    prospect.add_argument('--protocol',type=Path)
    freeze=sub.add_parser('freeze-protocol')
    for name in ('data-root','improvements-root','calibration-root','output'):freeze.add_argument('--'+name,type=Path,required=True)
    freeze.add_argument('--start',required=True);freeze.add_argument('--end',required=True)
    context=sub.add_parser('context')
    context.add_argument('--history',type=Path,required=True);context.add_argument('--venue',type=Path)
    context.add_argument('--player-id',required=True);context.add_argument('--start',required=True)
    context.add_argument('--decision-at',required=True);context.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.command in ('discover','shadow','historical'):
        policy=json.loads(args.policy.read_text(encoding='utf-8')) if args.policy else {}
        if args.credit_cap is None:args.credit_cap=policy.get('monthly_tennis_credit_cap',0)
        if args.account_reserve is None:args.account_reserve=policy.get('shared_account_reserve',6000)
    if args.command=='seed-identities':
        import pandas as pd
        from .identities import Registry
        result={'canonical_players':Registry(args.db).seed(pd.read_parquet(args.root/'canonical/matches.parquet')),'provider_aliases_automatically_verified':0}
    elif args.command=='bind-identity':
        from .identities import Registry
        result={'player_id':Registry(args.db).bind('the_odds_api',args.circuit,'name:'+args.source_name,args.player_id,args.evidence,args.reviewer)}
    elif args.command=='reconcile':
        from .identities import Registry,reconcile
        events=json.loads(args.events.read_text(encoding='utf-8'))
        result=reconcile(events,Registry(args.db));save_json(args.output,result)
    elif args.command=='discover':
        from .operations import discover
        key=os.environ.get('TENNIS_ODDS_API_KEY') or os.environ.get('ODDS_API_KEY')
        if not key: raise ValueError('Set TENNIS_ODDS_API_KEY securely in the process environment')
        if args.max_events<0: raise ValueError('Nonnegative event bound required')
        result=discover(args.root,key,args.credit_cap,args.account_reserve,args.regions,args.max_events)
    elif args.command=='settle':
        from .settlement import ledger
        result=ledger(json.loads(args.bets.read_text(encoding='utf-8')));save_json(args.output,result)
    elif args.command=='pool':
        from .research import compare_pool
        result=compare_pool(args.root,args.output,args.circuit)
    elif args.command=='walk-forward':
        from .research import walk_forward
        result=walk_forward(args.root,args.output,args.circuit,args.start,args.end,args.pool)
    elif args.command=='predict-hybrid':
        from .research import hybrid_forecast
        result=hybrid_forecast(args.root,args.model,args.pool,args.player_a,args.player_b,args.surface,args.best_of,args.deciding_tiebreak)
        save_json(args.output,result)
    elif args.command=='shadow':
        from .shadow import run_shadow
        key=os.environ.get('TENNIS_ODDS_API_KEY') or os.environ.get('ODDS_API_KEY')
        if not key: raise ValueError('Set TENNIS_ODDS_API_KEY securely in the process environment')
        result=run_shadow(args.data_root,args.models_root,args.pools_root,args.operations_root,
                          args.identity_db,args.tournament_config,key,args.credit_cap,
                          args.account_reserve,args.regions,args.fixture_file,args.capture_odds,
                          calibration_root=args.calibration_root,refresh_official=args.refresh_official)
    elif args.command=='audit':
        from .audit import audit
        from .reporting import render
        report=audit(args.root,args.operations_root,args.output)
        render(report,args.output/'audit.html')
        result={'report':str(args.output/'audit.json'),'html':str(args.output/'audit.html'),
                'integrity_pass':report['integrity_pass'],'production_approved':False,
                'failures':report['failures'],'warnings':report['warnings']}
    elif args.command=='dynamic-experiment':
        from .dynamic import experiment
        report=experiment(args.canonical_root,args.baseline_root,args.output,args.circuit)
        result={'report':str(args.output/'report.json'),'production_approved':False}
    elif args.command=='calibrate-derivatives':
        from .calibration import derivative_experiment
        report=derivative_experiment(args.root,args.output,args.circuit,args.training_cache)
        result={'report':str(args.output/'report.json'),'production_approved':False}
    elif args.command=='historical':
        from .history import historical_snapshot
        key=os.environ.get('TENNIS_ODDS_API_KEY') or os.environ.get('ODDS_API_KEY')
        if not key:raise ValueError('Set the Odds API key securely in the process environment')
        result=historical_snapshot(args.root,key,args.sport,args.date,args.credit_cap,args.account_reserve,
                                   args.bookmakers,args.markets)
    elif args.command=='evaluate-prospective':
        from .prospective import evaluate_prospective
        report=evaluate_prospective(args.operations_root,args.results,args.output,args.protocol)
        result={'output':str(args.output),'scored_event_windows':report['scored_event_windows'],
                'metrics':report['metrics'],'production_approved':False}
    elif args.command=='freeze-protocol':
        from .prospective import freeze_protocol
        freeze_protocol(args.data_root,args.improvements_root,args.calibration_root,args.output,args.start,args.end)
        result={'output':str(args.output),'production_approved':False}
    elif args.command=='context':
        from .context import player_context
        history=json.loads(args.history.read_text(encoding='utf-8'))
        venue=json.loads(args.venue.read_text(encoding='utf-8')) if args.venue else None
        result=player_context(args.player_id,args.start,args.decision_at,history,venue);save_json(args.output,result)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if result.get('integrity_pass') is False: raise SystemExit(1)


if __name__=='__main__': main()
