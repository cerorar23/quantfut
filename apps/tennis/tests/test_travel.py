from dataclasses import replace
import hashlib

import pytest

from tennis_engine.travel import Evidence, TournamentTransition, InterTournamentTravelExtractor, TransportPolicy
from tennis_engine.venues import VenueRegistry


DECISION='2026-10-18T10:00:00Z'


@pytest.fixture
def setup(tmp_path):
    path=tmp_path/'facts.json';path.write_text('reviewed transition facts')
    evidence=Evidence(str(path),hashlib.sha256(path.read_bytes()).hexdigest(),'2026-10-17T08:00:00Z')
    registry=VenueRegistry(tmp_path/'registry.sqlite')
    registry.add_source({'source_id':'s','url':'https://example.org/official','received_at':evidence.received_at,
                         'source_path':str(path),'sha256':evidence.sha256})
    def add(identity,lat,lon,zone,alt=0,recorded='2026-10-17T09:00:00Z'):
        registry.register_venue({'venue_id':identity,'name':identity,'city':'Test','country':'XX','timezone':zone,
            'lat':lat,'lon':lon,'coordinate_scope':'venue_point','coordinate_precision_m':300,
            'altitude_m':alt,'recorded_at':recorded,
            'field_sources':{k:['s'] for k in ('name','city','country','timezone','coordinates','altitude_m')}})
    add('china',31.2,121.5,'Asia/Shanghai',20)
    add('paris',48.85,2.35,'Europe/Paris',40)
    t=TournamentTransition('api_tennis:123','china:2026','paris:2026','china','paris','2026-10-19T12:00:00Z',
        (evidence,),True,True,True,True,'2026-10-16T12:00:00Z','2026-10-16T12:00:00Z','actual')
    yield registry,InterTournamentTravelExtractor(registry),t,add
    registry.db.close()


def test_china_to_paris_reports_exposure_without_claiming_itinerary_or_rest(setup):
    _,extractor,t,_=setup
    result=extractor.extract(t,DECISION)
    assert 9000<result['distance_km']<10000
    assert result['timezone_clock_delta_hours']==-6
    assert result['geographic_direction']=='west'
    assert result['transport_candidate']=='air_candidate'
    assert result['altitude_change_m']==20
    assert result['exit_to_scheduled_debut_days_lower']==3
    assert result['exit_to_scheduled_debut_days_upper']==3
    assert result['rest_days'] is None and not result['arrival_time_known']
    assert result['jet_lag_score'] is None and not result['probabilities_modified']


def test_different_court_in_same_edition_is_not_a_trip(setup):
    _,extractor,t,_=setup
    result=extractor.extract(replace(t,target_edition_id=t.previous_edition_id),DECISION)
    assert result['status']=='same_tournament_no_new_transition'
    assert result['distance_km'] is None and result['timezone_clock_delta_hours'] is None


@pytest.mark.parametrize('flag',['consecutive_verified','target_is_debut_verified','participation_closed','all_disciplines_checked'])
def test_incomplete_history_or_doubles_participation_blocks_inference(setup,flag):
    _,extractor,t,_=setup
    result=extractor.extract(replace(t,**{flag:False}),DECISION)
    assert result['status']=='insufficient_transition_evidence' and result['review_flags']
    assert result['distance_km'] is None


def test_missing_exit_times_do_not_become_zero_rest(setup):
    _,extractor,t,_=setup
    result=extractor.extract(replace(t,exit_time_kind='unknown',exit_earliest_at=None,exit_latest_at=None),DECISION)
    assert result['distance_km'] is not None
    assert result['exit_to_scheduled_debut_days_lower'] is None
    assert 'exit_to_scheduled_debut' in result['missing_features']


def test_verified_end_interval_is_preserved_instead_of_imputing_midnight(setup):
    _,extractor,t,_=setup
    result=extractor.extract(replace(t,exit_earliest_at='2026-10-16T00:00:00Z',
        exit_latest_at='2026-10-17T00:00:00Z',exit_time_kind='verified_interval'),DECISION)
    assert result['exit_to_scheduled_debut_days_lower']==2.5
    assert result['exit_to_scheduled_debut_days_upper']==3.5


@pytest.mark.parametrize('end',['2026-10-18T10:00:00Z','2026-10-18T11:00:00Z'])
def test_exit_at_or_after_decision_is_rejected(setup,end):
    _,extractor,t,_=setup
    with pytest.raises(ValueError,match='strictly before'):
        extractor.extract(replace(t,exit_earliest_at=end,exit_latest_at=end),DECISION)


def test_future_evidence_and_tampering_are_rejected(setup):
    _,extractor,t,_=setup
    with pytest.raises(ValueError,match='precede'):
        extractor.extract(replace(t,evidence=(replace(t.evidence[0],received_at=DECISION),)),DECISION)
    from pathlib import Path
    Path(t.evidence[0].source_path).write_text('tampered')
    with pytest.raises(ValueError,match='changed'):extractor.extract(t,DECISION)


def test_future_venue_revision_is_not_backfilled(setup):
    _,extractor,t,add=setup
    add('future',0,0,'UTC',recorded=DECISION)
    result=extractor.extract(replace(t,target_venue_id='future'),DECISION)
    assert result['status']=='venue_unavailable_at_decision'


def test_both_offsets_share_reference_instant_and_respect_dst(setup):
    _,extractor,t,_=setup
    # Paris changes to UTC+1 on Oct25; China stays UTC+8.
    result=extractor.extract(replace(t,scheduled_debut_at='2026-10-26T12:00:00Z'),DECISION)
    assert result['timezone_clock_delta_hours']==-7


def test_date_line_clock_difference_is_not_jet_lag_magnitude(setup):
    _,extractor,t,add=setup
    add('east',-13.8,-171.75,'Pacific/Apia')
    add('west',-14.3,-170.7,'Pacific/Pago_Pago')
    result=extractor.extract(replace(t,previous_venue_id='east',target_venue_id='west'),DECISION)
    assert result['timezone_clock_delta_hours']==-24
    assert result['date_line_crossing_candidate']
    assert result['jet_lag_score'] is None


def test_short_water_crossing_is_not_automatically_a_car_journey(setup):
    _,extractor,t,add=setup
    add('bol',43.26,16.64,'Europe/Zagreb')
    add('split',43.5,16.44,'Europe/Zagreb')
    result=extractor.extract(replace(t,previous_venue_id='bol',target_venue_id='split'),DECISION)
    assert result['distance_km']<200 and result['transport_candidate']=='unknown'
    result=extractor.extract(replace(t,previous_venue_id='bol',target_venue_id='split',road_connection_confirmed=True),DECISION)
    assert result['transport_candidate']=='road_candidate'


def test_same_site_in_different_weekly_editions_has_no_air_or_road_trip(setup):
    _,extractor,t,_=setup
    result=extractor.extract(replace(t,target_venue_id='china'),DECISION)
    assert result['same_physical_site'] and result['distance_km']==0
    assert result['transport_candidate']=='unknown'


def test_policy_rejects_invalid_thresholds():
    with pytest.raises(ValueError):TransportPolicy(2000,1000)
