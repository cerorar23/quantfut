"""Ejecución y liquidación de challengers sin publicar ni apostar."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import settings
from ..db import conn, execute, query, query_one
from ..ingest.lineups import availability
from ..eval.cierre import cierre_o_vencido, es_cierre_real
from .devig import consensus_devig, devig
from .lineup_challenger import LINEUP_FEATURES, LineupLambdaChallenger
from .market_anchor import anchor_from_consensus
from .pricing import market_1x2, score_matrix

log = logging.getLogger(__name__)


def select_h2h_candidates(probs: dict[str, float], quotes: list[dict],
                          shrinkage: float, min_edge_pct: float) -> list[dict]:
    """Elige la mejor cuota por selección; solo registra, nunca crea un pick."""
    best: dict[str, dict] = {}
    for quote in quotes:
        selection = quote["selection"]
        if selection not in probs:
            continue
        if selection not in best or float(quote["price"]) > float(best[selection]["price"]):
            best[selection] = quote
    out = []
    for selection, quote in best.items():
        raw = (float(probs[selection]) * float(quote["price"]) - 1.0) * 100.0
        edge = raw * shrinkage
        if edge >= min_edge_pct:
            out.append({"market": "h2h", "selection": selection, "line": None,
                        "model_prob": float(probs[selection]),
                        "observed_price": float(quote["price"]),
                        "bookmaker": quote["bookmaker"], "raw_edge_pct": raw,
                        "edge_pct": edge})
    return out


def _features_from_availability(data: dict) -> dict | None:
    if not data or "home" not in data or "away" not in data:
        return None
    values = {}
    for side in ("home", "away"):
        item = data[side]
        if item.get("missing_regulars") is None:
            return None
        values[f"{side}_missing_regulars"] = float(item["missing_regulars"])
        values[f"{side}_lineup_continuity"] = float(item.get("lineup_continuity", np.nan))
        by_pos = item.get("missing_by_position") or {}
        for pos in "GDMF":
            values[f"{side}_missing_{pos.lower()}"] = float(by_pos.get(pos, 0))
    values["missing_diff"] = (values["home_missing_regulars"]
                              - values["away_missing_regulars"])
    values["continuity_diff"] = (values["home_lineup_continuity"]
                                 - values["away_lineup_continuity"])
    return values


def _quotes(match_id: str, lineup_as_of) -> list[dict]:
    return query(
        """SELECT DISTINCT ON (bookmaker, selection)
                  bookmaker, selection, price, captured_at
           FROM odds_snapshots
           WHERE match_id=%s AND market='h2h' AND window_tag='post_xi'
             AND mins_to_kickoff >= 15
             AND captured_at >= %s
             AND captured_at >= now() - interval '15 minutes'
           ORDER BY bookmaker, selection, captured_at DESC""",
        (match_id, lineup_as_of),
    )


def _market_anchor(quotes: list[dict], rho: float):
    """
    Intensidades IMPLÍCITAS EN EL MERCADO a partir de las cuotas posteriores al
    XI. Devuelve None si no se pueden obtener; nunca un apaño.

    Es el ancla del punto 2.B del plan de fase 2. `meta.py` midió w_model =
    0.0001: el nivel lo sabe mejor el mercado, así que ajustar por el XI unas
    lambdas propias solo mueve una estimación peor. Anclando en el mercado, el
    ajuste de XI es lo ÚNICO que separa al challenger del precio vigente, y la
    comparación responde justo la pregunta que importa: ¿el XI añade algo a lo
    que el mercado ya ha preciado?
    """
    by_book: dict[str, dict[str, float]] = {}
    for q in quotes:
        by_book.setdefault(q["bookmaker"], {})[q["selection"]] = float(q["price"])
    cons = consensus_devig(by_book, method=settings.devig_method,
                           sharp_book=settings.sharp_book)
    fit = anchor_from_consensus(cons, rho=rho)
    if fit is None or not fit.usable:
        # El mercado cotiza algo que la familia Dixon-Coles no representa. No
        # hay ancla; registrar el arma igualmente falsearía la comparación.
        return None
    return fit


def _complete_quotes(quotes: list[dict]) -> list[dict]:
    books = {q["bookmaker"] for q in quotes}
    complete = {book for book in books
                if {q["selection"] for q in quotes if q["bookmaker"] == book}
                == {"home", "draw", "away"}}
    return [q for q in quotes if q["bookmaker"] in complete]


def _insert_shadow(match: dict, version: str, lam: float, mu: float,
                   rho: float, probs: dict, features: dict,
                   challenger_name: str = "lineup_lambda",
                   quotes: list[dict] | None = None) -> str | None:
    # Si todavía no existe una cuota posterior al XI, espera al próximo ciclo.
    # Insertar primero la predicción bloquearía el reintento por el UNIQUE y
    # dejaría el partido sin CLV medible.
    quotes = _complete_quotes(
        quotes if quotes is not None else _quotes(match["match_id"], match["as_of"]))
    if not quotes:
        return None
    candidates = select_h2h_candidates(
        probs, quotes, settings.edge_shrinkage, settings.min_edge_pct)
    # Igual que la selección publicada, un solo lado por encuentro: evita
    # contar varias apuestas correlacionadas como evidencia independiente.
    candidates = sorted(candidates, key=lambda c: -c["edge_pct"])[:1]
    # Predicción y selecciones se guardan en una sola transacción. Si falla una
    # inserción, no queda una predicción huérfana cuyo UNIQUE bloquee reintentos.
    with conn() as c, c.cursor() as cur:
        cur.execute(
            """INSERT INTO shadow_predictions
                 (match_id, base_prediction_id, challenger, model_version,
                  as_of, home_lambda, away_lambda, rho, probabilities, features)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (match_id, challenger, model_version) DO NOTHING
               RETURNING shadow_prediction_id""",
            (match["match_id"], match["prediction_id"], challenger_name, version,
             match["as_of"], lam, mu, rho, json.dumps(probs),
             json.dumps(features)),
        )
        row = cur.fetchone()
        if not row:
            return None
        shadow_id = str(row["shadow_prediction_id"])
        for candidate in candidates:
            cur.execute(
                """INSERT INTO shadow_picks
                     (shadow_prediction_id, match_id, market, selection, line,
                      model_prob, observed_price, bookmaker, raw_edge_pct,
                      edge_pct)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (shadow_id, match["match_id"], candidate["market"],
                 candidate["selection"], candidate["line"],
                 candidate["model_prob"], candidate["observed_price"],
                 candidate["bookmaker"], candidate["raw_edge_pct"],
                 candidate["edge_pct"]),
            )
    return shadow_id


