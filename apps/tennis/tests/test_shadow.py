import json
from pathlib import Path
import pytest

from tennis_engine.shadow import capture_phase, capture_targets, verified_fixture, build_plan, write_immutable


def event():
    return {"id":"e1","sport_key":"tennis_atp_test","home_team":"A","away_team":"B",
            "commence_time":"2026-10-18T10:00:00Z"}


def test_capture_windows_are_explicit_and_utc():
    assert capture_phase(event()["commence_time"],"2026-10-18T08:00:00Z") == "t_minus_120"
    assert capture_phase(event()["commence_time"],"2026-10-18T09:45:00Z") == "t_minus_15"
    assert capture_phase(event()["commence_time"],"2026-10-17T10:00:00Z") == "waiting_t_minus_120"
    assert capture_phase(event()["commence_time"],"2026-10-18T10:20:00Z") == "estimated_start_passed"
    assert capture_targets(event()["commence_time"])["t_minus_120"] == "2026-10-18T08:00:00+00:00"


def test_fixture_needs_fresh_exact_participants_and_reconciled_time(tmp_path):
    import hashlib
    source=tmp_path/'official.json';source.write_bytes(b'official status observation')
    fixture={"event_id":"e1","status":"scheduled","observed_at":"2026-10-18T07:59:00Z",
             "actual_start":None,"participants_verified":True,"provider_time_reconciled":True,
             "source_url":"https://www.atptour.com/schedule","evidence":"reviewed schedule receipt",
             'sport_key':event()['sport_key'],'participants':['A','B'],
             'provider_commence_time':event()['commence_time'],
             'source_path':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
    assert verified_fixture(event(),fixture,"2026-10-18T08:00:00Z")["eligible"]
    fixture["provider_time_reconciled"]=False
    assert "provider_time_not_reconciled" in verified_fixture(event(),fixture,"2026-10-18T08:00:00Z")["reasons"]
    fixture["provider_time_reconciled"]=True
    assert "stale_fixture_receipt" in verified_fixture(event(),fixture,"2026-10-18T08:20:00Z")["reasons"]
    source.write_bytes(b'modified')
    assert 'fixture_source_hash_mismatch' in verified_fixture(event(),fixture,'2026-10-18T08:00:00Z')['reasons']


def test_shadow_plan_predicts_verified_identity_but_never_releases(tmp_path):
    from tennis_engine.identities import Registry
    import pandas as pd
    db=tmp_path/"ids.sqlite"; registry=Registry(db)
    registry.seed(pd.DataFrame({"circuit":["ATP"],"winner_id":["p1"],"winner_name":["A"],
                                "loser_id":["p2"],"loser_name":["B"]}))
    registry.bind("the_odds_api","ATP","name:A","p1","official profile","reviewer")
    registry.bind("the_odds_api","ATP","name:B","p2","official profile","reviewer")
    config=tmp_path/"tournaments.json";config.write_text(json.dumps({"tennis_atp_test":{
        "surface":"Hard","best_of":3,"deciding_tiebreak":7,"metadata_verified":True,
        'source_url':'https://official.example','valid_from':'2026-10-01','valid_to':'2026-10-31'}}))
    models=tmp_path/"models";pool=tmp_path/"pools/ATP_pool/pool.json"
    for name in ("model.json","precision.npz","training_receipt.json"):
        target=models/"ATP_current"/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b"x")
    pool.parent.mkdir(parents=True);pool.write_bytes(b"x")
    prediction={"winner_A":.6,"winner_B":.4,'cutoff':'2026-10-16'}
    plan=build_plan([event()],tmp_path,models,tmp_path/"pools",db,config,
                    "2026-10-17T10:00:00Z",forecast_function=lambda *a:prediction)
    row=plan["events"][0]
    assert row["prediction"]==prediction and not row["release_gate"]["eligible"]
    assert not row["odds_capture_allowed"] and "missing_exact_fixture_receipt" in row["release_gate"]["reasons"]
    path=write_immutable(tmp_path,plan)
    assert path.exists() and json.loads(path.read_text())["payload_sha256"]
