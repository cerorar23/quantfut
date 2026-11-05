"""Todos los contratos cotizados evaluables con distribuciones ya selladas; solo lectura."""
from __future__ import annotations

import math
import numpy as np

from ..contratos.validar import validar_equipo, validar_jugador
from ..v2.contratos_apuesta import desde_masas
from .comun import contrato_linea

PROPS = {"player_points": "puntos", "player_rebounds": "rebotes",
         "player_assists": "asistencias", "player_threes": "triples"}
MERCADOS = ("h2h", "spreads", "totals", "team_totals", *PROPS)


def construir(partido_id, local, visitante, sellos, cuotas):
    """Todas las líneas y lados, con cuotas recibidas antes del objetivo de SU sello.

    Las cuotas llegan por recepción descendente; se conserva la más reciente de
    cada casa y contrato que ya existía al objetivo de ese pronóstico.
    """
    por_sello, proyecciones = {}, []
    for mercado, entidad, h, objetivo, sellado, escenarios, dist in sellos:
        if mercado == "equipo":
            validar_equipo(dist)
        elif mercado in {f"jugador:{m}" for m in PROPS.values()}:
            validar_jugador(dist)
            proyecciones.append({"player_id": entidad, "player": escenarios.get("nombre"),
                                "team": local if escenarios.get("lado") == "local" else visitante,
                                "market": mercado.split(":", 1)[1], "estimate": dist["media"],
                                "p10": dist["p10"], "p50": dist["p50"], "p90": dist["p90"],
                                "p_juega": dist["p_juega"], "sealed_at": sellado.isoformat(), "seal": h})
        else:
            continue
        por_sello[(mercado, entidad)] = (h, objetivo, sellado, escenarios, dist)
    rows = {}
    equipo = por_sello.get(("equipo", None))
    if equipo:
        h, _, fecha, _, d = equipo
        for lado, prob in (("local", d["p_local"]), ("visit", 1 - d["p_local"])):
            rows[("h2h", None, None, lado)] = {
                "id": f"winner-{partido_id}-{lado}", "market": "winner", "side": lado,
                "team": local if lado == "local" else visitante, "line": None,
                "probability": prob, "push_probability": 0., "conditional": False,
                "player": None, "player_id": None, "sealed_at": fecha.isoformat(), "seal": h,
                "estimate": None, "price": None, "book": None, "odds_at": None}
    vistos = set()
    for mercado, entidad, linea, lado, casa, precio, recibido in cuotas:
        if mercado not in MERCADOS:
            continue
        sello = por_sello.get((f"jugador:{PROPS[mercado]}", entidad)) if mercado in PROPS else equipo
        if not sello or recibido > sello[1]:
            continue
        h, _, fecha, esc, d = sello
        linea = None if mercado == "h2h" else float(linea) if linea is not None else None
        precio = float(precio)
        if not math.isfinite(precio) or precio <= 1 or (mercado != "h2h" and (linea is None or not math.isfinite(linea))):
            continue
        clave = (mercado, entidad, linea, lado)
        if (*clave, casa) in vistos:
            continue
        vistos.add((*clave, casa))
        player, team, estimate = None, None, None
        conditional = mercado in PROPS
        if conditional:
            if lado not in ("over", "under"):
                continue
            pmf = np.asarray(d["pmf"], float)
            contrato = desde_masas(np.arange(len(pmf)), pmf, linea).salida(d["p_juega"])
            player, estimate = esc.get("nombre"), d["media"]
            team = local if esc.get("lado") == "local" else visitante
        elif mercado == "h2h":
            if lado not in ("local", "visit"):
                continue
            contrato = {"p_mas": d["p_local"], "p_menos": 1 - d["p_local"], "p_push": 0.}
            team = local if lado == "local" else visitante
        elif mercado == "spreads":
            if lado not in ("local", "visit"):
                continue
            contrato = contrato_linea(d, "margen", -linea if lado == "local" else linea)
            team = local if lado == "local" else visitante
        else:
            if lado not in ("over", "under"):
                continue
            if mercado == "team_totals":
                if entidad not in (local, visitante):
                    continue
                team = entidad
                metrica = "puntos_local" if entidad == local else "puntos_visitante"
            else:
                metrica = "total"
            contrato = contrato_linea(d, metrica, linea)
        prob = contrato["p_mas" if lado in ("over", "local") else "p_menos"]
        if prob is None:
            continue
        anterior = rows.get(clave)
        if anterior and anterior["price"] is not None and (anterior["price"] > precio or
                (anterior["price"] == precio and anterior["book"] <= casa)):
            continue
        rows[clave] = {"id": f"{mercado}-{entidad}-{linea}-{lado}",
                       "market": {"h2h": "winner", "spreads": "handicap", "totals": "game_total", "team_totals": "team_points"}.get(mercado, mercado),
                       "side": lado, "team": team, "line": linea, "probability": prob,
                       "push_probability": contrato["p_push"], "conditional": conditional,
                       "player": player, "player_id": entidad if conditional else None,
                       "sealed_at": fecha.isoformat(), "seal": h, "estimate": estimate,
                       "price": precio, "book": casa, "odds_at": recibido.isoformat()}
    return {"partido_id": partido_id, "markets": list(rows.values()), "projections": proyecciones}