def _challenger_validado(version: str):
    """
    El challenger del modelo activo; si no existe (un reentreno no promovido
    guarda el suyo con otra versión), el último validado fuera de muestra.
    Sus coeficientes ajustan log(lambda) sobre cualquier base, así que siguen
    valiendo con el modelo activo.
    """
    carpeta = Path(settings.artifact_dir)
    propio = carpeta / f"lineup_{version}.pkl"
    candidatos = ([propio] if propio.exists() else []) + sorted(
        carpeta.glob("lineup_*.pkl"), key=lambda p: p.stat().st_mtime, reverse=True)
    for ruta in candidatos:
        challenger = LineupLambdaChallenger.load(str(ruta))
        # Los brazos de la fuerza por jugador (lineup_valor_, lineup_nota_)
        # comparten prefijo pero usan otras señales: no son el XI simple.
        if (challenger.params and challenger.params.offline_validated
                and challenger.params.features == LINEUP_FEATURES):
            return challenger
    return None


def capture_lineup_shadows() -> dict:
    """Registra base y, si existe, XI sobre las mismas cuotas posteriores al XI."""
    active = query_one("SELECT model_version FROM model_artifacts WHERE is_active LIMIT 1")
    if not active:
        return {"captured": 0, "reason": "sin modelo activo"}
    version = active["model_version"]
    challenger = _challenger_validado(version)

    matches = query(
        """SELECT DISTINCT ON (m.match_id)
                  m.match_id, m.kickoff_utc, p.prediction_id,
                  p.home_lambda AS base_lam, p.away_lambda AS base_mu, p.rho,
                  (SELECT max(l.captured_at) FROM lineups l
                   WHERE l.match_id=m.match_id) AS as_of
           FROM matches m
           JOIN predictions p USING (match_id)
           WHERE p.etapa = 'diaria' AND m.status='scheduled' AND m.kickoff_utc > now()
             AND m.kickoff_utc < now() + interval '100 minutes'
             AND (SELECT count(DISTINCT l.side) FROM lineups l
                  WHERE l.match_id=m.match_id) = 2
             AND p.generated_at < (SELECT max(l.captured_at) FROM lineups l
                                    WHERE l.match_id=m.match_id)
           ORDER BY m.match_id, p.generated_at DESC"""
    )
    baseline_captured, lineup_captured = 0, 0
    market_captured, market_xi_captured = 0, 0
    for match in matches:
        quotes = _complete_quotes(_quotes(match["match_id"], match["as_of"]))
        if not quotes:
            continue
        base_prob = market_1x2(score_matrix(
            float(match["base_lam"]), float(match["base_mu"]),
            float(match["rho"])))
        if _insert_shadow(match, version, float(match["base_lam"]),
                          float(match["base_mu"]), float(match["rho"]),
                          base_prob, {"baseline": "pre_xi_model_at_t60"},
                          challenger_name="baseline_t60", quotes=quotes):
            baseline_captured += 1
        # Ancla de mercado: control y base del arma anclada. Se registra aunque
        # no haya challenger, porque por sí sola ya contesta cuánto de la
        # diferencia venía del modelo y cuánto del precio.
        anchor = _market_anchor(quotes, float(match["rho"]))
        if anchor is not None:
            p_mkt = market_1x2(score_matrix(anchor.lam, anchor.mu,
                                            float(match["rho"])))
            if _insert_shadow(match, version, anchor.lam, anchor.mu,
                              float(match["rho"]), p_mkt,
                              {"baseline": "market_implied_at_post_xi",
                               "anchor_residual": anchor.residual},
                              challenger_name="baseline_market", quotes=quotes):
                market_captured += 1

        if challenger is None:
            continue
        features = _features_from_availability(availability(match["match_id"]))
        if features is None:
            continue
        frame = pd.DataFrame([{**features, "base_lam": match["base_lam"],
                               "base_mu": match["base_mu"]}])
        lam, mu = challenger.apply(frame)
        p = market_1x2(score_matrix(float(lam[0]), float(mu[0]), float(match["rho"])))
        if _insert_shadow(match, version, float(lam[0]), float(mu[0]),
                          float(match["rho"]), p, features,
                          quotes=quotes):
            lineup_captured += 1

        # El mismo ajuste de XI, pero sobre el nivel del MERCADO. Las cuatro
        # armas sobre las mismas cuotas y el mismo partido hacen que la
        # comparación aísle una sola cosa cada vez:
        #   modelo            -> modelo+XI      : ¿el XI aporta?
        #   mercado           -> mercado+XI     : ¿aporta SOBRE lo ya preciado?
        #   modelo            -> mercado        : cuánto de la diferencia era nivel
        if anchor is not None:
            frame_m = pd.DataFrame([{**features, "base_lam": anchor.lam,
                                     "base_mu": anchor.mu}])
            lam_m, mu_m = challenger.apply(frame_m)
            p_m = market_1x2(score_matrix(float(lam_m[0]), float(mu_m[0]),
                                          float(match["rho"])))
            if _insert_shadow(match, version, float(lam_m[0]), float(mu_m[0]),
                              float(match["rho"]), p_m,
                              {**features, "anchor": "market"},
                              challenger_name="lineup_lambda_market",
                              quotes=quotes):
                market_xi_captured += 1

    result = {"baseline_captured": baseline_captured,
              "lineup_captured": lineup_captured,
              "market_captured": market_captured,
              "market_xi_captured": market_xi_captured,
              "eligible_matches": len(matches), "version": version,
              "lineup_challenger_available": challenger is not None}
    log.info("Challenger en sombra: %s", result)
    return result


