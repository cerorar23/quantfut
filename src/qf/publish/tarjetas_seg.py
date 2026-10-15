"""
Seguimiento SIN PUBLICAR de los candidatos de tarjetas (decisión del usuario, 2026-10-14).

Las tarjetas dominan los tickets del parley y casi no tienen historial propio. Cada día se
guardan en `tarjetas_seg` (db/068) TODOS los candidatos de tarjetas de los partidos con precio:
las líneas habilitadas de `estadisticas_mercado.LINEAS_HABILITADAS["cards"]`, con la misma
probabilidad que usaría el parley (la menor entre modelo y mercado, `escalera_datos.prudente`)
y la mejor cuota de las casas de la lista. Así la muestra crece con decenas de filas al día en
vez de las 2-3 patas del parley, y `eval/calibracion_mercados.py` mide prometido frente a real.

NO SE PUBLICA: ninguna ruta de la API ni de la app lee esta tabla, y no influye en ningún
pronóstico ni en el control. Es inmutable y va sellada en el lote (`tarjetas_seg`,
`hashchain.LOTE_TARJETAS_DESDE`), con el mismo orden que la ampliada: `daily` llama a
`select_and_persist()` justo ANTES de `seal()`.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from ..config import settings
from ..db import execute, query
from ..model import estadisticas_mercado as em
from . import alta_prob as ap
from . import alta_prob_datos as ad
from . import hashchain
from . import picks as pk
from . import ventana

log = logging.getLogger(__name__)

MERCADO = "cards"


def sql_sellado() -> str:
    return ad._sql_sellado(hashchain.LOTE_TARJETAS_DESDE)


def _partidos(now: datetime) -> list[dict]:
    return query(
        """SELECT m.match_id, m.kickoff_utc, m.league_id, m.home_team_id,
                  m.away_team_id, m.referee
           FROM matches m
           JOIN leagues l ON l.league_id = m.league_id
           WHERE m.status = 'scheduled' AND l.active
             AND NOT EXISTS (SELECT 1 FROM tarjetas_seg t WHERE t.match_id = m.match_id)
             AND m.kickoff_utc BETWEEN %s AND %s
           ORDER BY m.kickoff_utc""",
        (now + pk.MIN_LEAD, ventana.fin_ventana(now, ap.HORIZONTE)))


def candidatos(m: dict, now: datetime, modelos, filas_af: list[dict]) -> list[dict]:
    """
    Candidatos de tarjetas de un partido: línea, lado, probabilidad prudente, cuota y casa.
    La línea solo entra si el mercado cotiza los dos lados (`prudente`) y alguna casa de la
    lista da cuota: sin eso no hay parlay que tomar, y tampoco aquí.
    """
    from . import escalera_datos as ed
    acc = modelos.de(m["league_id"], em.FUENTE[MERCADO])
    lam = (acc.lambdas(now, m["home_team_id"], m["away_team_id"], m.get("referee"))
           if acc is not None else None)
    if lam is None:
        return []
    out = []
    for lado, linea in em.LINEAS_HABILITADAS[MERCADO]:
        modelo = em.prob(MERCADO, lam, lado, linea)
        c = ed.prudente(ap.Candidato(MERCADO, lado, linea, modelo), filas_af)
        if c is None:
            continue
        precio, casa, hora = ed._ref_af(filas_af, c)
        if precio is None:
            continue
        out.append({"selection": lado, "line": linea, "prob": c.prob, "ref_price": precio,
                    "ref_book": casa, "odds_as_of": hora,
                    "fit": {"modelo": round(modelo, 6), "mercado": round(ed.prob_mercado(filas_af, c), 6),
                            "lambdas": [round(lam[0], 4), round(lam[1], 4)]}})
    return out


def select_and_persist(now: datetime | None = None, dry_run: bool = False) -> dict:
    now = now or datetime.now(timezone.utc)
    hoy = now.astimezone(timezone.utc).date()
    out = {"estado": "activa", "guardados": 0, "partidos": 0, "sin_modelo": 0, "decisiones": []}
    if not settings.tarjetas_seg_enabled and not dry_run:
        return {**out, "estado": "desactivado"}
    if not dry_run and not hashchain.lote_lleva_tarjetas(hoy):
        return {**out, "estado": "sin_corte",
                "motivo": "LOTE_TARJETAS_DESDE no fijada o posterior a hoy: no se guarda nada"}
    if not dry_run and ad._lote_sellado(hoy):
        return {**out, "estado": "lote_sellado", "motivo": "Lote del día ya sellado: no se guarda nada"}
    from . import escalera_datos as ed
    modelos = ed.Modelos(now)
    for m in _partidos(now):
        filas_af = ed._cuotas_af(m["match_id"], now)
        if not filas_af:
            continue
        cands = candidatos(m, now, modelos, filas_af)
        if not cands:
            out["sin_modelo"] += 1
            continue
        out["partidos"] += 1
        for c in cands:
            if dry_run:
                out["decisiones"].append({"match_id": m["match_id"], **{k: c[k] for k in
                                          ("selection", "line", "ref_price", "ref_book")},
                                          "prob": round(c["prob"], 4)})
                continue
            out["guardados"] += execute(
                """INSERT INTO tarjetas_seg
                     (match_id, market, selection, line, prob, fair_price, ref_price, ref_book,
                      odds_source, odds_as_of, fit)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT ON CONSTRAINT tarjetas_seg_uq DO NOTHING""",
                (m["match_id"], MERCADO, c["selection"], c["line"], round(c["prob"], 6),
                 round(1.0 / c["prob"], 4), c["ref_price"], c["ref_book"], "api_football",
                 c["odds_as_of"], json.dumps(c["fit"]))) or 0
    log.info("Seguimiento de tarjetas: %s", {k: v for k, v in out.items() if k != "decisiones"})
    return out


def settle_pending(now: datetime | None = None) -> dict:
    """Misma liquidación que la escalera: total = amarillas + rojas, push si es igual a la línea."""
    from . import escalera_datos as ed
    now = now or datetime.now(timezone.utc)
    rows = query(
        """SELECT a.seg_id, a.market, a.selection, a.line, m.status, m.kickoff_utc,
                  m.home_goals, m.away_goals, m.home_corners, m.away_corners,
                  m.home_yellow, m.away_yellow, m.home_red, m.away_red
           FROM tarjetas_seg a
           JOIN matches m ON m.match_id = a.match_id
           LEFT JOIN tarjetas_seg_results r ON r.seg_id = a.seg_id
           WHERE r.seg_id IS NULL
             AND ((m.status = 'finished' AND m.home_goals IS NOT NULL)
                  OR (m.status = 'postponed' AND m.kickoff_utc < %s))""",
        (now - ed.MARGEN_APLAZADO,))
    n = 0
    for r in rows:
        res = ed.resultado(r, now)
        if res is None:
            continue
        n += execute(
            """INSERT INTO tarjetas_seg_results (seg_id, outcome, home_goals, away_goals, valor)
               VALUES (%s,%s,%s,%s,%s) ON CONFLICT (seg_id) DO NOTHING""",
            (r["seg_id"], *res)) or 0
    return {"settled": n}


if __name__ == "__main__":
    import argparse
    a = argparse.ArgumentParser(description="Seguimiento sin publicar de tarjetas")
    a.add_argument("accion", choices=["preview", "settle"])
    out = {"preview": lambda: select_and_persist(dry_run=True),
           "settle": settle_pending}[a.parse_args().accion]()
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
