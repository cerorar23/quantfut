import json
from pathlib import Path
import pandas as pd
from tennis_engine.research import fit_pool,pooled
from tennis_engine.evaluate import scores
from tennis_engine.ingest import save_json

base=Path('data/tennis/extension_20261017')
for circuit in ('ATP','WTA'):
    root=base/(circuit+'_dynamic_v2');data=pd.read_parquet(root/'predictions.parquet')
    fit=data.loc[data.year.eq(2025)&data.period.lt('2025-11-27')].copy()
    held=data.loc[data.year.eq(2026)].copy();result={}
    for variant in ('dynamic_base','dynamic_context'):
        training=fit.rename(columns={variant+'_probability':'model_probability'})
        test=held.rename(columns={variant+'_probability':'model_probability'})
        scale=fit_pool(training,1.);blend=fit_pool(training)
        result[variant]={'scale_only_parameters':scale,'blend_parameters':blend,
                         'scale_only_2026':scores(test.y,pooled(test,scale)),
                         'blend_with_elo_2026':scores(test.y,pooled(test,blend))}
    reference=json.loads(Path(f'data/tennis/improvements_20261016/{circuit}_controls.json').read_text())
    result['previous_candidate']=reference['evaluations']['frozen_2026']['metrics']
    report={'circuit':circuit,'production_approved':False,'fit_period':'2025 prior to 2025-11-27',
            'scope':'Additional exploratory controls. No automatic model promotion.', 'results':result}
    save_json(root/'calibrated_controls.json',report)
    print(json.dumps(report))
