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


def test_high_volume_sports_separate_featured_without_extra_planned_calls():
    config = dict(max_markets_per_request=10, soccer_markets_per_request=13,
                  football_markets_per_request=11)
    featured = ["h2h","spreads","totals"]
    soccer = featured + [f"soccer_{i}" for i in range(26)]
    nfl = featured + [f"nfl_{i}" for i in range(33)]
    nba = featured + ["player_points","player_rebounds","player_assists"] + [f"nba_{i}" for i in range(18)]
    assert list(map(len,pl.market_batches("soccer_epl",soccer,config))) == [3,13,13]
    assert list(map(len,pl.market_batches("football_nfl",nfl,config))) == [3,11,11,11]
    assert list(map(len,pl.market_batches("basketball_nba",nba,config))) == [3,1,1,1,5,5,5,3]
    assert sum(pl.market_batches("football_nfl",nfl,config),[]) == nfl


def test_explicitly_excluded_sport_is_never_selected():
    catalog = [dict(key="football_nfl",active=True),dict(key="basketball_nba",active=True)]
    assert pl.select_sports(catalog,dict(sports="all_active",exclude_sports=["football_nfl"])) == ["basketball_nba"]


def test_only_soccer_tennis_and_nba_are_selected_for_hourly_capture():
    catalog = [dict(key=k,active=True) for k in
               ("football_nfl","soccer_epl","soccer_mexico_ligamx","tennis","basketball_nba","hockey_nhl")]
    config = dict(sports=["basketball_nba","tennis"],sport_prefixes=["soccer_"])
    assert pl.select_sports(catalog,config) == ["soccer_epl","soccer_mexico_ligamx","tennis","basketball_nba"]


def test_league_outside_provider_catalog_is_uncovered_not_stale(monkeypatch):
    from types import SimpleNamespace
    from qf.ingest import propline_ingest as pi, odds_worker
    rows = [dict(match_id="m1", odds_api_key="soccer_epl"), dict(match_id="m2", odds_api_key="soccer_denmark_superliga"),
            dict(match_id="m3", odds_api_key="soccer_la_liga")]
    monkeypatch.setattr(pi, "query", lambda *a, **k: rows)
    monkeypatch.setattr(pi, "settings", SimpleNamespace(propline_archive="x"))
    monkeypatch.setattr(odds_worker, "match_meta", lambda ids: {})
    catalog = [dict(key="soccer_epl"), dict(key="soccer_la_liga")]
    def newest(root, path, as_of, **kw):
        if path == "/v1/sports":
            return (catalog, {"received_at": "x"}) if catalog is not None else (None, None)
        return None, None
    monkeypatch.setattr(pi, "newest", newest)
    result = pi._ingest_hourly(None, NOW)
    assert result["sin_cobertura"] == ["soccer_denmark_superliga"]
    assert sorted(result["stale_sports"]) == ["soccer_epl", "soccer_la_liga"]
    catalog = None  # sin catálogo no se puede afirmar cobertura: todo cuenta como atrasado
    result = pi._ingest_hourly(None, NOW)
    assert result["sin_cobertura"] == [] and len(result["stale_sports"]) == 3


def two_way_event(sport, home, away, **extra):
    def market(key, outcomes):
        return dict(key=key, period=None, team=None, line_type="main", outcomes=outcomes)
    def out(name, side, price, point=None, updated="2026-10-23T21:20:00Z"):
        return dict(name=name, side=side, price=price, point=point, player_id=None,
                    book_updated_at=updated, last_seen_at="2026-10-23T21:29:00Z")
    return dict(id="g1", sport_key=sport, commence_time="2026-10-24T01:00:00Z", home_team=home, away_team=away,
        bookmakers=[dict(key="pinnacle", markets=[
            market("h2h", [out(home, "home", -150), out(away, "away", 130)]),
            market("spreads", [out(home, "home", -110, -3.5), out(away, "away", -110, 3.5)]),
            market("totals", [out("Over", None, -105, 221.5), out("Under", None, -115, 221.5)]),
            market("totals", [out("Over", None, -110, 230.5)]),
        ])], **extra)