def _closing(match_id: str) -> dict[str, float]:
    rows = query(
        f"""SELECT DISTINCT ON (selection) selection, price
           FROM odds_snapshots
           WHERE match_id=%s AND market='h2h' AND mins_to_kickoff >= 0
             AND window_tag='close' AND {es_cierre_real()} AND bookmaker=%s
           ORDER BY selection, captured_at DESC""",
        (match_id, settings.sharp_book),
    )
    return {r["selection"]: float(r["price"]) for r in rows}


def settle_pending() -> dict:
    rows = query(
        f"""SELECT sp.shadow_pick_id, sp.match_id, sp.selection,
                  sp.observed_price, m.home_goals, m.away_goals
           FROM shadow_picks sp JOIN matches m USING (match_id)
           LEFT JOIN shadow_results sr USING (shadow_pick_id)
           WHERE sr.shadow_pick_id IS NULL AND m.status='finished'
             AND m.home_goals IS NOT NULL AND {cierre_o_vencido()}"""
    )
    settled, clvs = 0, []
    for row in rows:
        closing = _closing(row["match_id"])
        if set(closing) != {"home", "draw", "away"}:
            continue  # Sin cierre sharp completo no se puede medir CLV real.
        cp = closing.get(row["selection"])
        close_prob = None
        if cp and set(closing) == {"home", "draw", "away"}:
            order = ["home", "draw", "away"]
            fair = devig([closing[s] for s in order], settings.devig_method)
            close_prob = float(fair[order.index(row["selection"])])
        clv = ((float(row["observed_price"]) / cp - 1) * 100) if cp else None
        ev = (float(row["observed_price"]) * close_prob - 1) * 100 if close_prob else None
        hg, ag = int(row["home_goals"]), int(row["away_goals"])
        winner = "home" if hg > ag else "away" if ag > hg else "draw"
        execute(
            """INSERT INTO shadow_results
                 (shadow_pick_id, closing_price, closing_prob_devig, clv_pct,
                  ev_close_pct, beat_close, outcome)
               VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
            (row["shadow_pick_id"], cp, close_prob, clv, ev,
             clv > 0 if clv is not None else None,
             "win" if row["selection"] == winner else "loss"),
        )
        settled += 1
        if clv is not None:
            clvs.append(clv)
    return {"settled": settled, "n_with_clv": len(clvs),
            "avg_clv": round(float(np.mean(clvs)), 3) if clvs else None}


def summary(challenger: str = "lineup_lambda") -> dict:
    """
    `n`, `ci95` y el desglose por liga van sobre `ev_close_pct` (cierre sin
    margen), igual que la puerta comercial. `avg_clv` es la cifra con margen,
    solo informativa.
    """
    rows = query(
        """SELECT sr.clv_pct, sr.ev_close_pct, sr.beat_close, m.league_id,
                  m.kickoff_utc
           FROM shadow_predictions sh
           JOIN shadow_picks sp USING (shadow_prediction_id)
           JOIN shadow_results sr USING (shadow_pick_id)
           JOIN matches m ON m.match_id = sh.match_id
           WHERE sh.challenger=%s""", (challenger,)) or []
    if not rows:
        return {"n": 0, "avg_ev_close": None, "avg_clv": None,
                "pct_beat_close": None, "ci95": None, "by_league": {}}
    frame = pd.DataFrame(rows)
    frame["clv_pct"] = pd.to_numeric(frame["clv_pct"], errors="coerce")
    frame["ev_close_pct"] = pd.to_numeric(frame["ev_close_pct"], errors="coerce")
    measured = frame.dropna(subset=["ev_close_pct"])
    by_league = {
        str(league): {"n": int(len(group)),
                      "avg_ev_close": round(float(group["ev_close_pct"].mean()), 3)}
        for league, group in measured.groupby("league_id")
    }
    ci = None
    if not measured.empty:
        weeks = (pd.to_datetime(measured["kickoff_utc"], utc=True)
                 .dt.tz_convert(None).dt.to_period("W"))
        groups = list(measured.groupby(weeks, sort=True).indices.values())
        if len(groups) >= 8:
            rng = np.random.default_rng(42)
            values = measured["ev_close_pct"].to_numpy(dtype=float)
            estimates = []
            for _ in range(500):
                draw = rng.integers(0, len(groups), size=len(groups))
                sample = np.concatenate([groups[i] for i in draw])
                estimates.append(float(np.mean(values[sample])))
            ci = [round(float(x), 3) for x in np.percentile(estimates, [2.5, 97.5])]
    return {
        "n": int(len(measured)),
        "avg_ev_close": (round(float(measured["ev_close_pct"].mean()), 3)
                         if not measured.empty else None),
        "avg_clv": (round(float(frame["clv_pct"].mean()), 3)
                    if frame["clv_pct"].notna().any() else None),
        "pct_beat_close": (round(float(frame["beat_close"].dropna().astype(float).mean()) * 100, 1)
                           if frame["beat_close"].notna().any() else None),
        "ci95": ci,
        "by_league": by_league,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(capture_lineup_shadows())
