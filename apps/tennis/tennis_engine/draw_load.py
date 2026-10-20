"""Observed earlier knockout-round workload, independent of unknown clock times.

These are cumulative counts within one singles main draw, never 3/7-day load.
The adapter is retrospective: source receipt dates remain in 2026. Ranking a
round establishes logical precedence for the same player, not elapsed rest.
"""
from collections import Counter,defaultdict
import json
from typing import Any,Sequence
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit,logit
from .normalize import standard_score
from .benchmark import probability_metrics
from .historical_comparison import attach_baseline,paired_interval

ROUND_ORDER={r:i for i,r in enumerate(('R128','R64','R32','R16','QF','SF','F'))}
COUNTERS=('points','games','sets','deciding_sets')
CONTROL_KEYS=('played_matches','walkovers','points_missing','games_missing','sets_missing','deciding_sets_missing')
CONTROL_FEATURES=tuple('coverage_'+k+'_difference' for k in CONTROL_KEYS)
LOAD_FEATURES=tuple('load_'+k+'_difference' for k in COUNTERS)


def observed_counters(row: Any) -> dict[str,int | None]:
    """Points from both recorded serve totals; games/sets from complete scores.

    Tie-break points belong to service totals, not to a games-to-points formula.
    A walkover is a non-played advancement. Other incomplete scores stay missing.
    """
    if str(row.score).strip().upper() in ('W/O','WO','WALKOVER'):
        return {k:0 for k in COUNTERS}
    values={k:None for k in COUNTERS}
    if bool(row.valid_serve_counts):
        totals=[getattr(row,k) for k in ('w_svpt','l_svpt')]
        if all(pd.notna(v) and np.isfinite(v) and v>0 and float(v).is_integer() for v in totals):
            values['points']=int(sum(totals))
    if standard_score(row.score,int(row.best_of)):
        import re
        pairs=[tuple(map(int,re.match(r'(\d+)-(\d+)',token).groups())) for token in row.score.split()]
        values.update(games=sum(a+b for a,b in pairs),sets=len(pairs),deciding_sets=int(len(pairs)==int(row.best_of)))
    return values


