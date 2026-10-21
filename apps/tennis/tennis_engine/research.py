"""Predeclared exploratory comparisons; never promote on already-viewed 2026."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit, logit
from .evaluate import elo_ratings, scores
from .model import train, training_rows, ServeModel
from .scoring import Rules, match_win
from .ingest import save_json


def calibration_bins(y, p):
    y=np.asarray(y); p=np.asarray(p)
    if len(y)!=len(p) or not len(y) or not np.isin(y,[0,1]).all() or not np.isfinite(p).all() or ((p<0)|(p>1)).any():
        raise ValueError('Valid binary observations and probabilities required')
    bins=np.minimum((p*10).astype(int),9)
    rows=[]
    for i in range(10):
        subset=bins==i
        if subset.any():
            rows.append({'lower':i/10,'upper':(i+1)/10,'n':int(subset.sum()),
                         'mean_probability':float(p[subset].mean()),'observed_rate':float(y[subset].mean())})
    return rows


def fit_pool(frame, fixed_weight=None):
    """Symmetric logit pooling: no arbitrary bonus for the higher Elo player."""
    a=logit(np.clip(frame.model_probability.to_numpy(),1e-7,1-1e-7))
    b=logit(np.clip(frame.surface_elo_probability.to_numpy(),1e-7,1-1e-7))
    y=frame.y.to_numpy()
    if len(y)<100 or not np.isin(y,[0,1]).all() or not np.isfinite(a+b).all():
        raise ValueError('Insufficient or invalid calibration sample')
    def loss(parameters):
        weight,scale=parameters
        z=scale*(weight*a+(1-weight)*b)
        return float(np.mean(np.logaddexp(0,z)-y*z))
    bounds=[(0,1),(.25,2.)] if fixed_weight is None else [(fixed_weight,fixed_weight),(.25,2.)]
    result=minimize(loss,[.5 if fixed_weight is None else fixed_weight,1.],bounds=bounds,method='L-BFGS-B')
    if not result.success: raise RuntimeError('Pool fit did not converge')
    return {'markov_weight':float(result.x[0]),'logit_scale':float(result.x[1]),
            'training_n':len(y),'first_period':frame.period.min(),'last_period':frame.period.max(),
            'kind':'Symmetric winner-only logit pool; does not alter point probabilities or other markets'}


def pooled(frame, parameters):
    a=logit(np.clip(np.asarray(frame.model_probability),1e-7,1-1e-7))
    b=logit(np.clip(np.asarray(frame.surface_elo_probability),1e-7,1-1e-7))
    return expit(parameters['logit_scale']*(parameters['markov_weight']*a+(1-parameters['markov_weight'])*b))


def compare_pool(root,output,circuit):
    output=Path(output); output.mkdir(parents=True,exist_ok=False)
    base=Path(root)/'experiments'
    path=base/f'{circuit}_2025/heldout_predictions.parquet'
    training=pd.read_parquet(path)
    training=training.loc[training.period.lt('2025-11-27')]
    parameters=fit_pool(training)
    parameters.update(circuit=circuit,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    test=pd.read_parquet(base/f'{circuit}_2026/heldout_predictions.parquet')
    test['hybrid_probability']=pooled(test,parameters)
    test.to_parquet(output/'predictions.parquet',index=False)
    report={'circuit':circuit,'parameters':parameters,'metrics':{},'calibration':{},
            'evaluation_label':'Exploratory 2026 reanalysis; coefficients fitted only on pre-2026 predictions',
            'production_approved':False,'financial_validation':False}
    for column in ('model_probability','surface_elo_probability','hybrid_probability'):
        report['metrics'][column]=scores(test.y,test[column])
        report['calibration'][column]=calibration_bins(test.y,test[column])
    save_json(output/'pool.json',parameters);save_json(output/'report.json',report)
    return report


def compare_controls(root, experiment_root, circuit):
    """Report simple recalibration controls too, so pooling gets no unearned credit."""
    training=pd.read_parquet(Path(root)/f'experiments/{circuit}_2025/heldout_predictions.parquet')
    training=training.loc[training.period.lt('2025-11-27')]
    pools={'hybrid':fit_pool(training),'calibrated_elo':fit_pool(training,0.),'calibrated_markov':fit_pool(training,1.)}
    result={'circuit':circuit,'parameters':pools,'evaluations':{},'production_approved':False,
            'label':'Exploratory additional controls, not preregistered final validation',
            'ci_limit':'Period block bootstrap does not model all cross-period player dependence or multiple comparisons'}
    for name,path in [('frozen_2026',Path(root)/f'experiments/{circuit}_2026/heldout_predictions.parquet'),
                      ('monthly_jul_sep',Path(experiment_root)/f'{circuit}_monthly/predictions.parquet')]:
        frame=pd.read_parquet(path)
        predictions={key:pooled(frame,p) for key,p in pools.items()}
        y=frame.y.to_numpy()
        def loss(p): return -(y*np.log(p)+(1-y)*np.log1p(-p))
        difference=loss(predictions['hybrid'])-loss(predictions['calibrated_elo'])
        blocks=pd.DataFrame({'period':frame.period,'loss':difference}).groupby('period').loss.agg(['sum','count'])
        rng=np.random.default_rng(20261016)
        draws=[]
        for _ in range(1000):
            selected=blocks.iloc[rng.integers(len(blocks),size=len(blocks))]
            draws.append(selected['sum'].sum()/selected['count'].sum())
        result['evaluations'][name]={'metrics':{key:scores(y,p) for key,p in predictions.items()},
             'hybrid_minus_calibrated_elo':{'mean':float(difference.mean()),'period_block_ci95':np.quantile(draws,[.025,.975]).tolist()}}
    save_json(Path(experiment_root)/(circuit+'_controls.json'),result)
    return result


def months(start,end):
    if len(start)!=7 or len(end)!=7: raise ValueError('Months must be YYYY-MM')
    first=pd.Timestamp(start+'-01'); last=pd.Timestamp(end+'-01')
    if last<first: raise ValueError('Invalid month interval')
    return pd.date_range(first,last,freq='MS')


def hybrid_forecast(root,model_path,pool_path,player_a,player_b,surface,best_of=3,deciding_tiebreak=7):
    model=ServeModel(model_path,uncertainty=False)
    parameters=json.loads(Path(pool_path).read_text())
    cutoff=model.summary['cutoff']; circuit=model.summary['circuit']
    if parameters['circuit']!=circuit or pd.Timestamp(parameters['last_period'])>=pd.Timestamp(cutoff)-pd.Timedelta(days=35):
        raise ValueError('Pool overlaps forecast cutoff or wrong circuit')
    source=Path(root)/'canonical/matches.parquet'
    receipt=json.loads((Path(model_path)/'training_receipt.json').read_text())
    if hashlib.sha256(source.read_bytes()).hexdigest()!=receipt['canonical_sha256']:
        raise ValueError('Canonical source does not match model receipt')
    a=model.resolve(player_a);b=model.resolve(player_b)
    point=model.predict(a,b,surface,uncertainty=False)
    markov=match_win(point['p'],point['q'],Rules(best_of,deciding_tiebreak=deciding_tiebreak))
    ratings,by_surface=elo_ratings(training_rows(root,circuit,cutoff))
    elo=1/(1+10**(((ratings[b]-ratings[a])+(by_surface[(b,surface)]-by_surface[(a,surface)]))/800))
    frame=pd.DataFrame({'model_probability':[markov],'surface_elo_probability':[elo]})
    probability=float(pooled(frame,parameters)[0])
    control_path=Path(pool_path).parent.parent/(circuit+'_controls.json')
    control=None;control_probability=None
    if control_path.exists():
        control=json.loads(control_path.read_text(encoding='utf-8'))['parameters']['calibrated_elo']
        if pd.Timestamp(control['last_period'])>=pd.Timestamp(cutoff)-pd.Timedelta(days=35):
            raise ValueError('Elo control calibration overlaps forecast origin')
        control_probability=float(pooled(frame,control)[0])
    return {'player_a':a,'player_b':b,'surface':surface,'best_of':best_of,'cutoff':cutoff,
            'serve':point,'deciding_tiebreak':deciding_tiebreak,
            'winner_A':probability,'winner_B':1-probability,'markov_A':markov,'surface_elo_A':elo,
            'calibrated_surface_elo_A':control_probability,'elo_control_parameters':control,
            'pool':parameters,'production_approved':False,'scheduled_event_verified':False,
            'scope':'Winner-only research candidate, completed-match conditional; other markets retain separate uncalibrated model',
            'uncertainty':'MAP inputs and fitted pool; full parameter/model uncertainty not integrated'}


def walk_forward(root,output,circuit,start,end,pool_path=None):
    """Frozen within each month, refit at every origin with a 35-day embargo."""
    origins=months(start,end)
    if any(origin.year<2022 for origin in origins):
        raise ValueError('Current final-set rules are restricted to 2022 onwards')
    output=Path(output); output.mkdir(parents=True,exist_ok=False)
    source=Path(root)/'canonical/matches.parquet'
    data=pd.read_parquet(source)
    parameters=json.loads(Path(pool_path).read_text()) if pool_path else None
    if parameters and (parameters['circuit']!=circuit or pd.Timestamp(parameters['last_period'])>=origins[0]-pd.Timedelta(days=35)):
        raise ValueError('Calibration source overlaps origin/embargo or belongs to another circuit')
    protocol={'circuit':circuit,'origins':[x.strftime('%Y-%m-%d') for x in origins],
              'canonical_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'embargo_days':35,
              'pool':parameters,'created_before_fits':True,'label':'Exploratory retrospective monthly walk-forward',
              'historical_availability_verified':False,'production_approved':False,
              'first_server':'unknown, integrated 50/50','probability_method':'MAP points to Markov; posterior not integrated'}
    save_json(output/'protocol.json',protocol)
    records=[];folds=[]
    for origin in origins:
        cutoff=origin.strftime('%Y-%m-%d'); upper=(origin+pd.offsets.MonthBegin()).strftime('%Y-%m-%d')
        test=data.loc[data.circuit.eq(circuit)&data.eligible_model&data.source_group.eq('tour')&data.period.ge(cutoff)&data.period.lt(upper)]
        if test.empty:
            folds.append({'origin':cutoff,'n':0,'reason':'No eligible matches'});continue
        folder=output/cutoff; train(root,folder,circuit,cutoff)
        history=training_rows(root,circuit,cutoff); overall,surfaces=elo_ratings(history)
        model=ServeModel(folder,uncertainty=False)
        batch=[]
        for row in test.itertuples():
            # Stable ID-based presentation, independent of order and fitted predictions.
            y=int(hashlib.sha256(row.match_id.encode()).digest()[0]%2)
            a,b=(row.winner_id,row.loser_id) if y else (row.loser_id,row.winner_id)
            pred=model.predict(a,b,row.surface,uncertainty=False)
            probability=match_win(pred['p'],pred['q'],Rules(int(row.best_of),deciding_tiebreak=10 if row.tourney_level=='G' else 7))
            elo=1/(1+10**(((overall[b]-overall[a])+(surfaces[(b,row.surface)]-surfaces[(a,row.surface)]))/800))
            batch.append({'match_id':row.match_id,'origin':cutoff,'period':row.period,'surface':row.surface,
                          'a':a,'b':b,'y':y,'model_probability':probability,'surface_elo_probability':elo})
        frame=pd.DataFrame(batch)
        if parameters: frame['hybrid_probability']=pooled(frame,parameters)
        columns=[c for c in frame if c.endswith('_probability')]
        folds.append({'origin':cutoff,'training_last_period':history.period.max(),'n':len(frame),
                      'metrics':{col:scores(frame.y,frame[col]) for col in columns}})
        records.extend(frame.to_dict('records'))
        print(f'{circuit} {cutoff}: {len(frame)} evaluated',flush=True)
    if not records: raise ValueError('No eligible folds')
    observations=pd.DataFrame(records)
    if observations.match_id.duplicated().any(): raise ValueError('Overlapping test folds')
    observations.to_parquet(output/'predictions.parquet',index=False)
    columns=[c for c in observations if c.endswith('_probability')]
    report={**protocol,'folds':folds,'metrics':{col:scores(observations.y,observations[col]) for col in columns},
            'calibration':{col:calibration_bins(observations.y,observations[col]) for col in columns},
            'financial_validation':False}
    save_json(output/'report.json',report)
    return report
