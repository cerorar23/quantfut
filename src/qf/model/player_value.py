"""
Fuerza por jugador, Fase B1: comparación offline de brazos del XI.

Diseño: docs/superpowers/specs/2026-09-29-fuerza-por-jugador-design.md.
Brazos sobre las MISMAS filas y la misma base (walk-forward guardado por
`train.py`): XI simple, XI con valor, XI con nota y, desde el 3-oct-2026, XI
por más-menos (`masmenos.py`). "XI con valor" y "más-menos" solo se validan
si pasan las exigencias de siempre Y mejoran RPS y log-loss del XI simple.
La sombra en vivo es la Fase B2, con su propio plan.
"""
from __future__ import annotations

import glob
import json
import logging
import os

import pandas as pd

from ..config import settings
from ..db import query
from . import lineup_challenger as lc
from .masmenos import MASMENOS_FEATURES, build_pm_features
from .player_ratings import NOTA_FEATURES, VALOR_FEATURES, build_value_features

log = logging.getLogger(__name__)


BRAZOS = (("simple", lc.LINEUP_FEATURES), ("valor", VALOR_FEATURES),
          ("nota", NOTA_FEATURES), ("masmenos", MASMENOS_FEATURES))
# Los que compiten con el XI simple; la nota es solo comparación.
RETADORES = ("valor", "masmenos")


def comparar(frame: pd.DataFrame, rho: float) -> tuple[dict, dict]:
    # Un brazo sin sus columnas no entra (marcos anteriores al más-menos).
    brazos = [(n, s) for n, s in BRAZOS if set(s) <= set(frame.columns)]
    exigidas = [c for n, s in brazos if n != "nota" for c in s]
    comun = frame.dropna(subset=["base_lam", "base_mu", "home_goals", "away_goals",
                                 *exigidas]).copy()
    comun[NOTA_FEATURES] = comun[NOTA_FEATURES].astype(float)
    informe, modelos = {"n_filas": int(len(comun))}, {}
    for nombre, senales in brazos:
        modelo, rep = lc.fit_and_validate(comun, rho=rho, features=senales)
        informe[nombre], modelos[nombre] = rep, modelo
    s = informe["simple"]
    for nombre in RETADORES:
        if nombre not in informe:
            continue
        r = informe[nombre]
        gana = bool(r.get("ok") and "rps_after" in s
                    and r["rps_after"] < s["rps_after"]
                    and r["log_loss_after"] < s["log_loss_after"])
        informe[nombre]["gana_al_simple"] = gana
        if modelos[nombre] is not None:
            modelos[nombre].params.offline_validated = gana
    if modelos["nota"] is not None:
        # La nota del proveedor es solo comparación: nunca se valida.
        modelos["nota"].params.offline_validated = False
    return informe, modelos


def _conjunto(oos: pd.DataFrame) -> pd.DataFrame:
    base, _ = lc.load_training_frame(oos)
    if base.empty:
        return base
    matches = pd.DataFrame(query(
        """SELECT m.match_id, m.kickoff_utc, m.home_team_id, m.away_team_id,
                  m.home_goals, m.away_goals, m.home_xg, m.away_xg,
                  m.xg_source, m.xg_recorded_at
           FROM matches m JOIN leagues l USING (league_id)
           WHERE l.model_enabled AND m.status = 'finished'
             AND m.kickoff_utc > now() - interval '500 days'"""))
    vivos = pd.DataFrame(query(
        """SELECT DISTINCT ON (l.match_id, l.side) l.match_id, l.side, l.starters
           FROM lineups l JOIN matches m USING (match_id)
           WHERE l.captured_at <= m.kickoff_utc
           ORDER BY l.match_id, l.side, l.captured_at DESC"""))
    historicas = lc._historical_lineups()
    lineups = pd.concat([x for x in (vivos, historicas) if not x.empty], ignore_index=True)
    lineups = lineups.drop_duplicates(subset=["match_id", "side"], keep="first")
    stats = pd.DataFrame(query(
        "SELECT * FROM estadisticas_jugador WHERE minutos > 0"))
    xi = lineups[["match_id", "side", "starters"]]
    valor = build_value_features(matches, xi, stats,
                                 vida_media_dias=settings.decay_halflife_days)
    pm = build_pm_features(matches, xi, stats, vida_media_dias=settings.decay_halflife_days,
                           xg_blend=settings.xg_blend)
    return base.merge(valor, on="match_id", how="inner").merge(pm, on="match_id", how="inner")


def evaluar(oos: pd.DataFrame, rho: float, version: str,
            carpeta: str | None = None) -> dict:
    frame = _conjunto(oos)
    if frame.empty:
        return {"ok": False, "status": "collecting", "reason": "Sin filas con XI y valor"}
    informe, modelos = comparar(frame, rho)
    carpeta = carpeta or settings.artifact_dir
    for nombre, prefijo in (("valor", "lineup_valor"), ("nota", "lineup_nota"),
                            ("masmenos", "lineup_masmenos")):
        if modelos.get(nombre) is not None:
            modelos[nombre].save(f"{carpeta}/{prefijo}_{version}.pkl")
    return informe


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    ruta = max(glob.glob(f"{settings.artifact_dir}/oos_*.pkl"), key=os.path.getmtime)
    version = os.path.basename(ruta)[len("oos_"):-len(".pkl")]
    oos = pd.read_pickle(ruta)
    rho = float(oos["rho"].median())
    print(json.dumps(evaluar(oos, rho, version), indent=2, ensure_ascii=False, default=str))
