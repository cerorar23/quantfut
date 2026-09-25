"""
Baseline Elo estrictamente point-in-time.

No pretende sustituir a Dixon-Coles. Su función es responder una pregunta más
modesta y necesaria: ¿el modelo probabilístico mejora siquiera a un rating
secuencial sencillo? Cada partido se predice antes de actualizar los ratings y
los encuentros con el mismo kickoff se actualizan juntos para que ninguno vea
el resultado de otro que aún no había terminado.

El empate se modela con la extensión de Davidson. La tasa de empate se estima
online por competición; nunca se calcula con el resultado del partido que se
está prediciendo. Los equipos se identifican por ``team_id`` cuando está
disponible, de modo que un club conserva su rating al ascender o jugar una copa.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class EloConfig:
    initial_rating: float = 1500.0
    k_factor: float = 20.0
    home_advantage: float = 65.0
    initial_draw_rate: float = 0.27
    draw_ema_alpha: float = 0.02
    new_team_penalty: float = 60.0
    min_league_teams_for_penalty: int = 8
    inactivity_days: int = 120
    inactivity_regression: float = 0.15
    min_draw_rate: float = 0.12
    max_draw_rate: float = 0.40
    result_delay_hours: float = 2.0


class EloRatings:
    """Rating secuencial con localía, empate y regresión por inactividad."""

    def __init__(self, config: EloConfig | None = None):
        self.config = config or EloConfig()
        self.ratings: dict[str, float] = {}
        self.team_league: dict[str, str] = {}
        self.matches_played: dict[str, int] = {}
        self.last_seen: dict[str, pd.Timestamp] = {}
        self.last_advanced: dict[str, pd.Timestamp] = {}
        self.draw_rates: dict[str, float] = {}

    @staticmethod
    def _team_key(row, side: str) -> str:
        team_id = row.get(f"{side}_team_id")
        if team_id is not None and not pd.isna(team_id):
            return f"id:{int(team_id)}"
        league = row.get(f"{side}_league") or row.get("league_id") or "unknown"
        return f"{league}||{row[f'{side}_team']}"

    def _league_mean(self, league: str) -> float:
        vals = [self.ratings[k] for k, lg in self.team_league.items()
                if lg == league]
        return float(np.mean(vals)) if vals else self.config.initial_rating

    def _ensure(self, key: str, league: str) -> None:
        if key in self.ratings:
            # El club conserva el rating al ascender. La liga doméstica sí se
            # actualiza para que la regresión futura apunte a la media correcta.
            self.team_league[key] = league
            return
        established = sum(1 for lg in self.team_league.values() if lg == league)
        penalty = (self.config.new_team_penalty
                   if established >= self.config.min_league_teams_for_penalty
                   else 0.0)
        self.ratings[key] = self._league_mean(league) - penalty
        self.team_league[key] = league
        self.matches_played[key] = 0

    def _regress_after_inactivity(self, key: str, kickoff: pd.Timestamp) -> None:
        if self.last_advanced.get(key) == kickoff:
            return
        self.last_advanced[key] = kickoff
        previous = self.last_seen.get(key)
        if previous is None or (kickoff - previous).days < self.config.inactivity_days:
            return
        league = self.team_league[key]
        mean = self._league_mean(league)
        w = self.config.inactivity_regression
        self.ratings[key] = (1.0 - w) * self.ratings[key] + w * mean

    def _prepare(self, row) -> tuple[str, str, str, pd.Timestamp]:
        competition = str(row.get("league_id") or "unknown")
        home_league = str(row.get("home_league") or competition)
        away_league = str(row.get("away_league") or competition)
        home_key = self._team_key(row, "home")
        away_key = self._team_key(row, "away")
        kickoff = pd.Timestamp(row["kickoff_utc"])
        if kickoff.tzinfo is None:
            kickoff = kickoff.tz_localize("UTC")
        self._ensure(home_key, home_league)
        self._ensure(away_key, away_league)
        self._regress_after_inactivity(home_key, kickoff)
        self._regress_after_inactivity(away_key, kickoff)
        return home_key, away_key, competition, kickoff

    def predict(self, row) -> dict[str, float | str]:
        home_key, away_key, competition, _ = self._prepare(row)
        rh = self.ratings[home_key]
        ra = self.ratings[away_key]

        # Davidson: nu se parametriza mediante la tasa de empate que tendría
        # un cruce equilibrado. d = nu / (2 + nu).
        draw_rate = float(np.clip(
            self.draw_rates.get(competition, self.config.initial_draw_rate),
            self.config.min_draw_rate, self.config.max_draw_rate,
        ))
        nu = 2.0 * draw_rate / max(1.0 - draw_rate, 1e-9)
        qh = 10.0 ** ((rh + self.config.home_advantage) / 400.0)
        qa = 10.0 ** (ra / 400.0)
        draw_term = nu * math.sqrt(qh * qa)
        denom = qh + qa + draw_term
        probs = np.array([qh, draw_term, qa], dtype=float) / denom
        return {
            "home": float(probs[0]), "draw": float(probs[1]),
            "away": float(probs[2]), "home_rating": float(rh),
            "away_rating": float(ra), "rating_diff": float(
                rh + self.config.home_advantage - ra),
            "home_key": home_key, "away_key": away_key,
            "competition": competition,
        }

    def update(self, row) -> None:
        home_key, away_key, competition, kickoff = self._prepare(row)
        hg, ag = int(row["home_goals"]), int(row["away_goals"])
        actual = 1.0 if hg > ag else 0.5 if hg == ag else 0.0
        expected = 1.0 / (1.0 + 10.0 ** (
            (self.ratings[away_key]
             - self.ratings[home_key]
             - self.config.home_advantage) / 400.0
        ))
        # El multiplicador de margen está acotado: evita que una goleada aislada
        # domine el baseline, pero distingue 1-0 de 5-0.
        margin = 1.0 + 0.25 * math.log1p(abs(hg - ag))
        delta = self.config.k_factor * margin * (actual - expected)
        self.ratings[home_key] += delta
        self.ratings[away_key] -= delta
        self.matches_played[home_key] = self.matches_played.get(home_key, 0) + 1
        self.matches_played[away_key] = self.matches_played.get(away_key, 0) + 1
        self.last_seen[home_key] = kickoff
        self.last_seen[away_key] = kickoff

        previous = self.draw_rates.get(competition, self.config.initial_draw_rate)
        is_draw = 1.0 if hg == ag else 0.0
        a = self.config.draw_ema_alpha
        self.draw_rates[competition] = (1.0 - a) * previous + a * is_draw

    def predict_sequential(
        self,
        df: pd.DataFrame,
        output_match_ids: Iterable[str] | None = None,
        start_date: datetime | pd.Timestamp | None = None,
    ) -> pd.DataFrame:
        """Predice antes de actualizar y devuelve un 1X2 por partido."""
        required = {"match_id", "kickoff_utc", "home_team", "away_team",
                    "home_goals", "away_goals", "league_id"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Faltan columnas para Elo: {sorted(missing)}")

        wanted = set(output_match_ids) if output_match_ids is not None else None
        start = pd.Timestamp(start_date) if start_date is not None else None
        if start is not None and start.tzinfo is None:
            start = start.tz_localize("UTC")

        ordered = df.copy()
        ordered["kickoff_utc"] = pd.to_datetime(ordered["kickoff_utc"], utc=True)
        ordered = ordered.sort_values(["kickoff_utc", "match_id"])
        rows: list[dict] = []
        pending: deque[tuple[pd.Timestamp, object]] = deque()

        # El resultado no existe al inicio del partido. Incluso encuentros que
        # empiezan 30 minutos después en la misma liga deben usar el rating y
        # tasa de empate previos. Dos horas es un retraso conservador cuando el
        # histórico carece de timestamp fiable de finalización.
        for kickoff, group in ordered.groupby("kickoff_utc", sort=True):
            while pending and pending[0][0] <= kickoff:
                _, finished = pending.popleft()
                self.update(finished)
            predicted: list[tuple[object, dict]] = []
            for _, row in group.iterrows():
                pred = self.predict(row)
                predicted.append((row, pred))
                should_emit = ((wanted is None or row["match_id"] in wanted)
                               and (start is None or row["kickoff_utc"] >= start))
                if should_emit:
                    hg, ag = int(row["home_goals"]), int(row["away_goals"])
                    rows.append({
                        "match_id": row["match_id"],
                        "kickoff_utc": row["kickoff_utc"],
                        "league_id": row["league_id"],
                        "elo_p_home": pred["home"],
                        "elo_p_draw": pred["draw"],
                        "elo_p_away": pred["away"],
                        "elo_home_rating": pred["home_rating"],
                        "elo_away_rating": pred["away_rating"],
                        "elo_diff": pred["rating_diff"],
                        "outcome": 0 if hg > ag else 1 if hg == ag else 2,
                    })
            for row, _ in predicted:
                pending.append((kickoff + timedelta(hours=self.config.result_delay_hours),
                                row))
        while pending:
            _, finished = pending.popleft()
            self.update(finished)
        return pd.DataFrame(rows)


def sequential_elo(
    df: pd.DataFrame,
    output_match_ids: Iterable[str] | None = None,
    start_date=None,
    config: EloConfig | None = None,
) -> pd.DataFrame:
    """Atajo funcional usado por entrenamiento, pruebas y análisis."""
    return EloRatings(config).predict_sequential(df, output_match_ids, start_date)