def test_two_way_feed_nba_keeps_main_pairs_and_drops_one_sided_markets():
    feed = pl.two_way_feed([two_way_event("basketball_nba", "Boston Celtics", "New York Knicks")],
                           "2026-10-23T21:30:00Z")
    markets = {(m["key"], m["outcomes"][0].get("point")): m for m in feed[0]["bookmakers"][0]["markets"]}
    assert set(m for m, _ in markets) == {"h2h", "spreads", "totals"} and (("totals", 230.5) not in markets)
    h2h = markets[("h2h", None)]
    assert [o["name"] for o in h2h["outcomes"]] == ["Boston Celtics", "New York Knicks"]
    assert round(h2h["outcomes"][0]["price"], 3) == 1.667 and h2h["last_update"] == "2026-10-23T21:20:00Z"
    assert feed[0]["_provider"] == "propline" and feed[0]["bookmakers"][0]["last_update"] == "2026-10-23T21:20:00Z"


def test_two_way_feed_never_invents_last_update():
    e = two_way_event("tennis", "Player A", "Player B")
    for market in e["bookmakers"][0]["markets"]:
        for o in market["outcomes"]:
            o["book_updated_at"] = None
    feed = pl.two_way_feed([e], "2026-10-23T21:30:00Z")
    book = feed[0]["bookmakers"][0]
    assert "last_update" not in book and all("last_update" not in m for m in book["markets"])


def test_two_way_feed_skips_periods_player_props_and_started_games():
    e = two_way_event("basketball_nba", "A", "B")
    e["bookmakers"][0]["markets"][0]["period"] = "1h"
    e["bookmakers"][0]["markets"][1]["outcomes"][0]["player_id"] = "p1"
    keys = {m["key"] for m in pl.two_way_feed([e], "2026-10-23T21:30:00Z")[0]["bookmakers"][0]["markets"]}
    assert keys == {"totals"}
    assert pl.two_way_feed([e], "2026-10-24T01:30:00Z") == []


def test_read_two_way_is_offline_point_in_time_and_sport_limited(tmp_path):
    c, calls = client(tmp_path, data=[two_way_event("basketball_nba", "Boston Celtics", "New York Knicks")])
    c.capture("/v1/sports/basketball_nba/odds")
    feed, receipt = pl.read_two_way(tmp_path, "basketball_nba", NOW)
    assert receipt is not None and feed[0]["home_team"] == "Boston Celtics" and len(calls) == 1
    assert pl.read_two_way(tmp_path, "basketball_nba", NOW - timedelta(seconds=1)) == (None, None)
    with pytest.raises(ValueError):
        pl.read_two_way(tmp_path, "soccer_epl", NOW)


REAL_COLLECTOR = pl.Collector


def settlement_run(tmp_path, monkeypatch, scores, *, results=None, budget=None, sports=("basketball_nba",),
                   stats_prefixes=(), injuries=(), settle_extra=None):
    """One collector run against a fake provider; returns the provider calls."""
    calls = []
    def get(path, params, key):
        calls.append((path, params))
        if path == "/v1/sports":
            body = [dict(key=s, active=True) for s in sports]
        elif path.endswith("/scores"):
            body = scores
        elif path.endswith("/ids"):
            body = [dict(id=e["id"], books={"pinnacle": {}} if e["id"] == "2" else {}) for e in scores]
        elif path.endswith("/odds/closing"):
            body = dict(id=path.split("/")[5], bookmakers=[])
        elif path.endswith("/stats"):
            body = dict(id=path.split("/")[5], status="final", stats=[])
        elif path.endswith("/injuries"):
            body = dict(sport=path.split("/")[3], count=1, players=[dict(player_name="A", status_code="out")])
        elif path.endswith("/results"):
            body = results if results is not None else dict(bookmakers=[dict(key="fanduel", markets=[dict(
                key="player_points", outcomes=[dict(name="Over", resolution="won", actual_value=31)])])])
        else:
            body = []
        return 200, {"X-Daily-Remaining": "4900", "X-Daily-Reset": "1792800000"}, json.dumps(body).encode()
    monkeypatch.setattr(pl, "Collector", lambda root, key, **kw: REAL_COLLECTOR(root, key, get=get, **kw))
    key_file = tmp_path / "key"; key_file.write_text("A" * 32)
    config = dict(sports=list(sports), daily_cap=4500, account_reserve=500, scores=True, scores_every_hours=1, identities_daily=True,
                  markets_by_family=dict(default=["h2h"], basketball_=["h2h", "player_points"]),
                  injuries_sports=list(injuries),
                  settlement=dict(enabled=True, min_hours_after_start=6, daily_budget=budget or {"basketball_nba": 100},
                                  stats_prefixes=list(stats_prefixes), **(settle_extra or {})))
    config_file = tmp_path / "config.json"; config_file.write_text(json.dumps(config))
    report = pl.run(tmp_path / "archive", key_file, config_file)
    return calls, report


