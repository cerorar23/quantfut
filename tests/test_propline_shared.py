"""Archive/budget/contract safeguards; no network or account secrets."""
import copy
import gzip
import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from qf.ingest import propline_shared as pl

NOW = datetime(2026, 10, 23, 21, 30, tzinfo=timezone.utc)


def event():
    return dict(id="42", sport_key="soccer_epl", commence_time="2026-10-24T14:00:00Z",
        home_team="Arsenal", away_team="Chelsea", home_team_id="home-id", away_team_id="away-id",
        bookmakers=[dict(key="pinnacle", markets=[dict(key="h2h", period=None, team=None,
        line_type="main", outcomes=[dict(name="Arsenal", side="home", price=-200, point=None,
        player_id=None, book_updated_at=None, last_seen_at="2026-10-23T21:29:00Z")])])])


def client(root, *, clock=None, remaining=4900, status=200, data=None):
    calls = []
    def get(path, params, key):
        calls.append((path, params))
        return status, {"X-Daily-Remaining": str(remaining), "X-Daily-Reset": "1792800000",
            "Set-Cookie": "SECRET_COOKIE"}, json.dumps(data if data is not None else [event()]).encode()
    return pl.Collector(root, "SECRET_API_KEY_NOT_SAVED", get=get, clock=clock or (lambda: NOW)), calls


def test_original_bytes_hash_receipt_and_no_secrets(tmp_path):
    c, calls = client(tmp_path)
    r, called = c.capture("/v1/sports/soccer_epl/odds", {"markets": "h2h"})
    assert called and len(calls) == 1
    assert pl.load_object(tmp_path, r) == [event()]
    assert pl.parse_time(r["received_at"]) == NOW
    assert "Set-Cookie" not in r["headers"] and "SECRET" not in r["headers"]
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        c.db.execute("DELETE FROM receipts")


def test_two_consumers_do_not_download_twice_in_one_hour(tmp_path):
    a, calls_a = client(tmp_path)
    b, calls_b = client(tmp_path)
    first, _ = a.capture("/v1/sports/tennis/odds")
    second, called = b.capture("/v1/sports/tennis/odds")
    assert not called and first["sha256"] == second["sha256"]
    assert len(calls_a) == 1 and calls_b == []


def test_next_hour_keeps_both_observations_even_if_price_is_unchanged(tmp_path):
    clock = [NOW]
    c, calls = client(tmp_path, clock=lambda: clock[0])
    a, _ = c.capture("/v1/sports/tennis/odds")
    clock[0] += timedelta(hours=1)
    b, _ = c.capture("/v1/sports/tennis/odds")
    assert a["sha256"] == b["sha256"] and a["request_id"] != b["request_id"]
    assert c.db.execute("SELECT count(*) FROM receipts").fetchone()[0] == 2
    assert len(list(tmp_path.glob("objects/*/*"))) == 1


def test_receipt_uses_time_after_network_not_start(tmp_path):
    times = iter([NOW, NOW + timedelta(seconds=23)])
    c, _ = client(tmp_path, clock=lambda: next(times))
    r, _ = c.capture("/v1/sports/tennis/odds")
    assert pl.parse_time(r["received_at"]) == NOW + timedelta(seconds=23)
    assert pl.newest(tmp_path, "/v1/sports/tennis/odds", NOW)[0] is None


def test_as_of_and_age_are_enforced_for_offline_read(tmp_path):
    c, _ = client(tmp_path)
    c.capture("/v1/sports/tennis/odds")
    assert pl.newest(tmp_path, "/v1/sports/tennis/odds", NOW - timedelta(seconds=1))[0] is None
    assert pl.newest(tmp_path, "/v1/sports/tennis/odds", NOW + timedelta(hours=2))[0] is None
    assert pl.newest(tmp_path, "/v1/sports/tennis/odds", NOW)[0] == [event()]


def test_corrupted_raw_object_is_never_served(tmp_path):
    c, _ = client(tmp_path)
    r, _ = c.capture("/v1/sports/tennis/odds")
    (tmp_path / r["body_path"]).write_bytes(gzip.compress(b"[]"))
    with pytest.raises(ValueError, match="hash"):
        pl.newest(tmp_path, "/v1/sports/tennis/odds", NOW)


def test_transport_failure_is_reserved_and_not_retried(tmp_path):
    c, _ = client(tmp_path)
    def failed(*args):
        raise TimeoutError("URL with SECRET_API_KEY")
    c.get = failed
    assert c.capture("/v1/sports/tennis/odds") == (None, True)
    assert c.capture("/v1/sports/tennis/odds") == (None, False)
    state = c.db.execute("SELECT state FROM requests").fetchone()[0]
    assert state == "transport_TimeoutError" and "SECRET" not in state


