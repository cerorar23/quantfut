"""
Base de datos del parley del día: elegir, liquidar e informar. Las reglas
están en `parley.py`.

ORDEN: `daily.run()` llama a `select_and_persist()` justo ANTES de `seal()` y
`hashchain._collect` mete en el lote los tickets y patas decididos ese día. Un
ticket solo se enseña si su lote existe y se selló DESPUÉS de decidirlo: lo
que no está en un lote sellado no existe.
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timedelta, timezone

from ..config import settings
from ..db import conn, execute, query, query_one
from . import alta_prob_datos as ad
from . import escalera_datos as ed
from . import hashchain
from . import parley as pl
from . import picks as pk
from . import ventana

log = logging.getLogger(__name__)

# El "día" del parley: de la decisión (08:00 UTC) a 24 h después, que cubre la
# jornada americana entera (02:00-02:00 en México).
VENTANA = timedelta(hours=24)


def _sql_sellado() -> str:
    """Mismo criterio que `escalera_datos._sql_sellado`, con la fecha del parley."""
    desde = hashchain.LOTE_PARLEY_DESDE
    corte = (f"AND b.batch_date >= DATE '{desde.isoformat()}'"
             if desde is not None else "AND FALSE")
    return f"""JOIN prediction_batches b
             ON b.batch_date = (t.decided_at AT TIME ZONE 'UTC')::date
            AND t.decided_at <= b.created_at
            AND b.batch_kind = 'diario'
            {corte}"""


def _partidos(now: datetime) -> list[dict]:
    return query(
        """SELECT m.match_id, m.kickoff_utc, m.league_id, m.home_team_id, m.away_team_id,
                  m.referee
           FROM matches m JOIN leagues l ON l.league_id = m.league_id
           WHERE m.status = 'scheduled' AND l.active
             AND m.kickoff_utc BETWEEN %s AND %s
           ORDER BY m.kickoff_utc""",
        (now + pk.MIN_LEAD, ventana.fin_ventana(now, VENTANA)))


def candidatas(now: datetime) -> tuple[list, int]:
    """Patas que pueden entrar y cuántos partidos no tenían precio."""
    rho = ad._rho_activo()
    modelos = ed.Modelos(now)
    todas, sin_precio = [], 0
    for m in _partidos(now):
        res = ed.opciones(m, now, rho, modelos, incluir_doble=True)
        if res is None:
            sin_precio += 1
            continue
        todas.extend(res)
    return pl.filtrar(todas, now), sin_precio


def mercados_bloqueados() -> list[str]:
    """Grupos de mercado bloqueados por el control de la alta probabilidad, principal o ampliada."""
    from . import alta_prob_ext as ae
    return sorted({*ad.estado()["bloqueados"], *ae.estado()["bloqueados"]} - {"todo"})


def _liquidados() -> list[dict]:
    """Tickets liquidados y sellados, con la hora del primer partido (semana del control)."""
    return query(
        f"""SELECT t.escalon, r.outcome, r.factor_pago, r.prob_efectiva AS prob,
                   (SELECT min(m.kickoff_utc) FROM parley_patas p
                    JOIN matches m ON m.match_id = p.match_id
                    WHERE p.ticket_id = t.ticket_id) AS kickoff_utc
            FROM parley_tickets t
            JOIN parley_resultados r ON r.ticket_id = t.ticket_id
            {_sql_sellado()}""")


def _ticket_json(escalon: int, sel: tuple) -> dict:
    cuota = 1.0
    prob = 1.0
    for o in sel:
        cuota *= o.price
        prob *= o.cand.prob
    return {"escalon": escalon, "cuota_total": round(cuota, 4), "prob_total": round(prob, 6),
            "n_patas": len(sel),
            "patas": [{"match_id": o.match_id, "market": o.cand.market,
                       "selection": o.cand.selection, "line": o.cand.line,
                       "prob": round(o.cand.prob, 4), "price": o.price, "book": o.book}
                      for o in sel]}


def select_and_persist(now: datetime | None = None, dry_run: bool = False) -> dict:
    now = now or datetime.now(timezone.utc)
    dia = now.astimezone(timezone.utc).date()
    if not settings.parley_enabled and not dry_run:
        return {"estado": "desactivado"}
    if not dry_run and not hashchain.lote_lleva_parley(dia):
        return {"estado": "sin_corte",
                "motivo": "LOTE_PARLEY_DESDE no fijada o posterior a hoy: no se elige nada"}
    if not dry_run and ad._lote_sellado(dia):
        return {"estado": "lote_sellado", "motivo": "Lote del día ya sellado: no se elige nada"}
    if not dry_run and query_one("SELECT 1 AS x FROM parley_tickets WHERE dia = %s", (dia,)):
        return {"estado": "ya_elegido", "dia": dia.isoformat()}

    patas, sin_precio = candidatas(now)
    bloqueados = mercados_bloqueados()
    patas = pl.sin_bloqueados(patas, bloqueados)
    ctl = pl.control(_liquidados())
    plan = pl.armar_dia(patas, set(ctl["pausados"]))
    out = {"estado": "elegido" if plan else "sin_combinacion", "dia": dia.isoformat(),
           "candidatas": len(patas), "partidos": len({o.match_id for o in patas}),
           "sin_precio": sin_precio, "pausados": ctl["pausados"],
           "mercados_bloqueados": bloqueados,
           "tickets": [_ticket_json(e, sel) for e, sel in plan]}
    if dry_run or not plan:
        return out
    if not _guardar(dia, plan, out["tickets"]):
        return {"estado": "ya_elegido", "dia": dia.isoformat()}
    log.info("Parley: %s", {k: v for k, v in out.items() if k != "tickets"})
    return out


def _guardar(dia, plan: list, tickets: list[dict]) -> bool:
    """
    Todos los tickets y patas del día en UNA transacción: las filas son
    inmutables y un ticket a medias (cortado entre pata y pata) quedaría
    sellado para siempre. El candado por día y la segunda mirada dentro de él
    impiden que dos ejecuciones a la vez repartan el mismo partido en dos
    parlays. False si otra ejecución ya eligió el día.
    """
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                    (f"parley:{dia.isoformat()}",))
        cur.execute("SELECT 1 AS x FROM parley_tickets WHERE dia = %s", (dia,))
        if cur.fetchone():
            return False
        for (escalon, sel), t in zip(plan, tickets):
            cur.execute(
                """INSERT INTO parley_tickets (dia, escalon, cuota_total, prob_total, n_patas)
                   VALUES (%s, %s, %s, %s, %s) RETURNING ticket_id""",
                (dia, escalon, t["cuota_total"], t["prob_total"], t["n_patas"]))
            ticket_id = cur.fetchone()["ticket_id"]
            for o in sel:
                cur.execute(
                    """INSERT INTO parley_patas (ticket_id, match_id, market, selection, line,
                                                 prob, fair_price, price, book, odds_source,
                                                 odds_as_of, kickoff_utc)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                               (SELECT kickoff_utc FROM matches WHERE match_id = %s))""",
                    (ticket_id, o.match_id, o.cand.market, o.cand.selection, o.cand.line,
                     round(o.cand.prob, 6), round(1.0 / o.cand.prob, 4), o.price, o.book,
                     o.odds_source, o.odds_as_of, o.match_id))
    return True


def _resultado_pata(r: dict, now: datetime) -> tuple | None:
    """
    Como `escalera_datos.resultado`, pero contra la hora ORIGINAL del partido:
    `fixtures` sobrescribe `matches.kickoff_utc` y vuelve a 'scheduled' un
    partido reprogramado. Si no se jugó a su hora (±48 h), la pata es nula a
    las 48 h de la hora original, como en las casas; nunca espera semanas.
    """
    movido = abs(r["kickoff_utc"] - r["kickoff_original"]) > ed.MARGEN_APLAZADO
    if not movido and r["status"] == "finished" and r["home_goals"] is not None:
        return ed.resultado(r, now)
    if now > r["kickoff_original"] + ed.MARGEN_APLAZADO:
        return ("void", None, None, None)
    return None


def settle_pending(now: datetime | None = None) -> dict:
    """Liquida las patas con resultado y después los tickets con todas sus patas liquidadas."""
    now = now or datetime.now(timezone.utc)
    rows = query(
        """SELECT p.pata_id, p.market, p.selection, p.line, m.status, m.kickoff_utc,
                  p.kickoff_utc AS kickoff_original,
                  m.home_goals, m.away_goals, m.home_corners, m.away_corners,
                  m.home_yellow, m.away_yellow, m.home_red, m.away_red
           FROM parley_patas p
           JOIN matches m ON m.match_id = p.match_id
           LEFT JOIN parley_resultados_pata r ON r.pata_id = p.pata_id
           WHERE r.pata_id IS NULL
             AND ((m.status = 'finished' AND m.home_goals IS NOT NULL)
                  OR p.kickoff_utc < %s)""",
        (now - ed.MARGEN_APLAZADO,))
    n_patas = 0
    for r in rows:
        res = _resultado_pata(r, now)
        if res is None:
            continue
        n_patas += execute(
            """INSERT INTO parley_resultados_pata (pata_id, outcome, home_goals, away_goals, valor)
               VALUES (%s,%s,%s,%s,%s) ON CONFLICT (pata_id) DO NOTHING""",
            (r["pata_id"], *res)) or 0

    pendientes = query(
        """SELECT t.ticket_id, p.price, p.prob, rp.outcome
           FROM parley_tickets t
           JOIN parley_patas p ON p.ticket_id = t.ticket_id
           LEFT JOIN parley_resultados_pata rp ON rp.pata_id = p.pata_id
           LEFT JOIN parley_resultados r ON r.ticket_id = t.ticket_id
           WHERE r.ticket_id IS NULL
           ORDER BY t.ticket_id""")
    por_ticket: dict = {}
    for f in pendientes:
        por_ticket.setdefault(f["ticket_id"], []).append(
            (f["outcome"], float(f["price"]), float(f["prob"])))
    n_tickets = 0
    for ticket_id, patas in por_ticket.items():
        liq = pl.liquidar(patas)
        if liq is None:
            continue
        n_tickets += execute(
            """INSERT INTO parley_resultados (ticket_id, outcome, factor_pago, prob_efectiva)
               VALUES (%s,%s,%s,%s) ON CONFLICT (ticket_id) DO NOTHING""",
            (ticket_id, liq["outcome"], liq["factor_pago"], liq["prob_efectiva"])) or 0
    return {"patas": n_patas, "tickets": n_tickets}


def _pata_publica(p: dict) -> dict:
    return {"match_id": p["match_id"], "league_id": p["league_id"],
            "kickoff_utc": p["kickoff_utc"], "local": p["local"], "visitante": p["visitante"],
            "texto": ed.texto(p["market"], p["selection"], p["line"], p["local"], p["visitante"]),
            "market": p["market"],
            # Como en la escalera: la app redacta el texto en el idioma del usuario desde
            # estos campos (`pick_labels.dart`); sin ellos las patas salían siempre en español.
            "selection": p["selection"],
            "line": None if p["line"] is None else float(p["line"]),
            # Misma precisión pública reducida que la escalera.
            "prob": round(float(p["prob"]), 2), "price": float(p["price"]), "book": p["book"],
            "outcome": p["outcome"],
            "marcador": (f"{p['home_goals']}-{p['away_goals']}"
                         if p["home_goals"] is not None else None),
            "valor": p["valor"]}


def informe_publico() -> dict:
    sellado = _sql_sellado()
    tickets = query(
        f"""SELECT t.ticket_id, t.dia, t.escalon, t.cuota_total, t.prob_total, t.n_patas,
                   t.decided_at, b.chain_sha256, r.outcome, r.factor_pago, r.prob_efectiva
            FROM parley_tickets t
            {sellado}
            LEFT JOIN parley_resultados r ON r.ticket_id = t.ticket_id
            ORDER BY t.dia DESC, t.escalon""")
    patas = query(
        f"""SELECT p.ticket_id, p.match_id, p.market, p.selection, p.line, p.prob, p.price,
                   p.book, m.kickoff_utc, m.league_id,
                   COALESCE(th.display_name, th.canonical_name) AS local,
                   COALESCE(ta.display_name, ta.canonical_name) AS visitante,
                   rp.outcome, rp.home_goals, rp.away_goals, rp.valor
            FROM parley_patas p
            JOIN parley_tickets t ON t.ticket_id = p.ticket_id
            {sellado}
            JOIN matches m ON m.match_id = p.match_id
            JOIN teams th ON th.team_id = m.home_team_id
            JOIN teams ta ON ta.team_id = m.away_team_id
            LEFT JOIN parley_resultados_pata rp ON rp.pata_id = p.pata_id
            ORDER BY m.kickoff_utc, p.match_id""")
    por_ticket: dict = {}
    for p in patas:
        por_ticket.setdefault(p["ticket_id"], []).append(_pata_publica(p))
    dias: list[dict] = []
    for t in tickets:
        if not dias or dias[-1]["dia"] != t["dia"]:
            dias.append({"dia": t["dia"], "chain_sha256": t["chain_sha256"], "tickets": []})
        dias[-1]["tickets"].append({
            "escalon": t["escalon"], "cuota_total": float(t["cuota_total"]),
            "prob_total": round(float(t["prob_total"]), 4), "n_patas": t["n_patas"],
            "outcome": t["outcome"],
            "factor_pago": None if t["factor_pago"] is None else float(t["factor_pago"]),
            "patas": por_ticket.get(t["ticket_id"], [])})
    liq = _liquidados()
    return {
        "activo": settings.parley_enabled,
        "reglas": {"escalones": [{"escalon": e, "cuota_min": lo, "cuota_max": hi}
                                 for e, lo, hi in pl.ESCALONES],
                   "cuota_min_pata": pl.CUOTA_MIN_PATA, "cuota_max_pata": pl.CUOTA_MAX_PATA,
                   "min_patas": pl.MIN_PATAS, "max_patas": pl.MAX_PATAS},
        "control": pl.control(liq),
        "resumen": pl.resumen(liq),
        "dias": dias,
    }


if __name__ == "__main__":
    a = argparse.ArgumentParser(description="Parley del día")
    a.add_argument("accion", choices=["preview", "settle", "informe"])
    accion = a.parse_args().accion
    out = {"preview": lambda: select_and_persist(dry_run=True),
           "settle": settle_pending, "informe": informe_publico}[accion]()
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
