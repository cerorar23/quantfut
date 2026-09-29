"""Challenger en sombra para ajustar lambdas con el XI confirmado."""
from __future__ import annotations

import pickle
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from ..db import query
from ..eval.metrics import ece, log_loss, rps
from .pricing import market_1x2, score_matrix


LINEUP_FEATURES = [
    "home_missing_regulars", "away_missing_regulars", "missing_diff",
    "home_lineup_continuity", "away_lineup_continuity", "continuity_diff",
    "home_missing_g", "away_missing_g", "home_missing_d", "away_missing_d",
    "home_missing_m", "away_missing_m", "home_missing_f", "away_missing_f",
]


def _players(starters) -> dict[int, str]:
    out = {}
    for player in starters or []:
        pid = player.get("player_id")
        if pid:
            out[int(pid)] = str(player.get("pos") or "").upper()[:1]
    return out


def build_lineup_features(matches: pd.DataFrame, lineups: pd.DataFrame,
                          lookback: int = 5) -> pd.DataFrame:
    """Reconstruye disponibilidad usando solo XI capturados anteriormente."""
    if matches.empty or lineups.empty:
        return pd.DataFrame(columns=["match_id", *LINEUP_FEATURES])
    ms = matches.copy()
    ms["kickoff_utc"] = pd.to_datetime(ms["kickoff_utc"], utc=True)
    lu = lineups.copy()
    if "captured_at" in lu:
        lu["captured_at"] = pd.to_datetime(lu["captured_at"], utc=True)
    lineup_map = {(r["match_id"], r["side"]): r for _, r in lu.iterrows()}
    histories: dict[object, deque[dict[int, str]]] = defaultdict(
        lambda: deque(maxlen=lookback))
    rows = []

    for kickoff, group in ms.sort_values(["kickoff_utc", "match_id"]).groupby(
            "kickoff_utc", sort=True):
        updates = []
        for _, match in group.iterrows():
            values = {"match_id": match["match_id"],
                      "league_id": match["league_id"]}
            complete = True
            current_by_side = {}
            captured_times = []
            for side in ("home", "away"):
                item = lineup_map.get((match["match_id"], side))
                if item is None or ("captured_at" in item and
                                    pd.Timestamp(item["captured_at"]) > kickoff):
                    complete = False
                    break
                current = _players(item["starters"])
                current_by_side[side] = current
                captured_times.append(pd.Timestamp(item["captured_at"]))
                team_id = match[f"{side}_team_id"]
                history = histories[team_id]
                if len(history) < 3:
                    complete = False
                    continue
                counts: dict[int, int] = {}
                positions: dict[int, str] = {}
                for old in history:
                    for pid, pos in old.items():
                        counts[pid] = counts.get(pid, 0) + 1
                        if pos:
                            positions[pid] = pos
                regulars = {pid for pid, n in counts.items()
                            if n >= 0.6 * len(history)}
                missing = regulars - set(current)
                values[f"{side}_missing_regulars"] = float(len(missing))
                values[f"{side}_lineup_continuity"] = (
                    len(set(current) & set(history[-1])) / max(len(current), 1))
                for pos in "GDMF":
                    values[f"{side}_missing_{pos.lower()}"] = float(
                        sum(positions.get(pid) == pos for pid in missing))
            if complete:
                # Un lado sin hora de captura (XI histórico, db/034) deja la
                # fila sin hora: así nunca pasa por predicción sellada.
                values["feature_as_of"] = (
                    pd.NaT if any(pd.isna(t) for t in captured_times)
                    else max(captured_times))
                values["missing_diff"] = (values["home_missing_regulars"]
                                          - values["away_missing_regulars"])
                values["continuity_diff"] = (values["home_lineup_continuity"]
                                             - values["away_lineup_continuity"])
                rows.append(values)
            if len(current_by_side) == 2:
                updates.append((match["home_team_id"], current_by_side["home"],
                                match["away_team_id"], current_by_side["away"]))
        for home_id, home_xi, away_id, away_xi in updates:
            histories[home_id].append(home_xi)
            histories[away_id].append(away_xi)
    return pd.DataFrame(rows)