def ago(hours):
    return pl.stamp(datetime.now(timezone.utc) - timedelta(hours=hours))


def settlement_paths(calls):
    return [p for p, _ in calls if p.endswith(("/odds/closing", "/results"))]


def test_closing_and_results_are_captured_once_for_finished_events(tmp_path, monkeypatch):
    scores = [dict(id="1", status="final", commence_time=ago(10)), dict(id="2", status="final", commence_time=ago(2)),
              dict(id="3", status="in_progress", commence_time=ago(9)), dict(id="4", status="retired", commence_time=ago(9)),
              dict(id="../x", status="final", commence_time=ago(9))]
    calls, report = settlement_run(tmp_path, monkeypatch, scores)
    assert sorted(settlement_paths(calls)) == [
        "/v1/sports/basketball_nba/events/1/odds/closing", "/v1/sports/basketball_nba/events/1/results",
        "/v1/sports/basketball_nba/events/4/odds/closing"]
    assert dict(calls)["/v1/sports/basketball_nba/events/1/odds/closing"] == dict(markets="h2h,player_points", period="all")
    assert report["settlement"]["basketball_nba"] == dict(closing=2, results=1, stats=0, over_budget=0)
    assert report["failures"] == 0
    calls, _ = settlement_run(tmp_path, monkeypatch, scores)
    assert settlement_paths(calls) == []


def test_settlement_budget_favours_most_quoted_event_and_is_reserved(tmp_path, monkeypatch):
    scores = [dict(id="1", status="final", commence_time=ago(20)), dict(id="2", status="final", commence_time=ago(10))]
    calls, report = settlement_run(tmp_path, monkeypatch, scores, budget={"basketball_nba": 1})
    assert settlement_paths(calls) == ["/v1/sports/basketball_nba/events/2/odds/closing"]
    assert report["settlement"]["basketball_nba"]["over_budget"] == 3
    monkeypatch.undo()
    c, _ = client(tmp_path / "cap")
    c.capture("/v1/sports/basketball_nba/odds", {"a": 1}, cap=1)
    with pytest.raises(pl.BudgetStop, match="local_daily_cap"):
        c.capture("/v1/sports/basketball_nba/odds", {"a": 2}, cap=1)


def test_soccer_settlement_only_for_listed_leagues_and_without_graded_props(tmp_path, monkeypatch):
    """24-oct-2026: J-League, Conference y Saudí gastaban el presupuesto antes de llegar a la Premier."""
    scores = [dict(id="1", status="final", commence_time=ago(10))]
    calls, report = settlement_run(
        tmp_path, monkeypatch, scores, sports=("soccer_japan_j_league", "soccer_epl"), budget={"soccer_": 100},
        settle_extra=dict(sports_by_prefix={"soccer_": ["soccer_epl"]}, results_prefixes=["basketball_nba"]))
    assert settlement_paths(calls) == ["/v1/sports/soccer_epl/events/1/odds/closing"]
    assert "soccer_japan_j_league" not in report["settlement"]
    # Sin las claves nuevas se comporta como antes: todas las del prefijo, con resultados.
    (tmp_path / "antes").mkdir()
    calls, _ = settlement_run(tmp_path / "antes", monkeypatch, scores, sports=("soccer_japan_j_league", "soccer_epl"),
                              budget={"soccer_": 100})
    assert len(settlement_paths(calls)) == 4


def test_competitions_outside_priority_are_captured_every_few_hours():
    config = dict(priority_sports=["basketball_nba", "tennis_", "soccer_epl"])
    assert pl.priority_sport("soccer_epl", config) and pl.priority_sport("tennis_atp_paris", config)
    assert not pl.priority_sport("soccer_japan_j_league", config)
    assert not pl.priority_sport("soccer_epl_women", config)      # exacto, no prefijo
    assert pl.priority_sport("soccer_japan_j_league", {})         # sin lista: todas cada hora


