"""Evidence-gated exposures between tournament editions, not individual matches.

Distances describe venue separation, never a personal itinerary. Scheduled
debut minus verified prior exit is an available interval, not rest or time
spent adapting at the destination. No physiological fatigue score is imposed.
"""
from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo

from .context import haversine_km
from .operations import utc
from .venues import VenueRegistry


@dataclass(frozen=True)
class Evidence:
    source_path: str
    sha256: str
    received_at: str

    def verify(self, decision_at: str) -> None:
        if utc(self.received_at) >= utc(decision_at):
            raise ValueError('Transition evidence must precede decision')
        if hashlib.sha256(Path(self.source_path).read_bytes()).hexdigest() != self.sha256:
            raise ValueError('Transition evidence changed')


@dataclass(frozen=True)
class TournamentTransition:
    """Reviewed input contract; flags must be established by the data adapter.

    ``consecutive_verified`` requires adequate coverage of intervening events;
    ``participation_closed`` includes doubles/qualifying when applicable. A
    missing match in a feed is not evidence of either fact. Exit bounds are
    accepted only for an actual timestamp or an independently verified interval,
    never from adding duration to scheduled start or from live polling brackets.
    """
    player_id: str
    previous_edition_id: str
    target_edition_id: str
    previous_venue_id: str
    target_venue_id: str
    scheduled_debut_at: str
    evidence: tuple[Evidence, ...]
    consecutive_verified: bool = False
    target_is_debut_verified: bool = False
    participation_closed: bool = False
    all_disciplines_checked: bool = False
    exit_earliest_at: str | None = None
    exit_latest_at: str | None = None
    exit_time_kind: Literal['unknown', 'actual', 'verified_interval'] = 'unknown'
    road_connection_confirmed: bool = False


@dataclass(frozen=True)
class TransportPolicy:
    road_candidate_max_km: float = 200.
    air_candidate_min_km: float = 1000.

    def __post_init__(self) -> None:
        values=(self.road_candidate_max_km,self.air_candidate_min_km)
        if any(isinstance(x,bool) or not math.isfinite(x) for x in values) or not 0 < values[0] < values[1]:
            raise ValueError('Explicit ordered positive transport thresholds required')


