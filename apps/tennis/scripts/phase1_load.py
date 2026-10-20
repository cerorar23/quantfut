"""Offline first-phase audit against archived API-Tennis and the current model.

Example: PYTHONPATH=apps/tennis python apps/tennis/scripts/phase1_load.py
 --data-root data/tennis --probe-root .local/api_tennis_probe/20261017T211250Z
 --output data/tennis/load_phase1_20261017

The two explicit provider/name mappings below are reviewed sample cases, not
an automatic fuzzy identity linker. This script makes no provider requests.
"""
import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import tennis_engine.benchmark as benchmark_module
import tennis_engine.recent_load as load_module
import tennis_engine.load_runner as runner_module

from tennis_engine.benchmark import BenchmarkCase, BenchmarkEvaluator
from tennis_engine.load_runner import ModelRunner
from tennis_engine.operations import now, utc
from tennis_engine.recent_load import api_tennis_history
from tennis_engine.research import hybrid_forecast


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('--data-root',type=Path,required=True)
    parser.add_argument('--probe-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        raise ValueError('Use a new immutable output directory')
    receipts=json.loads((args.probe_root/'manifest.json').read_text())
    receipt={r['label']:r for r in receipts}
    for label in ('recent','upcoming'):
        if receipt[label].get('success')!=1 or receipt[label].get('http_status')!=200:
            raise ValueError('Successful capture receipt required')
        raw=(args.probe_root/(label+'.json')).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=receipt[label]['sha256']:
            raise ValueError('Capture hash mismatch')
    history=api_tennis_history(args.probe_root/'recent.json',receipt['recent']['received_at'],receipt['recent']['sha256'])
    upcoming=json.loads((args.probe_root/'upcoming.json').read_bytes())['result']
    mapping={
        '12171959':('ATP','2842','50323','A. Davidovich Fokina','R. Jodar','atp:DH50','atp:J0DZ'),
        '12171967':('WTA','1434','1961','M. Chwalinska','S. Kartal','wta:216081','wta:222661'),
    }
    decision=now();cases=[];metadata={}
    for row in upcoming:
        key=str(row['event_key'])
        if key not in mapping:continue
        circuit,a,b,name_a,name_b,internal_a,internal_b=mapping[key]
        if (str(row['first_player_key']),str(row['second_player_key']),row['event_first_player'],row['event_second_player'])!=(a,b,name_a,name_b):
            raise ValueError('Reviewed sample pairing no longer matches')
        start=row['event_date']+'T'+row['event_time']+':00+00:00'
        if utc(receipt['upcoming']['received_at'])>=utc(decision):
            raise ValueError('Calendar was not available before decision')
        case=BenchmarkCase('api_tennis:'+key+':phase1', 'api_tennis:'+key,a,b,decision,start)
        cases.append(case);metadata[case.case_id]=(circuit,internal_a,internal_b)
    if len(cases)!=2:raise ValueError('Two reviewed fixtures required')
    base_details={}
    def current(case: BenchmarkCase) -> float:
        circuit,a,b=metadata[case.case_id]
        detail=hybrid_forecast(args.data_root/'full_20261016',
                args.data_root/f'full_20261016/models/{circuit}_current',
                args.data_root/f'improvements_20261016/{circuit}_pool/pool.json',a,b,'Hard',3,7)
        base_details[case.case_id]=detail
        return detail['winner_A']
    run=ModelRunner(current).run(cases,history)
    report=BenchmarkEvaluator().evaluate(cases,[],run['variants'],now())
    report.update({'cases':[asdict(c) for c in cases],
                   'predictions':{k:[asdict(p) for p in v] for k,v in run['variants'].items()},
                   'load_features':run['features'],'baseline_details':base_details,
                   'source_receipts':[receipt[k] for k in ('recent','upcoming')],
                   'normalized_history_matches':len(history),
                   'history_statuses':dict(Counter(r.status for r in history)),
                   'load_training_rows':0,'load_correction_fitted':False,
                   'implementation_sha256': {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in [Path(__file__),Path(benchmark_module.__file__),Path(load_module.__file__),Path(runner_module.__file__)]},
                   'reason':'No archived pre-decision load training sample with verified completion bounds.',
                   'holdout_note':'Existing frozen future protocol unchanged. This experiment is not a new validated candidate.',
                   'financial_validation':False,'paid_api_calls':0})
    args.output.mkdir(parents=True,exist_ok=False)
    (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'report':str(args.output/'report.json'),'baseline_predictions':len(cases),
                     'n_common':report['n_common'],'load_training_rows':0,'paid_api_calls':0}))


if __name__=='__main__':main()