def test_account_reserve_uses_provider_headers_not_local_counter(tmp_path):
    clock = [NOW]
    c, _ = client(tmp_path, clock=lambda: clock[0], remaining=500)
    c.capture("/v1/sports")
    with pytest.raises(pl.BudgetStop, match="account_reserve"):
        c.capture("/v1/sports/tennis/odds")
    clock[0] += timedelta(days=1)
    assert c.capture("/v1/sports")[1]


def test_daily_reservation_cap_includes_ambiguous_requests(tmp_path):
    c, _ = client(tmp_path)
    c.cap = 1
    c.get = lambda *args: (_ for _ in ()).throw(TimeoutError())
    c.capture("/v1/sports")
    with pytest.raises(pl.BudgetStop, match="local_daily_cap"):
        c.capture("/v1/sports/tennis/odds")


@pytest.mark.parametrize("status", [401, 403, 429])
def test_rejected_requests_are_saved_before_halt(tmp_path, status):
    c, _ = client(tmp_path, status=status, data={"error": "quota"})
    with pytest.raises(pl.BudgetStop, match=str(status)):
        c.capture("/v1/sports")
    assert c.db.execute("SELECT status FROM receipts").fetchone()[0] == status


@pytest.mark.parametrize("american,decimal", [(100, 2), (-200, 1.5), (150, 2.5), (-110, 1 + 100/110)])
def test_american_prices_are_not_mistaken_for_decimals(american, decimal):
    assert pl.decimal_price({"price": american}) == pytest.approx(decimal)


def test_context_and_missing_published_timestamp_remain_distinct():
    q = next(pl.quotes([event()], pl.stamp(NOW)))
    assert q["received_at"] == pl.stamp(NOW) and q["book_updated_at"] is None
    assert q["last_seen_at"] and q["home_team_id"] == "home-id"
    assert q["price_american"] == -200 and q["price_decimal"] == 1.5


def test_fullgame_teamtotal_period_dfs_suspension_and_live_not_mixed():
    base = event()
    base_market = base["bookmakers"][0]["markets"][0]
    base_market.update(key="totals", outcomes=[dict(name="Over", price=-110, point=2.5)])
    base["bookmakers"][0]["markets"] += [dict(copy.deepcopy(base_market), team="Arsenal"),
        dict(copy.deepcopy(base_market), period="h1"), dict(copy.deepcopy(base_market), suspended_at="2026-10-23T21:00:00Z")]
    base["bookmakers"].append(dict(key="prizepicks", markets=[base_market]))
    result = pl.football_feed([base], pl.stamp(NOW))
    assert len(result[0]["bookmakers"]) == 1
    assert len(result[0]["bookmakers"][0]["markets"]) == 1
    assert result[0]["bookmakers"][0]["markets"][0]["outcomes"][0]["point"] == 2.5
    base["live"] = True
    assert pl.football_feed([base], pl.stamp(NOW)) == []


def test_invalid_prices_are_kept_for_audit_but_not_consumers():
    e = event()
    e["bookmakers"][0]["markets"][0]["outcomes"][0]["price"] = 1.91
    q = next(pl.quotes([e], pl.stamp(NOW)))
    assert q["price_american"] == 1.91 and q["price_decimal"] is None
    assert "invalid_price" in q["flags"] and pl.football_feed([e], pl.stamp(NOW)) == []


def test_football_import_does_not_claim_close_or_mix_team_total():
    from qf.ingest.propline_ingest import football_rows
    e = event()
    market = e["bookmakers"][0]["markets"][0]
    e["bookmakers"][0]["markets"] += [dict(key="totals",period=None,team="Arsenal",
        outcomes=[dict(name="Over",price=-110,point=1.5)]),
        dict(key="total_corners",period="h1",outcomes=[dict(name="Over",price=-110,point=4.5)])]
    rows = football_rows(e,"match",NOW,pl.parse_time(e["commence_time"]),"hourly:1")
    assert {r[2] for r in rows} == {"h2h","team_totals_home"}
    assert all(r[6] == NOW and r[8] == "hourly:1" and r[9] == "propline" and r[10] is None for r in rows)


def test_restricted_or_future_published_prices_cannot_feed_predictions():
    e = event()
    o=e["bookmakers"][0]["markets"][0]["outcomes"][0]
    o["book_updated_at"] = pl.stamp(NOW+timedelta(seconds=1))
    assert "future_book_update" in next(pl.quotes([e],pl.stamp(NOW)))["flags"]
    assert pl.football_feed([e],pl.stamp(NOW)) == []


