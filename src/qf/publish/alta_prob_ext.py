"""
Alta probabilidad ampliada, 62-95 % (decisión del usuario, 2026-10-11).

Tabla aparte (`alta_prob_ext`, db/057): TODOS los candidatos aprobados de cada
partido, no uno solo. La línea de 80-95 % de `alta_prob_datos` no cambia. Qué
mercados entran lo fija la prueba histórica de los tramos 62-80 %
(`eval/alta_prob_calibracion.py --amplio`, constantes `alta_prob.*_EXT`).

Mismo orden que la línea original: `daily` llama a `select_and_persist()` justo
ANTES de `seal()`, y el lote lleva el bloque `alta_ext`
(`hashchain.LOTE_ALTA_EXT_DESDE`). Lo que no está en un lote sellado después de
decidirse no se enseña (`alta_prob_datos._sql_sellado`).
"""
from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import datetime, timezone

from ..config import settings
from ..db import execute, query
from ..model.devig import devig
from . import alta_prob as ap
from . import alta_prob_datos as ad
from . import hashchain
from . import picks as pk
from . import ventana

log = logging.getLogger(__name__)


def sql_sellado() -> str:
    return ad._sql_sellado(hashchain.LOTE_ALTA_EXT_DESDE)


def _liquidados() -> list[dict]:
    return query(
        f"""SELECT a.match_id, a.market, a.prob, a.ref_price, r.outcome, m.kickoff_utc
            FROM alta_prob_ext a
            JOIN alta_prob_ext_results r ON r.ext_id = a.ext_id
            JOIN matches m ON m.match_id = a.match_id
            {sql_sellado()}
            WHERE r.outcome IN ('win', 'loss')""")


def estado() -> dict:
    if not settings.alta_prob_ext_enabled:
        return {"estado": "desactivada", "bloqueados": [], "motivos": ["Ampliación desactivada"]}
    ctl = ap.control(_liquidados())
    return {"estado": "pausada" if "todo" in ctl["bloqueados"] else "activa", **ctl}


def _partidos(now: datetime) -> list[dict]:
    return query(
        """SELECT m.match_id, m.kickoff_utc, m.league_id, m.home_team_id,
                  m.away_team_id, m.referee
           FROM matches m
           JOIN leagues l ON l.league_id = m.league_id
           WHERE m.status = 'scheduled' AND l.active
             AND NOT EXISTS (SELECT 1 FROM alta_prob_ext e WHERE e.match_id = m.match_id)
             AND m.kickoff_utc BETWEEN %s AND %s
           ORDER BY m.kickoff_utc""",
        (now + pk.MIN_LEAD, ventana.fin_ventana(now, ap.HORIZONTE)))


def candidatos(snap: pk.Snapshot, totales: list[dict], rho: float | None,
               corners: list[ap.Candidato], excluir: set[str],
               cuota: Callable[[ap.Candidato], tuple] | None = None
               ) -> tuple[list[ap.Candidato], dict | None]:
    """Candidatos aprobados de un partido (62-95 %) y el ajuste de goles que los respalda.
    Con `cuota` (`ad.cotizador`), solo los que tienen cuota de referencia."""
    q = snap.books[settings.sharp_book]
    fair = devig([q[s] for s in ad.SEL], settings.devig_method)
    p = {s: float(fair[i]) for i, s in enumerate(ad.SEL)}
    cands = ap.candidatos_1x2(p) + ap.candidatos_doble(p)
    ajuste = None
    if rho is not None:
        linea = ad.linea_pinnacle(totales)
        if linea is not None:
            ajuste = ap.ajuste_goles(p, linea[0], linea[1], rho)
    cands += ap.candidatos_goles(ajuste, ap.GOLES_EXT)
    cands += ap.candidatos_equipo(ajuste, ap.MERCADOS_EQUIPO_HABILITADOS)
    cands += ap.candidatos_btts(ajuste, ap.BTTS_EXT)
    cands += ap.candidatos_handicap(p, ajuste, ap.HANDICAP_HABILITADOS)
    cands += corners
    if cuota is not None:
        cands = [c for c in cands if cuota(c)[0] is not None]
    return ap.elegir_ext(cands, excluir), ajuste


