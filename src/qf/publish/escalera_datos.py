"""
Base de datos del reto escalera: elegir el siguiente escalón, liquidar e
informar. Las reglas están en `escalera.py`.

ORDEN: `daily.run()` llama a `select_and_persist()` justo ANTES de `seal()` y
`hashchain._collect` mete en el lote los retos creados y los escalones
decididos ese día. Un escalón solo se enseña si su lote existe y se selló
DESPUÉS de decidirlo, como la línea de alta probabilidad: lo que no está en un
lote sellado no existe.
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ..config import settings
from ..db import execute, query, query_one
from ..eval.clv import _settle_outcome
from ..model import estadisticas_mercado as em
from ..model.devig import devig
from ..model.pricing import score_matrix
from . import alta_prob as ap
from . import alta_prob_datos as ad
from . import escalera as es
from . import hashchain
from . import picks as pk

log = logging.getLogger(__name__)

# Un partido aplazado se da por nulo pasado este margen desde su hora original,
# como hacen las casas. Si luego se juega, el escalón sigue nulo (inmutable).
MARGEN_APLAZADO = timedelta(hours=48)


def _sql_sellado() -> str:
    """Mismo criterio que `alta_prob_datos._sql_sellado`, con la fecha de la escalera."""
    desde = hashchain.LOTE_ESCALERA_DESDE
    corte = (f"AND b.batch_date >= DATE '{desde.isoformat()}'"
             if desde is not None else "AND FALSE")
    return f"""JOIN prediction_batches b
             ON b.batch_date = (p.decided_at AT TIME ZONE 'UTC')::date
            AND p.decided_at <= b.created_at
            {corte}"""


def _retos() -> list[dict]:
    return query("SELECT * FROM escalera_retos ORDER BY reto_id")


def _pasos(reto_id: int, solo_sellados: bool = False) -> list[dict]:
    return query(
        f"""SELECT p.paso_id, p.reto_id, p.paso, p.match_id, p.market, p.selection, p.line,
                   p.prob, p.fair_price, p.price, p.book, p.decided_at,
                   r.outcome, r.home_goals, r.away_goals, r.valor,
                   m.kickoff_utc, m.league_id,
                   th.canonical_name AS local, ta.canonical_name AS visitante
                   {', b.batch_date, b.chain_sha256' if solo_sellados else ''}
            FROM escalera_pasos p
            JOIN matches m ON m.match_id = p.match_id
            JOIN teams th ON th.team_id = m.home_team_id
            JOIN teams ta ON ta.team_id = m.away_team_id
            LEFT JOIN escalera_resultados r ON r.paso_id = p.paso_id
            {_sql_sellado() if solo_sellados else ''}
            WHERE p.reto_id = %s
            ORDER BY p.paso""", (reto_id,))


def estado_reto(reto: dict, pasos: list[dict]) -> dict:
    return es.estado(Decimal(str(reto["stake_inicial"])), int(reto["pasos_objetivo"]),
                     reto["freeroll_x"],
                     [es.Paso(int(p["paso"]), float(p["price"]), p["outcome"]) for p in pasos])


# --------------------------------------------------------------------------
# Elección
# --------------------------------------------------------------------------

def _partidos(now: datetime) -> list[dict]:
    return query(
        """SELECT m.match_id, m.kickoff_utc, m.league_id, m.home_team_id, m.away_team_id,
                  m.referee
           FROM matches m JOIN leagues l ON l.league_id = m.league_id
           WHERE m.status = 'scheduled' AND l.active
             AND m.kickoff_utc BETWEEN %s AND %s
           ORDER BY m.kickoff_utc""",
        (now + pk.MIN_LEAD, now + es.HORIZONTE))


# --- Córners y tarjetas: modelo estadístico, sin cuotas -----------------------

class Modelos:
    """
    Acumuladores de córners y tarjetas por liga, construidos UNA vez por
    pasada con los partidos terminados antes de `now` (punto en el tiempo).
    """
    def __init__(self, now: datetime):
        self.now = now
        self._cache: dict[tuple[str, str], em.Acumulador | None] = {}

    def de(self, liga: str, mercado: str) -> em.Acumulador | None:
        clave = (liga, mercado)
        if clave not in self._cache:
            self._cache[clave] = self._construir(liga, mercado)
        return self._cache[clave]

    def _construir(self, liga: str, mercado: str) -> em.Acumulador | None:
        if mercado == "corners":
            valores = "home_corners AS vl, away_corners AS vv"
            hay = "home_corners IS NOT NULL AND away_corners IS NOT NULL"
        else:
            valores = ("home_yellow + coalesce(home_red, 0) AS vl, "
                       "away_yellow + coalesce(away_red, 0) AS vv")
            hay = "home_yellow IS NOT NULL AND away_yellow IS NOT NULL"
        filas = query(
            f"""SELECT kickoff_utc, home_team_id, away_team_id, referee, {valores}
                FROM matches
                WHERE league_id = %s AND status = 'finished' AND {hay}
                  AND kickoff_utc < %s AND kickoff_utc > %s - interval '4 years'
                ORDER BY kickoff_utc""", (liga, self.now, self.now))
        if not filas:
            return None
        acc = em.acumulador(mercado)
        for f in filas:
            acc.agregar(f["kickoff_utc"], f["home_team_id"], f["away_team_id"],
                        int(f["vl"]), int(f["vv"]), f["referee"])
        return acc


def _cuotas_af(match_id: str, now: datetime) -> list[dict]:
    """
    Última cotización de cada casa para ambos anotan, córners y tarjetas, ya
    recibida en `now` y con menos de MAX_EDAD_PRECIO.
    """
    return query(
        """SELECT DISTINCT ON (bookmaker, market, selection, line)
                  bookmaker, market, selection, line, price, provider_updated_at
           FROM af_odds_snapshots
           WHERE match_id = %s AND market IN ('btts', 'corners', 'cards')
             AND fetched_at <= %s AND provider_updated_at >= %s
           ORDER BY bookmaker, market, selection, line, provider_updated_at DESC""",
        (match_id, now, now - es.MAX_EDAD_PRECIO))


def _ref_af(rows: list[dict], c) -> tuple:
    """(cuota, casa, hora) de la mejor casa de la lista para ese mercado, lado y línea."""
    precios = [(float(r["price"]), pk.canonical_book(r["bookmaker"]), r["provider_updated_at"])
               for r in rows
               if pk.canonical_book(r["bookmaker"]) in settings.soft_books
               and r["market"] == c.market and r["selection"] == c.selection
               and (c.line is None or (r["line"] is not None
                                       and abs(float(r["line"]) - c.line) < 1e-9))]
    return max(precios) if precios else (None, None, None)


def _candidatos_estadisticos(m: dict, modelos: "Modelos") -> list:
    out = []
    for mercado, lineas in em.LINEAS_HABILITADAS.items():
        acc = modelos.de(m["league_id"], mercado)
        if acc is None:
            continue
        lam = acc.lambdas(modelos.now, m["home_team_id"], m["away_team_id"], m.get("referee"))
        if lam is None:
            continue
        for lado, linea in lineas:
            pr = em.prob_total(lam[0] + lam[1], em.PARAMETROS[mercado]["phi"], linea)[lado]
            out.append(ap.Candidato(mercado, lado, linea, pr))
    return out


def opciones(m: dict, now: datetime, rho: float | None,
             modelos: "Modelos | None" = None) -> list[es.Opcion] | None:
    """
    Todos los candidatos de un partido con la mejor cuota de la lista. Los de
    Pinnacle (1X2, goles, ambos anotan, hándicap) necesitan su precio vigente;
    córners y tarjetas salen del modelo estadístico y de las cuotas de
    API-Football. None si no hay ni precio de Pinnacle ni nada con cuota.
    """
    match_id, kickoff = m["match_id"], m["kickoff_utc"]
    out = []
    filas_af = _cuotas_af(match_id, now)
    snap = ad._snapshot(match_id, kickoff, now)
    if snap is not None:
        equipos: list[dict] = []
        if snap.source == "the_odds_api":
            totales = ad._totales(match_id, snap.as_of)
        elif snap.source == "api_football":
            totales = ad._totales_af(match_id, snap.as_of, now)
            equipos = ad._equipos_af(match_id, snap.as_of, now)
        else:
            totales = []
        q = snap.books[settings.sharp_book]
        fair = devig([q[s] for s in ad.SEL], settings.devig_method)
        p = {s: float(fair[i]) for i, s in enumerate(ad.SEL)}
        cands = ap.candidatos_1x2(p)
        linea = ad.linea_pinnacle(totales) if rho is not None else None
        ajuste = ap.ajuste_goles(p, linea[0], linea[1], rho) if linea else None
        cands += ap.candidatos_goles(ajuste, es.LINEAS_GOLES)
        cands += ap.candidatos_equipo(ajuste, ("home", "away"))
        mat = (score_matrix(ajuste["lambda"], ajuste["mu"], ajuste["rho"])
               if ajuste is not None else None)
        if mat is not None and es.BTTS_LADOS:
            si = float(1.0 - mat[0, :].sum() - mat[:, 0].sum() + mat[0, 0])
            cands += [ap.Candidato("btts", lado, None, si if lado == "yes" else 1.0 - si)
                      for lado in es.BTTS_LADOS]
        # Hándicap: solo hay cuotas de las casas en The Odds API.
        lineas_ah: list[dict] = []
        if es.LINEAS_HANDICAP and snap.source == "the_odds_api":
            cands += es.candidatos_handicap(p, mat)
            lineas_ah = _handicaps(match_id, snap.as_of)
        for c in cands:
            if c.market == "btts":
                price, book, _ = _ref_af(filas_af, c)
            elif c.market == "spreads":
                price, book = _ref_handicap(lineas_ah, c)
            else:
                price, book = ad._ref(snap, totales, c, equipos)
            if price is not None:
                out.append(es.Opcion(match_id, c, float(price), book, snap.source, snap.as_of))
    if modelos is not None and filas_af:
        for c in _candidatos_estadisticos(m, modelos):
            price, book, as_of = _ref_af(filas_af, c)
            if price is not None:
                out.append(es.Opcion(match_id, c, float(price), book, "api_football", as_of))
    return out if (snap is not None or out) else None


def _handicaps(match_id: str, as_of: datetime) -> list[dict]:
    """Hándicaps de la MISMA respuesta de The Odds API que el 1X2."""
    return query(
        """SELECT bookmaker, selection, line, price FROM odds_snapshots
           WHERE match_id = %s AND market = 'spreads' AND source = 'the_odds_api'
             AND captured_at = %s""",
        (match_id, as_of))


def _ref_handicap(rows: list[dict], c) -> tuple[float | None, str | None]:
    """Mejor cuota de la lista para ese lado y esa línea (la del propio lado)."""
    precios = [(float(r["price"]), pk.canonical_book(r["bookmaker"])) for r in rows
               if pk.canonical_book(r["bookmaker"]) in settings.soft_books
               and r["selection"] == c.selection and r["line"] is not None
               and abs(float(r["line"]) - c.line) < 1e-9]
    return max(precios) if precios else (None, None)


def _seis_en_mes(now: datetime) -> int:
    return query_one(
        """SELECT count(*) AS n FROM escalera_retos
           WHERE pasos_objetivo = 6
             AND date_trunc('month', created_at AT TIME ZONE 'UTC')
               = date_trunc('month', %s AT TIME ZONE 'UTC')""", (now,))["n"]


def select_and_persist(now: datetime | None = None, dry_run: bool = False) -> dict:
    now = now or datetime.now(timezone.utc)
    hoy = now.astimezone(timezone.utc).date()
    if not settings.escalera_enabled and not dry_run:
        return {"estado": "desactivado"}
    if not dry_run and not hashchain.lote_lleva_escalera(hoy):
        return {"estado": "sin_corte",
                "motivo": "LOTE_ESCALERA_DESDE no fijada o posterior a hoy: no se elige nada"}
    if not dry_run and ad._lote_sellado(hoy):
        return {"estado": "lote_sellado", "motivo": "Lote del día ya sellado: no se elige nada"}

    # Retos abiertos: los que esperan resultado y los que necesitan escalón.
    abiertos, en_curso, ocupados = [], [], set()
    for reto in _retos():
        pasos = _pasos(reto["reto_id"])
        st = estado_reto(reto, pasos)
        if st["estado"] in ("completado", "fallido"):
            continue
        abiertos.append(int(reto["pasos_objetivo"]))
        if st["estado"] == "en_curso":
            en_curso.append((reto["reto_id"], st["ganados"]))
        ocupados |= {p["match_id"] for p in pasos if p["outcome"] is None}

    rho = ad._rho_activo()
    todas, sin_precio = [], 0
    modelos = Modelos(now)
    for m in _partidos(now):
        res = opciones(m, now, rho, modelos)
        if res is None:
            sin_precio += 1
            continue
        todas.extend(res)
    plan = es.planificar(en_curso, abiertos, _seis_en_mes(now), todas, ocupados)
    out = {"estado": "elegido" if plan else "sin_candidato",
           "retos_abiertos": len(abiertos), "necesitan_escalon": len(en_curso),
           "evaluados": len(todas), "sin_precio": sin_precio,
           "en_rango": sum(1 for o in todas if es.CUOTA_MIN <= o.price <= es.CUOTA_MAX),
           "plan": [{"reto_id": r, "nuevo_de": n, **_opcion_json(o)} for r, n, o in plan]}
    if dry_run:
        mejores = sorted((o for o in todas if es.CUOTA_MIN <= o.price <= es.CUOTA_MAX),
                         key=lambda o: o.ev, reverse=True)[:12]
        out["mejores_en_rango"] = [_opcion_json(o) for o in mejores]
        return out

    for reto_id, nuevo_de, o in plan:
        if reto_id is None:
            reto_id = query_one(
                """INSERT INTO escalera_retos (stake_inicial, pasos_objetivo, cuota_min, cuota_max,
                                               ev_min, freeroll_x)
                   VALUES (%s, %s, %s, %s, %s, %s) RETURNING reto_id""",
                (es.STAKE, nuevo_de, es.CUOTA_MIN, es.CUOTA_MAX, es.EV_MIN, es.FREEROLL_X)
            )["reto_id"]
        siguiente = query_one("SELECT coalesce(max(paso), 0) + 1 AS n FROM escalera_pasos "
                              "WHERE reto_id = %s", (reto_id,))["n"]
        execute(
            """INSERT INTO escalera_pasos (reto_id, paso, match_id, market, selection, line, prob,
                                           fair_price, price, book, odds_source, odds_as_of)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (reto_id, siguiente, o.match_id, o.cand.market, o.cand.selection, o.cand.line,
             round(o.cand.prob, 6), round(1.0 / o.cand.prob, 4), o.price, o.book,
             o.odds_source, o.odds_as_of))
    log.info("Escalera: %s", out)
    return out


