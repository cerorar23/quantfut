"""T4 (2026-11-09): ¿el margen esperado explica los minutos de los titulares (paliza = descanso)?

Uso: python apps/nba/ops/evaluar_minutos_margen.py [--archivo ...player_games.jsonl.gz]
Datos: `player_games.jsonl.gz` (2024-25 y 2025-26, temporada regular). Sin spread de apertura en el archivo, el margen
ESPERADO se aproxima con un Elo de equipos construido solo con partidos anteriores (25 puntos Elo ≈ 1 punto de
margen); la ventaja de campo no está en el archivo, así que se usa |Δ Elo|. El margen REAL se reporta como cota
superior (no se conoce antes del partido). Previo de minutos del jugador: media de sus últimos 5 partidos jugados.
Titulares = previo ≥ 24 min. Se ajusta con 2024-25 y se juzga en 2025-26: MAE de minutos con solo intercepto frente
a intercepto + pendiente en |margen|, y pendiente con IC95 por bootstrap de partidos.
Criterio fijado antes de medir: entra si el MAE de prueba baja con IC95 entero bajo cero usando el margen ESPERADO.
"""
import argparse
import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd

ARCHIVO = Path(__file__).resolve().parents[1] / ".local" / "normalized" / "player_games.jsonl.gz"
K_ELO, PTS_POR_ELO, REPLICAS = 20.0, 1 / 25, 2000


def cargar(ruta: Path) -> pd.DataFrame:
    with gzip.open(ruta, "rt", encoding="utf-8") as f:
        d = pd.DataFrame(json.loads(x) for x in f)
    d = d[d.season_type == "regular"].copy()
    d["date"] = pd.to_datetime(d["date"])
    return d


def equipos(d: pd.DataFrame) -> pd.DataFrame:
    """Un renglón por (partido, equipo): puntos, rival, margen real y margen esperado previo (Elo)."""
    t = d.groupby(["game_id", "team_id"], as_index=False).agg(date=("date", "first"), season=("season", "first"),
                                                                pts=("points", "sum"))
    t = t[t.groupby("game_id").team_id.transform("nunique") == 2]
    a = t.merge(t, on="game_id", suffixes=("", "_r"))
    a = a[a.team_id != a.team_id_r].sort_values(["date", "game_id"]).reset_index(drop=True)
    a["margen_real"] = a.pts - a.pts_r
    elo, temp, esp = {}, None, {}
    for r in a.drop_duplicates("game_id").itertuples():       # un paso por partido: ambos equipos se ponen al día JUNTOS
        if r.season != temp:                                  # regresión parcial entre temporadas
            elo = {k: 1500 + 0.75 * (v - 1500) for k, v in elo.items()}
            temp = r.season
        ea, eb = elo.get(r.team_id, 1500.0), elo.get(r.team_id_r, 1500.0)
        esp[(r.game_id, r.team_id)], esp[(r.game_id, r.team_id_r)] = (ea - eb) * PTS_POR_ELO, (eb - ea) * PTS_POR_ELO
        p = 1 / (1 + 10 ** (-(ea - eb) / 400))
        gan = 1.0 if r.margen_real > 0 else 0.0
        mult = (abs(r.margen_real) + 3) ** 0.8 / (7.5 + 0.006 * abs(ea - eb))      # margen de victoria, estilo 538
        delta = K_ELO * mult * (gan - p)
        elo[r.team_id], elo[r.team_id_r] = ea + delta, eb - delta
    a["margen_esperado"] = [esp[(g, t_)] for g, t_ in zip(a.game_id, a.team_id)]
    return a[["game_id", "team_id", "margen_real", "margen_esperado"]]


def jugadores(d: pd.DataFrame, t: pd.DataFrame) -> pd.DataFrame:
    j = d[d.participated & d.minutes.notna() & (d.minutes > 0)].sort_values(["player_id", "date", "game_id"]).copy()
    j["previo"] = j.groupby("player_id").minutes.transform(lambda s: s.shift(1).rolling(5, min_periods=5).mean())
    j = j.merge(t, on=["game_id", "team_id"], how="inner").dropna(subset=["previo"])
    j = j[j.previo >= 24].copy()
    j["res"] = j.minutes - j.previo
    j["abs_esp"], j["abs_real"] = j.margen_esperado.abs(), j.margen_real.abs()
    return j


def ols(x, y):
    X = np.c_[np.ones(len(x)), x]
    return np.linalg.lstsq(X, y, rcond=None)[0]


def evaluar(j: pd.DataFrame, col: str, rng) -> dict:
    ent, prb = j[j.season == "2024-25"], j[j.season == "2025-26"]
    b0 = float(ent.res.mean())
    a, b = ols(ent[col].to_numpy(), ent.res.to_numpy())
    mae0 = np.abs(prb.res - b0).to_numpy()
    mae1 = np.abs(prb.res - (a + b * prb[col])).to_numpy()
    diff, juegos = mae1 - mae0, prb.game_id.to_numpy()
    _, inv = np.unique(juegos, return_inverse=True)
    k, s, n = inv.max() + 1, np.bincount(inv, weights=diff), np.bincount(inv)
    m = [s[i].sum() / n[i].sum() for i in (rng.integers(0, k, k) for _ in range(REPLICAS))]
    return {"n_entreno": len(ent), "n_prueba": len(prb), "pendiente_min_por_punto": round(float(b), 4),
            "mae_solo_intercepto": round(float(mae0.mean()), 4), "mae_con_margen": round(float(mae1.mean()), 4),
            "dif_mae": round(float(diff.mean()), 5),
            "ic95": [round(float(np.percentile(m, 2.5)), 5), round(float(np.percentile(m, 97.5)), 5)],
            "entra": bool(np.percentile(m, 97.5) < 0)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archivo", type=Path, default=ARCHIVO)
    d = cargar(ap.parse_args().archivo)
    j = jugadores(d, equipos(d))
    rng = np.random.default_rng(20261109)
    print(json.dumps({"margen_esperado_elo": evaluar(j, "abs_esp", rng),
                      "margen_real_cota_superior": evaluar(j, "abs_real", rng),
                      "correlacion_esperado_real": round(float(j[["abs_esp", "abs_real"]].corr().iloc[0, 1]), 3)},
                     indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
