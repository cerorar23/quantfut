"""El experimento no ve cierre ni resultado al elegir y conserva la vara."""
import pandas as pd

from qf.eval import sharp_challengers as challengers


def _raw(close=(2.0, 3.4, 4.0), goals=(2, 1)):
    return pd.DataFrame([
        {"league_id": "gb.premier_league",
         "Date": (pd.Timestamp("2024-08-03") + pd.Timedelta(weeks=w)).strftime("%d/%m/%Y"),
         "HomeTeam": "Home", "AwayTeam": "Away", "FTHG": goals[0],
         "FTAG": goals[1], "PSH": 2.0, "PSD": 3.4, "PSA": 4.0,
         "PSCH": close[0], "PSCD": close[1], "PSCA": close[2],
         "AvgH": 1.98, "AvgD": 3.35, "AvgA": 3.9,
         "B365H": 2.2, "B365D": 3.3, "B365A": 3.8}
        for w in range(10)
    ])


def test_comparacion_usa_las_mismas_filas_y_una_vara_fija():
    report = challengers.compare(_raw(), {"sha256": "test"}, ("bet365",))
    methods = report["methods"]
    assert {methods[m]["calibration"]["n_matches"] for m in methods} == {10}
    assert report["close_reference"] == "pinnacle_shin_constant"
    assert methods["shin"]["variants"]["0.02"]["n"] == 10
    assert methods["shin"]["variants"]["0.02"]["new_matches_vs_2pct"] == 0


def test_cierre_y_resultado_no_cambian_la_seleccion():
    base = challengers.compare(_raw(), {"sha256": "a"}, ("bet365",))
    changed = challengers.compare(_raw(close=(1.8, 3.6, 4.6), goals=(0, 2)),
                                  {"sha256": "b"}, ("bet365",))
    for method in challengers.METHODS:
        a = base["methods"][method]["variants"]["0.02"]
        b = changed["methods"][method]["variants"]["0.02"]
        assert a["n"] == b["n"]
        assert a["edge_early"] == b["edge_early"]
        assert a["ev_close"] != b["ev_close"]


def test_umbral_dinamico_prefijado_es_solo_experimental():
    price = pd.Series([1.4, 2.0, 5.0])
    assert challengers._threshold(price, "dynamic_v1").tolist() == [0.015, 0.02, 0.03]
