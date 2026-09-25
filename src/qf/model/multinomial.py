"""Challengers multinomiales interpretables para 1X2; nunca se activan solos."""
from __future__ import annotations

import pickle
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ..eval.metrics import brier, ece, log_loss, rps
from .features import FEATURE_GROUPS


MARKET_FEATURES = ["market_log_home_draw", "market_log_away_draw"]


def prepare_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Añade una parametrización estable del mercado sin margen."""
    out = df.sort_values(["kickoff_utc", "match_id"]).reset_index(drop=True).copy()
    for col in ("mk_home", "mk_draw", "mk_away"):
        if col not in out:
            out[col] = np.nan
    mk = out[["mk_home", "mk_draw", "mk_away"]].to_numpy(dtype=float)
    sums = np.nansum(mk, axis=1, keepdims=True)
    mk = np.divide(mk, sums, out=np.full_like(mk, np.nan), where=sums > 0)
    out[["mk_home", "mk_draw", "mk_away"]] = mk
    out["market_log_home_draw"] = np.log(
        np.clip(out["mk_home"], 1e-6, 1) / np.clip(out["mk_draw"], 1e-6, 1))
    out["market_log_away_draw"] = np.log(
        np.clip(out["mk_away"], 1e-6, 1) / np.clip(out["mk_draw"], 1e-6, 1))
    return out


def _metrics(probs: np.ndarray, outcomes: np.ndarray) -> dict:
    onehot = np.zeros_like(probs)
    onehot[np.arange(len(outcomes)), outcomes] = 1.0
    return {
        "rps": round(rps(probs, outcomes), 5),
        "log_loss": round(log_loss(probs, outcomes), 5),
        "brier": round(brier(probs, outcomes), 5),
        "ece": round(ece(probs.ravel(), onehot.ravel()), 5),
    }


def _pipeline(c: float, penalty: str = "l1") -> Pipeline:
    kwargs = {"solver": "saga", "penalty": penalty, "C": float(c),
              "max_iter": 2500, "random_state": 0, "tol": 1e-4}
    if penalty == "elasticnet":
        kwargs["l1_ratio"] = 0.5
    return Pipeline([
        ("impute", SimpleImputer(strategy="median", add_indicator=True)),
        ("scale", StandardScaler()),
        ("model", LogisticRegression(**kwargs)),
    ])


@dataclass
class ChallengerParams:
    features: list[str]
    anchored_to_market: bool
    penalty: str
    c: float
    n_fit: int
    offline_validated: bool = False


class MultinomialChallenger:
    def __init__(self, pipeline: Pipeline | None = None,
                 params: ChallengerParams | None = None):
        self.pipeline = pipeline
        self.params = params

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        if self.pipeline is None or self.params is None:
            raise RuntimeError("Challenger no ajustado")
        raw = self.pipeline.predict_proba(frame[self.params.features])
        classes = self.pipeline.named_steps["model"].classes_
        out = np.zeros((len(frame), 3), dtype=float)
        for i, cls in enumerate(classes):
            out[:, int(cls)] = raw[:, i]
        return out / out.sum(axis=1, keepdims=True)

    def save(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"pipeline": self.pipeline,
                         "params": asdict(self.params) if self.params else None}, f)

    @classmethod
    def load(cls, path: str) -> "MultinomialChallenger":
        with open(path, "rb") as f:
            data = pickle.load(f)
        params = ChallengerParams(**data["params"]) if data["params"] else None
        return cls(data["pipeline"], params)


def _feature_names(groups: tuple[str, ...], anchored: bool) -> list[str]:
    unknown = set(groups) - set(FEATURE_GROUPS)
    if unknown:
        raise ValueError(f"Grupos de features desconocidos: {sorted(unknown)}")
    names = [name for group in groups for name in FEATURE_GROUPS[group]]
    return (MARKET_FEATURES if anchored else []) + names


def fit_and_validate(
    df: pd.DataFrame,
    groups: tuple[str, ...] = ("elo", "rest", "form", "shots"),
    anchored: bool = False,
    penalty: str = "l1",
    holdout_frac: float = 0.30,
    min_fit: int = 800,
    min_val: int = 300,
    c_grid: tuple[float, ...] = (0.03, 0.10, 0.30, 1.0),
) -> tuple[MultinomialChallenger | None, dict]:
    """Selecciona regularización temporalmente y evalúa en un holdout final."""
    frame = prepare_frame(df)
    features = _feature_names(groups, anchored)
    required = ["outcome", *features]
    # Las features deportivas se imputan, pero el challenger anclado no puede
    # entrenarse si no existe un mercado completo para esa fila.
    usable = frame.dropna(subset=["outcome"])
    if anchored:
        usable = usable.dropna(subset=MARKET_FEATURES +
                               ["mk_home", "mk_draw", "mk_away"])
    usable = usable.reset_index(drop=True)
    cut = int(len(usable) * (1.0 - holdout_frac))
    if cut < min_fit or len(usable) - cut < min_val:
        return None, {"ok": False, "reason": (
            f"Datos insuficientes: {cut} fit y {len(usable) - cut} validación; "
            f"se exigen {min_fit}/{min_val}."), "features": features}

    train, val = usable.iloc[:cut], usable.iloc[cut:]
    inner_cut = max(int(len(train) * 0.8), 1)
    inner_train, inner_val = train.iloc[:inner_cut], train.iloc[inner_cut:]
    y_train = inner_train["outcome"].to_numpy(dtype=int)
    y_inner = inner_val["outcome"].to_numpy(dtype=int)

    candidates: list[tuple[float, float, Pipeline]] = []
    for c in c_grid:
        model = _pipeline(c, penalty)
        model.fit(inner_train[features], y_train)
        score = log_loss(model.predict_proba(inner_val[features]), y_inner)
        candidates.append((score, c, model))
    _, best_c, _ = min(candidates, key=lambda x: x[0])

    pipeline = _pipeline(best_c, penalty)
    pipeline.fit(train[features], train["outcome"].to_numpy(dtype=int))
    params = ChallengerParams(features, anchored, penalty, float(best_c), len(train))
    challenger = MultinomialChallenger(pipeline, params)
    predicted = challenger.predict_proba(val)
    outcomes = val["outcome"].to_numpy(dtype=int)

    if anchored:
        baseline = val[["mk_home", "mk_draw", "mk_away"]].to_numpy(dtype=float)
        baseline_name = "market"
    else:
        baseline = val[["p_home", "p_draw", "p_away"]].to_numpy(dtype=float)
        baseline = baseline / baseline.sum(axis=1, keepdims=True)
        baseline_name = "dixon_coles"
    before, after = _metrics(baseline, outcomes), _metrics(predicted, outcomes)

    leagues_improved = 0
    league_report = {}
    for league, idx in val.groupby("league_id").groups.items():
        positions = val.index.get_indexer(idx)
        # val conserva índices del frame; get_indexer devuelve posiciones locales.
        bp, ap, oc = baseline[positions], predicted[positions], outcomes[positions]
        br, ar = rps(bp, oc), rps(ap, oc)
        improved = ar < br
        leagues_improved += int(improved)
        league_report[str(league)] = {"n": int(len(positions)),
                                      "rps_before": round(br, 5),
                                      "rps_after": round(ar, 5),
                                      "improved": bool(improved)}

    offline_ok = bool(after["rps"] < before["rps"]
                      and after["log_loss"] < before["log_loss"]
                      and after["ece"] <= before["ece"]
                      and leagues_improved >= min(2, len(league_report)))
    challenger.params.offline_validated = offline_ok
    report = {
        "ok": offline_ok, "status": "shadow_only", "baseline": baseline_name,
        "anchored_to_market": anchored, "penalty": penalty, "c": best_c,
        # El histórico de football-data solo trae cierres. Este experimento
        # responde si hay información deportiva adicional AL CIERRE, pero no
        # es desplegable a T-60 sin entrenar con snapshots de esa ventana.
        "market_timing": ("closing_odds_diagnostic_only" if anchored
                          else "sports_only"),
        "features": features, "groups": list(groups), "n_fit": int(cut),
        "n_val": int(len(val)), "before": before, "after": after,
        "rps_before": before["rps"], "rps_after": after["rps"],
        "log_loss_before": before["log_loss"],
        "log_loss_after": after["log_loss"], "ece_before": before["ece"],
        "ece_after": after["ece"], "leagues_improved": leagues_improved,
        "by_league": league_report,
        "promotion_blocked_until_clv": True,
    }
    return challenger, report


def run_ablations(df: pd.DataFrame, **kwargs) -> dict:
    """Mercado solo frente a mercado + cada familia de información."""
    reports = {}
    for group in FEATURE_GROUPS:
        _, report = fit_and_validate(df, groups=(group,), anchored=True, **kwargs)
        reports[f"market_plus_{group}"] = report
    _, report = fit_and_validate(
        df, groups=tuple(FEATURE_GROUPS), anchored=True, **kwargs)
    reports["market_plus_all"] = report
    return reports
