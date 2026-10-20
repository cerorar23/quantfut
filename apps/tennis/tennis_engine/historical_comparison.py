"""Retrospective spatial ablation; never pretends source receipts were pre-match.

The prospective BenchmarkEvaluator requires verified individual clocks. This
adapter instead preserves source-period uncertainty, freezes whole competition
blocks and explicitly labels its outputs as exploratory retrospective research.
"""
from typing import Any
import hashlib
import json
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit, logit
from .benchmark import probability_metrics

FEATURES=('difference_distance_km','difference_delta_altitude_m','difference_delta_timezone_hours')


def attach_baseline(dataset: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    """Join exact canonical identities; reject conflicting labels or future fits."""
    required={'match_id','player_a','player_b','y','baseline_probability','origin',
              'training_latest_period','pool_latest_period'}
    if not required.issubset(predictions):raise ValueError('Incomplete baseline receipt')
    if not dataset.match_id.is_unique or not predictions.match_id.is_unique:
        raise ValueError('Duplicate match identity')
    if not set(predictions.match_id).issubset(set(dataset.match_id)):
        raise ValueError('Foreign prediction')
    joined=dataset.merge(predictions,on='match_id',how='left',validate='one_to_one',suffixes=('','_prediction'))
    supplied=joined.origin.notna()
    for key in ('player_a','player_b','y'):
        if not joined.loc[supplied,key].eq(joined.loc[supplied,key+'_prediction']).all():
            raise ValueError('Baseline orientation or label differs')
    p=joined.loc[supplied,'baseline_probability'].to_numpy(dtype=float)
    if not np.isfinite(p).all() or ((p<0)|(p>1)).any():raise ValueError('Invalid baseline probability')
    for row in joined.loc[supplied].itertuples():
        origin=pd.Timestamp(row.origin)
        if pd.Timestamp(row.training_latest_period)>=origin-pd.Timedelta(days=35):
            raise ValueError('Baseline training violates origin embargo')
        if pd.Timestamp(row.pool_latest_period)>=origin-pd.Timedelta(days=35):
            raise ValueError('Calibration violates origin embargo')
        if pd.Timestamp(row.edition_source_period_first)<=max(pd.Timestamp(row.training_latest_period),pd.Timestamp(row.pool_latest_period))+pd.Timedelta(days=6):
            raise ValueError('Baseline information overlaps target source period')
        expected='2024-01-01' if row.partition=='development_2024' else '2025-01-01' if row.partition=='exploratory_2025' else None
        if expected and origin!=pd.Timestamp(expected):raise ValueError('Wrong baseline origin for partition')
    return joined


class HistoricalSpatialCorrection:
    """Symmetric ridge logistic offset; RMS and beta use development rows only.

    logit(p_spatial)=logit(p_base)+sum(beta_j * (x_A-x_B)_j / RMS_train_j).
    Fixed ridge multiplies half squared coefficient norm in mean-log-loss units.
    No intercept, centering, test tuning or assumed monotonic fatigue penalty.
    """
    def __init__(self,ridge: float=1.0,min_rows: int=100):
        if isinstance(ridge,bool) or not np.isfinite(ridge) or ridge<=0 or type(min_rows) is not int or min_rows<2:
            raise ValueError('Positive ridge and minimum sample required')
        self.ridge=float(ridge);self.min_rows=min_rows;self.artifact: dict[str,Any] | None=None

    @staticmethod
    def matrix(frame: pd.DataFrame) -> np.ndarray:
        x=frame[list(FEATURES)].to_numpy(dtype=float)
        if not np.isfinite(x).all():raise ValueError('Missing spatial features')
        return x

    def fit(self,training: pd.DataFrame) -> dict[str,Any]:
        if self.artifact is not None:raise ValueError('Use a new object for another fit')
        if len(training)<self.min_rows or not training.partition.eq('development_2024').all():
            raise ValueError('Only sufficient development-2024 rows can train')
        if not training.match_id.is_unique or not training.eligible_spatial_probability_cohort.all():
            raise ValueError('Unique eligible training rows required')
        if pd.to_datetime(training.edition_source_period_last).max()+pd.Timedelta(days=6)>=pd.Timestamp('2025-01-01'):
            raise ValueError('Training source period overlaps test origin')
        x=self.matrix(training);p=training.baseline_probability.to_numpy(dtype=float);y=training.y.to_numpy(dtype=float)
        if not np.isfinite(p).all() or ((p<0)|(p>1)).any() or not set(y)=={0,1}:
            raise ValueError('Both outcomes and valid baseline required')
        scale=np.sqrt(np.mean(x*x,axis=0));scale[scale==0]=1
        z=x/scale;offset=logit(np.clip(p,1e-12,1-1e-12))
        def objective(beta):
            eta=offset+z@beta
            return float(np.mean(np.logaddexp(0,eta)-y*eta)+self.ridge*np.dot(beta,beta)/2),z.T@(expit(eta)-y)/len(y)+self.ridge*beta
        fitted=minimize(objective,np.zeros(len(FEATURES)),jac=True,method='L-BFGS-B',options={'gtol':1e-9})
        if not fitted.success:raise RuntimeError('Spatial fit failed: '+str(fitted.message))
        identity=training.sort_values('match_id')[['match_id','baseline_probability','y',*FEATURES]].to_json(orient='records',double_precision=15)
        self.artifact=dict(label='experimental_retrospective',beta=fitted.x.tolist(),rms_train=scale.tolist(),ridge=self.ridge,
            features=list(FEATURES),training_n=len(training),training_event_ids=sorted(training.match_id.tolist()),
            training_competition_ids=sorted(training.comparison_block_id.unique().tolist()),
            training_matrix_sha256=hashlib.sha256(identity.encode()).hexdigest(),optimizer_success=True,
            last_training_source_period=training.edition_source_period_last.max())
        return self.artifact

    def predict(self,frame: pd.DataFrame) -> np.ndarray:
        if self.artifact is None:raise ValueError('Fit first')
        x=self.matrix(frame)/np.asarray(self.artifact['rms_train'])
        p=frame.baseline_probability.to_numpy(dtype=float)
        if not np.isfinite(p).all() or ((p<0)|(p>1)).any():raise ValueError('Invalid baseline')
        return expit(logit(np.clip(p,1e-12,1-1e-12))+x@self.artifact['beta'])


def paired_interval(frame: pd.DataFrame,draws: int=1000,seed: int=20261018) -> dict[str,Any]:
    """Paired competition-block resampling, descriptive rather than a selection test."""
    y=frame.y.to_numpy(dtype=float)
    def loss(p):
        p=np.clip(np.asarray(p),1e-12,1-1e-12)
        return -(y*np.log(p)+(1-y)*np.log1p(-p))
    delta=loss(frame.spatial_probability)-loss(frame.baseline_probability)
    grouped=pd.DataFrame({'block':frame.comparison_block_id,'loss':delta,
        'brier':(frame.spatial_probability-y)**2-(frame.baseline_probability-y)**2}).groupby('block').agg(loss=('loss','sum'),brier=('brier','sum'),n=('loss','size'))
    rng=np.random.default_rng(seed);samples=[]
    for _ in range(draws):
        selected=grouped.iloc[rng.integers(len(grouped),size=len(grouped))]
        samples.append([selected.loss.sum()/selected.n.sum(),selected.brier.sum()/selected.n.sum()])
    intervals=np.quantile(samples,[.025,.975],axis=0)
    return dict(n_competitions=len(grouped),draws=draws,seed=seed,
        log_loss_spatial_minus_base=float(delta.mean()),log_loss_ci95=intervals[:,0].tolist(),
        brier_spatial_minus_base=float(((frame.spatial_probability-y)**2-(frame.baseline_probability-y)**2).mean()),brier_ci95=intervals[:,1].tolist(),
        limitation='Competition blocks do not capture all cross-event player dependence; exploratory, no multiple-comparison correction')


def compare_historical(dataset: pd.DataFrame,predictions: pd.DataFrame,*,exclude_coarse: bool=False,ridge: float=1.0) -> tuple[pd.DataFrame,dict[str,Any]]:
    """Identical evaluation intersection and a separate training-only sensitivity fit."""
    if not dataset.historical_reconstruction.all() or dataset.genuine_asof_validation.any():
        raise ValueError('This adapter is retrospective only')
    if not dataset.groupby('comparison_block_id').partition.nunique().eq(1).all():
        raise ValueError('Competition split across partitions')
    frame=attach_baseline(dataset,predictions)
    eligible=frame.eligible_spatial_probability_cohort & frame.baseline_probability.notna()
    if exclude_coarse:eligible &= ~frame.coarse_venue_reference_used
    train=frame.loc[eligible & frame.partition.eq('development_2024')].copy()
    test=frame.loc[eligible & frame.partition.eq('exploratory_2025')].copy()
    if test.empty:raise ValueError('No common test rows')
    if set(train.comparison_block_id)&set(test.comparison_block_id):raise ValueError('Competition overlap')
    correction=HistoricalSpatialCorrection(ridge=ridge);artifact=correction.fit(train)
    test['spatial_probability']=correction.predict(test)
    n_total=int(frame.partition.eq('exploratory_2025').sum())
    def metrics(group):return {name:probability_metrics(group.y.astype(int).tolist(),group[col].astype(float).tolist()) for name,col in [('base','baseline_probability'),('base_plus_spatial','spatial_probability')]}
    report=dict(schema='tennis-retrospective-spatial-comparison-v1',label='2025_exploratory',status='evaluated',
        exclude_coarse=exclude_coarse,n_train_common=len(train),n_test_total=n_total,n_test_common=len(test),coverage=len(test)/n_total,
        n_test_completed=int((frame.partition.eq('exploratory_2025') & frame.completed_standard).sum()),
        metrics=metrics(test),by_circuit={c:dict(metrics=metrics(g),paired=paired_interval(g)) for c,g in test.groupby('circuit')},
        paired=paired_interval(test),artifact=artifact,genuine_asof_validation=False,
        financial_validation=False,production_approved=False,test_used_for_tuning=False,
        rest_imputed=False,comparison_contract='Same IDs and labels for both variants; exact-clock prospective evaluator deliberately not used')
    return test,report
