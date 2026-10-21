"""Original implementation of the published WElo equations, not copied R code.

Angelini, Candila & De Angelis (2022), doi:10.1016/j.ejor.2021.04.011.
The score factor is games won by the MATCH WINNER / all games, even when
the winner has fewer total games. Both players share that factor. K depends
on each player's own number of prior matches (explicit pre-update convention).

Single-event blocks implement the recursion. Multi-match source-period blocks
are a declared adaptation: all updates use pre-block ratings/counts, because
weekly tournament dates cannot justify any invented within-week sequence.
"""
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Sequence

import numpy as np
import pandas as pd
from scipy.special import expit

from .benchmark import probability_metrics
from .model import training_rows
from .normalize import standard_score
from .research import pooled


@dataclass(frozen=True)
class EloResult:
    event_id: str
    winner_id: str
    loser_id: str
    score: str  # winner-first conventional set scores
    best_of: int


def winner_games_share(score: str, best_of: int) -> float:
    if best_of not in (3,5) or not standard_score(score,best_of):
        raise ValueError('Completed conventional winner-first score required')
    pairs=[tuple(map(int,re.match(r'(\d+)-(\d+)',s).groups())) for s in score.split()]
    won=sum(a for a,b in pairs);total=sum(a+b for a,b in pairs)
    return won/total


class WeightedEloModel:
    def __init__(self, weighted: bool=True):
        self.weighted=weighted
        self.ratings: dict[str,float]={}
        self.counts: Counter[str]=Counter()
        self.seen: set[str]=set()
        self.last_block: str | None=None
        self.frozen=False

    @classmethod
    def load_frozen(cls, path: Path, expected_sha256: str) -> 'WeightedEloModel':
        """Load a hash-pinned inference artifact; never resume partial history."""
        raw=Path(path).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=expected_sha256:raise ValueError('WElo artifact hash mismatch')
        value=json.loads(raw)
        if value.get('schema')!='tennis-welo-period-v1' or type(value.get('weighted')) is not bool:
            raise ValueError('Unsupported WElo artifact')
        model=cls(value['weighted']);model.frozen=True
        if not all(isinstance(k,str) and isinstance(v,(int,float)) and not isinstance(v,bool) and np.isfinite(v)
                   for k,v in value['ratings'].items()):raise ValueError('Invalid frozen ratings')
        model.ratings=dict(value['ratings']);model.last_block=value['last_block']
        return model

    def predict(self, a: str, b: str) -> float:
        if not a or not b or a==b:raise ValueError('Distinct players required')
        return float(expit(np.log(10)*(self.ratings.get(a,1500.)-self.ratings.get(b,1500.))/400))

    def update_block(self, rows: Sequence[EloResult], block: str) -> None:
        # ISO date/period strings must increase. A block is committed atomically.
        if self.frozen:raise ValueError('Frozen inference artifact cannot be updated')
        pd.Timestamp(block)
        if self.last_block is not None and pd.Timestamp(block)<=pd.Timestamp(self.last_block):
            raise ValueError('Blocks must advance strictly in time')
        if not rows:raise ValueError('Empty block')
        if len({r.event_id for r in rows})!=len(rows) or any(r.event_id in self.seen for r in rows):
            raise ValueError('Duplicate/reused event')
        delta=defaultdict(list);counts=Counter()
        for row in rows:
            if not row.event_id:raise ValueError('Event identity required')
            factor=winner_games_share(row.score,row.best_of) if self.weighted else 1.
            if not self.weighted:winner_games_share(row.score,row.best_of)
            p=self.predict(row.winner_id,row.loser_id)
            for pid,residual in [(row.winner_id,1-p),(row.loser_id,-(1-p))]:
                k=250/(self.counts[pid]+5)**.4
                delta[pid].append(k*residual*factor);counts[pid]+=1
        import math
        for pid,changes in delta.items():
            self.ratings[pid]=self.ratings.get(pid,1500.)+math.fsum(sorted(changes))
        self.counts.update(counts);self.seen.update(r.event_id for r in rows);self.last_block=block

    def artifact(self) -> dict[str,Any]:
        return {'schema':'tennis-welo-period-v1','initial_rating':1500.,'weighted':self.weighted,
                'k':'250 / (prior_completed_matches + 5)^0.4',
                'score_weight':'match winner games / total games' if self.weighted else '1',
                'last_block':self.last_block,'ratings':self.ratings,'counts':dict(self.counts),
                'n_events':len(self.seen),'ordering':'simultaneous source-period blocks',
                'reproduction_scope':'published equations; prior-count convention; period-block adaptation',
                'production_approved':False}