def readiness_report(matches: pd.DataFrame, lineups: pd.DataFrame) -> dict:
    if not lineups.empty:
        eligible = set(matches["match_id"]) if "match_id" in matches else set()
        lineups = lineups[lineups["match_id"].isin(eligible)]
    features = build_lineup_features(matches, lineups)
    if lineups.empty or not {"match_id", "side"}.issubset(lineups.columns):
        complete_ids = set()
    else:
        complete_ids = set(lineups.groupby("match_id")["side"].nunique()
                           .loc[lambda s: s >= 2].index)
    by_league = (features.groupby("league_id").size().astype(int).to_dict()
                 if not features.empty else {})
    return {
        "matches_total": int(len(matches)),
        "matches_with_both_lineups": int(len(complete_ids)),
        "matches_with_usable_history": int(len(features)),
        "ready_for_training": bool(len(features) >= 1000),
        "by_league": {str(k): int(v) for k, v in by_league.items()},
    }


@dataclass
class LineupParams:
    medians: list[float]
    scales: list[float]
    beta_home: list[float]
    beta_away: list[float]
    rho: float
    shrink: float
    n_fit: int
    offline_validated: bool = False


class LineupLambdaChallenger:
    def __init__(self, params: LineupParams | None = None):
        self.params = params

    @property
    def is_fitted(self) -> bool:
        return self.params is not None

    def _matrix(self, frame: pd.DataFrame) -> np.ndarray:
        if not self.params:
            raise RuntimeError("Challenger de XI no ajustado")
        x = frame[LINEUP_FEATURES].to_numpy(dtype=float)
        med = np.asarray(self.params.medians)
        x = np.where(np.isnan(x), med, x)
        x = (x - med) / np.asarray(self.params.scales)
        return np.column_stack([np.ones(len(x)), x])

    def apply(self, frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        x = self._matrix(frame)
        bh = np.asarray(self.params.beta_home)
        ba = np.asarray(self.params.beta_away)
        shrink = self.params.shrink
        lam = frame["base_lam"].to_numpy(dtype=float) * np.exp(
            np.clip(shrink * (x @ bh), -1.0, 1.0))
        mu = frame["base_mu"].to_numpy(dtype=float) * np.exp(
            np.clip(shrink * (x @ ba), -1.0, 1.0))
        return lam, mu

    def save(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(asdict(self.params) if self.params else None, f)

    @classmethod
    def load(cls, path: str) -> "LineupLambdaChallenger":
        with open(path, "rb") as f:
            data = pickle.load(f)
        return cls(LineupParams(**data) if data else None)


def _fit_poisson_offset(x: np.ndarray, offset: np.ndarray, y: np.ndarray,
                        l2: float) -> np.ndarray:
    def objective(beta):
        eta = np.clip(offset + x @ beta, -5.0, 5.0)
        return float(np.sum(np.exp(eta) - y * eta) + l2 * np.sum(beta[1:] ** 2))
    result = minimize(objective, np.zeros(x.shape[1]), method="L-BFGS-B")
    if not result.success:
        raise RuntimeError(f"No convergió el ajuste de XI: {result.message}")
    return np.asarray(result.x, dtype=float)


def _probabilities(lam: np.ndarray, mu: np.ndarray,
                   rho: np.ndarray | float) -> np.ndarray:
    rows = []
    rhos = np.broadcast_to(np.asarray(rho, dtype=float), len(lam))
    for la, m, r in zip(lam, mu, rhos):
        p = market_1x2(score_matrix(float(la), float(m), float(r)))
        rows.append([p["home"], p["draw"], p["away"]])
    return np.asarray(rows, dtype=float)


def fit_and_validate(frame: pd.DataFrame, rho: float = 0.0, shrink: float = 0.5,
                     holdout_frac: float = 0.30, min_fit: int = 500,
                     min_val: int = 200, l2: float = 10.0):
    ordered = frame.sort_values(["kickoff_utc", "match_id"]).dropna(
        subset=["base_lam", "base_mu", "home_goals", "away_goals"]
    ).reset_index(drop=True)
    cut = int(len(ordered) * (1.0 - holdout_frac))
    if cut < min_fit or len(ordered) - cut < min_val:
        return None, {"ok": False, "status": "collecting", "reason": (
            f"Alineaciones insuficientes: {cut} fit y {len(ordered)-cut} validación; "
            f"se exigen {min_fit}/{min_val}."), "n": int(len(ordered))}

    train, val = ordered.iloc[:cut], ordered.iloc[cut:]
    raw = train[LINEUP_FEATURES].to_numpy(dtype=float)
    medians = np.nanmedian(raw, axis=0)
    medians = np.where(np.isnan(medians), 0.0, medians)
    filled = np.where(np.isnan(raw), medians, raw)
    scales = np.std(filled, axis=0)
    scales = np.where(scales < 1e-8, 1.0, scales)
    x = np.column_stack([np.ones(len(train)), (filled - medians) / scales])
    bh = _fit_poisson_offset(x, np.log(train["base_lam"].to_numpy()),
                             train["home_goals"].to_numpy(dtype=float), l2)
    ba = _fit_poisson_offset(x, np.log(train["base_mu"].to_numpy()),
                             train["away_goals"].to_numpy(dtype=float), l2)
    model = LineupLambdaChallenger(LineupParams(
        medians.tolist(), scales.tolist(), bh.tolist(), ba.tolist(), float(rho),
        float(shrink), int(cut), False))

    # La rho de cada predicción fue estimada antes de ESE partido. Usar la rho
    # del artefacto entrenado hoy introduciría conocimiento del futuro.
    historical_rho = (val["rho"].to_numpy(dtype=float)
                      if "rho" in val.columns else rho)
    before = _probabilities(val["base_lam"].to_numpy(),
                            val["base_mu"].to_numpy(), historical_rho)
    lam, mu = model.apply(val)
    after = _probabilities(lam, mu, historical_rho)
    outcomes = np.where(val["home_goals"] > val["away_goals"], 0,
                        np.where(val["home_goals"] == val["away_goals"], 1, 2))
    onehot = np.zeros_like(before)
    onehot[np.arange(len(outcomes)), outcomes] = 1.0
    report = {
        "status": "shadow_only", "n_fit": int(cut), "n_val": int(len(val)),
        "rps_before": round(rps(before, outcomes), 5),
        "rps_after": round(rps(after, outcomes), 5),
        "log_loss_before": round(log_loss(before, outcomes), 5),
        "log_loss_after": round(log_loss(after, outcomes), 5),
        "ece_before": round(ece(before.ravel(), onehot.ravel()), 5),
        "ece_after": round(ece(after.ravel(), onehot.ravel()), 5),
        "promotion_blocked_until_clv": True,
    }
    league_report = {}
    improved_leagues = 0
    for league, group in val.groupby("league_id"):
        positions = val.index.get_indexer(group.index)
        old_rps = rps(before[positions], outcomes[positions])
        new_rps = rps(after[positions], outcomes[positions])
        improved_leagues += int(new_rps < old_rps)
        league_report[str(league)] = {
            "n": int(len(positions)), "rps_before": round(old_rps, 5),
            "rps_after": round(new_rps, 5),
            "improved": bool(new_rps < old_rps),
        }
    report["by_league"] = league_report
    report["leagues_improved"] = improved_leagues
    improved = (report["rps_after"] < report["rps_before"]
                and report["log_loss_after"] < report["log_loss_before"]
                and report["ece_after"] <= report["ece_before"]
                and improved_leagues >= 2)
    report["ok"] = bool(improved)
    model.params.offline_validated = bool(improved)
    return model, report


def _historical_matches(oos: pd.DataFrame) -> pd.DataFrame:
    """
    Partidos del walk-forward de `train.py` como base: sus lambdas son fuera
    de muestra (modelo ajustado solo con partidos anteriores), igual de
    honestas que una predicción sellada.
    """
    if oos is None or oos.empty:
        return pd.DataFrame()
    teams = pd.DataFrame(query(
        """SELECT match_id, home_team_id, away_team_id FROM matches
           WHERE match_id = ANY(%s)""", (list(oos["match_id"].dropna()),)))
    if teams.empty:
        return pd.DataFrame()
    cols = ["match_id", "league_id", "kickoff_utc", "home_goals", "away_goals",
            "lam", "mu"] + (["rho"] if "rho" in oos.columns else [])
    out = oos[cols].rename(columns={"lam": "base_lam", "mu": "base_mu"})
    out = out.merge(teams, on="match_id", how="inner")
    out["base_generated_at"] = pd.NaT
    out["fuente"] = "walk_forward"
    return out


def _historical_lineups() -> pd.DataFrame:
    """XI de `lineups_historicas` (db/034). Sin hora de captura: no la tienen."""
    rows = pd.DataFrame(query(
        """SELECT match_id, side, starters FROM lineups_historicas
           WHERE jsonb_array_length(starters) >= 11"""))
    if not rows.empty:
        rows["captured_at"] = pd.NaT
        rows["fuente"] = "historico"
    return rows


def load_training_frame(oos: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    """
    Une predicciones pre-kickoff, resultados y XI.

    En vivo: predicción sellada y XI capturado ANTES del inicio (punto en el
    tiempo estricto). Desde 2026-09-29, con autorización del usuario, también
    las predicciones fuera de muestra del walk-forward (`oos`) con los XI de
    `lineups_historicas`, descargados después del partido. Solo aquí: esos XI
    no llegan nunca a la predicción diaria ni a la sombra.
    """
    matches = pd.DataFrame(query(
        """SELECT DISTINCT ON (m.match_id)
                  m.match_id, m.league_id, m.kickoff_utc,
                  m.home_team_id, m.away_team_id, m.home_goals, m.away_goals,
                  p.home_lambda AS base_lam, p.away_lambda AS base_mu, p.rho,
                  p.generated_at AS base_generated_at
           FROM matches m JOIN predictions p USING (match_id)
           WHERE m.status='finished' AND m.home_goals IS NOT NULL
             AND p.generated_at < m.kickoff_utc
           ORDER BY m.match_id, p.generated_at DESC"""
    ))
    lineups = pd.DataFrame(query(
        """SELECT DISTINCT ON (l.match_id, l.side)
                  l.match_id, l.side, l.starters, l.captured_at
           FROM lineups l JOIN matches m USING (match_id)
           WHERE l.captured_at <= m.kickoff_utc
           ORDER BY l.match_id, l.side, l.captured_at DESC"""
    ))
    if not matches.empty:
        matches["fuente"] = "sellada"
    if not lineups.empty:
        lineups["fuente"] = "en_vivo"
    hist_m, hist_l = _historical_matches(oos), _historical_lineups()
    if not hist_m.empty:
        # Si un partido tiene predicción sellada, manda la sellada.
        hist_m = hist_m[~hist_m["match_id"].isin(
            set(matches["match_id"]) if not matches.empty else set())]
        matches = pd.concat([matches, hist_m], ignore_index=True)
    if not hist_l.empty:
        vivos = (set(zip(lineups["match_id"], lineups["side"]))
                 if not lineups.empty else set())
        hist_l = hist_l[[(m, s) not in vivos
                         for m, s in zip(hist_l["match_id"], hist_l["side"])]]
        lineups = pd.concat([lineups, hist_l], ignore_index=True)
    if matches.empty or lineups.empty:
        return pd.DataFrame(), readiness_report(matches, lineups)
    matches["kickoff_utc"] = pd.to_datetime(matches["kickoff_utc"], utc=True)
    features = build_lineup_features(matches, lineups)
    if features.empty:
        # Nadie tiene aún 3 XI previos: sin columnas, el cruce revienta.
        return pd.DataFrame(), readiness_report(matches, lineups)
    frame = matches.merge(features, on=["match_id", "league_id"], how="inner")
    if not frame.empty:
        frame["base_generated_at"] = pd.to_datetime(
            frame["base_generated_at"], utc=True)
        # Las filas históricas no tienen hora de captura (NaT): sin forzar el
        # tipo, la columna queda como objeto y la comparación revienta.
        frame["feature_as_of"] = pd.to_datetime(frame["feature_as_of"], utc=True)
        # El punto en el tiempo se sigue exigiendo a todo lo sellado en vivo.
        frame = frame[(frame["fuente"] == "walk_forward")
                      | (frame["base_generated_at"] < frame["feature_as_of"])]
    report = readiness_report(matches, lineups)
    report["por_fuente"] = (frame["fuente"].value_counts().astype(int).to_dict()
                            if not frame.empty else {})
    return frame, report
