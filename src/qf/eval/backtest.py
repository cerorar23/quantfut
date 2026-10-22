"""
Backtest walk-forward.

NUNCA uses K-fold aleatorio aquí. Entrenar con partidos de mayo para predecir
partidos de marzo produce métricas espectaculares y completamente falsas.

Protocolo:
  - Ventana expansiva, reentrenando cada `step_days`.
  - En cada paso, el modelo solo ve partidos con kickoff < corte.
  - Se compara contra el cierre sin margen del mercado.

Señal de alarma: si el backtest te da ROI de dos dígitos, NO celebres.
Busca la fuga. Las tres más comunes están listadas en check_leakage().
"""
from __future__ import annotations

import logging
from datetime import timedelta

import numpy as np
import pandas as pd

from ..config import settings
from ..model.devig import devig
from ..model.dixon_coles import DixonColes
from .metrics import evaluate

log = logging.getLogger(__name__)


def walk_forward_oos(df: pd.DataFrame, start_date, step_days: int = 30,
                     min_train: int = 500, halflife: float = 270.0,
                     xg_blend: float = 0.65) -> pd.DataFrame:
    """
    Predicciones FUERA DE MUESTRA, una fila por partido.

    Es la materia prima honesta de todo lo que viene después: el calibrador
    (`model/calibration.py`), el meta-learner y el modelo de residuo. Ajustar
    cualquiera de esos sobre predicciones dentro de muestra produce una capa
    que "corrige" un error que en producción no existe, y hace daño.

    df: columnas kickoff_utc, home_team, away_team, home_goals, away_goals,
        home_xg, away_xg, league_id, y opcionalmente
        home_league/away_league (liga doméstica de cada equipo, distinta de la
        competición solo en las copas europeas) y
        odds_home/odds_draw/odds_away (cierre, para el baseline).
    """
    df = df.sort_values("kickoff_utc").reset_index(drop=True)
    # `start_date` puede llegar con o sin zona horaria: desde `train.py` viene
    # de `df["kickoff_utc"].max()`, que SÍ la trae, y pasar tz= a un Timestamp
    # que ya es consciente de zona revienta. Se normaliza en vez de asumir.
    cutoff = pd.Timestamp(start_date)
    cutoff = (cutoff.tz_localize("UTC") if cutoff.tzinfo is None
              else cutoff.tz_convert("UTC"))
    end = df["kickoff_utc"].max()
    rows = []

    while cutoff < end:
        train = df[df["kickoff_utc"] < cutoff]
        nxt = cutoff + timedelta(days=step_days)
        test = df[(df["kickoff_utc"] >= cutoff) & (df["kickoff_utc"] < nxt)]

        if len(train) < min_train or test.empty:
            cutoff = nxt
            continue

        try:
            m = DixonColes(halflife_days=halflife, xg_blend=xg_blend)
            m.fit(train, as_of=cutoff.to_pydatetime())
        except Exception as exc:  # noqa: BLE001
            log.warning("Ajuste fallido en %s: %s", cutoff.date(), exc)
            cutoff = nxt
            continue

        for _, r in test.iterrows():
            league = r.get("league_id")
            pred = m.predict(r["home_team"], r["away_team"], league,
                             r.get("home_league"), r.get("away_league"))
            p = pred["1x2"]
            hg, ag = int(r["home_goals"]), int(r["away_goals"])

            if all(c in r and pd.notna(r[c]) for c in
                   ("odds_home", "odds_draw", "odds_away")):
                mk = devig([r["odds_home"], r["odds_draw"], r["odds_away"]],
                           settings.devig_method)
            else:
                mk = [np.nan] * 3

            rows.append({
                "match_id": r.get("match_id"),
                "kickoff_utc": r["kickoff_utc"],
                "league_id": league,
                "home_team": r["home_team"],
                "away_team": r["away_team"],
                "p_home": p["home"], "p_draw": p["draw"], "p_away": p["away"],
                # Intensidades sin calibrar: son la entrada del calibrador
                # (`model/calibration.py`), que corrige a este nivel para que
                # los ~150 mercados sigan siendo coherentes entre sí.
                "lam": pred["_meta"]["home_lambda"],
                "mu": pred["_meta"]["away_lambda"],
                # La rho de ESTE paso: el challenger de XI la necesita para no
                # usar la estimada después del partido.
                "rho": m.params.rho,
                "mk_home": mk[0], "mk_draw": mk[1], "mk_away": mk[2],
                "outcome": 0 if hg > ag else 1 if hg == ag else 2,
                "both_known": pred["_meta"]["both_teams_known"],
                "home_goals": hg, "away_goals": ag,
            })

        log.info("Paso %s: train=%d test=%d", cutoff.date(), len(train), len(test))
        cutoff = nxt

    if not rows:
        raise RuntimeError("El backtest no produjo predicciones. Revisa min_train.")
    return pd.DataFrame(rows)