def test_hourly_run_skips_other_competitions_off_the_hour(tmp_path, monkeypatch):
    calls, _ = settlement_run(tmp_path, monkeypatch, [], sports=("soccer_epl", "soccer_japan_j_league"),
                              budget={"soccer_": 10})
    assert {p.split("/")[3] for p, _ in calls if p.endswith("/odds")} == {"soccer_epl", "soccer_japan_j_league"}
    hora = datetime.now(timezone.utc).hour
    if hora == 0:
        pytest.skip("a las 00 UTC toca cualquier cadencia")
    cada = 3 if hora % 3 else 7 if hora % 7 else 5           # una cadencia que NO toca esta hora
    (tmp_path / "b").mkdir()
    monkeypatch.setattr(pl, "run", lambda root, key_file, config_file, **kw: REAL_RUN(
        root, key_file, _con(config_file, priority_sports=["soccer_epl"], other_sports_every_hours=cada), **kw))
    calls, _ = settlement_run(tmp_path / "b", monkeypatch, [], sports=("soccer_epl", "soccer_japan_j_league"),
                              budget={"soccer_": 10})
    assert {p.split("/")[3] for p, _ in calls if p.endswith("/odds")} == {"soccer_epl"}


REAL_RUN = pl.run


def _con(config_file, **extra):
    config = json.loads(config_file.read_text())
    config.update(extra)
    config_file.write_text(json.dumps(config))
    return config_file


def test_redacted_results_stop_further_results_that_day(tmp_path, monkeypatch):
    scores = [dict(id="1", status="final", commence_time=ago(20)), dict(id="2", status="final", commence_time=ago(10))]
    calls, _ = settlement_run(tmp_path, monkeypatch, scores, results=dict(redacted=True, bookmakers=[]))
    assert len([p for p in settlement_paths(calls) if p.endswith("/results")]) == 1
    assert len([p for p in settlement_paths(calls) if p.endswith("/odds/closing")]) == 2


def test_ungraded_results_are_retried_on_a_later_day_only(tmp_path):
    c, _ = client(tmp_path)
    path = "/v1/sports/tennis/events/7/results"
    pending = dict(bookmakers=[dict(markets=[dict(outcomes=[dict(name="Over", resolution=None)])])])
    c.get = lambda p, params, key: (200, {"X-Daily-Remaining": "4900"}, json.dumps(pending).encode())
    row, _ = c.capture(path, daily=True)
    assert row["events"] == 1 and row["error"] is None
    midnight = NOW.replace(hour=0, minute=0, second=0, microsecond=0)
    today, tomorrow = pl.stamp(midnight), pl.stamp(midnight + timedelta(days=1))
    assert not pl.settlement_due(c.db, tmp_path, path, today, 3)
    assert pl.settlement_due(c.db, tmp_path, path, tomorrow, 3)
    assert not pl.settlement_due(c.db, tmp_path, path, tomorrow, 1)
    closing = "/v1/sports/tennis/events/7/odds/closing"
    c.get = lambda p, params, key: (200, {"X-Daily-Remaining": "4900"}, b'{"bookmakers": []}')
    c.capture(closing, daily=True)
    assert not pl.settlement_due(c.db, tmp_path, closing, tomorrow, 3)


def test_discovered_market_starting_with_digit_is_requested(tmp_path, monkeypatch):
    calls = []
    def get(path, params, key):
        calls.append((path, params))
        if path == "/v1/sports":
            body = [dict(key="soccer_epl", active=True), dict(key="9bad", active=True)]
        elif path.endswith("/markets"):
            body = [dict(key="2plus_goals", outcomes_count=3), dict(key="h2h", outcomes_count=3)]
        elif path.endswith("/odds"):
            body = [event()]
        else:
            body = []
        return 200, {"X-Daily-Remaining": "4900", "X-Daily-Reset": "1792800000"}, json.dumps(body).encode()
    original = pl.Collector
    monkeypatch.setattr(pl, "Collector", lambda root, key, **kw: original(root, key, get=get, **kw))
    key_file = tmp_path / "key"; key_file.write_text("A" * 32)
    config = dict(sports="all_active", daily_cap=4500, account_reserve=500,
                  markets_by_family=dict(default=["h2h"], soccer_=["h2h", "totals"]))
    config_file = tmp_path / "config.json"; config_file.write_text(json.dumps(config))
    pl.run(tmp_path / "archive", key_file, config_file)
    requested = [p["markets"] for path, p in calls if path == "/v1/sports/soccer_epl/odds"]
    assert any("2plus_goals" in m.split(",") for m in requested)
    assert not any("9bad" in path for path, _ in calls)


