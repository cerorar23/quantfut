"""T3 (2026-11-09): ¿el reparto del uso cuando falta un anotador mejora los puntos esperados de sus compañeros?

Uso: python apps/nba/ops/evaluar_reparto_uso.py [--archivo ...player_games.jsonl.gz]
Datos: `player_games.jsonl.gz` (2024-25 y 2025-26, temporada regular, filas con DNP incluidas). Para cada jugador que
juega, previo = media de puntos de sus últimas 10 filas jugadas. Ausente relevante = compañero con previo de minutos
>= 25 y de puntos >= 12 que no participó. Puntos perdidos L = suma de los previos de puntos de los ausentes;
cuota s_i = previo_i / suma de previos de los que juegan. Predicción: previo_i + alfa * s_i * L, alfa por mínimos
cuadrados con 2024-25 y juicio en 2025-26, solo en jugadores con previo de minutos >= 15 y partidos con L > 0.
Quién está ausente se toma de la participación real: en la práctica sale del parte de lesiones horas antes, pero este
archivo no trae su hora (limitación). Criterio fijado antes de medir: entra si el MAE de prueba baja con IC95 por
bootstrap de partidos entero bajo cero.
"""
import argparse
import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd

ARCHIVO = Path(__file__).resolve().parents[1] / ".local" / "normalized" / "player_games.jsonl.gz"
REPLICAS = 2000


def cargar(ruta: Path) -> pd.DataFrame:
    with gzip.open(ruta, "rt", encoding="utf-8") as f:
        d = pd.DataFrame(json.loads(x) for x in f)
    d = d[d.season_type == "regular"].copy()
    d["date"] = pd.to_datetime(d["date"])
    d["jugo"] = d.participated & d.minutes.notna() & (d.minutes > 0)
    d = d.sort_values(["player_id", "date", "game_id"]).reset_index(drop=True)
    for col, ventana in (("points", 10), ("minutes", 10)):
        s = d[col].where(d.jugo)
        d["prev_" + col] = s.groupby(d.player_id).transform(lambda x: x.shift(1).rolling(ventana, min_periods=5).mean())
    return d


def construir(d: pd.DataFrame) -> pd.DataFrame:
    rel = d.prev_minutes.ge(25) & d.prev_points.ge(12)
    aus = d[rel & ~d.jugo].groupby(["game_id", "team_id"]).prev_points.sum().rename("L")
    juegan = d[d.jugo & d.prev_points.notna()].groupby(["game_id", "team_id"]).prev_points.sum().rename("suma_juegan")
    j = d[d.jugo & d.prev_minutes.ge(15) & d.prev_points.notna()].join(aus, on=["game_id", "team_id"]) \
        .join(juegan, on=["game_id", "team_id"])
    j = j[j.L.notna() & (j.L > 0)].copy()
    j["x"] = j.prev_points / j.suma_juegan * j.L
    j["res"] = j.points - j.prev_points
    return j


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archivo", type=Path, default=ARCHIVO)
    j = construir(cargar(ap.parse_args().archivo))
    ent, prb = j[j.season == "2024-25"], j[j.season == "2025-26"]
    alfa = float((ent.x * ent.res).sum() / (ent.x ** 2).sum())
    mae0, mae1 = np.abs(prb.res).to_numpy(), np.abs(prb.res - alfa * prb.x).to_numpy()
    diff = mae1 - mae0
    _, inv = np.unique(prb.game_id.to_numpy(), return_inverse=True)
    k, s, n = inv.max() + 1, np.bincount(inv, weights=diff), np.bincount(inv)
    rng = np.random.default_rng(20261109)
    m = [s[i].sum() / n[i].sum() for i in (rng.integers(0, k, k) for _ in range(REPLICAS))]
    print(json.dumps({"n_entreno": len(ent), "n_prueba": len(prb), "partidos_prueba": int(k),
                      "alfa": round(alfa, 3), "L_medio_prueba": round(float(prb.L.mean()), 2),
                      "sesgo_prueba_sin_ajuste": round(float(prb.res.mean()), 3),
                      "mae_previo": round(float(mae0.mean()), 4), "mae_con_reparto": round(float(mae1.mean()), 4),
                      "dif_mae": round(float(diff.mean()), 5),
                      "ic95": [round(float(np.percentile(m, 2.5)), 5), round(float(np.percentile(m, 97.5)), 5)],
                      "entra": bool(np.percentile(m, 97.5) < 0)}, indent=1))


if __name__ == "__main__":
    main()