def walk_forward(df: pd.DataFrame, start_date, step_days: int = 30,
                 min_train: int = 500, halflife: float = 270.0,
                 xg_blend: float = 0.65) -> dict:
    """Métricas agregadas del walk-forward. El retorno es JSON-serializable."""
    oos = walk_forward_oos(df, start_date, step_days=step_days,
                           min_train=min_train, halflife=halflife,
                           xg_blend=xg_blend)
    return metrics_from_oos(oos, {"halflife": halflife, "xg_blend": xg_blend,
                                  "step_days": step_days,
                                  "devig": settings.devig_method})


def metrics_from_oos(oos: pd.DataFrame, config: dict | None = None) -> dict:
    """Evalúa un DataFrame de predicciones fuera de muestra."""
    mp = oos[["p_home", "p_draw", "p_away"]].to_numpy(dtype=float)
    kp = oos[["mk_home", "mk_draw", "mk_away"]].to_numpy(dtype=float)
    oc = oos["outcome"].to_numpy(dtype=int)
    valid = ~np.isnan(kp).any(axis=1)

    if valid.any():
        res = evaluate(mp[valid], kp[valid], oc[valid])
        res["n_without_market"] = int((~valid).sum())
    else:
        res = evaluate(mp, None, oc)
    if config:
        res["config"] = config
    return res


def tune_halflife(df: pd.DataFrame, start_date,
                  grid=(90, 120, 180, 250, 365)) -> dict:
    """
    Barrido de la media vida del decaimiento. Es el hiperparámetro con más
    impacto del modelo y el único que vale la pena ajustar a mano.
    """
    out = {}
    for hl in grid:
        try:
            r = walk_forward(df, start_date, halflife=float(hl))
            out[hl] = {"rps": r["rps"], "log_loss": r["log_loss"],
                       "rps_delta_vs_market": r.get("rps_delta")}
            log.info("halflife=%s -> RPS=%.5f", hl, r["rps"])
        except Exception as exc:  # noqa: BLE001
            log.warning("halflife=%s falló: %s", hl, exc)
    best = min(out, key=lambda k: out[k]["rps"]) if out else None
    return {"results": out, "best_halflife": best}


def check_leakage(df: pd.DataFrame) -> list[str]:
    """
    Las tres fugas que arruinan estos backtests, en orden de frecuencia.
    Córrelo antes de creerte cualquier resultado.
    """
    problems = []

    if "xg_recorded_at" in df.columns and "kickoff_utc" in df.columns:
        late = (pd.to_datetime(df["xg_recorded_at"]) >
                pd.to_datetime(df["kickoff_utc"]) + timedelta(hours=6)).sum()
        if late:
            problems.append(
                f"{late} partidos con xG registrado >6h tras el kickoff. "
                "Si esos valores se revisaron, tu histórico contiene información "
                "que no existía en el momento de predecir."
            )

    for c in ("odds_home", "odds_draw", "odds_away"):
        if c in df.columns and "odds_captured_at" not in df.columns:
            problems.append(
                f"La columna {c} no tiene timestamp de captura. No puedes saber "
                "si son cuotas de apertura o de cierre. Trátalas como cierre "
                "(baseline) y nunca como feature de entrenamiento."
            )
            break

    if df["kickoff_utc"].duplicated().sum() > len(df) * 0.5:
        problems.append(
            "Más de la mitad de los kickoff están duplicados exactamente. "
            "Probablemente solo tienes la fecha, no la hora. El orden temporal "
            "dentro de cada jornada será arbitrario."
        )

    if not problems:
        problems.append("Sin fugas evidentes en las comprobaciones automáticas. "
                        "Esto no garantiza que no las haya.")
    return problems