def test_shipped_config_keeps_settlement_inside_the_daily_cap():
    from pathlib import Path
    config = json.loads((Path(__file__).resolve().parents[1] / "scripts" / "propline_shared_config.json").read_bytes())
    families, settle = config["markets_by_family"], config["settlement"]
    # server, 24-oct-2026: hourly odds, daily ids/futures/markets, scores; plus the hourly NBA injury report
    measured_daily = 129 * 24 + 110 + 4 * 33 + 24 * len(config.get("injuries_sports", []))
    assert measured_daily + sum(settle["daily_budget"].values()) <= config["daily_cap"]
    assert all(len(keys) <= 50 for keys in families.values())  # one closing call per event
    assert {"player_aces", "player_double_faults", "player_games_won", "player_break_points_won",
            "total_aces"} <= set(families["tennis"])
    assert {"player_points_10plus", "player_points_15plus"} <= set(families["basketball_"])
    # Six more soccer keys would add one hourly batch per competition (+744 calls/day);
    # they arrive through the daily per-fixture discovery instead.
    assert len(pl.market_batches("soccer_epl", families["soccer_"], config)) == 3


def test_hourly_cap_reserves_only_the_unspent_settlement_budget(tmp_path, monkeypatch):
    scores = [dict(id="1", status="final", commence_time=ago(20))]
    calls, report = settlement_run(tmp_path, monkeypatch, scores, budget={"basketball_nba": 4496})
    # Cap 4 for hourly calls: catalog, two odds batches and scores; ids is refused.
    assert report["stop"] == "local_daily_cap" and not [p for p, _ in calls if p.endswith("/ids")]
    assert settlement_paths(calls) == ["/v1/sports/basketball_nba/events/1/odds/closing",
                                       "/v1/sports/basketball_nba/events/1/results"]
    # Next run: 6 calls today, reserve left 4494, hourly cap 6. Nothing is sent.
    calls, report = settlement_run(tmp_path, monkeypatch, scores, budget={"basketball_nba": 4496})
    assert report["stop"] == "local_daily_cap" and calls == []


# --- Box score, injury report and offline readers -------------------------------------------------

def closing_doc(kickoff="2026-10-23T19:00:00Z"):
    return dict(id="42", sport_key="soccer_epl", home_team="Arsenal", away_team="Chelsea", commence_time=kickoff,
        bookmakers=[dict(key="pinnacle", markets=[dict(key="totals", period=None, team="Arsenal", line_type="main",
            outcomes=[dict(name="Over", price=-120, point=1.5, closing_at="2026-10-23T18:59:00Z", is_stale=False,
                           opening_price=105, opening_point=1.5, opening_at="2026-10-20T10:00:00Z", outcome_id=7)])])])


def test_box_score_and_injury_report_are_archived_with_their_shape(tmp_path):
    c, _ = client(tmp_path, data=dict(id="42", status="final", stats=[dict(stat_type="corners")]))
    r, _ = c.capture("/v1/sports/soccer_epl/events/42/stats", daily=True)
    assert (r["status"], r["error"], r["events"]) == (200, None, 1)
    c, _ = client(tmp_path / "inj", data=dict(sport="basketball_nba", count=2, players=[{}, {}]))
    r, _ = c.capture("/v1/sports/basketball_nba/injuries")
    assert (r["events"], r["error"]) == (2, None)
    with pytest.raises(ValueError, match="unsupported"):
        c.capture("/v1/sports/basketball_nba/events/1/odds/history")


def test_box_score_uses_only_what_closing_and_results_leave(tmp_path, monkeypatch):
    scores = [dict(id="1", status="final", commence_time=ago(10)), dict(id="2", status="final", commence_time=ago(12))]
    calls, report = settlement_run(tmp_path, monkeypatch, scores, budget={"basketball_nba": 5},
                                   stats_prefixes=["basketball_nba"])
    paths = [p for p, _ in calls if p.endswith(("/odds/closing", "/results", "/stats"))]
    assert paths == ["/v1/sports/basketball_nba/events/2/odds/closing", "/v1/sports/basketball_nba/events/2/results",
                     "/v1/sports/basketball_nba/events/2/stats", "/v1/sports/basketball_nba/events/1/odds/closing",
                     "/v1/sports/basketball_nba/events/1/results"]
    assert report["settlement"]["basketball_nba"] == dict(closing=2, results=2, stats=1, over_budget=1)
    (tmp_path / "off").mkdir()
    calls, _ = settlement_run(tmp_path / "off", monkeypatch, scores)
    assert not [p for p, _ in calls if p.endswith("/stats")]