def _opcion_json(o: es.Opcion) -> dict:
    return {"match_id": o.match_id, "market": o.cand.market, "selection": o.cand.selection,
            "line": o.cand.line, "prob": round(o.cand.prob, 4), "price": o.price,
            "book": o.book, "ev_pct": round(o.ev * 100, 2)}


# --------------------------------------------------------------------------
# Liquidación e informe
# --------------------------------------------------------------------------

# Córners y tarjetas llegan con las estadísticas del partido. Si pasado este
# margen siguen sin llegar, el escalón se da por nulo (no se adivina).
MARGEN_SIN_ESTADISTICAS = timedelta(hours=72)


def total_estadistico(market: str, r: dict) -> int | None:
    """Córners, o tarjetas = amarillas + rojas, una por tarjeta (db/046)."""
    if market == "corners":
        vals = (r["home_corners"], r["away_corners"])
    else:
        vals = (r["home_yellow"], r["away_yellow"])
        if None in vals:
            return None
        vals = (*vals, r["home_red"] or 0, r["away_red"] or 0)
    return None if None in vals else int(sum(vals))


def resultado(r: dict, now: datetime) -> tuple | None:
    """(outcome, goles local, goles visitante, valor) o None si aún no se puede liquidar."""
    if r["status"] == "postponed":
        return ("void", None, None, None) if r["kickoff_utc"] < now - MARGEN_APLAZADO else None
    hg, ag = int(r["home_goals"]), int(r["away_goals"])
    if r["market"] in ("corners", "cards"):
        total = total_estadistico(r["market"], r)
        if total is None:
            if r["kickoff_utc"] < now - MARGEN_SIN_ESTADISTICAS:
                return ("void", None, None, None)
            return None
        line = float(r["line"])
        gana = total > line if r["selection"] == "over" else total < line
        return ("win" if gana else "loss", hg, ag, total)
    outcome, _, _ = _settle_outcome(r["market"], r["selection"], r["line"], hg, ag)
    # Las líneas de la escalera son enteras o medias: no hay medias ganadas.
    if outcome not in ("win", "loss", "push"):
        return ("void", None, None, None)
    return (outcome, hg, ag, None)