def compare_weighted_elo(root: Path, improvements_root: Path, output: Path, circuit: str) -> dict[str,Any]:
    """Fair frozen-origin 2026 development comparison, no fabricated timestamps.

    Uses the SAME eligible training rows/35-day embargo as the archived model,
    and exact archived A/B orientations. Reports against raw/calibrated surface
    Elo and the existing hybrid. It does not call this an actual-time benchmark,
    nor reproduce the paper's original data, daily sequence or financial study.
    """
    root=Path(root);output=Path(output)
    if circuit not in ('ATP','WTA') or output.exists():raise ValueError('Supported circuit and new output required')
    folder=root/f'experiments/{circuit}_2026'
    model=json.loads((folder/'model/model.json').read_text())
    cutoff=model['summary']['cutoff']
    training_receipt=json.loads((folder/'model/training_receipt.json').read_text())
    if hashlib.sha256((root/'canonical/matches.parquet').read_bytes()).hexdigest()!=training_receipt['canonical_sha256']:
        raise ValueError('Canonical data differs from archived baseline training receipt')
    history=training_rows(root,circuit,cutoff)
    models={'weighted_elo':WeightedEloModel(),'adaptive_elo':WeightedEloModel(False)}
    for period,block in history.groupby('period',sort=True):
        rows=[EloResult(r.match_id,r.winner_id,r.loser_id,r.score,int(r.best_of)) for r in block.itertuples()]
        for m in models.values():m.update_block(rows,str(period))
    frame=pd.read_parquet(folder/'heldout_predictions.parquet')
    if frame.match_id.duplicated().any() or frame.period.lt(cutoff).any():raise ValueError('Invalid archived test cohort')
    pool_path=Path(improvements_root)/f'{circuit}_pool/pool.json'
    controls_path=Path(improvements_root)/f'{circuit}_controls.json'
    pool=json.loads(pool_path.read_text())
    control=json.loads(controls_path.read_text())['parameters']['calibrated_elo']
    for parameters in (pool,control):
        if pd.Timestamp(parameters['last_period'])>=pd.Timestamp(cutoff)-pd.Timedelta(days=35):
            raise ValueError('Calibration overlaps frozen forecast origin')
    frame['current_hybrid']=pooled(frame,pool)
    frame['calibrated_surface_elo']=pooled(frame,control)
    for name,m in models.items():
        frame[name]=[m.predict(a,b) for a,b in zip(frame.a,frame.b)]
    columns=['current_hybrid','model_probability','surface_elo_probability','calibrated_surface_elo','adaptive_elo','weighted_elo']
    common=frame.loc[np.isfinite(frame[columns]).all(axis=1)].copy()
    metrics={name:probability_metrics([int(x) for x in common.y],common[name].tolist()) for name in columns}
    # Paired resampling by source period; exploratory dependence limitation.
    y=common.y.to_numpy();rng=np.random.default_rng(20261017)
    losses={name:-(y*np.log(np.clip(common[name].to_numpy(),1e-12,1-1e-12))+
                  (1-y)*np.log1p(-np.clip(common[name].to_numpy(),1e-12,1-1e-12))) for name in columns}
    paired={}
    for reference in ('current_hybrid','adaptive_elo','calibrated_surface_elo'):
        delta=losses['weighted_elo']-losses[reference]
        groups=pd.DataFrame({'period':common.period,'delta':delta}).groupby('period').delta.agg(['sum','count'])
        draws=[]
        for _ in range(1000):
            sampled=groups.iloc[rng.integers(len(groups),size=len(groups))]
            draws.append(float(sampled['sum'].sum()/sampled['count'].sum()))
        paired[reference]={'weighted_minus_reference_log_loss':float(delta.mean()),
                           'source_period_block_ci95':np.quantile(draws,[.025,.975]).tolist()}
    files=[root/'canonical/matches.parquet',folder/'heldout_predictions.parquet',folder/'model/training_receipt.json',pool_path,controls_path]
    report={'schema':'tennis-welo-comparison-v1','label':'experimental_retrospective_2026',
            'circuit':circuit,'cutoff':cutoff,'embargo_days':35,'training_matches':len(history),
            'first_period':str(history.period.min()),'last_period':str(history.period.max()),
            'n_total':len(frame),'n_common':len(common),'coverage':len(common)/len(frame),
            'metrics':metrics,'paired_comparisons':paired,
            'cold_start_cases':sum(a not in models['weighted_elo'].ratings or b not in models['weighted_elo'].ratings for a,b in zip(common.a,common.b)),
            'sources':{str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
            'implementation_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'historical_availability_verified':False,'actual_time_benchmark':False,
            'paper_data_reproduction':False,'automatic_promotion':False,'financial_validation':False,
            'limitations':['Source-period simultaneous adaptation, not daily sequential replication.',
                          'Year 2026 already inspected during development.',
                          'Static within-year forecasts match the frozen baseline protocol.',
                          'Period bootstrap does not capture all player dependence/multiple comparisons.']}
    output.mkdir(parents=True,exist_ok=False)
    common.to_parquet(output/'predictions.parquet',index=False)
    for name,m in models.items():(output/(name+'.json')).write_text(json.dumps(m.artifact(),indent=2),encoding='utf-8')
    (output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report