def test_injury_report_is_captured_hourly_and_read_point_in_time(tmp_path, monkeypatch):
    calls, report = settlement_run(tmp_path, monkeypatch, [], injuries=["basketball_nba"])
    assert [p for p, _ in calls if p.endswith("/injuries")] == ["/v1/sports/basketball_nba/injuries"]
    root = tmp_path / "archive"
    players, receipt = pl.read_injuries(root, "basketball_nba", datetime.now(timezone.utc))
    assert players[0]["status_code"] == "out" and players[0]["received_at"] == receipt["received_at"]
    assert pl.read_injuries(root, "basketball_nba", datetime.now(timezone.utc) - timedelta(hours=1)) == (None, None)


def test_read_closing_keeps_team_total_and_flags_a_capture_before_kickoff(tmp_path):
    c, _ = client(tmp_path, data=closing_doc(kickoff="2026-10-23T22:00:00Z"))
    c.capture("/v1/sports/soccer_epl/events/42/odds/closing", daily=True)
    rows, receipt = pl.read_closing(tmp_path, "soccer_epl", "42", NOW + timedelta(days=3))
    assert len(rows) == 1 and rows[0]["team"] == "Arsenal" and rows[0]["opening_price"] == 105
    assert rows[0]["price_decimal"] == pytest.approx(1 + 100 / 120)
    assert "pre_kickoff_capture" in rows[0]["flags"]
    assert pl.read_closing(tmp_path, "soccer_epl", "42", NOW - timedelta(seconds=1)) == (None, None)


def test_read_results_flattens_provider_grading(tmp_path):
    c, _ = client(tmp_path, data=dict(id="42", status="final", bookmakers=[dict(key="pinnacle", markets=[dict(
        key="totals", team="Arsenal", outcomes=[dict(name="Over", point=1.5, resolution="won", actual_value=2.0)])])]))
    c.capture("/v1/sports/soccer_epl/events/42/results", daily=True)
    rows, _ = pl.read_results(tmp_path, "soccer_epl", "42", NOW)
    assert [(r["team"], r["resolution"], r["actual_value"]) for r in rows] == [("Arsenal", "won", 2.0)]


def team_rows(*pairs):
    return [dict(player_name=n, team_abbr="", stat_type=t, stat_value=v) for n, t, v in pairs]


def test_team_stats_match_accented_names_and_never_guess():
    doc = dict(home_team="Tigre", away_team="Atletico Tucuman", stats=team_rows(
        ("Atlético Tucumán", "corners", 4.0), ("Tigre", "cards", 2.0)) + [
        dict(player_name="Bruno Leyes", team_abbr="TIG", stat_type="yellow_cards", stat_value=1.0)])
    assert pl.team_stats(doc) == {"away": {"corners": 4.0}, "home": {"cards": 2.0}}
    third = dict(doc, stats=doc["stats"] + team_rows(("Club Desconocido", "corners", 9.0)))
    assert pl.team_stats(third) == {}


@pytest.mark.parametrize("home, away, names", [
    ("Ipswich", "Nottingham Forest", ("Ipswich Town", "Nottingham Forest")),
    ("Brisbane Roar", "Perth Glory", ("Brisbane Roar FC", "Perth Glory FC")),
    ("Stuttgart", "Borussia M'gladbach", ("VfB Stuttgart", "Borussia Mönchengladbach")),
    ("Western Sydney", "Auckland FC", ("Western Sydney Wanderers FC", "Auckland FC")),
    ("Gimnasia y Esgrima La Plata", "CA Sarmiento Junin", ("Gimnasia La Plata", "Sarmiento (Junín)")),
])
def test_team_stats_pairs_differently_spelled_clubs(home, away, names):
    doc = dict(home_team=home, away_team=away, stats=team_rows((names[0], "corners", 5.0), (names[1], "corners", 3.0)))
    assert pl.team_stats(doc) == {"home": {"corners": 5.0}, "away": {"corners": 3.0}}


def test_team_stats_refuses_when_both_names_fit_one_side_or_none_fits():
    # "Real Madrid" contains "Madrid" and so does "Atletico Madrid" for an event side "Madrid": ambiguous.
    doc = dict(home_team="Madrid", away_team="Getafe", stats=team_rows(("Real Madrid", "corners", 5.0),
                                                                       ("Atletico Madrid", "corners", 3.0)))
    assert pl.team_stats(doc) == {}
    doc = dict(home_team="Palmeiras-SP", away_team="Fluminense-RJ", stats=team_rows(("Alpha", "corners", 1.0),
                                                                                     ("Beta", "corners", 2.0)))
    assert pl.team_stats(doc) == {}
