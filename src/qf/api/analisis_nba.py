"""Análisis del destacado de NBA: casillas según el mercado y resumen redactado (decisión del titular, 2026-11-17).

Todo viene de lo que `nba-api` ya publica y `nba_datos` ya lee: el sello del modelo (puntos proyectados de cada equipo,
días de descanso y posesiones proyectadas), las estadísticas de equipo a la fecha del partido y el reporte oficial de
bajas. Aquí no se calcula ninguna probabilidad. Los mercados de jugador no tienen receta y conservan la tarjeta compacta.

Misma regla que fútbol y tenis: las tres primeras casillas con dato de la lista de prioridad de la receta, una casilla
nunca queda vacía, y el resumen lo redacta la IA solo con las cifras entregadas (`analisis_futbol.resumen_para`).
"""
from __future__ import annotations

import logging
import math
from datetime import timedelta
from typing import Any

from . import analisis_futbol as ia
from . import nba_datos

log = logging.getLogger(__name__)

RECETAS = {"winner": "ganador", "handicap": "ganador", "game_total": "total", "team_points": "equipo"}
PRIORIDAD = {"ganador": ("proy_margen", "forma", "dif", "descanso", "bajas"),
             "total": ("proy_total", "ritmo", "h2h_total", "ataque", "descanso", "bajas"),
             "equipo": ("proy_equipo", "ataque_defensa", "ritmo", "descanso", "bajas")}
CASILLAS = 3
MIN_PARTIDOS = 5      # partidos de la temporada para fiarse de un promedio de puntos
MIN_H2H = 2
BUSCAR_ATRAS, BUSCAR_ADELANTE = 4, 4

GLOSARIO = (
    "Meaning of each item in 'datos' (a = home team, b = away team): "
    "proy_total = total points the MODEL projects for the game ('total'; a, b = projected points of each team; a "
    "projection, NOT past performance); proy_margen = projected point margin ('margen' > 0 favours the home team); "
    "proy_equipo = points the model projects for one team ('a'); "
    "ritmo = possessions the model projects for the game ('pos'); "
    "forma = wins and losses of each team in its last 6 games (a_w, a_l, b_w, b_l); "
    "dif = average point differential per game this season (points scored minus conceded; n_a/n_b = games); "
    "ataque = average points scored per game this season; "
    "ataque_defensa = the team's average points scored ('a') against the points per game its opponent concedes ('b'); "
    "h2h_total = average total points in the recent head-to-head games ('avg', n games); "
    "descanso = days of rest before the game for each team; "
    "bajas = players ruled OUT in the official injury report, for each team."
)


