"""Pre-year, per-contract marginal calibration. No joint coherence is claimed."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit,logit
from .evaluate import scores,observed_markets
from .model import ServeModel
from .scoring import Rules,match_distribution,market
from .ingest import save_json

SPECS={'over_22_5_games':('games_total',22.5,'over'),
       'A_minus_3_5_games':('games_handicap',-3.5,'A'),
       'any_tiebreak':('tiebreak',None,'yes'),'first_set_A':('first_set',None,'A')}


def fit_calibrator(y,p,symmetric=False):
    y=np.asarray(y);p=np.asarray(p)
    if len(y)<100 or len(y)!=len(p) or not np.isin(y,[0,1]).all() or not np.isfinite(p).all() or ((p<=0)|(p>=1)).any():
        raise ValueError('At least 100 valid binary calibration observations required')
    x=logit(p)
    def objective(parameters):
        intercept,slope=parameters;z=intercept+slope*x;delta=np.array([intercept,slope-1.])
        value=np.sum(np.logaddexp(0,z)-y*z)+5*np.dot(delta,delta)
        residual=expit(z)-y
        return float(value),np.array([residual.sum(),np.dot(residual,x)])+10*delta
    fitted=minimize(objective,[0.,1.],jac=True,bounds=[(0.,0.) if symmetric else (-3.,3.),(.25,3.)],method='L-BFGS-B')
    if not fitted.success:raise RuntimeError('Calibration did not converge')
    return {'intercept':float(fitted.x[0]),'slope':float(fitted.x[1]),'ridge_precision':10.,'n':len(y),'symmetric':symmetric}


def calibrated(p,parameters):
    p=np.asarray(p)
    if not np.isfinite(p).all() or ((p<0)|(p>1)).any():raise ValueError('Invalid probabilities')
    return expit(parameters['intercept']+parameters['slope']*logit(np.clip(p,1e-7,1-1e-7)))


def generate(root,output,circuit,year):
    experiment=Path(root)/f'experiments/{circuit}_{year}'
    held=pd.read_parquet(experiment/'heldout_predictions.parquet')
    source=pd.read_parquet(Path(root)/'canonical/matches.parquet').set_index('match_id',verify_integrity=True)
    model=ServeModel(experiment/'model',uncertainty=False);records=[]
    for i,reference in enumerate(held.itertuples()):
        row=source.loc[reference.match_id]
        points=model.predict(reference.a,reference.b,row.surface,uncertainty=False)
        distribution=match_distribution(points['p'],points['q'],Rules(int(row.best_of),deciding_tiebreak=10 if row.tourney_level=='G' else 7))
        actual=observed_markets(row,reference.a==row.winner_id)
        for name,(kind,line,side) in SPECS.items():
            records.append({'match_id':reference.match_id,'period':row.period,'market':name,'y':actual[name],
                            'probability':market(distribution,kind,line,side)['win']})
        if (i+1)%500==0:print(f'{circuit} {year} secondary markets: {i+1}/{len(held)}',flush=True)
    result=pd.DataFrame(records);result.to_parquet(output/f'heldout_markets_{year}.parquet',index=False)
    return result


def derivative_experiment(root,output,circuit,training_cache=None):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    protocol={'circuit':circuit,'fit_year':2025,'test_year':2026,'ridge_precision':10.,
              'contracts':{k:list(v) for k,v in SPECS.items()},'created_before_fits':True,
              'canonical_sha256':hashlib.sha256((Path(root)/'canonical/matches.parquet').read_bytes()).hexdigest(),
              'scope':'Exploratory retrospective fixed-contract marginal calibration; all 2026 remains development',
              'production_approved':False,'jointly_coherent':False,'financial_validation':False}
    save_json(output/'protocol.json',protocol)
    if training_cache is None:training=generate(root,output,circuit,2025)
    else:
        training=pd.read_parquet(training_cache)
        if not training.period.str.startswith('2025').all():raise ValueError('Cache must contain pre-2026 calibration observations only')
        training.to_parquet(output/'heldout_markets_2025.parquet',index=False)
    training=training.loc[training.period.lt('2025-11-27')]
    # Reuse already archived 2026 model predictions rather than recomputing an unchanged experiment.
    path=Path(root)/f'experiments/{circuit}_2026/heldout_markets.parquet'
    test=pd.read_parquet(path)
    source_col='probability' if 'probability' in test else 'model_probability'
    results={};parameters={};all_rows=[]
    for name,spec in SPECS.items():
        fit=training.loc[training.market.eq(name)];held=test.loc[test.market.eq(name)].copy()
        parameters[name]={**fit_calibrator(fit.y,fit.probability,symmetric=name=='first_set_A'),'contract':list(spec),
                          'training_last_period':fit.period.max(),'source_year':2025}
        held['calibrated_probability']=calibrated(held[source_col],parameters[name])
        # Join period explicitly when the old market table lacks one.
        if 'period' not in held:
            periods=pd.read_parquet(Path(root)/f'experiments/{circuit}_2026/heldout_predictions.parquet')[['match_id','period']]
            held=held.merge(periods,on='match_id',validate='many_to_one')
        y=held.y.to_numpy();p=np.clip(held[source_col].to_numpy(),1e-7,1-1e-7);q=held.calibrated_probability.to_numpy()
        loss=lambda v:-(y*np.log(v)+(1-y)*np.log1p(-v))
        delta=loss(q)-loss(p)
        blocks=pd.DataFrame({'period':held.period,'delta':delta}).groupby('period').delta.agg(['sum','count'])
        rng=np.random.default_rng(20261017);draws=[]
        for _ in range(1000):
            selected=blocks.iloc[rng.integers(len(blocks),size=len(blocks))]
            draws.append(float(selected['sum'].sum()/selected['count'].sum()))
        results[name]={'raw':scores(y,p),'calibrated':scores(y,q),
                       'calibrated_minus_raw_log_loss':float(delta.mean()),'period_block_ci95':np.quantile(draws,[.025,.975]).tolist()}
        all_rows.extend(held.to_dict('records'))
    pd.DataFrame(all_rows).to_parquet(output/'predictions_2026.parquet',index=False)
    save_json(output/'calibrators.json',parameters)
    report={**protocol,'metrics':results,'training_predictions_sha256':hashlib.sha256((output/'heldout_markets_2025.parquet').read_bytes()).hexdigest(),
            'test_predictions_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'limit':'No coefficients may be reused at untested lines or transformed into a coherent multi-market portfolio'}
    save_json(output/'report.json',report)
    print(json.dumps({'circuit':circuit,'metrics':results}),flush=True)
    return report


def apply_contract(probabilities,kind,line,selection,profiles):
    """Experimental exact-line marginal overlay, with complements kept together."""
    if probabilities['push']>1e-10:return None
    reverse=False;name=None
    if kind=='first_set':name='first_set_A'
    elif kind=='games_total' and line==22.5:
        name='over_22_5_games';reverse=selection=='under'
    elif kind=='games_handicap' and line in (-3.5,3.5):
        name='A_minus_3_5_games';reverse=line==3.5
    elif kind=='tiebreak':name='any_tiebreak';reverse=selection=='no'
    if name not in profiles:return None
    parameters=profiles[name]
    if name=='first_set_A' and (not parameters.get('symmetric') or parameters['intercept']!=0):return None
    x=probabilities['win'];x=1-x if reverse else x
    value=float(calibrated(x,parameters));value=1-value if reverse else value
    return {'experimental_calibrated_win':value,'experimental_calibrated_loss':1-value,
            'calibrated_push':0.,'calibrated_fair_decimal_odds':1/value if value else None,
            'calibration_contract':name,'calibration_production_approved':False}
