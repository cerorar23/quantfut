"""
Liquidación y CLV (Closing Line Value).

EL CLV ES TU MÉTRICA PRINCIPAL, no el P&L.

Si aconsejaste 2.10 y la línea cerró en 2.00, capturaste valor real
independientemente de si el partido se ganó. El CLV converge en cientos de
apuestas; el ROI necesita miles. Con 300 picks puedes saber si tienes edge
mirando CLV, y no puedes saberlo mirando ganancias.

Si tu CLV medio es negativo de forma sostenida, no tienes un modelo: tienes
un generador de ruido caro. Mejor saberlo en el mes 3 que en el año 2.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import numpy as np

from ..config import settings
from ..db import execute, query
from ..model.devig import devig

log = logging.getLogger(__name__)


def _closing_prices(match_id: str, market: str, line: float | None) -> dict[str, float]:
    """Último precio antes del kickoff, preferentemente de la casa sharp."""
    rows = query(
        """SELECT DISTINCT ON (selection)
                  selection, price, bookmaker, captured_at
           FROM odds_snapshots
           WHERE match_id = %s AND market = %s
             -- Los casts son obligatorios: en la comparación IS NULL, Postgres
             -- no puede inferir el tipo de un parámetro suelto y aborta con
             -- IndeterminateDatatype. Falla siempre, no solo con line nula.
             AND (line = %s::real OR (%s::real IS NULL AND line IS NULL))
             AND mins_to_kickoff >= 0
           ORDER BY selection,
                    (bookmaker = %s) DESC,
                    captured_at DESC""",
        (match_id, market, line, line, settings.sharp_book),
    )
    return {r["selection"]: float(r["price"]) for r in rows}


def _sharp_close_quotes(match_id: str, market: str) -> dict[tuple[str, float | None], float]:
    """
    Último snapshot de cierre de la casa sharp para este mercado, todas las
    líneas: {(selection, line): price}. Un único `captured_at`, para no mezclar
    precios de momentos distintos en el mismo de-vig.
    """
    rows = query(
        """SELECT selection, line, price
           FROM odds_snapshots
           WHERE match_id = %s AND market = %s AND bookmaker = %s
             AND window_tag = 'close' AND mins_to_kickoff >= 0
             AND captured_at = (
                 SELECT max(captured_at) FROM odds_snapshots
                 WHERE match_id = %s AND market = %s AND bookmaker = %s
                   AND window_tag = 'close' AND mins_to_kickoff >= 0)""",
        (match_id, market, settings.sharp_book,
         match_id, market, settings.sharp_book),
    )
    return {(r["selection"], None if r["line"] is None else float(r["line"])):
            float(r["price"]) for r in rows}


def fair_close_prob(market: str, selection: str, line: float | None,
                    quotes: dict[tuple[str, float | None], float]) -> float | None:
    """
    Probabilidad SIN MARGEN de la selección en el cierre sharp.

    Exige el grupo complementario completo de la MISMA casa y el mismo
    snapshot. En hándicap el rival está en la línea opuesta: local -0,5 se
    empareja con visitante +0,5. Mercados que la casa sharp no cotiza en este
    sistema (BTTS, doble oportunidad, totales por equipo) devuelven None: sin
    precio sharp no hay cierre justo contra el que medir.
    """
    ln = None if line is None else float(line)
    if market == "h2h":
        grupo = [("home", None), ("draw", None), ("away", None)]
    elif market == "totals" and ln is not None:
        grupo = [("over", ln), ("under", ln)]
    elif market == "spreads" and ln is not None:
        otra = "away" if selection == "home" else "home"
        grupo = [(selection, ln), (otra, -ln)]
    else:
        return None
    if (selection, ln) not in grupo or not all(k in quotes for k in grupo):
        return None
    probs = devig([quotes[k] for k in grupo], settings.devig_method)
    return float(probs[grupo.index((selection, ln))])


def ev_close_pct(price: float, fair_prob: float) -> float:
    """Valor esperado de la cuota tomada, valorada al cierre sin margen, en %."""
    return (price * fair_prob - 1.0) * 100.0


_WIN, _LOSS, _PUSH = ("win", 1.0, 0.0), ("loss", 0.0, 0.0), ("push", 0.0, 1.0)


def _settle_outcome(market: str, selection: str, line: float | None,
                    hg: int, ag: int) -> tuple[str, float, float]:
    """
    Devuelve (outcome, fracción_ganada, fracción_devuelta) del stake.

    Van separadas porque no pagan igual: lo ganado cobra a cuota y lo devuelto
    cobra 1. Un multiplicador único sobre la cuota pagaba a cuota la mitad
    empujada de una línea de cuarto. Ver `settle_profit`.
    """
    diff, total = hg - ag, hg + ag

    if market == "h2h":
        winner = "home" if diff > 0 else "away" if diff < 0 else "draw"
        return _WIN if selection == winner else _LOSS

    if market == "btts":
        yes = hg > 0 and ag > 0
        hit = (selection == "yes") == yes
        return _WIN if hit else _LOSS

    if market == "double_chance":
        winner = "home" if diff > 0 else "away" if diff < 0 else "draw"
        mapping = {"1X": {"home", "draw"}, "12": {"home", "away"}, "X2": {"draw", "away"}}
        return _WIN if winner in mapping[selection] else _LOSS

    if market == "totals":
        if total == line:
            return _PUSH
        over = total > line
        hit = (selection == "over") == over
        return _WIN if hit else _LOSS

    if market.startswith("team_totals"):
        g = hg if market.endswith("home") else ag
        if g == line:
            return _PUSH
        hit = (selection == "over") == (g > line)
        return _WIN if hit else _LOSS

    if market == "spreads":
        adj = diff + line if selection == "home" else -diff + line
        # Líneas de cuarto: media apuesta en cada línea adyacente. Se suman las
        # fracciones de cada mitad, igual que en `pricing.market_asian_handicap`.
        if abs(line * 2 - round(line * 2)) > 1e-9:
            legs = [_spread_leg(adj - 0.25), _spread_leg(adj + 0.25)]
            win = 0.5 * sum(w for w, _ in legs)
            push = 0.5 * sum(p for _, p in legs)
            name = ("win" if win == 1.0 else "half_win" if win == 0.5
                    else "push" if push == 1.0 else "half_loss" if push == 0.5
                    else "loss")
            return name, win, push
        if abs(adj) < 1e-9:
            return _PUSH
        return _WIN if adj > 0 else _LOSS

    raise ValueError(f"Mercado no liquidable: {market}")


def _spread_leg(adj: float) -> tuple[float, float]:
    """(ganada, devuelta) de una línea entera o media."""
    if adj > 1e-9:
        return 1.0, 0.0
    if abs(adj) < 1e-9:
        return 0.0, 1.0
    return 0.0, 0.0


def settle_profit(stake: float, price: float, win: float, push: float) -> float:
    """Beneficio en unidades: lo ganado cobra `price`, lo devuelto cobra 1."""
    return stake * (win * price + push - 1.0)


def settle_pending(lookback_hours: int = 96) -> dict:
    """Liquida picks de partidos terminados que aún no tienen resultado."""
    since = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    rows = query(
        """SELECT p.pick_id, p.match_id, p.market, p.selection, p.line,
                  p.advised_price, p.stake_units,
                  m.home_goals, m.away_goals
           FROM picks p
           JOIN matches m USING (match_id)
           LEFT JOIN pick_results r USING (pick_id)
           WHERE r.pick_id IS NULL
             AND m.status = 'finished'
             AND m.home_goals IS NOT NULL
             AND m.kickoff_utc > %s""",
        (since,),
    )

    settled, clvs = 0, []
    for r in rows:
        try:
            outcome, win, push = _settle_outcome(
                r["market"], r["selection"], r["line"],
                int(r["home_goals"]), int(r["away_goals"])
            )
        except ValueError as exc:
            log.error("No se pudo liquidar %s: %s", r["pick_id"], exc)
            continue

        price = float(r["advised_price"])
        profit = settle_profit(float(r["stake_units"]), price, win, push)

        closing = _closing_prices(r["match_id"], r["market"], r["line"])
        clv_pct, beat = None, None
        cp = closing.get(r["selection"])
        if cp:
            clv_pct = (price / cp - 1.0) * 100.0
            beat = clv_pct > 0
            clvs.append(clv_pct)

        close_prob = fair_close_prob(r["market"], r["selection"], r["line"],
                                     _sharp_close_quotes(r["match_id"], r["market"]))
        ev = ev_close_pct(price, close_prob) if close_prob else None

        execute(
            """INSERT INTO pick_results
                 (pick_id, closing_price, closing_prob_devig, clv_pct,
                  ev_close_pct, beat_close, outcome, profit_units)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (pick_id) DO NOTHING""",
            (r["pick_id"], cp, close_prob, clv_pct, ev, beat, outcome,
             round(profit, 4)),
        )
        settled += 1

    # Los challengers se liquidan en una tabla separada: medirlos nunca crea ni
    # altera picks publicados.
    try:
        from ..model.shadow import settle_pending as settle_shadow
        shadow = settle_shadow()
    except Exception as exc:  # noqa: BLE001
        log.warning("No se pudieron liquidar challengers en sombra: %s", exc)
        shadow = {"settled": 0, "error": str(exc)}
    try:
        from ..publish.shadow_sharp import settle_pending as settle_sharp
        sharp = settle_sharp()
    except Exception as exc:  # noqa: BLE001
        log.warning("No se pudo liquidar la sombra del criterio sharp: %s", exc)
        sharp = {"settled": 0, "error": str(exc)}

    result = {"settled": settled,
              "avg_clv": round(float(np.mean(clvs)), 3) if clvs else None,
              "n_with_clv": len(clvs), "shadow": shadow, "sharp_shadow": sharp}
    log.info("Liquidación: %s", result)
    return result


def summary(days: int = 7) -> dict:
    row = query(
        """SELECT count(*) AS n,
                  avg(r.clv_pct) AS avg_clv,
                  avg(r.ev_close_pct) AS avg_ev_close,
                  avg(CASE WHEN r.beat_close THEN 1.0 ELSE 0.0 END)*100 AS pct_beat,
                  sum(r.profit_units) AS profit,
                  sum(p.stake_units) AS staked
           FROM picks p JOIN pick_results r USING (pick_id)
           WHERE r.settled_at > now() - make_interval(days => %s)""",
        (days,),
    )[0]
    n = row["n"] or 0
    staked = float(row["staked"] or 0)
    profit = float(row["profit"] or 0)
    return {
        "n": n,
        "avg_clv": round(float(row["avg_clv"] or 0), 3),
        "avg_ev_close": (round(float(row["avg_ev_close"]), 3)
                         if row["avg_ev_close"] is not None else None),
        "pct_beat_close": round(float(row["pct_beat"] or 0), 1),
        "profit_units": round(profit, 2),
        "roi": round(profit / staked * 100, 2) if staked else 0.0,
        # Intervalo de confianza aproximado del ROI. Publícalo SIEMPRE:
        # sin él, cualquier ROI a 50 apuestas es una anécdota, no un resultado.
        "roi_ci95": _roi_ci(days),
    }


def clv_report(days: int = 90, n_boot: int = 2000) -> dict:
    """
    CLV con intervalo de confianza, y desglosado por liga y por ventana.

    ES LA MEDIDA QUE DECIDE LA FASE 2, y no `rps` contra el cierre. Son dos
    afirmaciones distintas y solo una es alcanzable:

      1. "mi probabilidad es mejor que el consenso de cierre"  -> nadie.
      2. "el precio que tomé era mejor que el cierre que vino" -> esto, y es
         exactamente lo que se cobra.

    Por eso se devuelve el intervalo y no solo la media: un CLV medio positivo
    con 40 apuestas no distingue una ventaja de una racha. Y por eso va
    desglosado: un CLV que solo vive en una liga es un descubrimiento sobre esa
    liga —o sobre una casa— no sobre el sistema.

    La cifra que decide es `ev_close_pct` (contra el cierre SIN margen).
    `clv_pct` va contra la cuota con margen y sale inflada por él; se reporta
    como `avg_clv` pero no alimenta el intervalo de la puerta.
    """
    rows = query(
        """SELECT r.clv_pct, r.ev_close_pct, r.beat_close, m.league_id, p.market
           FROM picks p
           JOIN pick_results r USING (pick_id)
           JOIN matches m ON m.match_id = p.match_id
           WHERE r.settled_at > now() - make_interval(days => %s)
             AND (r.clv_pct IS NOT NULL OR r.ev_close_pct IS NOT NULL)""",
        (days,),
    )
    return summarize_clv(rows, n_boot=n_boot)


def _mean(xs: list[float]) -> float | None:
    return round(float(np.mean(xs)), 4) if xs else None


def summarize_clv(rows: list[dict], n_boot: int = 2000) -> dict:
    """
    Parte pura de `clv_report`, para poder probarla sin base de datos.

    `n`, el intervalo y el recuento de ligas se calculan SOLO sobre las filas
    con `ev_close_pct`. Una apuesta sin cierre sharp completo no puede
    demostrar valor, y contarla con su `clv_pct` reintroduciría el margen.
    """
    ev_rows = [r for r in rows if r.get("ev_close_pct") is not None]
    clv = [float(r["clv_pct"]) for r in rows if r.get("clv_pct") is not None]
    beat = [1.0 if r["beat_close"] else 0.0
            for r in rows if r.get("beat_close") is not None]
    x = np.array([float(r["ev_close_pct"]) for r in ev_rows])
    n = len(ev_rows)

    ci = None
    if n >= 20:
        rng = np.random.default_rng(0)
        boots = rng.choice(x, size=(n_boot, n), replace=True).mean(axis=1)
        ci = [round(float(np.percentile(boots, 2.5)), 4),
              round(float(np.percentile(boots, 97.5)), 4)]

    por_liga: dict[str, dict] = {}
    for r in rows:
        d = por_liga.setdefault(r.get("league_id") or "?",
                                {"ev": [], "clv": []})
        if r.get("ev_close_pct") is not None:
            d["ev"].append(float(r["ev_close_pct"]))
        if r.get("clv_pct") is not None:
            d["clv"].append(float(r["clv_pct"]))
    por_liga = {lg: {"n": len(d["ev"]), "avg_ev_close": _mean(d["ev"]),
                     "avg_clv": _mean(d["clv"])}
                for lg, d in por_liga.items()}

    return {"n": n,
            "n_without_fair_close": len(rows) - n,
            "days_window": None,
            "avg_ev_close": _mean(list(x)),
            "ev_close_ci95": ci,
            "avg_clv": _mean(clv),
            "pct_beat_close": round(float(np.mean(beat)) * 100, 1) if beat else None,
            "by_league": por_liga,
            "n_leagues": sum(1 for d in por_liga.values() if d["n"] > 0),
            # Ligas con muestra suficiente para que su cifra signifique algo.
            "n_leagues_with_sample": sum(1 for d in por_liga.values() if d["n"] >= 30)}


def _roi_ci(days: int) -> list[float] | None:
    rows = query(
        """SELECT r.profit_units, p.stake_units
           FROM picks p JOIN pick_results r USING (pick_id)
           WHERE r.settled_at > now() - make_interval(days => %s)""",
        (days,),
    )
    if len(rows) < 20:
        return None
    x = np.array([float(r["profit_units"]) for r in rows])
    s = np.array([float(r["stake_units"]) for r in rows])
    boots = [float(np.random.choice(x, len(x)).sum() / s.sum() * 100) for _ in range(2000)]
    return [round(float(np.percentile(boots, 2.5)), 2),
            round(float(np.percentile(boots, 97.5)), 2)]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    print(settle_pending())
