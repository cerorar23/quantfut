"""Análisis del destacado de tenis: casillas según el mercado y resumen redactado (decisión del titular, 2026-11-17).

Los datos salen de `tenis-db` (TML, carga semanal), no del feed de estadísticas de API-Tennis, que vence: Hold % y Break %
por superficie, ranking, forma, cara a cara y partidos a tres sets. Los jugadores se resuelven por nombre exacto y
ÚNICO dentro del circuito del torneo; si hay duda no se muestra nada (mejor sin tarjeta que con los datos de otro).

Misma regla que fútbol: la proyección y las casillas son las primeras de la lista de prioridad de la receta con dato,
una casilla nunca queda vacía, y el resumen lo redacta la IA solo con las cifras entregadas (`analisis_futbol`).
"""
from __future__ import annotations

import logging
import re
import time
from datetime import date, timedelta
from typing import Any

import os

import psycopg
from psycopg.rows import dict_row

from ..db import query
from . import analisis_futbol as ia

log = logging.getLogger(__name__)

RECETAS = {"winner": "ganador", "games_handicap": "ganador", "sets_handicap": "ganador", "set_winner": "ganador",
           "games_total": "duracion", "sets_total": "duracion", "tiebreak": "duracion"}
PRIORIDAD = {"ganador": ("saque", "rank", "h2h", "resto", "forma", "superficie"),
             "duracion": ("saque", "tres_sets", "resto", "forma", "superficie")}
CASILLAS = 3
VENTANA_DIAS = 365
MIN_SAQUE = 15        # partidos con estadística de saque para fiarse de un Hold % / Break %
MIN_SUPERFICIE = 8    # partidos en la superficie para usar la cifra de esa superficie
MIN_FORMA = 5
MIN_TRES_SETS = 10
TTL_S = 3600.0

GLOSARIO = (
    "Meaning of each item in 'datos' (a = first player, b = second player; n_a/n_b = matches counted, last 52 weeks; "
    "'sup' says whether a figure is on the match surface or on all surfaces): "
    "saque = % of service games held; resto = % of the opponent's service games broken (return); "
    "rank = ranking position (a lower number is better); forma = wins in the last n matches; "
    "h2h = head-to-head wins (a, b) in n meetings; superficie = % of matches won on the match surface; "
    "tres_sets = % of recent best-of-3 matches that went to a deciding third set."
)

_cache: dict[tuple, tuple[float, Any]] = {}


def _cacheado(clave: tuple, ttl: float, calcular):
    ahora = time.monotonic()
    hit = _cache.get(clave)
    if hit and hit[0] > ahora:
        return hit[1]
    valor = calcular()
    if len(_cache) > 400:
        _cache.clear()
    _cache[clave] = (ahora + ttl, valor)
    return valor


def _consultar(sql: str, params=()) -> list[dict]:
    """Lectura de `tenis-db` (mismo DSN que `tenis_v2`); sin DSN, la base principal (entornos de prueba)."""
    dsn = os.getenv("TENIS_PG_DSN")
    if not dsn:
        return query(sql, params)
    with psycopg.connect(dsn, row_factory=dict_row) as c, c.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def receta_de(market: str | None) -> str:
    return RECETAS.get(market or "", "ganador")


def circuito_de(liga: str | None) -> str | None:
    t = (liga or "").strip().upper()
    return "atp" if t.startswith("ATP") else "wta" if t.startswith("WTA") else None


def superficie_de(texto: str | None) -> str | None:
    t = (texto or "").strip().lower()
    return t if t in ("hard", "clay", "grass") else None


# --- datos de tenis-db ----------------------------------------------------------------------------------

def jugador_id(nombre: str, circuito: str) -> int | None:
    """Coincidencia exacta (sin mayúsculas) y única. Dos personas con el mismo nombre = no se adivina."""
    filas = _consultar(
        "SELECT DISTINCT a.jugador_id FROM tenis.jugador_asercion a JOIN tenis.jugador j USING (jugador_id) "
        "WHERE a.campo = 'nombre' AND lower(a.valor) = lower(%s) AND j.circuito = %s", (nombre, circuito))
    return int(filas[0]["jugador_id"]) if len(filas) == 1 else None