def _num(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _equipos_est(est: dict | None, local: str, visita: str) -> tuple[dict, dict]:
    """Los dos bloques de equipo de `estadisticas`, casados por nombre (si no, por orden)."""
    teams = [t for t in (est or {}).get("teams") or [] if isinstance(t, dict)]
    if len(teams) != 2:
        return {}, {}
    por_nombre = {str(t.get("name")): t for t in teams}
    return por_nombre.get(local, teams[0]), por_nombre.get(visita, teams[1])


def _promedios(t: dict) -> tuple[float, float, int] | None:
    sc = t.get("scoring") or {}
    pf, pc, n = _num(sc.get("points_for")), _num(sc.get("points_against")), int(sc.get("games") or 0)
    return (pf, pc, n) if pf is not None and pc is not None and n >= MIN_PARTIDOS else None


def _casilla(id_: str, ctx: dict) -> dict | None:
    mu, esc, ea, eb = ctx["mu"], ctx["escenarios"], ctx["est_a"], ctx["est_b"]
    if id_ == "proy_margen":
        return {"id": id_, "margen": round(mu[0] - mu[1], 1), "a": round(mu[0], 1), "b": round(mu[1], 1)}
    if id_ == "proy_total":
        out = {"id": id_, "total": round(mu[0] + mu[1], 1), "a": round(mu[0], 1), "b": round(mu[1], 1)}
        if ctx["tipo"] == "game_total" and ctx["linea"] is not None:
            out["linea"] = ctx["linea"]
        return out
    if id_ == "proy_equipo":
        lado = ctx["lado"]
        return {"id": id_, "a": round(mu[0] if lado == "a" else mu[1], 1), "equipo": lado,
                "linea": ctx["linea"]} if lado else None
    if id_ == "ritmo":
        pos = _num(esc.get("posesiones_regulacion"))
        return {"id": id_, "pos": round(pos, 1)} if pos else None
    if id_ == "forma":
        la, lb = ea.get("last6") or {}, eb.get("last6") or {}
        if min(int(la.get("games") or 0), int(lb.get("games") or 0)) < MIN_PARTIDOS:
            return None
        return {"id": id_, "a_w": int(la["won"]), "a_l": int(la["lost"]), "b_w": int(lb["won"]),
                "b_l": int(lb["lost"]), "n": min(int(la["games"]), int(lb["games"]))}
    if id_ in ("dif", "ataque"):
        pa, pb = _promedios(ea), _promedios(eb)
        if not pa or not pb:
            return None
        if id_ == "dif":
            return {"id": id_, "a": round(pa[0] - pa[1], 1), "b": round(pb[0] - pb[1], 1), "n_a": pa[2], "n_b": pb[2]}
        return {"id": id_, "a": round(pa[0], 1), "b": round(pb[0], 1), "n_a": pa[2], "n_b": pb[2]}
    if id_ == "ataque_defensa":
        lado = ctx["lado"]
        propio, rival = (_promedios(ea), _promedios(eb)) if lado == "a" else (_promedios(eb), _promedios(ea))
        if not lado or not propio or not rival:
            return None
        return {"id": id_, "a": round(propio[0], 1), "b": round(rival[1], 1), "equipo": lado}
    if id_ == "h2h_total":
        h = ctx["h2h"]
        n, avg = len(h.get("matches") or []), _num(h.get("average_total"))
        return {"id": id_, "avg": round(avg, 1), "n": n} if avg and n >= MIN_H2H else None
    if id_ == "descanso":
        d = esc.get("descanso_dias") or {}
        a, b = d.get("local"), d.get("visitante")
        return {"id": id_, "a": int(a), "b": int(b)} if isinstance(a, int) and isinstance(b, int) else None
    if id_ == "bajas":
        dis = ctx["disponibilidad"]
        if not dis or dis.get("estado") != "reporte_aplicado":
            return None
        cuenta = lambda lado: sum(1 for j in (dis.get(lado) or {}).get("jugadores") or [] if j.get("estado") == "Out")  # noqa: E731
        return {"id": id_, "a": cuenta("local"), "b": cuenta("visitante")}
    return None


def casillas(receta: str, ctx: dict) -> list[dict]:
    out = []
    for id_ in PRIORIDAD[receta]:
        c = _casilla(id_, ctx)
        if c:
            out.append(c)
        if len(out) == CASILLAS:
            break
    return out


def significado(mercado: dict) -> str | None:
    """Lo que quiere decir el pronóstico, en inglés y sin ambigüedad entre idiomas (ver `analisis_futbol.significado`)."""
    tipo, lado, linea = mercado.get("market"), mercado.get("side"), _num(mercado.get("line"))
    equipo = mercado.get("team")
    if tipo == "winner":
        return f"{equipo} wins the game" if equipo else None
    if tipo == "handicap" and equipo and linea is not None:
        return (f"{equipo} covers the point spread {linea:+g}: its points plus {linea:+g} must be more than the "
                f"opponent's")
    if tipo == "game_total" and linea is not None:
        return f"{'More' if lado == 'over' else 'Fewer'} than {linea:g} total points in the game"
    if tipo == "team_points" and equipo and linea is not None:
        return f"{equipo} scores {'more' if lado == 'over' else 'fewer'} than {linea:g} points"
    return None


def construir(evento: dict, mercado: dict, est: dict | None, disponibilidad: dict | None) -> dict | None:
    """Bloque `analisis` del destacado, o None si el mercado no tiene receta o falta el sello del modelo."""
    receta = RECETAS.get(str(mercado.get("market")))
    pron = evento.get("pronostico") or {}
    mu = pron.get("mu")
    if not receta or not (isinstance(mu, list) and len(mu) == 2 and all(_num(x) is not None for x in mu)):
        return None
    local, visita = str(evento["local"]["nombre"]), str(evento["visitante"]["nombre"])
    ea, eb = _equipos_est(est, local, visita)
    lado = None
    if mercado.get("market") == "team_points":
        lado = "a" if mercado.get("team") == local else "b" if mercado.get("team") == visita else None
    ctx = {"mu": [float(mu[0]), float(mu[1])], "escenarios": pron.get("escenarios") or {}, "est_a": ea, "est_b": eb,
           "h2h": (est or {}).get("h2h") or {}, "disponibilidad": disponibilidad, "tipo": mercado.get("market"),
           "linea": _num(mercado.get("line")), "lado": lado}
    tarjetas = casillas(receta, ctx)
    if not tarjetas:
        return None
    out: dict[str, Any] = {"receta": receta, "casillas": tarjetas, "resumen": None}
    prob = _num(mercado.get("probability"))
    if prob:
        sig = significado(mercado)
        hechos = {"partido": f"{local} vs {visita}", "pronostico": sig or str(mercado.get("market")),
                  "mercado": receta, "probabilidad_pct": round(prob * 100), "datos": tarjetas}
        if sig:
            hechos["significado"] = sig
        out["resumen"] = ia.resumen_para(str(evento["id"]), f"nba|{mercado.get('id')}", hechos,
                                         "basketball (NBA)", GLOSARIO)
    return out


def _buscar(partido_id: str) -> tuple[dict, Any] | None:
    hoy = nba_datos.hoy_et()
    ventana = nba_datos.cartelera_ventana(hoy - timedelta(days=BUSCAR_ATRAS), hoy + timedelta(days=BUSCAR_ADELANTE))
    for fecha, partidos in ventana.items():
        for p in partidos:
            if str(p.get("id")) == partido_id:
                return p, fecha
    return None


def para_partido(partido_id: str) -> dict | None:
    """Análisis del destacado de un partido de NBA (el que elige el servidor en `mercados.destacado`).
    Lleva `mercado_id` para que la app solo lo use si su destacado es ese mismo mercado."""
    try:
        hallado = _buscar(partido_id)
        if not hallado:
            return None
        evento, fecha = hallado
        pid = int(evento["id"])
        mercado = nba_datos.mercados(pid, fecha).get("destacado")
        if not isinstance(mercado, dict):
            return None
        out = construir(evento, mercado, nba_datos.estadisticas(pid, fecha), nba_datos.disponibilidad(pid))
        return None if out is None else {**out, "mercado_id": mercado.get("id")}
    except Exception:  # noqa: BLE001 - sin análisis la app sigue con su tarjeta compacta
        log.exception("análisis de NBA del partido %s", partido_id)
        return None
