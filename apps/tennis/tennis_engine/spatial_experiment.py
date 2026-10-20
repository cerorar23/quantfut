"""Three-model common-cohort experiment with train-only transformations.

Spatial covariates come from the evidence-gated tournament extractor. Fixed
clock hours exist only in named sensitivity scenarios, never in the spatial
branch or original data. Scenario variation is not a confidence interval.
"""
from collections import Counter
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timezone
from itertools import product
import math
import hashlib
from typing import Any, Sequence
from zoneinfo import ZoneInfo

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logit

from .benchmark import BenchmarkCase, BenchmarkPrediction, BenchmarkResult, BenchmarkEvaluator
from .operations import utc
from .travel import Evidence, InterTournamentTravelExtractor, TournamentTransition
from .venues import canonical


class UnavailableFeatures(ValueError):
    """A valid but incomplete observation; not permission to fabricate a value."""


@dataclass(frozen=True)
class DayPair:
    previous_exit_day: str
    target_debut_day: str
    previous_timezone: str
    target_timezone: str
    exit_precision: str
    debut_precision: str
    evidence: tuple[Evidence, ...]
    actual_exit_at: str | None = None
    known_debut_at: str | None = None


@dataclass(frozen=True)
class ClockScenario:
    exit_hour: int
    debut_hour: int
    other_exit_hour: int | None = None

    def __post_init__(self) -> None:
        hours=(self.exit_hour,self.debut_hour)+(() if self.other_exit_hour is None else (self.other_exit_hour,))
        if any(type(h) is not int or not 0<=h<=23 for h in hours):
            raise ValueError('Scenario hours must be integers in 0..23')

    @property
    def name(self) -> str:
        other=self.exit_hour if self.other_exit_hour is None else self.other_exit_hour
        return f'experimental_exitlo{self.exit_hour:02d}_exithi{other:02d}_debut{self.debut_hour:02d}'


def sensitivity_grid() -> tuple[ClockScenario, ...]:
    """Predeclared stress scenarios, not empirically established travel times."""
    # Applying the same clock shift to both players cancels in a difference.
    # Perturb exit clocks independently, assigned by canonical player-ID order
    # rather than A/B orientation. Debut belongs to the same match for both.
    return tuple(ClockScenario(a,14,b) for a,b in product((12,18,23),repeat=2))


def local_scenario_time(day: str, hour: int, zone: str) -> datetime:
    """Reject ambiguous/nonexistent wall times rather than silently choosing DST."""
    naive=datetime.combine(date.fromisoformat(day),time(hour))
    tz=ZoneInfo(zone)
    candidates=set()
    for fold in (0,1):
        candidate=naive.replace(tzinfo=tz,fold=fold).astimezone(timezone.utc)
        if candidate.astimezone(tz).replace(tzinfo=None)==naive:candidates.add(candidate)
    if len(candidates)!=1:raise UnavailableFeatures('ambiguous_or_nonexistent_scenario_local_time')
    return next(iter(candidates))


def estimated_gap(pair: DayPair | None, scenario: ClockScenario, decision_at: str) -> float:
    if pair is None:raise UnavailableFeatures('verified_local_days_missing')
    if pair.exit_precision!='verified_actual_day' or pair.debut_precision not in ('verified_actual_day','verified_scheduled_day'):
        raise UnavailableFeatures('tournament_week_or_unknown_is_not_a_match_day')
    if not pair.evidence:raise ValueError('Date evidence required')
    for evidence in pair.evidence:evidence.verify(decision_at)
    # A day can only be called a completed prior day when its entire verified
    # interval has elapsed before decision, not merely the imputed hour.
    if pair.actual_exit_at is None:
        end_day=date.fromisoformat(pair.previous_exit_day).toordinal()+1
        end_bound=local_scenario_time(date.fromordinal(end_day).isoformat(),0,pair.previous_timezone)
        if end_bound>=utc(decision_at):raise UnavailableFeatures('exit_day_not_fully_before_decision')
    end=utc(pair.actual_exit_at) if pair.actual_exit_at is not None else local_scenario_time(pair.previous_exit_day,scenario.exit_hour,pair.previous_timezone)
    start=utc(pair.known_debut_at) if pair.known_debut_at is not None else local_scenario_time(pair.target_debut_day,scenario.debut_hour,pair.target_timezone)
    if pair.actual_exit_at is not None and end>=utc(decision_at):raise ValueError('Known exit must precede decision')
    if end.astimezone(ZoneInfo(pair.previous_timezone)).date()!=date.fromisoformat(pair.previous_exit_day):
        raise ValueError('Known exit timestamp differs from verified local day')
    if start.astimezone(ZoneInfo(pair.target_timezone)).date()!=date.fromisoformat(pair.target_debut_day):
        raise ValueError('Known debut timestamp differs from verified local day')
    if end>=start:raise UnavailableFeatures('scenario_exit_not_before_debut')
    return (start-end).total_seconds()/86400