SQL_PARTIDOS = """
SELECT p.partido_id, p.mejor_de, e.superficie, e.lunes_semana,
       CASE WHEN p.jugador_1 = %(j)s THEN 1 ELSE 2 END AS lado, r.ganador, r.sets,
       s1.juegos_saque, s1.bp_afrontados, s1.bp_salvados,
       s2.juegos_saque AS o_js, s2.bp_afrontados AS o_bpa, s2.bp_salvados AS o_bps
FROM tenis.partido p
JOIN tenis.edicion e ON e.edicion_id = p.edicion_id
JOIN LATERAL (SELECT ganador, sets FROM tenis.resultado r WHERE r.partido_id = p.partido_id
              AND r.estado = 'completado' AND r.visible_desde <= now() ORDER BY r.recibido_en DESC LIMIT 1) r ON true
LEFT JOIN LATERAL (SELECT juegos_saque, bp_afrontados, bp_salvados FROM tenis.estadistica s
                   WHERE s.partido_id = p.partido_id AND s.visible_desde <= now()
                     AND s.lado = (CASE WHEN p.jugador_1 = %(j)s THEN 1 ELSE 2 END)
                   ORDER BY s.recibido_en DESC LIMIT 1) s1 ON true
LEFT JOIN LATERAL (SELECT juegos_saque, bp_afrontados, bp_salvados FROM tenis.estadistica s
                   WHERE s.partido_id = p.partido_id AND s.visible_desde <= now()
                     AND s.lado = (CASE WHEN p.jugador_1 = %(j)s THEN 2 ELSE 1 END)
                   ORDER BY s.recibido_en DESC LIMIT 1) s2 ON true
WHERE (p.jugador_1 = %(j)s OR p.jugador_2 = %(j)s) AND p.visible_desde <= now()
  AND e.lunes_semana BETWEEN %(desde)s AND %(hasta)s AND r.ganador IS NOT NULL
ORDER BY e.lunes_semana DESC, p.partido_id DESC
"""


def _pct(parte: float, total: float) -> float | None:
    return 100.0 * parte / total if total else None


def _saque_resto(filas: list[dict]) -> tuple[float | None, float | None, int]:
    """(Hold %, Break %, partidos con estadística). Break conseguido = punto de quiebre que el rival no salvó."""
    con = [f for f in filas if None not in (f["juegos_saque"], f["bp_afrontados"], f["bp_salvados"])
           and f["juegos_saque"] > 0]
    cedidos = sum(f["bp_afrontados"] - f["bp_salvados"] for f in con)
    juegos = sum(f["juegos_saque"] for f in con)
    rivales = [f for f in filas if None not in (f["o_js"], f["o_bpa"], f["o_bps"]) and f["o_js"] > 0]
    logrados = sum(f["o_bpa"] - f["o_bps"] for f in rivales)
    juegos_rival = sum(f["o_js"] for f in rivales)
    hold = 100.0 - _pct(cedidos, juegos) if juegos else None
    return hold, _pct(logrados, juegos_rival), min(len(con), len(rivales))


def perfil_de_filas(filas: list[dict], superficie: str | None) -> dict:
    """Todo lo que las casillas necesitan de un jugador, a partir de sus partidos de los últimos 52 semanas."""
    en_sup = [f for f in filas if superficie and f["superficie"] == superficie]
    hold, brk, n = _saque_resto(filas)
    hold_s, brk_s, n_s = _saque_resto(en_sup)
    ganados = lambda fs: sum(1 for f in fs if f["ganador"] == f["lado"])  # noqa: E731
    bo3 = [f for f in filas if f["mejor_de"] == 3][:20]
    tres = [f for f in bo3 if sum(1 for s in (f["sets"] or []) if s and s[0] is not None) == 3]
    return {"n": len(filas), "hold": hold, "brk": brk, "n_saque": n, "hold_s": hold_s, "brk_s": brk_s,
            "n_saque_s": n_s, "n_s": len(en_sup), "victorias_s": ganados(en_sup),
            "forma": ganados(filas[:10]), "n_forma": len(filas[:10]),
            "tres": len(tres), "n_bo3": len(bo3)}


def _perfil(jid: int, superficie: str | None) -> dict:
    hoy = date.today()

    def calcular():
        filas = _consultar(SQL_PARTIDOS, {"j": jid, "desde": hoy - timedelta(days=VENTANA_DIAS), "hasta": hoy})
        return perfil_de_filas(filas, superficie)
    perfil = _cacheado(("perfil", jid, superficie), TTL_S, calcular)
    return perfil


