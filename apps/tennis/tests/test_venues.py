from copy import deepcopy
import hashlib,json,sqlite3

import pytest

from tennis_engine.venues import VenueRegistry


REGISTERED='2026-10-17T12:00:00Z'
DECISION='2026-10-17T13:00:00Z'


@pytest.fixture
def registry(tmp_path):
    path=tmp_path/'source.json';path.write_text('official source')
    r=VenueRegistry(tmp_path/'registry.sqlite')
    r.add_source({'source_id':'s','url':'https://example.org/official','received_at':'2026-10-17T11:00:00Z',
                  'source_path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    return r


def venue(**kwargs):
    v={'venue_id':'p12','name':'Palais 12','city':'Brussels','country':'BE','timezone':'Europe/Brussels',
       'lat':50.9011,'lon':4.3422,'coordinate_scope':'venue_geometry_representative','coordinate_precision_m':250,
       'altitude_m':None,'indoor':True,'recorded_at':REGISTERED,
       'field_sources':{k:['s'] for k in ('name','city','country','timezone','coordinates','indoor')}}
    v.update(kwargs);return v


def binding(**kwargs):
    b={'binding_id':'one','provider':'api_tennis','provider_tournament_id':'3669','provider_event_type':'Atp Singles',
       'season':'2026','edition_id':'atp:brussels:2026','venue_id':'p12','valid_from':'2026-10-17',
       'valid_until':'2026-10-23','timezone':'Europe/Brussels','surface':'Hard',
       'sources':['s'],'surface_sources':['s'],'recorded_at':REGISTERED}
    b.update(kwargs);return b


def resolve(r,start='2026-10-22T21:59:00Z',decision=DECISION,**kwargs):
    arguments=dict(provider='api_tennis',tournament_id='3669',event_type='Atp Singles',season='2026',
                   scheduled_start=start,decision_at=decision)
    arguments.update(kwargs);return r.resolve(**arguments)


def test_resolves_exact_provider_edition_and_predecision_registration(registry):
    registry.register_venue(venue());registry.register_binding(binding())
    row=resolve(registry)
    assert row['status']=='resolved' and row['venue']['venue_id']=='p12'
    assert row['roof_state_at_match'] is None and not row['actual_court_verified']
    assert resolve(registry,season='2025')['status']=='unresolved'
    assert resolve(registry,event_type='Atp Doubles')['status']=='unresolved'
    assert resolve(registry,tournament_id='name:Brussels')['status']=='unresolved'
    assert resolve(registry,decision=REGISTERED)['status']=='unresolved'


def test_local_date_midnight_selects_changed_site_and_dst_date(registry):
    registry.register_venue(venue());registry.register_venue(venue(venue_id='p5',name='Palais 5'))
    registry.register_binding(binding())
    registry.register_binding(binding(binding_id='two',venue_id='p5',valid_from='2026-10-23',valid_until='2026-10-26'))
    assert resolve(registry)['venue']['venue_id']=='p12'
    # 22:00 UTC is local midnight in Brussels before DST ends.
    assert resolve(registry,start='2026-10-22T22:00:00Z')['venue']['venue_id']=='p5'
    assert resolve(registry,start='2026-10-25T22:59:00Z')['venue']['venue_id']=='p5'
    assert resolve(registry,start='2026-10-25T23:00:00Z')['status']=='unresolved'


def test_versions_do_not_rewrite_prior_decisions(registry):
    registry.register_venue(venue());registry.register_binding(binding())
    registry.register_venue(venue(name='Corrected name',recorded_at='2026-10-17T14:00:00Z'))
    assert resolve(registry)['venue']['name']=='Palais 12'
    assert resolve(registry,decision='2026-10-17T15:00:00Z')['venue']['name']=='Corrected name'


def test_binding_revisions_can_correct_validity_without_leaving_stale_binding(registry):
    registry.register_venue(venue());registry.register_binding(binding())
    registry.register_binding(binding(valid_until='2026-10-22',recorded_at='2026-10-17T14:00:00Z'))
    assert resolve(registry)['status']=='resolved'
    assert resolve(registry,decision='2026-10-17T15:00:00Z')['status']=='unresolved'


def test_overlapping_distinct_bindings_are_ambiguous(registry):
    registry.register_venue(venue());registry.register_binding(binding())
    registry.register_binding(binding(binding_id='other'))
    assert resolve(registry)['status']=='ambiguous'


@pytest.mark.parametrize('kwargs',[{'lat':float('nan')},{'lat':91},{'lon':None},{'coordinate_scope':'city_centre'},
                                  {'indoor':1},{'timezone':'not/a/zone'},{'altitude_m':float('inf')},
                                  {'coordinate_precision_m':0},{'roof_state_at_match':'closed'}])
def test_invalid_venue_metadata_rejected(registry,kwargs):
    with pytest.raises((ValueError,KeyError)):registry.register_venue(venue(**kwargs))


def test_evidence_required_per_known_field_and_receipt_precedes_registration(registry):
    v=venue();v['field_sources'].pop('coordinates')
    with pytest.raises(ValueError):registry.register_venue(v)
    with pytest.raises(ValueError):registry.register_venue(venue(recorded_at='2026-10-17T10:00:00Z'))
    v=venue();v['field_sources']['name']=['absent']
    with pytest.raises(ValueError):registry.register_venue(v)


def test_changed_source_detected_at_query_and_registry_is_append_only(registry):
    registry.register_venue(venue());registry.register_binding(binding())
    with pytest.raises(sqlite3.IntegrityError):registry.db.execute('DELETE FROM venue_bindings')
    registry.db.rollback()
    s=json.loads(registry.db.execute('SELECT body FROM venue_sources').fetchone()[0])
    from pathlib import Path
    Path(s['source_path']).write_text('changed')
    with pytest.raises(ValueError):resolve(registry)


def test_idempotence_and_conflicting_revision_at_same_clock(registry):
    first=registry.register_venue(venue())
    assert registry.register_venue(venue())==first
    with pytest.raises(ValueError):registry.register_venue(venue(name='other'))


def test_timezone_conflicts_and_reversed_date_windows_rejected(registry):
    registry.register_venue(venue())
    with pytest.raises(ValueError):registry.register_binding(binding(timezone='Asia/Tokyo'))
    with pytest.raises(ValueError):registry.register_binding(binding(valid_until='2026-10-16'))


def test_unknown_fields_not_filled_with_zero_or_roof_inferences(registry):
    v=venue(lat=None,lon=None,indoor=None)
    registry.register_venue(v);registry.register_binding(binding())
    row=resolve(registry)
    assert row['venue']['lat'] is None and row['venue']['altitude_m'] is None
    assert row['venue']['indoor'] is None and row['roof_state_at_match'] is None


def test_enrichment_reports_coverage_and_stale_provider_season(registry):
    registry.register_venue(venue());registry.register_binding(binding())
    event={'event_key':1,'tournament_key':3669,'event_type_type':'Atp Singles','tournament_season':'2026',
           'tournament_name':'Brussels','event_date':'2026-10-18','event_time':'12:00'}
    old={**event,'event_key':2,'tournament_season':'2025'}
    report=registry.enrich_calendar([event,old],DECISION,input_timezone='UTC',source_received_at=REGISTERED)
    assert report['coverage']==.5 and not report['probabilities_modified']
    assert report['events'][1]['review_flags']==['provider_season_differs_from_scheduled_year']
    with pytest.raises(ValueError):registry.enrich_calendar([event],DECISION,input_timezone='Europe/Berlin',source_received_at=REGISTERED)
    with pytest.raises(ValueError):registry.enrich_calendar([event],DECISION,input_timezone='UTC',source_received_at=DECISION)
