"""
Sombra del criterio de picks "casa blanda contra precio sharp".

Con la publicación pausada (`PUBLISH_PICKS_ENABLED=0`), esto es lo único que
puede demostrar que el criterio merece reactivarla: registra lo que HABRÍA
recomendado, lo liquida contra el cierre de Pinnacle sin margen y lo pasa por
la misma puerta comercial (`promotion.evaluate_clv_gate`).

TRES PIEZAS
-----------
- `capture`: cada hora, tras la captura de API-Football. Todas las ofertas de
  `picks.offers` para partidos de las próximas 72 h, incluidas las de stake 0
  (casa con persistencia medida nula): justo esas son las que hay que medir
  para saber si la persistencia está bien. Desde 2026-09-28 se miden TODAS
  las casas no exchange del snapshot, no solo las de `SOFT_BOOKS`: la puerta
  sigue contando solo las de la lista (filtro al informar, así se puede
  recalcular para otra lista sin volver a capturar).
- `settle_pending`: al terminar el partido, encadenada desde
  `eval/clv.settle_pending`. Espera al cierre de Pinnacle (`window_tag='close'`;
  el de PropLine llega horas después del partido) hasta `cierre.ESPERA_CIERRE_H`;
  sin él la oferta se liquida sin `ev_close_pct` y no cuenta.
- `report`: dos vistas.
    * "publicables": por partido, la PRIMERA vez que el criterio habría dado un
      pick con stake, y de esa pasada la oferta de mayor edge esperado. Es lo
      que se habría publicado, y lo único que ve la puerta.
    * todas las ofertas, desglosadas por antelación, casa, fuente y liga.
  Las ofertas pendientes también aparecen en los conteos; solo las que ya
  tienen cierre justo entran en el CLV y en la puerta comercial.

ANTELACIÓN
----------
El histórico solo validó precios de 24-48 h antes del partido. En vivo el
criterio decide a cualquier distancia, así que el informe separa por tramos:
si el valor solo aparece en uno, la regla de publicación tiene que
restringirse a ese tramo antes de reactivarla.
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timedelta, timezone

import pandas as pd

from ..config import settings
from ..db import execute, executemany, query
from ..eval import clv
from ..eval.cierre import cierre_o_vencido, es_cierre_real
from ..eval.soft_vs_sharp import _weekly_ci
from . import picks as pk

log = logging.getLogger(__name__)

HORIZON = timedelta(hours=72)
# La misma antelación mínima que la publicación, para el precio y para la
# decisión (ver `picks.MIN_LEAD`).
MIN_LEAD = pk.MIN_LEAD
LEAD_BUCKETS = ((0, 6), (6, 24), (24, 48), (48, 72))


def lead_bucket(lead_minutes: int) -> str:
    h = lead_minutes / 60.0
    for lo, hi in LEAD_BUCKETS:
        if lo <= h < hi:
            return f"{lo}-{hi}h"
    return f">={LEAD_BUCKETS[-1][1]}h" if h >= LEAD_BUCKETS[-1][1] else "<0h"


# --------------------------------------------------------------------------
# Captura
# --------------------------------------------------------------------------

def en_lista(book: str | None) -> bool:
    """¿Cuenta para la puerta? Solo las casas de los suscriptores."""
    return book is None or book in settings.soft_books


def casas_medibles(snap: pk.Snapshot) -> tuple[str, ...]:
    """Todas las casas del snapshot salvo la referencia y los exchanges."""
    return tuple(b for b in snap.books
                 if b != settings.sharp_book and b not in pk.EXCHANGES)

def offer_rows(offers: list[pk.Offer], match: dict,
               factores: dict[str, float] | None = None) -> list[tuple]:
    """
    `stake` sin factor (decide si es publicable, como siempre) y, aparte, el
    que se publicaría: × factor de incertidumbre de la casa (db/039).
    """
    factores = {} if factores is None else factores
    rows = []
    for o in offers:
        p_exp = (1.0 + o.expected_edge / 100.0) / o.price
        stake = pk.kelly(p_exp, o.price, settings.kelly_fraction, settings.max_stake_units)
        k = factores.get(o.book, pk.factor_sin_medir())
        lead = int((match["kickoff_utc"] - o.as_of).total_seconds() // 60)
        rows.append((match["match_id"], match["league_id"], match["kickoff_utc"],
                     o.book, "h2h", o.selection, o.price, o.fair_prob,
                     round(o.raw_edge, 4), round(o.expected_edge, 4),
                     o.persistence, round(stake, 2), round(o.min_price, 4),
                     o.source, o.as_of, lead, round(stake * k, 2), round(k, 4)))
    return rows


def capture(now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    matches = query(
        """SELECT m.match_id, m.league_id, m.kickoff_utc
           FROM matches m JOIN leagues l ON l.league_id = m.league_id
           WHERE m.status = 'scheduled' AND l.active
             AND m.kickoff_utc BETWEEN %s AND %s""",
        (now, now + HORIZON),
    )
    rows, snaps = [], 0
    vigente = pk.persistencias()
    k_vigente = pk.factores()
    for m in matches:
        # Decidir a T-5 con un precio de T-55 no se puede publicar a tiempo,
        # y el cierre se capturaría antes de la decisión (auditoría 3-oct).
        if m["kickoff_utc"] - now < MIN_LEAD:
            continue
        for snap in (pk._odds_api_snapshot(m["match_id"], now),):
            if snap is None or m["kickoff_utc"] - snap.as_of < MIN_LEAD:
                continue
            snaps += 1
            rows += offer_rows(pk.offers(snap, now, books=casas_medibles(snap),
                                          persistencia=vigente), m, k_vigente)
    new = executemany(
        """INSERT INTO sharp_shadow_offers
             (match_id, league_id, kickoff_utc, book, market, selection, price,
              fair_prob, raw_edge_pct, expected_edge_pct, persistence,
              stake_units, min_price, odds_source, odds_as_of, lead_minutes,
              stake_publicado_units, factor_incertidumbre)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
           ON CONFLICT (match_id, book, market, selection, odds_source,
                        odds_as_of) DO NOTHING""",
        rows,
    )
    result = {"matches": len(matches), "snapshots": snaps,
              "offers_seen": len(rows), "offers_new": new}
    log.info("Sombra del criterio sharp: %s", result)
    return result


# --------------------------------------------------------------------------
# Liquidación
# --------------------------------------------------------------------------

def settle_row(selection: str, price: float, close_quotes: dict,
               home_goals: int, away_goals: int) -> tuple:
    """(closing_price, closing_prob, clv_pct, ev_close_pct, beat, outcome, profit)."""
    p = clv.fair_close_prob("h2h", selection, None, close_quotes)
    cp = close_quotes.get((selection, None))
    clv_pct = (price / cp - 1.0) * 100.0 if cp else None
    ev = clv.ev_close_pct(price, p) if p else None
    outcome, win, push = clv._settle_outcome("h2h", selection, None,
                                             home_goals, away_goals)
    return (cp, p, clv_pct, ev, clv_pct > 0 if clv_pct is not None else None,
            outcome, round(clv.settle_profit(1.0, price, win, push), 4))


def settle_pending() -> dict:
    rows = query(
        f"""SELECT o.offer_id, o.match_id, o.selection, o.price,
                  m.home_goals, m.away_goals
           FROM sharp_shadow_offers o
           JOIN matches m USING (match_id)
           LEFT JOIN sharp_shadow_results r USING (offer_id)
           WHERE r.offer_id IS NULL AND m.status = 'finished'
             AND m.home_goals IS NOT NULL AND {cierre_o_vencido()}"""
    )
    closes: dict[str, dict] = {}
    with_ev = 0
    for r in rows:
        if r["match_id"] not in closes:
            closes[r["match_id"]] = clv._sharp_close_quotes(r["match_id"], "h2h")
        out = settle_row(r["selection"], float(r["price"]), closes[r["match_id"]],
                         int(r["home_goals"]), int(r["away_goals"]))
        execute(
            """INSERT INTO sharp_shadow_results
                 (offer_id, closing_price, closing_prob_devig, clv_pct,
                  ev_close_pct, beat_close, outcome, profit_units)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (offer_id) DO NOTHING""",
            (r["offer_id"], *out),
        )
        with_ev += out[3] is not None
    return {"settled": len(rows), "with_fair_close": with_ev}


# --------------------------------------------------------------------------
# Informe
# --------------------------------------------------------------------------

def publishable(frame: pd.DataFrame) -> pd.DataFrame:
    """
    Por partido, la primera pasada en la que hubo una oferta con stake, y de
    esa pasada la de mayor edge esperado. Una fila por partido.
    """
    f = frame[frame["stake_units"] > pk.MIN_STAKE_UNITS]
    if "book" in f:
        f = f[f["book"].map(en_lista)]
    if f.empty:
        return f
    first = f.groupby("match_id")["decided_at"].transform("min")
    f = f[f["decided_at"] == first]
    return f.sort_values("expected_edge_pct", ascending=False).drop_duplicates("match_id")


def _block(g: pd.DataFrame) -> dict:
    m = g.dropna(subset=["ev_close_pct"])
    if m.empty:
        return {"n": int(len(g)), "n_with_fair_close": 0}
    ev = m["ev_close_pct"].to_numpy(float)
    weeks = pd.to_datetime(m["kickoff_utc"], utc=True).dt.tz_convert(None) \
        .dt.to_period("W").astype(str).to_numpy()
    return {"n": int(len(g)), "n_with_fair_close": int(len(m)),
            "edge_early": round(float(m["raw_edge_pct"].mean()), 3),
            "ev_close": round(float(ev.mean()), 3),
            "ev_close_ci95": _weekly_ci(ev, weeks),
            "roi": round(float(m["profit_units"].mean()) * 100, 3)}


def summarize(frame: pd.DataFrame) -> dict:
    """La parte pura de `report`, para probarla sin base de datos."""
    from ..model.promotion import evaluate_clv_gate
    if frame.empty:
        ok, motivos = evaluate_clv_gate(None)
        return {"n_offers": 0, "publishable": {"n": 0},
                "gate": {"authorized": ok, "reasons": motivos}}
    frame = frame.assign(lead=frame["lead_minutes"].map(lead_bucket))
    pub = publishable(frame)
    # Un LEFT JOIN trae ofertas aún pendientes: pandas convierte los NULL
    # numéricos a NaN. La puerta solo reconoce `None` como ausencia de cierre;
    # pasar NaN contaría una oferta pendiente como CLV medido.
    gate_cols = ["ev_close_pct", "clv_pct", "beat_close", "league_id"]
    gate_rows = pub[gate_cols].astype(object).where(pd.notna(pub[gate_cols]), None)
    gate_input = clv.summarize_clv(gate_rows.to_dict("records"))
    ok, motivos = evaluate_clv_gate(gate_input)
    by = lambda col: {str(k): _block(g) for k, g in frame.groupby(col)}  # noqa: E731
    return {
        "n_offers": int(len(frame)),
        "publishable": {**_block(pub), "by_league": gate_input["by_league"],
                        "by_lead": {str(k): _block(g) for k, g in pub.groupby("lead")}},
        "all_offers": {"by_lead": by("lead"), "by_book": by("book"),
                       "by_source": by("odds_source"), "by_league": by("league_id")},
        "gate": {"authorized": ok, "reasons": motivos,
                 "ev_close_ci95": gate_input.get("ev_close_ci95"),
                 "n_leagues_with_sample": gate_input.get("n_leagues_with_sample")},
    }


def report() -> dict:
    rows = query(
        """SELECT o.match_id, o.league_id, o.kickoff_utc, o.book, o.odds_source,
                  o.raw_edge_pct, o.expected_edge_pct, o.stake_units,
                  o.lead_minutes, o.decided_at,
                  r.ev_close_pct, r.clv_pct, r.beat_close, r.profit_units
           FROM sharp_shadow_offers o
           LEFT JOIN sharp_shadow_results r USING (offer_id)"""
    )
    frame = pd.DataFrame(rows)
    for c in ("raw_edge_pct", "expected_edge_pct", "stake_units", "ev_close_pct",
              "clv_pct", "profit_units"):
        if c in frame:
            frame[c] = pd.to_numeric(frame[c], errors="coerce")
    return summarize(frame)


_NUMERIC = ("price", "min_price", "raw_edge_pct", "expected_edge_pct", "stake_units",
            "stake_publicado", "closing_price", "ev_close_pct", "profit_units")


def listado(frame: pd.DataFrame) -> list[dict]:
    """
    Una fila por pick que se habría publicado, la más reciente primero. Sale
    de `publishable`, no de una consulta aparte: el panel tiene que enseñar
    exactamente la muestra que cuenta la puerta.
    """
    if frame.empty:
        return []
    frame = frame.copy()
    for c in _NUMERIC:
        if c in frame:
            frame[c] = pd.to_numeric(frame[c], errors="coerce")
    pub = publishable(frame).sort_values(["kickoff_utc", "match_id"], ascending=False)
    pub = pub.astype(object).where(pd.notna(pub), None)
    out = []
    for r in pub.to_dict("records"):
        jugado = r.get("home_goals") is not None and r.get("away_goals") is not None
        out.append({
            "kickoff_utc": r["kickoff_utc"], "league_id": r["league_id"],
            "partido": f"{r['local']} - {r['visita']}", "selection": r["selection"],
            "book": r["book"], "price": r["price"], "min_price": r.get("min_price"),
            "closing_price": r.get("closing_price"),
            "expected_edge_pct": r["expected_edge_pct"],
            "stake_units": r.get("stake_publicado"),
            "lead_minutes": r["lead_minutes"], "ev_close_pct": r.get("ev_close_pct"),
            "outcome": r.get("outcome"), "profit_units": r.get("profit_units"),
            "marcador": f"{int(r['home_goals'])}-{int(r['away_goals'])}" if jugado else None,
        })
    return out


def publishable_list() -> list[dict]:
    rows = query(
        """SELECT o.match_id, o.league_id, o.kickoff_utc, o.book, o.selection,
                  o.price, o.min_price, o.raw_edge_pct, o.expected_edge_pct,
                  o.stake_units,
                  coalesce(o.stake_publicado_units, o.stake_units) AS stake_publicado,
                  o.lead_minutes, o.decided_at,
                  r.closing_price, r.ev_close_pct, r.outcome, r.profit_units,
                  coalesce(th.display_name, th.canonical_name) AS local,
                  coalesce(ta.display_name, ta.canonical_name) AS visita,
                  m.home_goals, m.away_goals
           FROM sharp_shadow_offers o
           LEFT JOIN sharp_shadow_results r USING (offer_id)
           JOIN matches m USING (match_id)
           JOIN teams th ON th.team_id = m.home_team_id
           JOIN teams ta ON ta.team_id = m.away_team_id"""
    )
    return listado(pd.DataFrame(rows))


def audit_summary(rows: list[dict], now: datetime | None = None) -> dict:
    """Traza oferta → partido → liquidación → cierre, sin cambiar la puerta.

    `candidates` reproduce la primera oferta con stake por partido de
    `publishable`: las demás ofertas sirven para diagnóstico, no para inflar la
    muestra que autoriza la venta.
    """
    now = now or datetime.now(timezone.utc)
    candidates: set[int] = set()
    first_by_match: dict[str, dict] = {}
    for row in rows:
        if float(row["stake_units"]) <= pk.MIN_STAKE_UNITS or not en_lista(row.get("book")):
            continue
        previous = first_by_match.get(row["match_id"])
        order = (row["decided_at"], -float(row["expected_edge_pct"]),
                 int(row["offer_id"]))
        if previous is None or order < previous[0]:
            first_by_match[row["match_id"]] = (order, int(row["offer_id"]))
    candidates = {value[1] for value in first_by_match.values()}

    states = ("scheduled", "in_play", "awaiting_result", "result_overdue",
              "finished_no_score", "awaiting_settlement", "settled_no_close",
              "settled_incomplete_close", "settled_with_fair_close",
              "postponed_or_other")

    def empty_counts() -> dict:
        return {"captured": 0, "with_stake": 0, "candidates": 0,
                "offer_states": dict.fromkeys(states, 0),
                "candidate_states": dict.fromkeys(states, 0)}

    total = empty_counts()
    by_league: dict[str, dict] = {}
    for row in rows:
        league = str(row["league_id"])
        counts = by_league.setdefault(league, empty_counts())
        for target in (total, counts):
            target["captured"] += 1
            if float(row["stake_units"]) > pk.MIN_STAKE_UNITS and en_lista(row.get("book")):
                target["with_stake"] += 1
            if int(row["offer_id"]) in candidates:
                target["candidates"] += 1

        if row["result_offer_id"] is not None:
            if row["ev_close_pct"] is not None:
                state = "settled_with_fair_close"
            elif row["complete_sharp_close"]:
                state = "settled_incomplete_close"
            else:
                state = "settled_no_close"
        elif row["match_status"] == "finished":
            state = ("awaiting_settlement" if row["home_goals"] is not None
                     and row["away_goals"] is not None else "finished_no_score")
        elif row["match_status"] == "live":
            state = "in_play"
        elif row["match_status"] == "scheduled":
            kickoff = row["kickoff_utc"]
            state = ("scheduled" if kickoff > now else "awaiting_result"
                     if kickoff > now - timedelta(hours=3) else "result_overdue")
        else:
            state = "postponed_or_other"
        for target in (total, counts):
            target["offer_states"][state] += 1
            if int(row["offer_id"]) in candidates:
                target["candidate_states"][state] += 1
    return {"as_of": now.isoformat(), "total": total,
            "by_league": dict(sorted(by_league.items())),
            "definitions": {
                "captured": "Ofertas únicas guardadas, incluidas las de stake cero.",
                "with_stake": "Ofertas de casas de la lista que superan el stake mínimo, no picks distintos.",
                "candidates": "Una primera selección con stake por partido; base de la puerta.",
                "result_overdue": "El inicio fue hace más de tres horas y aún no hay resultado.",
                "awaiting_settlement": "El marcador final existe, falta liquidar la oferta.",
                "settled_no_close": "Liquidada sin snapshot completo de cierre sharp.",
                "settled_incomplete_close": "Hay cierre sharp completo, pero la liquidación no obtuvo CLV; revisar.",
                "settled_with_fair_close": "Liquidada con valor al cierre justo; solo las candidatas cuentan para la puerta.",
            }}


def audit(now: datetime | None = None) -> dict:
    """Diagnóstico interno por liga, de solo lectura y sin datos de usuario."""
    rows = query(
        f"""WITH latest_close AS (
               SELECT DISTINCT ON (match_id) match_id, captured_at
               FROM odds_snapshots
               WHERE match_id IN (SELECT DISTINCT match_id FROM sharp_shadow_offers)
                 AND bookmaker = %s AND market = 'h2h'
                 AND window_tag = 'close' AND mins_to_kickoff >= 0 AND {es_cierre_real()}
               ORDER BY match_id, captured_at DESC
           ), close_quality AS (
               SELECT lc.match_id,
                      count(DISTINCT s.selection) FILTER (
                          WHERE s.line IS NULL
                            AND s.selection IN ('home', 'draw', 'away')
                            AND s.price > 1) = 3 AS complete_sharp_close
               FROM latest_close lc
               JOIN odds_snapshots s ON s.match_id = lc.match_id
                   AND s.captured_at = lc.captured_at
                   AND s.bookmaker = %s AND s.market = 'h2h'
                   AND s.window_tag = 'close' AND s.mins_to_kickoff >= 0 AND {es_cierre_real("s")}
               GROUP BY lc.match_id
           )
           SELECT o.offer_id, o.match_id, o.league_id, o.kickoff_utc,
                  o.book, o.stake_units, o.expected_edge_pct, o.decided_at,
                  m.status AS match_status, m.home_goals, m.away_goals,
                  res.offer_id AS result_offer_id, res.ev_close_pct,
                  coalesce(cq.complete_sharp_close, false) AS complete_sharp_close
           FROM sharp_shadow_offers o
           JOIN matches m USING (match_id)
           LEFT JOIN sharp_shadow_results res USING (offer_id)
           LEFT JOIN close_quality cq ON cq.match_id = o.match_id""",
        (settings.sharp_book, settings.sharp_book),
    )
    return audit_summary(rows, now)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    ap = argparse.ArgumentParser(description="Sombra del criterio de picks")
    ap.add_argument("accion", choices=["capture", "settle", "report"])
    a = ap.parse_args()
    out = {"capture": capture, "settle": settle_pending, "report": report}[a.accion]()
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
