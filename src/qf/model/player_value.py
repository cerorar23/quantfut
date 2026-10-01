"""
Fuerza por jugador, Fase B1: comparación offline de brazos del XI.

Diseño: docs/superpowers/specs/2026-09-29-fuerza-por-jugador-design.md.
Tres brazos sobre las MISMAS filas y la misma base (walk-forward guardado
por `train.py`): XI simple, XI con valor y XI con nota. "XI con valor" solo
se valida si pasa las exigencias de siempre Y mejora RPS y log-loss del XI
simple. La sombra en vivo es la Fase B2, con su propio plan.
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
from .player_ratings import NOTA_FEATURES, VALOR_FEATURES, build_value_features

log = logging.getLogger(__name__)


def comparar(frame: pd.DataFrame, rho: float) -> tuple[dict, dict]:
    comun = frame.dropna(subset=["base_lam", "base_mu", "home_goals", "away_goals",
                                 *lc.LINEUP_FEATURES, *VALOR_FEATURES]).copy()
    comun[NOTA_FEATURES] = comun[NOTA_FEATURES].astype(float)
    informe, modelos = {"n_filas": int(len(comun))}, {}
    for nombre, senales in (("simple", lc.LINEUP_FEATURES), ("valor", VALOR_FEATURES),
                            ("nota", NOTA_FEATURES)):
        modelo, rep = lc.fit_and_validate(comun, rho=rho, features=senales)
        informe[nombre], modelos[nombre] = rep, modelo
    s, v = informe["simple"], informe["valor"]
    gana = bool(v.get("ok") and "rps_after" in s
                and v["rps_after"] < s["rps_after"]
                and v["log_loss_after"] < s["log_loss_after"])
    informe["valor"]["gana_al_simple"] = gana
    if modelos["valor"] is not None:
        modelos["valor"].params.offline_validated = gana
    if modelos["nota"] is not None:
        # La nota del proveedor es solo comparación: nunca se valida.
        modelos["nota"].params.offline_validated = False
    return informe, modelos


def _conjunto(oos: pd.DataFrame) -> pd.DataFrame:
    base, _ = lc.load_training_frame(oos)
    if base.empty:
        return base
    matches = pd.DataFrame(query(
        """SELECT m.match_id, m.kickoff_utc, m.home_team_id, m.away_team_id
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
    valor = build_value_features(matches, lineups[["match_id", "side", "starters"]], stats,
                                 vida_media_dias=settings.decay_halflife_days)
    return base.merge(valor, on="match_id", how="inner")


def evaluar(oos: pd.DataFrame, rho: float, version: str,
            carpeta: str | None = None) -> dict:
    frame = _conjunto(oos)
    if frame.empty:
        return {"ok": False, "status": "collecting", "reason": "Sin filas con XI y valor"}
    informe, modelos = comparar(frame, rho)
    carpeta = carpeta or settings.artifact_dir
    for nombre, prefijo in (("valor", "lineup_valor"), ("nota", "lineup_nota")):
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