def settle_pending(now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    rows = query(
        """SELECT p.paso_id, p.market, p.selection, p.line, m.status, m.kickoff_utc,
                  m.home_goals, m.away_goals, m.home_corners, m.away_corners,
                  m.home_yellow, m.away_yellow, m.home_red, m.away_red
           FROM escalera_pasos p
           JOIN matches m ON m.match_id = p.match_id
           LEFT JOIN escalera_resultados r ON r.paso_id = p.paso_id
           WHERE r.paso_id IS NULL
             AND ((m.status = 'finished' AND m.home_goals IS NOT NULL)
                  OR (m.status = 'postponed' AND m.kickoff_utc < %s))""",
        (now - MARGEN_APLAZADO,))
    n = 0
    for r in rows:
        res = resultado(r, now)
        if res is None:
            continue
        n += execute(
            """INSERT INTO escalera_resultados (paso_id, outcome, home_goals, away_goals, valor)
               VALUES (%s,%s,%s,%s,%s) ON CONFLICT (paso_id) DO NOTHING""",
            (r["paso_id"], *res)) or 0
    return {"settled": n}


def texto(market: str, selection: str, line, local: str, visitante: str) -> str:
    if market == "spreads":
        return es.texto_handicap(selection, float(line), local, visitante)
    if market in ("corners", "cards"):
        return es.texto_total(market, selection, float(line))
    if market == "btts":
        return es.texto_btts(selection)
    return ap.texto(market, selection, line, local, visitante)


def _paso_publico(p: dict) -> dict:
    return {"paso": p["paso"], "match_id": p["match_id"], "league_id": p["league_id"],
            "kickoff_utc": p["kickoff_utc"], "local": p["local"], "visitante": p["visitante"],
            "texto": texto(p["market"], p["selection"], p["line"], p["local"], p["visitante"]),
            "market": p["market"],
            # Misma precisión pública reducida que la línea de alta probabilidad.
            "prob": round(float(p["prob"]), 2), "price": float(p["price"]), "book": p["book"],
            "outcome": p["outcome"],
            "marcador": (f"{p['home_goals']}-{p['away_goals']}"
                         if p["home_goals"] is not None else None),
            # Córners o tarjetas del partido, para enseñar con qué se liquidó.
            "valor": p.get("valor"),
            "batch_date": p.get("batch_date"), "chain_sha256": p.get("chain_sha256")}


def _json_estado(st: dict) -> dict:
    return {k: (str(v) if isinstance(v, Decimal) else v) for k, v in st.items()}


def informe_publico() -> dict:
    retos = query("SELECT * FROM escalera_retos ORDER BY reto_id")
    salida, escalones = [], []
    for reto in retos:
        pasos = _pasos(reto["reto_id"], solo_sellados=True)
        st = estado_reto(reto, pasos)
        escalones += [p for p in pasos if p["outcome"] in ("win", "loss")]
        salida.append({"reto_id": reto["reto_id"], "inicio": reto["created_at"],
                       "stake_inicial": str(reto["stake_inicial"]),
                       "pasos_objetivo": reto["pasos_objetivo"],
                       "cuota_min": reto["cuota_min"], "cuota_max": reto["cuota_max"],
                       "freeroll_x": reto["freeroll_x"],
                       **_json_estado(st),
                       "pasos": [_paso_publico(p) for p in pasos]})
    cerrados = [r for r in salida if r["estado"] in ("completado", "fallido")]
    actuales = [r for r in salida if r["estado"] not in ("completado", "fallido")]
    acumulado, serie = Decimal("0"), []
    for r in cerrados:
        acumulado += Decimal(r["ganancia"])
        serie.append({"reto_id": r["reto_id"], "ganancia": r["ganancia"], "acumulado": str(acumulado)})
    return {
        "activo": settings.escalera_enabled,
        "reglas": {"cuota_min": es.CUOTA_MIN, "cuota_max": es.CUOTA_MAX,
                   "longitudes": list(es.LONGITUDES), "max_seis_mes": es.MAX_SEIS_MES,
                   "stake": str(es.STAKE), "freeroll_x": es.FREEROLL_X, "ev_min": es.EV_MIN,
                   "lineas_handicap": list(es.LINEAS_HANDICAP)},
        "actuales": actuales,
        "historial": list(reversed(cerrados)),
        "resumen": es.resumen(cerrados),
        "por_longitud": {str(n): es.resumen([r for r in cerrados if r["pasos_objetivo"] == n])
                         for n in es.LONGITUDES},
        "serie": serie,
        "escalones": {"n": len(escalones),
                      "aciertos": sum(1 for p in escalones if p["outcome"] == "win"),
                      "prob_media": (round(sum(float(p["prob"]) for p in escalones)
                                           / len(escalones) * 100, 1) if escalones else None)},
    }


if __name__ == "__main__":
    a = argparse.ArgumentParser(description="Reto escalera")
    a.add_argument("accion", choices=["preview", "settle", "informe"])
    accion = a.parse_args().accion
    out = {"preview": lambda: select_and_persist(dry_run=True),
           "settle": settle_pending, "informe": informe_publico}[accion]()
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