def extract_draw_load(canonical: pd.DataFrame,targets: pd.DataFrame) -> tuple[pd.DataFrame,dict[str,Any]]:
    """Use exact player/draw identity and earlier rounds; no match_num ordering.

    Round-robin editions are explicitly unsupported. Multiple appearances at one
    knockout stage, or a loss followed by an advancement, quarantine that player.
    The primary comparison later requires observed prior play for both players.
    No absent record is claimed to prove an absence of workload.
    """
    required={'match_id','circuit','source_group','tourney_id','tourney_level','round','winner_id','loser_id','score','best_of','valid_serve_counts','w_svpt','l_svpt'}
    if not required.issubset(canonical):raise ValueError('Canonical counter contract missing')
    if not canonical.match_id.is_unique or not targets.match_id.is_unique:raise ValueError('Duplicate identity')
    original=canonical.set_index('match_id',verify_integrity=True)
    if not set(targets.match_id).issubset(original.index):raise ValueError('Unknown target')
    groups={};player_rows=defaultdict(list)
    for key,frame in canonical.groupby(['circuit','source_group','tourney_id'],sort=False):
        groups[key]=set(frame['round'])
        for row in frame.itertuples(index=False):
            for player in (row.winner_id,row.loser_id):player_rows[key,player].append(row)
    records=[];statuses=Counter()
    for target in targets.itertuples(index=False):
        row=original.loc[target.match_id]
        if sorted((row.winner_id,row.loser_id))!=[target.player_a,target.player_b]:raise ValueError('Target orientation differs')
        key=(row.circuit,row.source_group,row.tourney_id)
        entry=dict(match_id=target.match_id,round=row['round'],load_scope='observed_earlier_knockout_rounds_same_singles_draw',
                   clock_window_verified=False,history_complete=False)
        # Team tie rounds describe team advancement, not an individual draw.
        # A player can lose a rubber and play again when their team advances.
        individual=row.tourney_level!='D' and not any(tag in row.tourney_id for tag in ('-M-DC-','-W-FC-'))
        supported=individual and row['round'] in ROUND_ORDER and 'RR' not in groups[key] and row.source_group=='tour'
        both_valid=supported
        for side,player in (('a',target.player_a),('b',target.player_b)):
            earlier=[r for r in player_rows[key,player] if r.match_id!=target.match_id and r.round in ROUND_ORDER and supported and ROUND_ORDER[r.round]<ROUND_ORDER[row['round']]]
            earlier.sort(key=lambda r:ROUND_ORDER[r.round])
            counts=Counter(r.round for r in earlier)
            status='observed_draw_history' if supported else 'unsupported_round_format'
            if supported and (any(n>1 for n in counts.values()) or any(r.winner_id!=player for r in earlier)):
                status='draw_progression_conflict';both_valid=False
            totals={k:0 for k in COUNTERS};missing={k:0 for k in COUNTERS};played=walkovers=0
            for prior in earlier:
                if str(prior.score).strip().upper() in ('W/O','WO','WALKOVER'):walkovers+=1
                else:played+=1
                counters=observed_counters(prior)
                for name,value in counters.items():
                    if value is None:missing[name]+=1
                    else:totals[name]+=value
            entry[side+'_status']=status;entry[side+'_prior_match_ids']=json.dumps([r.match_id for r in earlier])
            entry[side+'_played_matches']=played;entry[side+'_walkovers']=walkovers
            for name in COUNTERS:
                entry[side+'_'+name+'_known_subtotal']=totals[name]
                entry[side+'_'+name+'_missing']=missing[name]
            statuses[status]+=1
        entry['draw_load_supported']=both_valid
        entry['both_have_prior_observed_play']=entry['a_played_matches']>0 and entry['b_played_matches']>0
        entry['observed_counters_complete']=all(entry[s+'_'+k+'_missing']==0 for s in ('a','b') for k in COUNTERS)
        for keyname in CONTROL_KEYS:entry['coverage_'+keyname+'_difference']=entry['a_'+keyname]-entry['b_'+keyname]
        for name in COUNTERS:entry['load_'+name+'_difference']=entry['a_'+name+'_known_subtotal']-entry['b_'+name+'_known_subtotal']
        records.append(entry)
    result=pd.DataFrame(records)
    return result,dict(schema='tennis-draw-load-extraction-v1',n_targets=len(result),statuses=dict(statuses),
        supported=int(result.draw_load_supported.sum()),both_prior_play=int((result.draw_load_supported & result.both_have_prior_observed_play).sum()),
        genuine_asof_validation=False,windows_3d_7d_available=False,minutes_or_rest_imputed=False,
        scope='Counters from observed preceding knockout rounds; no doubles, qualifiers or previous tournaments; incomplete draw coverage remains possible')


class DrawLoadCorrection:
    """Train-only symmetric ridge offset with a declared coverage-only control."""
    def __init__(self,features: Sequence[str],ridge: float=1.,min_rows: int=100):
        if not features or len(set(features))!=len(features) or not set(features).issubset(set(CONTROL_FEATURES+LOAD_FEATURES)):
            raise ValueError('Declared unique draw-load features required')
        if not np.isfinite(ridge) or ridge<=0 or type(min_rows) is not int or min_rows<2:raise ValueError('Invalid fit settings')
        self.features=tuple(features);self.ridge=float(ridge);self.minimum=min_rows;self.artifact=None

    def fit(self,frame: pd.DataFrame) -> dict[str,Any]:
        if self.artifact is not None:raise ValueError('Use a new fit object')
        if len(frame)<self.minimum or not frame.partition.eq('development_2024').all() or not frame.match_id.is_unique:
            raise ValueError('Sufficient unique development rows required')
        if pd.to_datetime(frame.edition_source_period_last).max()+pd.Timedelta(days=6)>=pd.Timestamp('2025-01-01'):
            raise ValueError('Training source period overlaps evaluation')
        x=frame[list(self.features)].to_numpy(dtype=float);y=frame.y.to_numpy(dtype=float)
        p=frame.baseline_probability.to_numpy(dtype=float)
        if not np.isfinite(x).all() or not np.isfinite(p).all() or ((p<0)|(p>1)).any() or set(y)!={0,1}:raise ValueError('Invalid training values')
        scale=np.sqrt(np.mean(x*x,axis=0));scale[scale==0]=1
        z=x/scale;offset=logit(np.clip(p,1e-12,1-1e-12))
        def objective(beta):
            eta=offset+z@beta
            return float(np.mean(np.logaddexp(0,eta)-y*eta)+self.ridge*np.dot(beta,beta)/2),z.T@(expit(eta)-y)/len(y)+self.ridge*beta
        fitted=minimize(objective,np.zeros(len(self.features)),jac=True,method='L-BFGS-B',options={'gtol':1e-9})
        if not fitted.success:raise RuntimeError('Draw-load correction failed')
        self.artifact=dict(features=list(self.features),beta=fitted.x.tolist(),rms_train=scale.tolist(),ridge=self.ridge,
            training_n=len(frame),training_event_ids=sorted(frame.match_id.tolist()),
            training_competition_ids=sorted(frame.comparison_block_id.unique().tolist()),label='experimental_retrospective_draw_load')
        return self.artifact

    def predict(self,frame: pd.DataFrame) -> np.ndarray:
        if self.artifact is None:raise ValueError('Fit first')
        x=frame[list(self.features)].to_numpy(dtype=float)
        p=frame.baseline_probability.to_numpy(dtype=float)
        if not np.isfinite(x).all() or not np.isfinite(p).all() or ((p<0)|(p>1)).any():raise ValueError('Invalid prediction values')
        return expit(logit(np.clip(p,1e-12,1-1e-12))+(x/self.artifact['rms_train'])@self.artifact['beta'])


