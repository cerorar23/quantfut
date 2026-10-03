"""
Más-menos aproximado por minutos (idea 2, 2026-10-03).

Lo que fijan: recupera al jugador que mueve el marcador, la señal es el
rating que falta respecto al XI habitual, y un partido nunca ve partidos
posteriores.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from qf.model import masmenos as mm

ESTRELLA = 1000      # player_id del jugador que suma +0,8 a la diferencia


def _liga(n_equipos: int = 10, dias: int = 400, seed: int = 0, sin_estrella_en=()):
    """
    Cada equipo tiene 14 jugadores y saca 11 al azar; el equipo 0 tiene una
    estrella que juega el 75 % de los partidos y nunca en `sin_estrella_en`.
    Si jugara siempre, su efecto sería inseparable del de su equipo: el
    más-menos solo identifica a un jugador por los partidos que se pierde.
    El objetivo es xG puro (`xg_blend=1`), así que la única señal es quién
    estaba en el campo. Se consume el mismo azar con o sin `sin_estrella_en`.
    """
    rng = np.random.default_rng(seed)
    plantilla = {e: [e * 100 + k for k in range(14)] for e in range(n_equipos)}
    plantilla[0][0] = ESTRELLA
    partidos, stats, xi = [], [], []
    inicio = pd.Timestamp("2024-01-01", tz="UTC")
    for d in range(0, dias, 3):
        orden = rng.permutation(n_equipos)
        for k in range(0, n_equipos, 2):
            h, a = int(orden[k]), int(orden[k + 1])
            mid = f"m{d}_{h}_{a}"
            efecto = {}
            for lado, eq in (("home", h), ("away", a)):
                once = list(rng.choice(plantilla[eq][1:], 10, replace=False))
                suplente = int(rng.choice([p for p in plantilla[eq][1:] if p not in once]))
                juega = rng.random() < 0.75
                if eq == 0 and juega and mid not in sin_estrella_en:
                    once.append(ESTRELLA)
                else:
                    once.append(suplente)
                efecto[lado] = 0.8 * (ESTRELLA in once)
                xi.append({"match_id": mid, "side": lado,
                           "starters": [{"player_id": int(p), "pos": "M"} for p in once]})
                stats += [{"match_id": mid, "side": lado, "player_id": int(p),
                           "minutos": 90} for p in once]
            partidos.append({
                "match_id": mid, "kickoff_utc": inicio + pd.Timedelta(days=d),
                "home_team_id": h, "away_team_id": a, "home_goals": 0, "away_goals": 0,
                "home_xg": 1.4 + efecto["home"] + rng.normal(0, 0.3),
                "away_xg": 1.1 + efecto["away"] + rng.normal(0, 0.3)})
    return pd.DataFrame(partidos), pd.DataFrame(xi), pd.DataFrame(stats)


def test_recupera_al_jugador_que_mueve_el_marcador():
    partidos, _, stats = _liga()
    ratings = mm._Disenio(partidos, stats, xg_blend=1.0).ajustar(
        pd.Timestamp("2025-06-01", tz="UTC"), vida_media_dias=180.0)
    assert max(ratings, key=ratings.get) == ESTRELLA
    assert ratings[ESTRELLA] > 0.3


def test_la_senal_es_el_rating_que_falta_respecto_al_habitual():
    partidos, _, _ = _liga()
    tardio = partidos[(partidos["home_team_id"] == 0)
                      & (partidos["kickoff_utc"] > pd.Timestamp("2024-12-01", tz="UTC"))]
    sin = tardio["match_id"].iloc[0]
    partidos, xi, stats = _liga(sin_estrella_en={sin})
    f = mm.build_pm_features(partidos, xi, stats, xg_blend=1.0).set_index("match_id")
    assert f.loc[sin, "home_d_pm"] < -0.3
    con = tardio["match_id"].iloc[1]
    assert abs(f.loc[con, "home_d_pm"]) < abs(f.loc[sin, "home_d_pm"])


def test_un_partido_no_ve_partidos_posteriores():
    partidos, xi, stats = _liga()
    corte = pd.Timestamp("2024-09-01", tz="UTC")
    antes = mm.build_pm_features(partidos, xi, stats, xg_blend=1.0)
    otro = partidos.copy()
    futuro = otro["kickoff_utc"] >= corte
    otro.loc[futuro, "home_xg"] = 9.0      # el futuro cambia por completo
    despues = mm.build_pm_features(otro, xi, stats, xg_blend=1.0)
    ids = set(partidos.loc[partidos["kickoff_utc"] < corte, "match_id"])
    a = antes[antes["match_id"].isin(ids)].set_index("match_id").sort_index()
    b = despues[despues["match_id"].isin(ids)].set_index("match_id").sort_index()
    assert len(a) > 50
    pd.testing.assert_frame_equal(a, b)


def test_objetivo_usa_goles_donde_falta_el_xg():
    p = pd.DataFrame({"home_goals": [2, 1], "away_goals": [0, 1],
                      "home_xg": [1.0, np.nan], "away_xg": [0.0, np.nan]})
    assert np.allclose(mm.objetivo(p, 0.65), [0.35 * 2 + 0.65 * 1.0, 0.0])


def test_el_masmenos_compite_con_el_simple_sobre_las_mismas_filas(monkeypatch):
    from qf.model import lineup_challenger as lc
    from qf.model.player_ratings import NOTA_FEATURES, VALOR_FEATURES
    from qf.model.player_value import comparar

    vistos = []

    def falso(frame, rho=0.0, features=None, **_):
        vistos.append(len(frame))
        modelo = lc.LineupLambdaChallenger(lc.LineupParams(
            [0.0] * len(features), [1.0] * len(features), [0.0] * (len(features) + 1),
            [0.0] * (len(features) + 1), rho, 0.5, 700, True, list(features)))
        rps = 0.205 if features == mm.MASMENOS_FEATURES else 0.210
        return modelo, {"ok": True, "rps_after": rps, "log_loss_after": 1.04 - (rps < 0.21) * 0.01}

    monkeypatch.setattr(lc, "fit_and_validate", falso)
    n = 400
    rng = np.random.default_rng(0)
    d = pd.DataFrame({"base_lam": 1.4, "base_mu": 1.1, "home_goals": 1, "away_goals": 1},
                     index=range(n))
    for c in lc.LINEUP_FEATURES + VALOR_FEATURES + NOTA_FEATURES + mm.MASMENOS_FEATURES:
        d[c] = rng.normal(size=n)
    d.loc[0, "home_d_pm"] = np.nan
    informe, modelos = comparar(d, rho=-0.05)
    assert informe["n_filas"] == n - 1 and set(vistos) == {n - 1}
    assert informe["masmenos"]["gana_al_simple"] is True
    assert informe["valor"]["gana_al_simple"] is False
    assert modelos["masmenos"].params.offline_validated is True
