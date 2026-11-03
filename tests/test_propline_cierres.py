from datetime import datetime, timezone

from qf.eval.cierre import ESPERA_CIERRE_H, cierre_o_vencido
from qf.ingest import propline_cierres as pc

KO = datetime(2026, 10, 23, 19, 0, tzinfo=timezone.utc)


def _o(name, price, point=None, seen="2026-10-23T19:00:00Z", closing="2026-10-23T18:57:08Z", stale=False):
    return dict(name=name, price=price, point=point, closing_at=closing, closing_last_seen_at=seen,
                is_stale=stale, book_updated_at=None)


def _doc(*markets, book="pinnacle"):
    return dict(id="372845", home_team="Ipswich", away_team="Nottingham Forest",
                commence_time="2026-10-23T19:00:00Z", bookmakers=[dict(key=book, markets=list(markets))])


H2H = dict(key="h2h", period=None, team=None, line_type="main", outcomes=[
    _o("Ipswich Town", 221), _o("Nottingham Forest", 131), _o("Draw", 249, closing="2026-10-23T18:41:37Z")])


def test_side_of_matches_long_book_names_and_rejects_doubt():
    assert pc.side_of("Ipswich Town", "Ipswich", "Nottingham Forest") == "home"
    assert pc.side_of("Draw", "Ipswich", "Nottingham Forest") == "draw"
    assert pc.side_of("Manchester", "Manchester City", "Manchester United") is None


def test_one_captured_at_per_match_so_devig_sees_the_whole_group():
    rows, at = pc.close_rows(_doc(H2H), "m1", KO, {"pinnacle"})
    assert {r[3] for r in rows} == {"home", "away", "draw"}
    assert {r[6] for r in rows} == {at} and at == KO
    assert all(r[8] == "close" and r[9] == "propline" and r[7] == 0 for r in rows)
    assert round(dict((r[3], r[5]) for r in rows)["home"], 2) == 3.21


def test_lines_not_seen_near_kickoff_or_stale_are_not_a_close():
    viejo = dict(H2H, outcomes=[_o("Ipswich Town", 221, seen="2026-10-23T18:30:00Z")])
    assert pc.close_rows(_doc(viejo), "m1", KO, {"pinnacle"}) == ([], None)
    rancio = dict(key="spreads", period=None, team=None, line_type="alternate",
                  outcomes=[_o("Ipswich Town", -408, 1.5, stale=True)])
    assert pc.close_rows(_doc(rancio), "m1", KO, {"pinnacle"}) == ([], None)


def test_markets_map_to_the_hourly_keys():
    mk = [dict(key="totals", period=None, team=None, description="Total 2.5",
               outcomes=[_o("Over", -119, 2.5), _o("Under", 106, 2.5)]),
          dict(key="totals", period=None, team="Ipswich Town", description="Total 1.5 - Ipswich Town",
               outcomes=[_o("Over", 120, 1.5)]),
          dict(key="team_corners", period=None, team=None, description="Total Corners - Nottingham Forest",
               outcomes=[_o("Under", -110, 4.5)]),
          dict(key="total_cards", period=None, team=None, description="Total Cards",
               outcomes=[_o("Over", -157, 3.5)]),
          dict(key="double_chance", period=None, team=None, description="Double Chance",
               outcomes=[_o("Draw Or Ipswich Town", -149), _o("Ipswich Town Or Nottingham Forest", -292)]),
          dict(key="both_teams_to_score", period=None, team=None, outcomes=[_o("Yes", -140)]),
          dict(key="totals", period="1h", team=None, outcomes=[_o("Over", 100, 1.5)]),
          dict(key="correct_score", period=None, team=None, outcomes=[_o("1-0", 700)])]
    rows, _ = pc.close_rows(_doc(*mk), "m1", KO, {"pinnacle"})
    assert {(r[2], r[3], r[4]) for r in rows} == {
        ("totals", "over", 2.5), ("totals", "under", 2.5), ("team_totals_home", "over", 1.5),
        ("corners_away", "under", 4.5), ("cards", "over", 3.5), ("double_chance", "1X", None),
        ("double_chance", "12", None), ("btts", "yes", None)}


def test_only_configured_books_are_kept():
    assert pc.close_rows(_doc(H2H, book="bovada"), "m1", KO, {"pinnacle"}) == ([], None)


def test_settlement_waits_for_the_close_until_the_deadline():
    sql = cierre_o_vencido("m")
    assert "window_tag = 'close'" in sql and f"interval '{ESPERA_CIERRE_H} hours'" in sql