def _ranking_pareja(a: int, b: int, circuito: str) -> tuple[int | None, int | None]:
    """Posición de cada uno en la MISMA semana (la última que tienen los dos): la última fila de cada jugador es de
    semanas distintas y daba «1 contra 1» (17-nov-2026). Con más de 35 días de antigüedad no se muestra."""
    def calcular():
        filas = _consultar("SELECT jugador_id, fecha_publicacion, posicion FROM tenis.ranking WHERE jugador_id = ANY(%s) "
                           "AND circuito = %s AND visible_desde <= now() AND fecha_publicacion >= %s "
                           "ORDER BY fecha_publicacion DESC", ([a, b], circuito, date.today() - timedelta(days=120)))
        por: dict[int, list] = {a: [], b: []}
        for f in filas:
            if f["jugador_id"] in por and f["posicion"] is not None:
                por[f["jugador_id"]].append((f["fecha_publicacion"], int(f["posicion"])))
        if not por[a] or not por[b]:
            return None, None
        comun = min(por[a][0][0], por[b][0][0])
        if (date.today() - comun).days > 35:
            return None, None
        elegir = lambda xs: next((pos for fch, pos in xs if fch <= comun), None)  # noqa: E731
        return elegir(por[a]), elegir(por[b])
    return _cacheado(("ranking", min(a, b), max(a, b), a, circuito), TTL_S, calcular)


def _h2h(a: int, b: int) -> tuple[int, int]:
    def calcular():
        filas = _consultar(
            "SELECT CASE WHEN r.ganador = 1 THEN p.jugador_1 ELSE p.jugador_2 END AS gana FROM tenis.partido p "
            "JOIN LATERAL (SELECT ganador FROM tenis.resultado r WHERE r.partido_id = p.partido_id "
            "AND r.estado = 'completado' AND r.visible_desde <= now() ORDER BY r.recibido_en DESC LIMIT 1) r ON true "
            "WHERE ((p.jugador_1 = %(a)s AND p.jugador_2 = %(b)s) OR (p.jugador_1 = %(b)s AND p.jugador_2 = %(a)s)) "
            "AND p.visible_desde <= now() AND r.ganador IS NOT NULL", {"a": a, "b": b})
        return sum(1 for f in filas if f["gana"] == a), sum(1 for f in filas if f["gana"] == b)
    return _cacheado(("h2h", min(a, b), max(a, b), a), TTL_S, calcular)


# --- casillas -------------------------------------------------------------------------------------------

def _redondo(v: float | None) -> int | None:
    return None if v is None else round(v)


def _casilla(id_: str, ctx: dict) -> dict | None:
    pa, pb, sup = ctx["pa"], ctx["pb"], ctx["superficie"]
    if id_ in ("saque", "resto"):
        campo = "hold" if id_ == "saque" else "brk"
        usa_sup = bool(sup) and all(p["n_saque_s"] >= MIN_SUPERFICIE and p[campo + "_s"] is not None for p in (pa, pb))
        sufijo, n = ("_s", "n_saque_s") if usa_sup else ("", "n_saque")
        if any(p[n] < (MIN_SUPERFICIE if usa_sup else MIN_SAQUE) for p in (pa, pb)):
            return None
        va, vb = pa[campo + sufijo], pb[campo + sufijo]
        if va is None or vb is None:
            return None
        return {"id": id_, "a": _redondo(va), "b": _redondo(vb), "n_a": pa[n], "n_b": pb[n],
                "sup": sup if usa_sup else "todas"}
    if id_ == "rank":
        a, b = ctx["rank_a"], ctx["rank_b"]
        return {"id": "rank", "a": a, "b": b} if a and b else None
    if id_ == "forma":
        if min(pa["n_forma"], pb["n_forma"]) < MIN_FORMA:
            return None
        return {"id": "forma", "a": pa["forma"], "b": pb["forma"], "n_a": pa["n_forma"], "n_b": pb["n_forma"]}
    if id_ == "h2h":
        a, b = ctx["h2h"]
        return {"id": "h2h", "a": a, "b": b, "n": a + b} if a + b >= 2 else None
    if id_ == "superficie":
        if not sup or min(pa["n_s"], pb["n_s"]) < MIN_SUPERFICIE:
            return None
        return {"id": "superficie", "a": _redondo(_pct(pa["victorias_s"], pa["n_s"])),
                "b": _redondo(_pct(pb["victorias_s"], pb["n_s"])), "n_a": pa["n_s"], "n_b": pb["n_s"], "sup": sup}
    if id_ == "tres_sets":
        if min(pa["n_bo3"], pb["n_bo3"]) < MIN_TRES_SETS:
            return None
        return {"id": "tres_sets", "a": _redondo(_pct(pa["tres"], pa["n_bo3"])),
                "b": _redondo(_pct(pb["tres"], pb["n_bo3"])), "n_a": pa["n_bo3"], "n_b": pb["n_bo3"]}
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


