from copy import deepcopy
import hashlib,json,sqlite3

import pytest

from tennis_engine.fixture_reviews import FixtureReviews,fixture_digest
from tennis_engine.venues import VenueRegistry


@pytest.fixture
def setup(tmp_path):
    row={'event_key':7,'tournament_key':2440,'event_type_type':'Challenger Men Singles',
         'tournament_season':'2025','tournament_name':'Guangzhou','event_date':'2026-10-19','event_time':'03:00'}
    source=tmp_path/'provider.json';source.write_text(json.dumps({'result':[row]}))
    registry=VenueRegistry(tmp_path/'v.sqlite')
    registry.add_source({'source_id':'provider','url':'https://example.org/provider','received_at':'2026-10-17T10:00:00Z',
        'source_path':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
    evidence=tmp_path/'official.txt';evidence.write_text('2026 edition, 18-25 October, Nansha')
    registry.add_source({'source_id':'official','url':'https://example.org/official','received_at':'2026-10-17T11:00:00Z',
        'source_path':str(evidence),'sha256':hashlib.sha256(evidence.read_bytes()).hexdigest()})
    review={'review_id':'api_tennis:7:season','provider':'api_tennis','provider_event_id':'7',
        'input_sha256':fixture_digest(row),'input_source_id':'provider','field':'tournament_season',
        'before':'2025','after':'2026','action':'correct','recorded_at':'2026-10-17T12:00:00Z',
        'sources':['official'],'reason':'Official edition date and venue reviewed.'}
    return FixtureReviews(registry),row,review,evidence


def test_revision_visible_only_strictly_after_registration_and_original_unchanged(setup):
    reviews,row,review,_=setup;original=deepcopy(row);reviews.register(review)
    for decision in ['2026-10-17T11:59:59Z',review['recorded_at']]:
        rows,audit=reviews.apply([row],decision)
        assert rows[0]['tournament_season']=='2025' and audit[0]['status']=='not_reviewed'
    rows,audit=reviews.apply([row],'2026-10-17T12:00:01Z')
    assert rows[0]['tournament_season']=='2026' and audit[0]['provider_season']=='2025'
    assert row==original


@pytest.mark.parametrize('field,value',[('event_key',8),('event_date','2026-10-20'),('event_time','04:00')])
def test_correction_does_not_apply_to_changed_or_other_fixture(setup,field,value):
    reviews,row,review,_=setup;reviews.register(review);changed={**row,field:value}
    if field=='event_key':
        assert reviews.apply([changed],'2026-10-18T00:00:00Z')[0][0]['tournament_season']=='2025'
    else:
        with pytest.raises(ValueError,match='changed'):reviews.apply([changed],'2026-10-18T00:00:00Z')


def test_registration_requires_actual_archived_row_and_received_evidence(setup):
    reviews,row,review,_=setup
    with pytest.raises(ValueError,match='archived'):reviews.register({**review,'input_sha256':'0'*64})
    with pytest.raises(ValueError,match='predates'):reviews.register({**review,'recorded_at':'2026-10-17T10:30:00Z'})


def test_tampered_evidence_rejected_at_use(setup):
    reviews,row,review,evidence=setup;reviews.register(review);evidence.write_text('altered')
    with pytest.raises(ValueError,match='changed'):reviews.apply([row],'2026-10-18T00:00:00Z')


def test_append_only_replay_and_conflicting_reviews(setup):
    reviews,row,review,_=setup
    assert reviews.register(review)==reviews.register(review)
    with pytest.raises(sqlite3.IntegrityError):reviews.registry.db.execute('DELETE FROM fixture_reviews')
    reviews.register({**review,'review_id':'another'})
    with pytest.raises(ValueError,match='Conflicting'):reviews.apply([row],'2026-10-18T00:00:00Z')


def test_report_keeps_provider_and_normalized_season_separate(setup):
    reviews,row,review,_=setup;reviews.register(review)
    report=reviews.enrich_calendar([row],'2026-10-18T00:00:00Z',input_timezone='UTC',source_received_at='2026-10-17T10:00:00Z')
    assert report['n_season_corrected']==1 and report['n_season_unresolved']==0
    assert report['events'][0]['provider_season']=='2025' and report['events'][0]['season']=='2026'
    assert not report['individual_fixtures_independently_verified']


def test_corrections_cannot_silently_change_times_or_scores(setup):
    reviews,row,review,_=setup
    with pytest.raises(ValueError,match='Only reviewed'):reviews.register({**review,'field':'event_time'})


def test_quarantined_fixture_stops_enrichment(setup):
    reviews,row,review,_=setup;reviews.register({**review,'action':'quarantine'})
    with pytest.raises(ValueError,match='Quarantined'):reviews.apply([row],'2026-10-18T00:00:00Z')