def test_propline_mode_cannot_spend_legacy_provider_credits(monkeypatch):
    from types import SimpleNamespace
    from qf.ingest import odds_worker,rafagas,af_odds,propline_ingest
    settings=SimpleNamespace(odds_provider="propline")
    for module in (odds_worker,rafagas,af_odds):
        monkeypatch.setattr(module,"settings",settings)
    monkeypatch.setattr(propline_ingest,"ingest_hourly",lambda: {"calls":0,"source":"propline"})
    monkeypatch.setattr(odds_worker,"_fetch",lambda *a: pytest.fail("legacy network"))
    monkeypatch.setattr(rafagas,"_fetch",lambda *a: pytest.fail("legacy network"))
    monkeypatch.setattr(af_odds,"_pending",lambda *a: pytest.fail("legacy network"))
    assert odds_worker.run_once()["calls"] == 0
    assert rafagas.run_once()["consultas"] == 0
    assert af_odds.run_once()["calls"] == 0


def test_predictions_read_only_configured_source_and_same_response(monkeypatch):
    from types import SimpleNamespace
    from qf.publish import picks,alta_prob_datos,escalera_datos
    settings=SimpleNamespace(odds_provider="propline")
    calls=[]
    def query(sql,args):
        calls.append(sql)
        if "market = 'h2h'" in sql:return [dict(bookmaker="pinnacle",selection="home",price=1.5,captured_at=NOW)]
        return []
    for module in (picks,alta_prob_datos,escalera_datos):
        monkeypatch.setattr(module,"settings",settings)
        monkeypatch.setattr(module,"query",query)
    snap=picks._odds_api_snapshot("match",NOW)
    assert snap.source == "propline" and snap.as_of == NOW
    assert picks._af_snapshot("match",NOW) is None
    alta_prob_datos._totales("match",NOW)
    escalera_datos._handicaps("match",NOW)
    assert len(calls) == 3 and all("source = 'propline'" in sql and "source = 'the_odds_api'" not in sql for sql in calls)


def test_market_batches_are_merged_without_reading_future_batches(tmp_path):
    clock=[NOW]
    c,_=client(tmp_path,clock=lambda:clock[0])
    c.capture("/v1/sports/soccer_epl/odds",{"markets":"h2h"})
    changed=event()
    changed["bookmakers"][0]["markets"][0]["key"]="totals"
    c.get=lambda *a:(200,{},json.dumps([changed]).encode())
    clock[0]+=timedelta(seconds=30)
    c.capture("/v1/sports/soccer_epl/odds",{"markets":"totals"})
    early,_=pl.newest(tmp_path,"/v1/sports/soccer_epl/odds",NOW)
    late,meta=pl.newest(tmp_path,"/v1/sports/soccer_epl/odds",clock[0])
    assert [m["key"] for m in early[0]["bookmakers"][0]["markets"]]==["h2h"]
    assert {m["key"] for m in late[0]["bookmakers"][0]["markets"]}=={"h2h","totals"}
    assert len(meta["component_receipts"])==2


def test_shared_provider_policy_is_explicit_and_fail_closed(tmp_path,monkeypatch):
    from qf.config import _odds_provider
    monkeypatch.delenv("ODDS_PROVIDER",raising=False)
    monkeypatch.setenv("PROPLINE_ARCHIVE",str(tmp_path))
    (tmp_path/"provider.json").write_text('{"provider":"propline"}')
    assert _odds_provider()=="propline"
    (tmp_path/"provider.json").write_text('{"provider":"unknown"}')
    with pytest.raises(ValueError):_odds_provider()


def test_stale_delivery_and_unchanged_old_price_are_different():
    e=event();o=e["bookmakers"][0]["markets"][0]["outcomes"][0]
    o["last_change_at"]="2026-10-01T00:00:00Z"
    assert not next(pl.quotes([e],pl.stamp(NOW)))["flags"]
    o["last_seen_at"]=pl.stamp(NOW-timedelta(hours=1))
    assert "stale_provider_delivery" in next(pl.quotes([e],pl.stamp(NOW)))["flags"]


def test_alternate_lines_do_not_collapse_when_merging_batches(tmp_path):
    e=event();m=e["bookmakers"][0]["markets"][0]
    m.update(key="totals",line_type="alternate",outcomes=[dict(name="Over",price=-110,point=2.5)])
    other=copy.deepcopy(m);other["outcomes"][0]["point"]=3.5
    e["bookmakers"][0]["markets"].append(other)
    c,_=client(tmp_path,data=[e]);c.capture("/v1/sports/soccer_epl/odds")
    data,_=pl.newest(tmp_path,"/v1/sports/soccer_epl/odds",NOW)
    assert {m["outcomes"][0]["point"] for m in data[0]["bookmakers"][0]["markets"]}=={2.5,3.5}