def select_and_persist(now: datetime | None = None, dry_run: bool = False) -> dict:
    now = now or datetime.now(timezone.utc)
    hoy = now.astimezone(timezone.utc).date()
    est = estado()
    out = {"elegidos": 0, "sin_precio": 0, "sin_candidato": 0, "estado": est["estado"],
           "motivos": est["motivos"], "decisiones": []}
    if est["estado"] != "activa":
        return out
    if not dry_run and not hashchain.lote_lleva_alta_ext(hoy):
        out["estado"] = "sin_corte"
        out["motivos"] = [*out["motivos"], "El lote de hoy no lleva el bloque alta_ext "
                          "(LOTE_ALTA_EXT_DESDE no fijada o posterior a hoy): no se elige nada"]
        return out
    if not dry_run and ad._lote_sellado(hoy):
        out["motivos"] = [*out["motivos"], "Lote del día ya sellado: no se elige nada"]
        return out
    from . import escalera_datos as ed
    excluir, rho, modelos = set(est["bloqueados"]), ad._rho_activo(), ed.Modelos(now)
    for m in _partidos(now):
        snap = ad._snapshot(m["match_id"], m["kickoff_utc"], now)
        if snap is None:
            out["sin_precio"] += 1
            continue
        totales, equipos = ad._referencias(m["match_id"], snap, now)
        filas_mercados = ed._cuotas_mercados(m["match_id"], now)
        corners, fits_corners = ad._corners(m, now, modelos, filas_mercados, ap.CORNERS_EXT)
        cuota = ad.cotizador(m["match_id"], snap, totales, equipos, filas_mercados)
        elegidos, ajuste = candidatos(snap, totales, rho, corners, excluir, cuota)
        if not elegidos:
            out["sin_candidato"] += 1
            continue
        for c in elegidos:
            fit = (fits_corners[(c.market, c.selection, c.line)] if c.market in ad.CORNERS
                   else ajuste if c.market in ap.MERCADOS_CON_AJUSTE else None)
            ref_price, ref_book = cuota(c)
            fila = (m["match_id"], c.market, c.selection, c.line, round(c.prob, 6),
                    round(1.0 / c.prob, 4), ref_price, ref_book, snap.source, snap.as_of,
                    json.dumps(fit) if fit else None)
            if dry_run:
                out["decisiones"].append({"match_id": m["match_id"], "market": c.market,
                                          "selection": c.selection, "line": c.line,
                                          "prob": round(c.prob, 4), "ref_price": ref_price})
                continue
            out["elegidos"] += execute(
                """INSERT INTO alta_prob_ext
                     (match_id, market, selection, line, prob, fair_price,
                      ref_price, ref_book, odds_source, odds_as_of, fit)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT ON CONSTRAINT alta_prob_ext_uq DO NOTHING""", fila) or 0
    log.info("Alta probabilidad ampliada: %s", {k: v for k, v in out.items() if k != "decisiones"})
    return out


def settle_pending(now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    rows = query(
        """SELECT a.ext_id, a.market, a.selection, a.line, m.home_goals, m.away_goals,
                  m.home_corners, m.away_corners, m.kickoff_utc
           FROM alta_prob_ext a
           JOIN matches m ON m.match_id = a.match_id
           LEFT JOIN alta_prob_ext_results r ON r.ext_id = a.ext_id
           WHERE r.ext_id IS NULL AND m.status = 'finished' AND m.home_goals IS NOT NULL""")
    n = 0
    for r in rows:
        res = ad.resultado(r, now)
        if res is None:
            continue
        n += execute(
            """INSERT INTO alta_prob_ext_results (ext_id, outcome, home_goals, away_goals, valor)
               VALUES (%s,%s,%s,%s,%s) ON CONFLICT (ext_id) DO NOTHING""",
            (r["ext_id"], res[0], int(r["home_goals"]), int(r["away_goals"]), res[1])) or 0
    return {"settled": n}


if __name__ == "__main__":
    import argparse
    a = argparse.ArgumentParser(description="Alta probabilidad ampliada 62-95 %")
    a.add_argument("accion", choices=["preview", "settle"])
    out = {"preview": lambda: select_and_persist(dry_run=True),
           "settle": settle_pending}[a.parse_args().accion]()
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