@dataclass(frozen=True)
class SpatialTrialRow:
    case: BenchmarkCase
    result: BenchmarkResult
    baseline: BenchmarkPrediction
    transition_a: TournamentTransition | None
    transition_b: TournamentTransition | None
    days_a: DayPair | None = None
    days_b: DayPair | None = None


class SpatialExperiment:
    """Ridge logistic residual around a supplied valid pre-match baseline.

    Spatial features are A-minus-B differences of distance, altitude change and
    signed clock difference. Experimental variants add only the difference of
    scenario-derived exit-to-debut intervals. No intercept/centering preserves
    player-swap symmetry. RMS scaling and coefficients use training rows only.
    The runner reports every scenario, never selects a winner on test labels.
    """
    def __init__(self, extractor: InterTournamentTravelExtractor, *, ridge: float=1.,
                 min_training_rows: int=20, scenarios: Sequence[ClockScenario] | None=None):
        if isinstance(ridge,bool) or not math.isfinite(ridge) or ridge<=0 or type(min_training_rows) is not int or min_training_rows<2:
            raise ValueError('Positive ridge and at least two training cases required')
        self.extractor=extractor;self.ridge=ridge;self.minimum=min_training_rows
        self.scenarios=tuple(sensitivity_grid() if scenarios is None else scenarios)
        if not self.scenarios or len({s.name for s in self.scenarios})!=len(self.scenarios):
            raise ValueError('Unique, nonempty sensitivity scenarios required')

    def _features(self, row: SpatialTrialRow) -> dict[str,np.ndarray]:
        case=row.case
        if row.transition_a is None or row.transition_b is None:raise UnavailableFeatures('reviewed_transition_missing')
        reports=[]
        for player,transition in zip((case.player_a,case.player_b),(row.transition_a,row.transition_b)):
            if transition.player_id!=player or utc(transition.scheduled_debut_at)!=utc(case.scheduled_start):
                raise ValueError('Transition player or scheduled decision target differs')
            reports.append(self.extractor.extract(transition,case.decision_at))
        if row.transition_a.target_edition_id!=row.transition_b.target_edition_id or row.transition_a.target_venue_id!=row.transition_b.target_venue_id:
            raise ValueError('Players must share target edition and site')
        if any(r['status']!='reviewed_tournament_transition' for r in reports):
            raise UnavailableFeatures('transition_not_verified')
        keys=('distance_km','altitude_change_m','timezone_clock_delta_hours')
        if any(r[k] is None for r in reports for k in keys):raise UnavailableFeatures('spatial_components_missing')
        spatial=np.array([reports[0][k]-reports[1][k] for k in keys],dtype=float)
        features={'spatial':spatial}
        zones=[(self.extractor.registry.venue(t.previous_venue_id,case.decision_at)['timezone'],
                self.extractor.registry.venue(t.target_venue_id,case.decision_at)['timezone'])
               for t in (row.transition_a,row.transition_b)]
        for scenario in self.scenarios:
            gaps=[]
            for player,pair,t,expected_zones in zip((case.player_a,case.player_b),(row.days_a,row.days_b),(row.transition_a,row.transition_b),zones):
                if pair is not None:
                    if (pair.previous_timezone,pair.target_timezone)!=expected_zones:
                        raise ValueError('Date zones differ from reviewed venues')
                    if date.fromisoformat(pair.target_debut_day)!=utc(case.scheduled_start).astimezone(ZoneInfo(pair.target_timezone)).date():
                        raise ValueError('Scenario debut day differs from scheduled target day')
                    if pair.known_debut_at is not None and utc(pair.known_debut_at)!=utc(case.scheduled_start):
                        raise ValueError('Known debut differs from case schedule')
                    if t.exit_time_kind=='actual':
                        if pair.actual_exit_at is not None and utc(pair.actual_exit_at)!=utc(t.exit_earliest_at):
                            raise ValueError('Known exit differs from reviewed transition')
                        pair=replace(pair,actual_exit_at=t.exit_earliest_at)
                exit_hour=scenario.exit_hour if player==min(case.player_a,case.player_b) or scenario.other_exit_hour is None else scenario.other_exit_hour
                gaps.append(estimated_gap(pair,ClockScenario(exit_hour,scenario.debut_hour),case.decision_at))
            features[scenario.name]=np.append(spatial,gaps[0]-gaps[1])
        return features

    def _fit(self, matrix: np.ndarray, offset: np.ndarray, y: np.ndarray) -> dict[str,Any]:
        scale=np.sqrt(np.mean(matrix**2,axis=0));scale[scale==0]=1
        x=matrix/scale
        def objective(beta):
            z=offset+x@beta
            return (float(np.mean(np.logaddexp(0,z)-y*z)+self.ridge*np.dot(beta,beta)/2),
                    x.T@(expit(z)-y)/len(y)+self.ridge*beta)
        fitted=minimize(objective,np.zeros(x.shape[1]),jac=True,method='L-BFGS-B')
        if not fitted.success:raise RuntimeError('Spatial correction did not converge')
        return {'beta':fitted.x.tolist(),'rms_train':scale.tolist(),'ridge':self.ridge}

    def run(self, training: Sequence[SpatialTrialRow], testing: Sequence[SpatialTrialRow],
            *, fitted_at: str, evaluated_at: str) -> dict[str,Any]:
        if utc(fitted_at)>=utc(evaluated_at):raise ValueError('Fit must precede evaluation')
        for rows in (training,testing):
            if len({r.case.event_id for r in rows})!=len(rows):raise ValueError('One decision per unique event required')
        if {r.case.event_id for r in training}&{r.case.event_id for r in testing}:raise ValueError('Training/test event overlap')
        for row in training:
            if utc(row.result.available_at)>=utc(fitted_at) or utc(row.case.decision_at)>=utc(fitted_at):
                raise ValueError('Training labels and decisions must precede fit')
        for row in testing:
            if utc(row.case.decision_at)<=utc(fitted_at):raise ValueError('Test decision must follow fit')
        train_features={};test_features={};exclusions={'train':Counter(),'test':Counter()}
        valid_train=[]
        for phase,rows,destination in [('train',training,train_features),('test',testing,test_features)]:
            for row in rows:
                try:destination[row.case.case_id]=self._features(row)
                except UnavailableFeatures as exc:exclusions[phase][str(exc)]+=1;continue
                assessment=BenchmarkEvaluator().evaluate([row.case],[row.result],{'base':[row.baseline]},
                                                         fitted_at if phase=='train' else evaluated_at)
                if assessment['n_common']!=1:
                    destination.pop(row.case.case_id)
                    exclusions[phase]['outside_completed_pre_match_contract']+=1
                elif phase=='train':valid_train.append(row)
        report={'schema':'tennis-spatial-three-model-v1','label':'experimental','fitted_at':fitted_at,
                'evaluated_at':evaluated_at,'n_train_total':len(training),'n_train_common':len(valid_train),
                'n_test_total':len(testing),'n_test_common':len(test_features),
                'coverage':len(test_features)/len(testing) if testing else None,
                'exclusions':{k:dict(v) for k,v in exclusions.items()},'production_approved':False,
                'hours_imputed_in_spatial_branch':False,'scenario_is_actual_rest':False,
                'scenario_names':[s.name for s in self.scenarios],'test_used_for_selection':False,
                'artifacts':{},'comparison':None,'sensitivity':None}
        if len(valid_train)<self.minimum or len(test_features)==0:
            return {**report,'status':'insufficient_common_training_or_test_sample'}
        labels=np.array([r.result.y for r in valid_train])
        if len(set(labels))<2:return {**report,'status':'insufficient_outcome_variation'}
        offset=logit(np.clip([r.baseline.probability for r in valid_train],1e-12,1-1e-12))
        names=['spatial']+[s.name for s in self.scenarios]
        artifacts={}
        for name in names:
            matrix=np.stack([train_features[r.case.case_id][name] for r in valid_train])
            artifacts[name]=self._fit(matrix,offset,labels)
            artifacts[name].update(training_event_ids=[r.case.event_id for r in valid_train],
                fitted_at=fitted_at,n=len(valid_train),
                training_matrix_sha256=hashlib.sha256(canonical({'x':matrix.tolist(),
                    'y':labels.tolist(),'baseline_log_odds':offset.tolist(),
                    'event_ids':[r.case.event_id for r in valid_train]}).encode()).hexdigest(),
                training_source_sha256s=sorted({e.sha256 for r in valid_train
                    for entry in (r.transition_a,r.transition_b,r.days_a,r.days_b) if entry is not None
                    for e in entry.evidence}))
        predictions={'base':[r.baseline for r in testing],**{name:[] for name in names}}
        for row in testing:
            for name in names:
                if row.case.case_id not in test_features:
                    p=None;reason='outside_common_feature_cohort'
                else:
                    artifact=artifacts[name]
                    x=test_features[row.case.case_id][name]/artifact['rms_train']
                    p=float(expit(logit(np.clip(row.baseline.probability,1e-12,1-1e-12))+x@artifact['beta']))
                    reason=None
                c=row.case
                predictions[name].append(BenchmarkPrediction(c.case_id,c.player_a,c.player_b,c.decision_at,p,reason))
        comparison=BenchmarkEvaluator().evaluate([r.case for r in testing],[r.result for r in testing],predictions,evaluated_at)
        if comparison['n_common']!=len(test_features):raise RuntimeError('Common sample changed during evaluation')
        scenario_losses=[comparison['metrics'][s.name]['log_loss'] for s in self.scenarios]
        return {**report,'status':'evaluated','artifacts':artifacts,'comparison':comparison,
                'sensitivity':{'log_loss_min':min(scenario_losses),'log_loss_max':max(scenario_losses),
                               'interpretation':'scenario range, not statistical confidence or selection'}}