def compare_draw_load(dataset: pd.DataFrame,baseline: pd.DataFrame,load: pd.DataFrame,*,complete_counters_only: bool=False) -> tuple[pd.DataFrame,dict[str,Any]]:
    """All three variants use one intersection; labels are not used for selection."""
    if not dataset.historical_reconstruction.all() or dataset.genuine_asof_validation.any():raise ValueError('Retrospective adapter only')
    if not dataset.groupby('comparison_block_id').partition.nunique().eq(1).all():raise ValueError('Competition crosses partitions')
    if not load.match_id.is_unique or set(load.match_id)!=set(dataset.match_id):raise ValueError('Load identities differ')
    frame=attach_baseline(dataset,baseline).merge(load,on='match_id',validate='one_to_one')
    eligible=frame.draw_load_supported & frame.both_have_prior_observed_play & frame.completed_standard & frame.baseline_probability.notna()
    if complete_counters_only:eligible &= frame.observed_counters_complete
    train=frame.loc[eligible & frame.partition.eq('development_2024')].copy()
    test=frame.loc[eligible & frame.partition.eq('exploratory_2025')].copy()
    if test.empty:raise ValueError('No common draw-load evaluation sample')
    if set(train.comparison_block_id)&set(test.comparison_block_id):raise ValueError('Competition overlap')
    artifacts={}
    for name,features in [('coverage',CONTROL_FEATURES),('load',CONTROL_FEATURES+LOAD_FEATURES)]:
        correction=DrawLoadCorrection(features);artifacts[name]=correction.fit(train)
        test[name+'_probability']=correction.predict(test)
    def metrics(rows):return {name:probability_metrics(rows.y.astype(int).tolist(),rows[col].astype(float).tolist()) for name,col in [('base','baseline_probability'),('base_plus_coverage','coverage_probability'),('base_plus_coverage_plus_load','load_probability')]}
    def delta(rows,alternative,reference):
        # Reuse the paired competition bootstrap; field names here are generic
        # aliases only, not a claim that these are spatial variables.
        tmp=rows.copy();tmp['spatial_probability']=tmp[alternative];tmp['baseline_probability']=tmp[reference]
        old=paired_interval(tmp)
        return {('log_loss_difference' if k=='log_loss_spatial_minus_base' else 'brier_difference' if k=='brier_spatial_minus_base' else k):v for k,v in old.items()}
    total=int(frame.partition.eq('exploratory_2025').sum())
    report=dict(schema='tennis-draw-load-comparison-v1',label='2025_exploratory',n_train_common=len(train),n_test_common=len(test),
        n_test_total=total,coverage=len(test)/total,complete_counters_only=complete_counters_only,metrics=metrics(test),
        paired={'load_minus_base':delta(test,'load_probability','baseline_probability'),
                'load_minus_coverage':delta(test,'load_probability','coverage_probability'),
                'coverage_minus_base':delta(test,'coverage_probability','baseline_probability')},
        by_circuit={c:dict(metrics=metrics(g),load_minus_coverage=delta(g,'load_probability','coverage_probability')) for c,g in test.groupby('circuit')},
        artifacts=artifacts,test_used_for_tuning=False,genuine_asof_validation=False,production_approved=False,
        financial_validation=False,windows_3d_7d_available=False,rest_imputed=False,
        interpretation='Cumulative observed prior rounds, not elapsed-day or metabolic fatigue; coverage control is mandatory')
    return test,report
