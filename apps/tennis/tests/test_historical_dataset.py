import hashlib,json
from copy import deepcopy

import pandas as pd
import pytest

from tennis_engine.historical_dataset import prepare_historical_dataset,clock_range,partition,load_historical_registry


def registry():
    sites=[dict(venue_id=k,lat=lat,lon=lon,altitude_m=h,timezone=z,coordinate_precision_m=500)
           for k,lat,lon,h,z in [('china',31.,121.,10.,'Asia/Shanghai'),('paris',48.,2.,100.,'Europe/Paris')]]
    links=[dict(circuit='ATP',phase='tour',tourney_id=tid,venue_id=v,evidence_season=int(tid[:4]))
           for tid,v in [('2024-1','china'),('2024-2','paris'),('2025-2','paris')]]
    return dict(historical_reconstruction=True,created_at='2026-10-18T12:00:00Z',venues=sites,links=links)


def match(mid,tid,day,w='a',l='b',phase='tour'):
    return dict(match_id=mid,tourney_id=tid,period=day,winner_id=w,loser_id=l,
                score='6-4 6-4',completed_standard=True,circuit='ATP',source_group=phase)


def test_whole_edition_preserves_identical_exposure_and_no_rest():
    frame=pd.DataFrame([match('1','2024-1','2024-05-06'),match('2','2024-2','2024-05-20'),
                        match('3','2024-2','2024-05-27','b','a')])
    data,report=prepare_historical_dataset(frame,registry())
    target=data[data.edition_id.eq('2024-2')]
    assert target.a_distance_km.nunique()==1
    assert target.a_distance_km.iloc[0]>8000
    assert list(target.y)==[1,0]
    assert target.a_delta_altitude_m.eq(90).all()
    assert target.a_delta_timezone_hours.eq(-6).all()
    assert target.rest_hours.isna().all()
    assert not target.genuine_asof_validation.any()
    assert report['metrics_computed'] is False


def test_unknown_immediate_previous_edition_cannot_be_skipped():
    frame=pd.DataFrame([match('1','2024-1','2024-05-06'),match('u','2024-99','2024-05-13'),match('2','2024-2','2024-05-20')])
    data,_=prepare_historical_dataset(frame,registry());target=data.iloc[-1]
    assert target.a_status=='immediate_previous_edition_unlinked'
    assert pd.isna(target.a_distance_km)
    assert target.a_previous_observed_block_id=='ATP:tour:2024-99'


def test_same_source_week_is_ambiguous():
    frame=pd.DataFrame([match('1','2024-1','2024-05-20'),match('2','2024-2','2024-05-20')])
    data,_=prepare_historical_dataset(frame,registry())
    assert data.a_status.eq('ambiguous_same_or_overlapping_source_period').all()
    assert data.a_distance_km.isna().all()


def test_overlapping_seven_day_reference_intervals_are_ambiguous():
    frame=pd.DataFrame([match('1','2024-1','2024-05-15'),match('2','2024-2','2024-05-20')])
    data,_=prepare_historical_dataset(frame,registry())
    assert data.iloc[-1].a_status=='ambiguous_same_or_overlapping_source_period'


def test_unlinked_qualifying_does_not_inherit_main_draw_location():
    frame=pd.DataFrame([match('q','2024-1','2024-05-06',phase='qualifying'),match('2','2024-2','2024-05-20')])
    data,_=prepare_historical_dataset(frame,registry())
    assert data.iloc[0].a_status=='immediate_previous_edition_unlinked'


def test_future_tournament_cannot_change_earlier_features():
    before=[match('1','2024-1','2024-05-06'),match('2','2024-2','2024-05-20')]
    first,_=prepare_historical_dataset(pd.DataFrame(before),registry())
    later,_=prepare_historical_dataset(pd.DataFrame(before+[match('f','2025-2','2025-06-02')]),registry())
    pd.testing.assert_frame_equal(first,later.iloc[:2].reset_index(drop=True),check_dtype=False)


def test_multiple_last_observed_tournaments_ambiguous():
    frame=pd.DataFrame([match('1','2024-1','2024-05-06'),match('x','2024-99','2024-05-06'),match('2','2024-2','2024-05-20')])
    data,_=prepare_historical_dataset(frame,registry())
    assert data.iloc[-1].a_status=='ambiguous_previous_source_period'


def test_dst_transition_keeps_range_and_does_not_fake_scalar():
    assert clock_range('Asia/Shanghai','Europe/Paris','2025-03-24','2025-03-24')==(-7,-6)


def test_complete_event_crossing_calendar_boundary_quarantined():
    frame=pd.DataFrame([match('1','2025-2','2024-12-30'),match('2','2025-2','2025-01-06')])
    data,_=prepare_historical_dataset(frame,registry())
    assert data.partition.eq('boundary_quarantine').all()
    assert data.exploratory_2025.all()


def test_later_data_and_duplicate_ids_rejected():
    for rows in [[match('1','2026-1','2026-01-05')],[match('1','2024-1','2024-05-06')]*2]:
        with pytest.raises(ValueError):prepare_historical_dataset(pd.DataFrame(rows),registry())


