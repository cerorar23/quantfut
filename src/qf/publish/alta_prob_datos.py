"""
Base de datos de la línea de alta probabilidad: elegir y guardar, liquidar e
informar. Las reglas están en `alta_prob.py`.

ORDEN: `daily.run()` llama a `select_and_persist()` justo ANTES de `seal()`, y
`hashchain._collect` mete las filas del día en el lote. Un pronóstico solo se
enseña si su lote existe y se selló DESPUÉS de decidirlo
(`decided_at <= created_at`): lo que no está en un lote sellado no existe.
Por eso, si el lote del día ya está sellado (job relanzado a mano), no se
elige nada: quedaría fuera de la cadena para siempre.
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import date, datetime, timezone

from ..config import settings
from ..db import execute, query, query_one
from ..eval.clv import _settle_outcome
from ..model.devig import devig, two_way_devig
from . import alta_prob as ap
from . import hashchain
from . import picks as pk

log = logging.getLogger(__name__)

SEL = ("home", "draw", "away")
_MEDIO_GOL = (2.5, 3.5)


def _sql_sellado() -> str:
    """
    JOIN con el lote que cubre cada fila: existe, se selló DESPUÉS de decidirla
    y es de un día cuyo payload LLEVA el bloque (`hashchain.lote_lleva_alta`).
    Sin esto último, una fila guardada en un día sin bloque se daría por sellada
    con un hash que no la cubre. Sin fecha de corte no hay lote que cubra nada:
    `AND FALSE`. El literal de fecha es seguro de incrustar: sale de una
    constante `date` del código (`LOTE_ALTA_PROB_DESDE`), no de entrada de usuario.
    """
    desde = hashchain.LOTE_ALTA_PROB_DESDE
    corte = (f"AND b.batch_date >= DATE '{desde.isoformat()}'"
             if desde is not None else "AND FALSE")
    return f"""JOIN prediction_batches b
             ON b.batch_date = (a.decided_at AT TIME ZONE 'UTC')::date
            AND a.decided_at <= b.created_at
            {corte}"""


# --------------------------------------------------------------------------
# Lecturas
# --------------------------------------------------------------------------

def _rho_activo() -> float | None:
    row = query_one("SELECT (params->>'rho')::float AS rho FROM model_artifacts "
                    "WHERE is_active LIMIT 1")
    return None if not row or row["rho"] is None else float(row["rho"])


def _lote_sellado(dia: date) -> bool:
    return query_one("SELECT 1 AS x FROM prediction_batches WHERE batch_date = %s",
                     (dia,)) is not None


def _partidos(now: datetime) -> list[dict]:
    return query(
        """SELECT m.match_id, m.kickoff_utc
           FROM matches m
           JOIN leagues l ON l.league_id = m.league_id
           LEFT JOIN alta_prob_picks a ON a.match_id = m.match_id
           WHERE m.status = 'scheduled' AND l.active AND a.match_id IS NULL
             AND m.kickoff_utc BETWEEN %s AND %s
           ORDER BY m.kickoff_utc""",
        (now + pk.MIN_LEAD, now + ap.HORIZONTE))


def _totales(match_id: str, as_of: datetime) -> list[dict]:
    """Totales de la MISMA respuesta de The Odds API que el 1X2."""
    return query(
        """SELECT bookmaker, selection, line, price FROM odds_snapshots
           WHERE match_id = %s AND market = 'totals' AND source = 'the_odds_api'
             AND captured_at = %s""",
        (match_id, as_of))


def _totales_af(match_id: str, as_of: datetime) -> list[dict]:
    """Totales de la MISMA respuesta de API-Football que el 1X2 (misma marca `update`)."""
    return query(
        """SELECT bookmaker, selection, line, price FROM af_odds_snapshots
           WHERE match_id = %s AND market = 'totals' AND provider_updated_at = %s""",
        (match_id, as_of))


def _liquidados(desde: str | None = "control") -> list[dict]:
    """
    Liquidados y sellados. Por defecto, desde ALTA_PROB_CONTROL_DESDE (lo que
    mide el control); con `None`, todos (el historial público nunca se recorta).
    """
    if desde == "control":
        desde = settings.alta_prob_control_desde or None
    return query(
        f"""SELECT a.market, a.prob, a.ref_price, r.outcome, m.kickoff_utc
            FROM alta_prob_picks a
            JOIN alta_prob_results r ON r.alta_id = a.alta_id
            JOIN matches m ON m.match_id = a.match_id
            {_sql_sellado()}
            WHERE %s::date IS NULL OR a.decided_at >= %s::date""",
        (desde, desde))


# --------------------------------------------------------------------------
# Decisión
# --------------------------------------------------------------------------

def _snapshot(match_id: str, kickoff: datetime, now: datetime) -> pk.Snapshot | None:
    """
    Vigente y con el 1X2 de Pinnacle completo; The Odds API primero. Los totales
    se leen de la MISMA fuente y respuesta que el 1X2 (`_totales` / `_totales_af`):
    nunca se mezclan fuentes.
    """
    for snap in (pk._odds_api_snapshot(match_id, now), pk._af_snapshot(match_id, now)):
        if snap is None:
            continue
        if now - snap.as_of > ap.MAX_EDAD_PRECIO or kickoff - snap.as_of < pk.MIN_LEAD:
            continue
        q = snap.books.get(settings.sharp_book, {})
        if set(q) == set(SEL) and min(q.values()) > 1.0:
            return snap
    return None


def linea_pinnacle(rows: list[dict]) -> tuple[float, float] | None:
    """(línea, p_over justa) de Pinnacle: medio gol primero, si no la más cercana a 2,5."""
    por_linea: dict[float, dict[str, float]] = {}
    for r in rows:
        if r["line"] is None or pk.canonical_book(r["bookmaker"]) != settings.sharp_book:
            continue
        por_linea.setdefault(float(r["line"]), {})[r["selection"]] = float(r["price"])
    completas = {ln: q for ln, q in por_linea.items()
                 if set(q) == {"over", "under"} and min(q.values()) > 1.0}
    if not completas:
        return None
    ln = min(completas, key=lambda x: (x not in _MEDIO_GOL, abs(x - 2.5)))
    p_over, _ = two_way_devig(completas[ln]["over"], completas[ln]["under"],
                              settings.devig_method)
    return ln, p_over


def decidir(snap: pk.Snapshot, totales: list[dict], rho: float | None,
            habilitados: tuple, excluir: set[str]) -> tuple[ap.Candidato, dict | None] | None:
    q = snap.books[settings.sharp_book]
    fair = devig([q[s] for s in SEL], settings.devig_method)
    p = {s: float(fair[i]) for i, s in enumerate(SEL)}
    cands = ap.candidatos_1x2(p) + ap.candidatos_doble(p)
    ajuste = None
    if rho is not None and habilitados and "totals" not in excluir:
        linea = linea_pinnacle(totales)
        if linea is not None:
            ajuste = ap.ajuste_goles(p, linea[0], linea[1], rho)
            cands += ap.candidatos_goles(ajuste, habilitados)
    elegido = ap.elegir(cands, excluir)
    if elegido is None:
        return None
    return elegido, (ajuste if elegido.market == "totals" else None)


def _ref(snap: pk.Snapshot, totales: list[dict], c: ap.Candidato) -> tuple[float | None, str | None]:
    """Mejor cuota de las casas de los suscriptores en el mismo snapshot."""
    if c.market == "h2h":
        precios = [(q[c.selection], b) for b, q in snap.books.items()
                   if b in settings.soft_books and c.selection in q]
    elif c.market == "totals":
        precios = [(float(r["price"]), pk.canonical_book(r["bookmaker"])) for r in totales
                   if pk.canonical_book(r["bookmaker"]) in settings.soft_books
                   and r["selection"] == c.selection and r["line"] is not None
                   and float(r["line"]) == c.line]
    else:   # doble oportunidad: ningún proveedor capturado la cotiza
        precios = []
    return max(precios) if precios else (None, None)


# --------------------------------------------------------------------------
# Estado, elección, liquidación, informe
# --------------------------------------------------------------------------

def estado() -> dict:
    if not settings.alta_prob_enabled:
        return {"estado": "desactivada", "bloqueados": [], "motivos": ["Línea desactivada"]}
    ctl = ap.control(_liquidados())
    return {"estado": "pausada" if "todo" in ctl["bloqueados"] else "activa", **ctl}


def select_and_persist(now: datetime | None = None, dry_run: bool = False) -> dict:
    now = now or datetime.now(timezone.utc)
    hoy = now.astimezone(timezone.utc).date()      # batch_date se calcula en UTC
    est = estado()
    out = {"elegidos": 0, "sin_precio": 0, "sin_candidato": 0,
           "estado": est["estado"], "motivos": est["motivos"], "decisiones": []}
    if dry_run:
        # Cuántas decisiones salen de cada fuente y de cada mercado. A las 08:00
        # UTC, con el límite de MAX_EDAD_PRECIO, muchos partidos europeos de la
        # tarde solo tienen precio de API-Football: sus goles (db/041) son los
        # que cuentan en ese caso. Hay que verlo ANTES de activar, porque lo
        # publicado es inmutable.
        out["resumen"] = {"por_fuente": {}, "por_mercado": {}}
    if est["estado"] != "activa":
        return out
    # Lo que se guarda tiene que entrar en el payload del lote del día. Si ese
    # lote no lleva el bloque, la fila quedaría fuera de la cadena: no se
    # elige nada. La vista previa (`dry_run`) no guarda, así que sigue valiendo.
    if not dry_run and not hashchain.lote_lleva_alta(hoy):
        out["estado"] = "sin_corte"
        out["motivos"] = [*out["motivos"],
                          "El lote de hoy no lleva bloque de alta probabilidad "
                          "(LOTE_ALTA_PROB_DESDE no fijada o posterior a hoy): no se elige nada"]
        return out
    if not dry_run and _lote_sellado(hoy):
        out["motivos"] = [*out["motivos"], "Lote del día ya sellado: no se elige nada"]
        return out
    excluir = set(est["bloqueados"])
    habilitados = ap.MERCADOS_GOLES_HABILITADOS
    rho = _rho_activo()
    for m in _partidos(now):
        snap = _snapshot(m["match_id"], m["kickoff_utc"], now)
        if snap is None:
            out["sin_precio"] += 1
            continue
        totales = (_totales(m["match_id"], snap.as_of) if snap.source == "the_odds_api"
                   else _totales_af(m["match_id"], snap.as_of))
        res = decidir(snap, totales, rho, habilitados, excluir)
        if res is None:
            out["sin_candidato"] += 1
            continue
        c, ajuste = res
        ref_price, ref_book = _ref(snap, totales, c)
        fila = (m["match_id"], c.market, c.selection, c.line, round(c.prob, 6),
                round(1.0 / c.prob, 4), ref_price, ref_book, snap.source, snap.as_of,
                json.dumps(ajuste) if ajuste else None)
        if dry_run:
            out["decisiones"].append({"match_id": m["match_id"], "market": c.market,
                                      "selection": c.selection, "line": c.line,
                                      "prob": round(c.prob, 4), "ref_price": ref_price,
                                      "ref_book": ref_book, "odds_source": snap.source})
            continue
        out["elegidos"] += execute(
            """INSERT INTO alta_prob_picks
                 (match_id, market, selection, line, prob, fair_price,
                  ref_price, ref_book, odds_source, odds_as_of, fit)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (match_id) DO NOTHING""", fila) or 0
    if dry_run:
        for d in out["decisiones"]:
            for clave, valor in (("por_fuente", d["odds_source"]), ("por_mercado", d["market"])):
                out["resumen"][clave][valor] = out["resumen"][clave].get(valor, 0) + 1
    log.info("Alta probabilidad: %s", {k: v for k, v in out.items() if k != "decisiones"})
    return out


def settle_pending() -> dict:
    rows = query(
        """SELECT a.alta_id, a.market, a.selection, a.line, m.home_goals, m.away_goals
           FROM alta_prob_picks a
           JOIN matches m ON m.match_id = a.match_id
           LEFT JOIN alta_prob_results r ON r.alta_id = a.alta_id
           WHERE r.alta_id IS NULL AND m.status = 'finished'
             AND m.home_goals IS NOT NULL""")
    for r in rows:
        outcome, _, _ = _settle_outcome(r["market"], r["selection"], r["line"],
                                        int(r["home_goals"]), int(r["away_goals"]))
        execute(
            """INSERT INTO alta_prob_results (alta_id, outcome, home_goals, away_goals)
               VALUES (%s,%s,%s,%s) ON CONFLICT (alta_id) DO NOTHING""",
            (r["alta_id"], outcome, int(r["home_goals"]), int(r["away_goals"])))
    return {"settled": len(rows)}


def informe_publico() -> dict:
    est = estado()
    proximos = query(
        f"""SELECT a.match_id, m.league_id, m.kickoff_utc,
                   th.canonical_name AS local, ta.canonical_name AS visitante,
                   a.market, a.selection, a.line, a.prob, a.fair_price,
                   a.ref_price, a.ref_book, b.batch_date, b.chain_sha256
            FROM alta_prob_picks a
            JOIN matches m ON m.match_id = a.match_id
            JOIN teams th ON th.team_id = m.home_team_id
            JOIN teams ta ON ta.team_id = m.away_team_id
            {_sql_sellado()}
            WHERE m.kickoff_utc > now()
            ORDER BY m.kickoff_utc""")
    for p in proximos:
        p["texto"] = ap.texto(p["market"], p["selection"], p["line"], p["local"], p["visitante"])
        # Precisión PÚBLICA reducida (decisión del usuario, 2026-10-06). La
        # probabilidad exacta es la de Pinnacle sin margen, y en doble
        # oportunidad `1 − prob` es la probabilidad justa del resultado
        # EXCLUIDO, donde viven los picks de valor: con cualquier cuota blanda
        # se reconstruiría su edge (`cuota × p − 1`, umbral 2 %). A punto
        # porcentual entero el error de `1 − prob` es ±0,5 puntos sobre un 13 %,
        # es decir ±3,8 % en precio: más que el umbral, no sirve para recalcular
        # el criterio. El lote sellado y la tabla conservan el valor exacto
        # (el hash no cambia): esto solo recorta lo que sale por la API.
        p["prob"] = round(float(p["prob"]), 2)
        p["fair_price"] = round(1.0 / p["prob"], 2)
    return {"estado": est["estado"], "motivos": est["motivos"],
            "proximos": proximos, "historial": ap.historial(_liquidados(None))}


if __name__ == "__main__":
    a = argparse.ArgumentParser(description="Línea de alta probabilidad")
    a.add_argument("accion", choices=["preview", "settle", "informe"])
    accion = a.parse_args().accion
    out = {"preview": lambda: select_and_persist(dry_run=True),
           "settle": settle_pending, "informe": informe_publico}[accion]()
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