_NUM = re.compile(r"(\d+(?:[.,]\d+)?)")
_HCP = re.compile(r"^(.*?)\s*([+-]\d+(?:[.,]\d+)?)\s*$")


def significado(tipo: str, selection: str) -> str | None:
    """Lo que quiere decir el pronóstico, en inglés y sin ambigüedad entre idiomas (ver `analisis_futbol.significado`)."""
    sel = (selection or "").strip()
    if tipo == "winner":
        return f"{sel} wins the match"
    if tipo in ("games_total", "sets_total"):
        n = _NUM.search(sel)
        cosa = "total games" if tipo == "games_total" else "total sets"
        if n:
            return f"{'More' if sel.lower().startswith('más') or sel.lower().startswith('mas') else 'Fewer'} than {n.group(1).replace(',', '.')} {cosa} in the match"
        return None
    if tipo == "tiebreak":
        return "At least one tie-break is played" if sel.lower() in ("sí", "si", "yes") else "No tie-break is played"
    if tipo in ("games_handicap", "sets_handicap"):
        m = _HCP.match(sel)
        if m:
            cosa = "games" if tipo == "games_handicap" else "sets"
            return (f"{m.group(1)} covers the {cosa} handicap {m.group(2)}: the {cosa} won by {m.group(1)} plus "
                    f"{m.group(2)} must be more than the opponent's")
    return None


def construir(evento_id: str, home: str, away: str, liga: str | None, superficie: str | None,
              mercado: dict) -> dict | None:
    """Bloque `analisis` del destacado de tenis, o None si no hay datos fiables de los dos jugadores."""
    try:
        circuito = circuito_de(liga)
        if not circuito or not mercado:
            return None
        ja, jb = jugador_id(home, circuito), jugador_id(away, circuito)
        if not ja or not jb or ja == jb:
            return None
        sup = superficie_de(superficie)
        tipo = re.sub(r"-\d+$", "", str(mercado.get("id") or ""))
        ctx = {"pa": _perfil(ja, sup), "pb": _perfil(jb, sup), "superficie": sup,
               "h2h": _h2h(ja, jb)}
        ctx["rank_a"], ctx["rank_b"] = _ranking_pareja(ja, jb, circuito)
        receta = receta_de(tipo)
        tarjetas = casillas(receta, ctx)
        if not tarjetas:
            return None
        out: dict[str, Any] = {"receta": receta, "casillas": tarjetas, "resumen": None}
        prob = float(mercado["probability"])
        hechos = {"partido": f"{home} vs {away}", "superficie": sup,
                  "pronostico": f"{mercado.get('label')}: {mercado.get('selection')}",
                  "mercado": receta, "probabilidad_pct": round(prob * 100), "datos": tarjetas}
        sig = significado(tipo, str(mercado.get("selection") or ""))
        if sig:
            hechos["significado"] = sig
        out["resumen"] = ia.resumen_para(str(evento_id), f"tenis|{mercado.get('id')}", hechos, "tennis", GLOSARIO)
        return out
    except Exception:  # noqa: BLE001 - sin análisis la app sigue con su tarjeta compacta
        log.exception("análisis de tenis del evento %s", evento_id)
        return None


def para_evento(evento: dict) -> dict | None:
    """Análisis del destacado de un evento del JSON público de tenis (el mismo que lee la app en `/web/deportes/tenis`).
    Lleva `mercado_id` para que la app solo lo use si su destacado es ese mismo mercado."""
    destacado = evento.get("destacado")
    destacado_id = str(destacado["id"]) if isinstance(destacado, dict) and destacado.get("id") is not None else None
    mercado = next((m for m in evento.get("markets") or [] if str(m.get("id")) == destacado_id), None)
    if mercado is None or evento.get("status") == "cancelled":
        return None
    out = construir(str(evento.get("id")), str(evento.get("home")), str(evento.get("away")), evento.get("league"),
                    evento.get("surface"), mercado)
    return None if out is None else {**out, "mercado_id": destacado_id}
