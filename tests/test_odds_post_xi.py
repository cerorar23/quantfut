from datetime import datetime, timedelta, timezone

from qf.ingest import odds_worker


def test_ventana_post_xi_solo_con_ambas_alineaciones(monkeypatch):
    now = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    rows = [
        {"match_id": "ready", "odds_api_key": "sport", "mins": 30,
         "lineup_sides": 2, "lineup_as_of": now - timedelta(minutes=2)},
        {"match_id": "partial", "odds_api_key": "sport", "mins": 30,
         "lineup_sides": 1, "lineup_as_of": now - timedelta(minutes=2)},
        {"match_id": "future", "odds_api_key": "sport", "mins": 30,
         "lineup_sides": 2, "lineup_as_of": now + timedelta(seconds=1)},
    ]
    monkeypatch.setattr(odds_worker, "query",
                        lambda sql: [] if "odds_capture_log" in sql else rows)
    assert odds_worker._pending_windows(now) == {
        "sport": [("ready", "post_xi")]
    }


def test_ventana_post_xi_no_se_repite_si_ya_fue_capturada(monkeypatch):
    now = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    row = {"match_id": "ready", "odds_api_key": "sport", "mins": 30,
           "lineup_sides": 2, "lineup_as_of": now - timedelta(minutes=2)}
    monkeypatch.setattr(
        odds_worker, "query",
        lambda sql: [{"match_id": "ready", "window_tag": "post_xi"}]
        if "odds_capture_log" in sql else [row],
    )
    assert odds_worker._pending_windows(now) == {}
