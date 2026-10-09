import pytest

from nba.context import availability_at, coherent_minutes, identity_join, utc, capture_public_context, verified_files


def fixtures():
    return ([dict(player_id="espn:1", team_id="espn:7", name="Nikola Jokic", date_of_birth="1995-02-19")],
            [dict(PERSON_ID=203999, PLAYER_FIRST_NAME="Nikola", PLAYER_LAST_NAME="Jokić", TEAM_ID=1610612743, TEAM_ABBREVIATION="DEN")],
            [dict(player_id=203999, birth_date="FEB 19, 1995")], [dict(id=7, abbreviation="DEN")])


def test_identity_requires_dob_and_membership_separately():
    espn, nba, refs, teams = fixtures()
    result = identity_join(espn, nba, refs, teams)[0]
    assert result["identity_verified"] and result["current_membership_verified"]
    espn[0]["date_of_birth"] = "1995-02-20"
    assert not identity_join(espn, nba, refs, teams)[0]["identity_verified"]
    espn[0]["date_of_birth"] = "1995-02-19"
    espn[0]["membership_conflict"] = True
    result = identity_join(espn, nba, refs, teams)[0]
    assert result["identity_verified"] and not result["current_membership_verified"]


def test_suffix_and_duplicate_reference_do_not_merge():
    espn, nba, refs, teams = fixtures()
    espn[0]["name"] += " Jr."
    assert not identity_join(espn, nba, refs, teams)[0]["identity_verified"]
    espn[0]["name"] = "Nikola Jokic"
    refs.append(dict(player_id=203999, birth_date="FEB 20, 1995"))
    assert not identity_join(espn, nba, refs, teams)[0]["identity_verified"]


def test_duplicate_crosswalk_quarantined():
    espn, nba, refs, teams = fixtures()
    espn.append(dict(espn[0], player_id="espn:2"))
    assert not any(r["identity_verified"] for r in identity_join(espn, nba, refs, teams))


def test_availability_is_game_specific_fresh_and_point_in_time():
    row = dict(player_id=1, event_id="espn:2", source_verified=True, status="out",
               published_at_utc="2026-10-05T19:00:00Z", first_received_at_utc="2026-10-05T19:01:00Z")
    assert availability_at([row], 1, "espn:2", "2026-10-05T19:02:00Z")["status"] == "out"
    for as_of in ("2026-10-05T18:59:00Z", "2026-10-05T19:00:30Z", "2026-10-05T20:01:00Z"):
        assert availability_at([row], 1, "espn:2", as_of)["status"] == "unknown"
    assert availability_at([row], 1, "espn:3", "2026-10-05T19:02:00Z")["status"] == "unknown"
    assert availability_at([], 1, "espn:2", "2026-10-05T19:02:00Z")["status"] == "unknown"
    assert availability_at([row, dict(row, status="available")], 1, "espn:2", "2026-10-05T19:02:00Z")["status"] == "unknown"


def test_minutes_conserve_and_exclude_absent_without_guessing_unknown():
    values = coherent_minutes([40, 35, 32, 28, 25, 20, 15, 10, 5, 30], [True]*9+[False])
    assert sum(values) == pytest.approx(240)
    assert values[-1] == 0 and all(0 <= m <= 48 for m in values)
    with pytest.raises(ValueError):
        coherent_minutes([30]*4, [True]*4)
    with pytest.raises(ValueError):
        coherent_minutes([30]*10, [None]*10)
    with pytest.raises(ValueError):
        utc("2026-10-05T19:00:00")


def test_context_capture_stops_after_provider_denial(tmp_path,monkeypatch):
    import httpx
    from nba.audit import write_json,digest
    ref=tmp_path/"reference"
    ref.mkdir()
    file=ref/"rosters_2026.parquet"
    file.write_bytes(b"fixture not parsed in capture")
    write_json(ref/"manifest.json",dict(files=[dict(name=file.name,sha256=digest(file),received_at_utc="2026-10-05T19:00:00Z")]))
    calls=[]
    class Client:
        def __init__(self,**kwargs): pass
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def stream(self,method,url):
            calls.append(url)
            class Stream:
                def __enter__(self): return httpx.Response(403,request=httpx.Request(method,url))
                def __exit__(self,*args): pass
            return Stream()
    monkeypatch.setattr("nba.context.httpx.Client",Client)
    with pytest.raises(httpx.HTTPStatusError):
        capture_public_context(tmp_path/"capture","2026-10-05",ref/"manifest.json")
    assert len(calls)==1
    import json
    manifest=json.loads(next((tmp_path/"capture").glob("*/manifest.json")).read_text())
    assert manifest["errors"][0]["kind"]=="HTTPStatusError"


def test_receipt_manifest_rejects_duplicate_files(tmp_path):
    from nba.audit import write_json,digest
    file=tmp_path/"data.json"
    file.write_bytes(b"{}")
    entry=dict(name=file.name,sha256=digest(file),received_at_utc="2026-10-05T19:00:00Z")
    write_json(tmp_path/"manifest.json",dict(files=[entry,entry]))
    with pytest.raises(ValueError):
        verified_files(tmp_path/"manifest.json")