def test_registry_rejects_projected_season_and_modified_evidence(tmp_path):
    evidence=tmp_path/'source.txt';evidence.write_text('2024 official venue fact')
    reg=registry();reg['schema']='tennis-historical-venue-links-v1'
    reg['sources']=[dict(source_id='s',source_path=str(evidence),sha256=hashlib.sha256(evidence.read_bytes()).hexdigest(),received_at='2026-10-18T10:00:00Z')]
    for v in reg['venues']:v.update(coordinate_scope='venue_point',coordinate_sources=['s'],altitude_sources=['s'])
    for l in reg['links']:l.update(evidence_season=int(l['tourney_id'][:4]),edition_sources=['s'])
    path=tmp_path/'registry.json';path.write_text(json.dumps(reg));load_historical_registry(path)
    bad=deepcopy(reg);bad['links'][0]['evidence_season']=2026;path.write_text(json.dumps(bad))
    with pytest.raises(ValueError,match='historical season'):load_historical_registry(path)
    path.write_text(json.dumps(reg));evidence.write_text('changed')
    with pytest.raises(ValueError,match='source changed'):load_historical_registry(path)


def match_link(mid,tid,venue):
    return dict(match_id=mid,circuit='ATP',phase='tour',tourney_id=tid,venue_id=venue,evidence_season=int(tid[:4]))


def test_multicity_target_uses_each_match_location():
    reg=registry();reg['match_links']=[match_link('2','2024-3','paris'),match_link('3','2024-3','china')]
    frame=pd.DataFrame([match('1','2024-1','2024-05-06'),match('2','2024-3','2024-05-20'),match('3','2024-3','2024-05-20')])
    data,report=prepare_historical_dataset(frame,reg)
    assert data.iloc[1].a_distance_km>8000
    assert data.iloc[2].a_distance_km==0
    assert data.iloc[1].venue_id=='paris' and data.iloc[2].venue_id=='china'
    assert next(e for e in report['edition_catalog'] if e['tourney_id']=='2024-3')['venue_status']=='match_level_complete'


def test_each_player_in_prior_multicity_edition_retains_own_location():
    reg=registry();reg['match_links']=[match_link('x','2024-3','china'),match_link('z','2024-3','paris')]
    frame=pd.DataFrame([match('x','2024-3','2024-05-06','a','c'),match('z','2024-3','2024-05-06','b','d'),match('2','2024-2','2024-05-20')])
    data,_=prepare_historical_dataset(frame,reg)
    assert data.iloc[-1].a_distance_km>8000 and data.iloc[-1].b_distance_km==0


def test_multiple_previous_player_locations_do_not_invent_departure():
    reg=registry();reg['match_links']=[match_link('x','2024-3','china'),match_link('z','2024-3','paris')]
    frame=pd.DataFrame([match('x','2024-3','2024-05-06'),match('z','2024-3','2024-05-06'),match('2','2024-2','2024-05-20')])
    data,_=prepare_historical_dataset(frame,reg)
    assert data.iloc[-1].a_status=='previous_edition_has_multiple_observed_venues'
    assert pd.isna(data.iloc[-1].a_distance_km)


def test_partial_match_locations_cannot_hide_unknown_antecedent():
    reg=registry();reg['match_links']=[match_link('x','2024-3','china')]
    frame=pd.DataFrame([match('x','2024-3','2024-05-06'),match('z','2024-3','2024-05-06'),match('2','2024-2','2024-05-20')])
    data,_=prepare_historical_dataset(frame,reg)
    assert data.iloc[-1].a_status=='immediate_previous_edition_unlinked'


def test_rubbers_of_one_official_tie_are_one_comparison_block():
    reg=registry();reg['links'][0]['competition_group_id']='official_tie_1'
    reg['links'].append(dict(reg['links'][0],tourney_id='2024-4'))
    frame=pd.DataFrame([match('x','2024-1','2024-05-06'),match('z','2024-4','2024-05-06')])
    data,_=prepare_historical_dataset(frame,reg)
    assert data.comparison_block_id.nunique()==1
    assert data.a_status.eq('no_earlier_observed_tournament').all()


def test_tie_spanning_partition_boundary_is_wholly_quarantined():
    reg=registry();reg['links'][0]['competition_group_id']='official_tie_1'
    reg['links'].append(dict(reg['links'][0],tourney_id='2024-4'))
    frame=pd.DataFrame([match('x','2024-1','2024-11-30'),match('z','2024-4','2024-12-01')])
    data,_=prepare_historical_dataset(frame,reg)
    assert data.partition.eq('boundary_quarantine').all()


def test_match_venue_wrong_edition_rejected():
    reg=registry();reg['match_links']=[match_link('x','2024-99','china')]
    with pytest.raises(ValueError,match='canonical edition'):
        prepare_historical_dataset(pd.DataFrame([match('x','2024-1','2024-05-06')]),reg)


def test_duplicate_match_venues_rejected():
    reg=registry();reg['match_links']=[match_link('x','2024-1','china')]*2
    with pytest.raises(ValueError,match='Duplicate match venue'):
        prepare_historical_dataset(pd.DataFrame([match('x','2024-1','2024-05-06')]),reg)
