"""Importar originales no puede fabricar identidades ni disponibilidad histórica."""
import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from qf.ingest.fotmob_import import Matcher, parse_payload, timestamp
from qf.model.xg import xg_at_cutoff


def source():
    fixture = {"league_id": "gb.championship", "fotmob_league_id": 48,
               "season": "2024/2025", "fotmob_match_id": "123",
               "kickoff_utc": "2025-01-01T12:00:00Z", "home_team_id": "10", "away_team_id": "20"}
    payload = {"general": {"matchId": "123", "leagueId": 48,
               "matchTimeUTCDate": fixture["kickoff_utc"],
               "homeTeam": {"id": 10, "name": "Southampton"}, "awayTeam": {"id": 20, "name": "Hull"}},
               "header": {"status": {"finished": True}, "teams": [{"score": 2}, {"score": 1}]},
               "content": {"lineup": {"homeTeam": {"id": 10, "starters": [{"id": i} for i in range(1, 12)]}},
                   "playerStats": {"1": {"id": 1, "name": "Player", "teamId": 10, "stats": []}}}}
    raw = json.dumps(payload).encode()
    meta = {"sha256": hashlib.sha256(raw).hexdigest(), "captured_at": "2026-10-03T12:00:00Z"}
    return fixture, raw, meta


def test_original_hash_missing_metrics_and_provider_namespace():
    f, raw, meta = source()
    result = parse_payload(f, raw, meta)
    assert result["home_name"] == "Southampton"
    assert result["home_xg"] is None and result["players"][0]["minutes"] is None
    assert result["players"][0]["source_player_id"] == 1
    assert result["lineups"][0]["complete"] is True
    with pytest.raises(ValueError, match="raw_hash_mismatch"):
        parse_payload(f, raw + b" ", meta)
    with pytest.raises(ValueError, match="invalid_capture_time"):
        parse_payload(f, raw, dict(meta, captured_at="2024-01-01T12:00:00Z"))


def test_placeholder_player_ids_do_not_discard_a_valid_match():
    f, raw, meta = source()
    payload = json.loads(raw)
    payload["content"]["playerStats"].update({
        "bad1": {"id": 0, "teamId": 10, "name": "Bad1"},
        "bad2": {"id": 0, "teamId": 10, "name": "Bad2"}})
    raw = json.dumps(payload).encode()
    meta["sha256"] = hashlib.sha256(raw).hexdigest()
    row = parse_payload(f, raw, meta)
    assert row["source_match_id"] == "123"
    assert [p["source_player_id"] for p in row["players"]] == [1]


def setup_matcher():
    row = parse_payload(*source())
    snapshot = {"leagues": [{"league_id": "gb.championship", "cross_league": False}],
        "teams": [{"team_id": 1, "league_id": "gb.premier_league", "canonical_name": "Southampton"},
                  {"team_id": 2, "league_id": "gb.championship", "canonical_name": "Hull"},
                  {"team_id": 3, "league_id": "us.mls", "canonical_name": "Hull"}],
        "aliases": [], "matches": [{"match_id": "existing", "league_id": "gb.championship",
            "kickoff_utc": row["kickoff_utc"], "home_team_id": 1, "away_team_id": 2,
            "status": "finished", "home_goals": 2, "away_goals": 1, "external_ids": {}}]}
    return row, snapshot


def test_promoted_club_reused_and_different_country_ignored():
    row, db = setup_matcher()
    decision = Matcher(db, [row]).match(row)
    assert decision["match_id"] == "existing" and decision["home_team_id"] == 1


def test_score_external_identity_and_ambiguous_match_fail_closed():
    row, db = setup_matcher()
    db["matches"][0]["away_goals"] = 2
    assert Matcher(db, [row]).match(row)["mapping_status"] == "conflict"
    db["matches"][0]["away_goals"] = 1
    db["matches"][0]["external_ids"] = {"fotmob": "456"}
    assert Matcher(db, [row]).match(row)["match_id"] is None
    db["matches"][0]["external_ids"] = {}
    db["matches"].append(dict(db["matches"][0], match_id="duplicate"))
    assert Matcher(db, [row]).match(row)["match_id"] is None


def test_unknown_and_swapped_fixture_do_not_create_duplicates():
    row, db = setup_matcher()
    unknown = dict(row, home_name="Unknown club")
    assert Matcher(db, [unknown]).match(unknown)["mapping_status"] == "unresolved"
    db["matches"][0].update(home_team_id=2, away_team_id=1)
    assert Matcher(db, [row]).match(row)["mapping_status"] == "conflict"
    db["matches"] = []
    assert Matcher(db, [row]).match(row)["match_id"] == "fotmob:123"


@pytest.mark.parametrize("provider", ["fotmob", "sofascore", "api_football"])
def test_each_observed_source_requires_real_receipt(provider):
    df = pd.DataFrame({"home_xg": [1.2, 1.3, 1.4], "away_xg": [0, 1, 2],
                       "xg_source": [provider, provider, None],
                       "xg_recorded_at": ["2026-10-03T12:00:00Z", None, None]})
    np.testing.assert_allclose(xg_at_cutoff(df, "2026-10-02")[0], [np.nan, np.nan, 1.4], equal_nan=True)
    np.testing.assert_allclose(xg_at_cutoff(df, "2026-10-04")[0], [1.2, np.nan, 1.4], equal_nan=True)


def test_timezone_is_required_for_source_receipt():
    with pytest.raises(ValueError, match="timestamp_without_timezone"):
        timestamp("2026-10-03")