def resolver(salida, local, visitante, valores):
    """Liquida con valores finales reales; la ausencia de una estadística queda pendiente."""
    a, b = valores.get((local, "puntos")), valores.get((visitante, "puntos"))
    final = a is not None and b is not None
    metricas = {"player_points": "puntos", "player_rebounds": "rebotes",
                "player_assists": "asistencias", "player_threes": "triples_anotados"}
    for row in salida["markets"]:
        row["outcome"] = None
        if not final:
            continue
        mercado, entidad = row["market"], row["player_id"]
        if entidad is not None:
            if valores.get((entidad, "jugo")) == 0:
                row["outcome"] = "void"
                continue
            actual = valores.get((entidad, metricas[mercado]))
        elif mercado in ("winner", "handicap"):
            actual = a - b if row["side"] == "local" else b - a
            if mercado == "handicap":
                actual += row["line"]
        elif mercado == "game_total":
            actual = a + b
        else:
            actual = a if row["team"] == local else b
        if actual is None:
            continue
        linea = 0 if mercado in ("winner", "handicap") else row["line"]
        row["outcome"] = ("push" if actual == linea else "win" if
                          (actual < linea if row["side"] == "under" else actual > linea) else "loss")


def consultar(db, fila):
    pid, _, local, visitante, *_ = fila
    sellos = db.execute(
        "SELECT DISTINCT ON (mercado, entidad_id) mercado, entidad_id, hash, objetivo_en, sellado_en, escenarios, distribucion "
        "FROM nba.pronostico WHERE partido_id = %s AND periodo = 0 "
        "ORDER BY mercado, entidad_id, sellado_en DESC, pronostico_id DESC", (pid,)).fetchall()
    if not sellos:
        return {"partido_id": pid, "markets": [], "projections": []}
    cuotas = db.execute(
        "SELECT mercado, entidad_id, linea, lado, casa, cuota, recibido_en FROM nba.cuota "
        "WHERE partido_id = %s AND periodo = 0 AND fase IN ('pre','cierre') "
        "AND mercado = ANY(%s) AND recibido_en <= %s ORDER BY recibido_en DESC, cuota_id DESC",
        (pid, list(MERCADOS), max(s[3] for s in sellos))).fetchall()
    salida = construir(pid, local, visitante, sellos, cuotas)
    resultados = db.execute(
        "SELECT DISTINCT ON (d.entidad_id, m.nombre) d.entidad_id, m.nombre, d.valor "
        "FROM nba.dato d JOIN nba.metrica m USING (metrica_id) JOIN nba.fuente f ON f.fuente = d.fuente "
        "WHERE d.partido_id = %s AND d.periodo = 0 AND d.fase = 'final' AND d.valor IS NOT NULL "
        "AND m.nombre = ANY(%s) ORDER BY d.entidad_id, m.nombre, f.prioridad, d.recibido_en DESC, d.dato_id DESC",
        (pid, ["puntos", "rebotes", "asistencias", "triples_anotados", "jugo"])).fetchall()
    resolver(salida, local, visitante, {(ent, m): valor for ent, m, valor in resultados})
    nombres = {local: fila[4], visitante: fila[5]}
    for row in [*salida["markets"], *salida["projections"]]:
        row["team"] = nombres.get(row["team"])
    return salida
