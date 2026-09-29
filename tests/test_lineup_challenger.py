from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from qf.model.lineup_challenger import build_lineup_features, readiness_report


def _data(n=8):
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    matches, lineups = [], []
    regular = [{"player_id": i, "pos": "G" if i == 1 else "D" if i < 6
                else "M" if i < 9 else "F"} for i in range(1, 12)]
    for i in range(n):
        match_id, ko = f"m{i}", start + timedelta(days=7 * i)
        matches.append({"match_id": match_id, "league_id": "L",
                        "kickoff_utc": ko, "home_team_id": 1,
                        "away_team_id": 2})
        home = regular if i < n - 1 else regular[1:] + [{"player_id": 99, "pos": "F"}]
        lineups.extend([
            {"match_id": match_id, "side": "home", "starters": home,
             "captured_at": ko - timedelta(minutes=60)},
            {"match_id": match_id, "side": "away", "starters": regular,
             "captured_at": ko - timedelta(minutes=60)},
        ])
    return pd.DataFrame(matches), pd.DataFrame(lineups)


def test_xi_actual_no_entra_en_su_propia_historia():
    matches, lineups = _data()
    features = build_lineup_features(matches, lineups)
    last = features.loc[features["match_id"] == "m7"].iloc[0]
    assert last["home_missing_regulars"] == 1
    assert last["home_missing_g"] == 1


def test_readiness_no_aprueba_muestra_pequena():
    matches, lineups = _data()
    report = readiness_report(matches, lineups)
    assert report["matches_with_both_lineups"] == len(matches)
    assert not report["ready_for_training"]


# ---------------------------------------------------------------------------
# XI históricos (db/034, autorizado por el usuario 2026-09-29)
# ---------------------------------------------------------------------------

def _consultas_falsas(monkeypatch, selladas, en_vivo, historicas, equipos):
    from qf.model import lineup_challenger as lc

    def q(sql, params=()):
        if "FROM lineups_historicas" in sql:
            return historicas
        if "JOIN predictions" in sql:
            return selladas
        if "FROM lineups l" in sql:
            return en_vivo
        if "home_team_id, away_team_id FROM matches" in sql:
            return equipos
        raise AssertionError(sql)
    monkeypatch.setattr(lc, "query", q)
    return lc


def test_el_walk_forward_con_xi_historico_entra_y_lo_sellado_sigue_estricto(monkeypatch):
    matches, lineups = _data(8)
    oos = matches.assign(home_goals=1, away_goals=0, lam=1.4, mu=1.1, rho=-0.05)
    historicas = [{"match_id": r["match_id"], "side": r["side"], "starters": r["starters"]}
                  for _, r in lineups.iterrows()]
    equipos = matches[["match_id", "home_team_id", "away_team_id"]].to_dict("records")
    # m7 además tiene predicción sellada, pero con su XI capturado DESPUÉS
    # de la predicción no: la regla estricta la descarta como sellada.
    sellada = {**matches.iloc[7].to_dict(), "home_goals": 1, "away_goals": 0,
               "base_lam": 1.3, "base_mu": 1.0, "rho": -0.05,
               "base_generated_at": matches.iloc[7]["kickoff_utc"] - timedelta(hours=10)}
    lc = _consultas_falsas(monkeypatch, [sellada], [], historicas, equipos)
    frame, report = lc.load_training_frame(oos)
    assert set(frame["fuente"]) == {"walk_forward"}, "m7 sellada sin XI en vivo no entra"
    assert "m7" not in set(frame["match_id"])
    assert len(frame) == 4                      # m3..m6: 3 XI previos de historia
    assert frame["rho"].notna().all()


def test_sin_walk_forward_no_se_usan_xi_historicos(monkeypatch):
    matches, lineups = _data(8)
    historicas = [{"match_id": r["match_id"], "side": r["side"], "starters": r["starters"]}
                  for _, r in lineups.iterrows()]
    lc = _consultas_falsas(monkeypatch, [], [], historicas, [])
    frame, _ = lc.load_training_frame(None)
    assert frame.empty


def test_un_lado_historico_no_se_cuela_como_sellado(monkeypatch):
    matches, lineups = _data(8)
    ko7 = matches.iloc[7]["kickoff_utc"]
    en_vivo = [{"match_id": r["match_id"], "side": r["side"], "starters": r["starters"],
                "captured_at": r["captured_at"]}
               for _, r in lineups.iterrows() if not (r["match_id"] == "m7" and r["side"] == "away")]
    historicas = [{"match_id": "m7", "side": "away",
                   "starters": lineups.iloc[-1]["starters"]}]
    selladas = [{**r.to_dict(), "home_goals": 1, "away_goals": 0, "base_lam": 1.3,
                 "base_mu": 1.0, "rho": -0.05,
                 "base_generated_at": r["kickoff_utc"] - timedelta(hours=10)}
                for _, r in matches.iterrows()]
    lc = _consultas_falsas(monkeypatch, selladas, en_vivo, historicas, [])
    frame, _ = lc.load_training_frame(None)
    assert {"m3", "m4", "m5", "m6"} <= set(frame["match_id"])
    assert "m7" not in set(frame["match_id"]), "XI visitante histórico: no es sellada"
    assert ko7 is not None