class InterTournamentTravelExtractor:
    def __init__(self, registry: VenueRegistry, policy: TransportPolicy | None = None):
        self.registry=registry
        self.policy=policy or TransportPolicy()

    def extract(self, transition: TournamentTransition, decision_at: str) -> dict[str, Any]:
        """Return reviewable exposure and missingness, never adjust probabilities.

        Both IANA offsets are evaluated at the same scheduled debut instant,
        including DST. Their signed clock difference is not the number of
        physiological hours shifted across the date line. Geographic direction
        uses the shorter signed longitude difference; neither identifies a route.
        """
        t=transition
        decision=utc(decision_at)
        debut=utc(t.scheduled_debut_at)
        if decision>=debut:raise ValueError('Pre-match decision must precede scheduled debut')
        if not all(isinstance(x,str) and x.strip() for x in
                   (t.player_id,t.previous_edition_id,t.target_edition_id,t.previous_venue_id,t.target_venue_id)):
            raise ValueError('Canonical player, edition and venue IDs required')
        if not t.evidence:raise ValueError('Transition provenance required')
        for e in t.evidence:e.verify(decision_at)
        result: dict[str,Any]={
            'schema':'tennis-intertournament-travel-v1','player_id':t.player_id,
            'previous_edition_id':t.previous_edition_id,'target_edition_id':t.target_edition_id,
            'decision_at':decision_at,'scheduled_debut_at':t.scheduled_debut_at,
            'status':'insufficient_transition_evidence','distance_km':None,
            'distance_spatial_allowance_km':None,'timezone_clock_delta_hours':None,
            'timezone_reference_at':t.scheduled_debut_at,'geographic_direction':None,
            'date_line_crossing_candidate':None,'transport_candidate':'unknown',
            'exit_to_scheduled_debut_days_lower':None,'exit_to_scheduled_debut_days_upper':None,
            'destination_altitude_m':None,'altitude_change_m':None,
            'missing_features':[],'review_flags':[], 'personal_itinerary_known':False,
            'arrival_time_known':False,'rest_days':None,'jet_lag_score':None,
            'probabilities_modified':False,
            'transport_thresholds_km':{'road_max':self.policy.road_candidate_max_km,
                                       'air_min':self.policy.air_candidate_min_km}}
        # A change of court or venue inside one edition is not a new tournament trip.
        if t.previous_edition_id==t.target_edition_id:
            result['status']='same_tournament_no_new_transition'
            return result
        required={'consecutive_tournaments_unverified':t.consecutive_verified,
                  'target_debut_unverified':t.target_is_debut_verified,
                  'previous_participation_not_closed':t.participation_closed,
                  'other_disciplines_not_checked':t.all_disciplines_checked}
        result['review_flags']=[reason for reason,ok in required.items() if ok is not True]
        if result['review_flags']:return result

        prior=self.registry.venue(t.previous_venue_id,decision_at)
        target=self.registry.venue(t.target_venue_id,decision_at)
        if prior is None or target is None:
            result['status']='venue_unavailable_at_decision'
            return result
        result['venue_revision_ids']=[prior['revision_id'],target['revision_id']]
        result['status']='reviewed_tournament_transition'
        if all(v.get('lat') is not None and v.get('lon') is not None for v in (prior,target)):
            distance=haversine_km((prior['lat'],prior['lon']),(target['lat'],target['lon']))
            result['distance_km']=distance
            result['distance_spatial_allowance_km']=(prior['coordinate_precision_m']+target['coordinate_precision_m'])/1000
            longitude_delta=(target['lon']-prior['lon']+180)%360-180
            result['geographic_direction']='east' if longitude_delta>0 else 'west' if longitude_delta<0 else 'same_longitude'
            result['date_line_crossing_candidate']=abs(target['lon']-prior['lon'])>180
            if distance>=self.policy.air_candidate_min_km:result['transport_candidate']='air_candidate'
            elif 0<distance<=self.policy.road_candidate_max_km and t.road_connection_confirmed is True:
                result['transport_candidate']='road_candidate'
            result['same_physical_site']=t.previous_venue_id==t.target_venue_id
        else:result['missing_features'].append('distance')
        a=debut.astimezone(ZoneInfo(prior['timezone'])).utcoffset()
        b=debut.astimezone(ZoneInfo(target['timezone'])).utcoffset()
        result['timezone_clock_delta_hours']=(b-a).total_seconds()/3600
        if abs(result['timezone_clock_delta_hours'])>12:
            # Political date-line deviations need not cross +/-180 longitude.
            result['date_line_crossing_candidate']=True
        if result['date_line_crossing_candidate']:
            result['review_flags'].append('clock_delta_is_not_circadian_phase_shift')
        if target.get('altitude_m') is not None:result['destination_altitude_m']=target['altitude_m']
        else:result['missing_features'].append('destination_altitude')
        if all(v.get('altitude_m') is not None for v in (prior,target)):
            result['altitude_change_m']=target['altitude_m']-prior['altitude_m']
        else:result['missing_features'].append('altitude_change')
        if t.exit_time_kind not in ('unknown','actual','verified_interval'):
            raise ValueError('Exit timing provenance unsupported')
        if t.exit_time_kind=='unknown':
            if t.exit_earliest_at is not None or t.exit_latest_at is not None:
                raise ValueError('Unknown exit timing cannot carry asserted bounds')
            result['missing_features'].append('exit_to_scheduled_debut')
        elif t.exit_earliest_at is None or t.exit_latest_at is None:
            raise ValueError('Both independently verified exit bounds required')
        else:
            low,high=utc(t.exit_earliest_at),utc(t.exit_latest_at)
            if not low<=high<decision:raise ValueError('Exit interval must be ordered and strictly before decision')
            if t.exit_time_kind=='actual' and low!=high:raise ValueError('Actual exit timestamp must be a point')
            result['exit_to_scheduled_debut_days_lower']=(debut-high).total_seconds()/86400
            result['exit_to_scheduled_debut_days_upper']=(debut-low).total_seconds()/86400
        return result
