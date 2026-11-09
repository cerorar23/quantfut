"""Datos de fútbol para las páginas públicas (F3.1 de docs/plan_seo_redes_web_20261108.md).

Lee en el propio proceso lo que la web ya publica sin cuenta (`fichas._agenda`, `fichas._ficha` y la fila de
`predictions` con el 1X2). Nunca toca picks, alta probabilidad ni escalera: ese contenido es el que puede ser VIP, y
una página que no lo consulta no puede filtrarlo. Solo hay página de un partido si existe un pronóstico generado
ANTES de su inicio (la corrida diaria de las 03:00 de México, ver `publish/ventana.py`).

Fecha de la URL: día del partido en hora de México, la misma base que usa el pronóstico diario y `dia_cerrado`
(el `match_id` lleva la fecha UTC, que puede diferir en los partidos de la noche).
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from ..publish import ventana as ventana_pub
from . import fichas, nba_datos

log = logging.getLogger("qf.futbol_datos")

MEXICO = ventana_pub.MEXICO
DIAS_ATRAS = 1          # mismos límites que `STATS_DAYS` de frontend/app.js: -1..3
DIAS_ADELANTE = 3
SLUG_PARTIDO = nba_datos.SLUG_PARTIDO
slug_texto = nba_datos.slug_texto


class FutbolNoDisponible(Exception):
    """La base no respondió o el contenido está desactivado."""


def hoy_mx(ahora: datetime | None = None) -> date:
    return (ahora or datetime.now(timezone.utc)).astimezone(MEXICO).date()


def fecha_mx(kickoff: datetime) -> date:
    if kickoff.tzinfo is None:
        kickoff = kickoff.replace(tzinfo=timezone.utc)
    return kickoff.astimezone(MEXICO).date()


def dia_utc(d: date) -> tuple[datetime, datetime]:
    inicio = datetime(d.year, d.month, d.day, tzinfo=MEXICO).astimezone(timezone.utc)
    return inicio, inicio + timedelta(days=1)


def competicion_slug(nombre: str) -> str:
    return slug_texto(nombre)


def slug_partido(fila: dict) -> str:
    return (f"{slug_texto(fila['local']['nombre'])}-vs-{slug_texto(fila['visitante']['nombre'])}-"
            f"{fecha_mx(fila['kickoff_utc']).isoformat()}")


def ruta_partido(fila: dict) -> str:
    return f"/futbol/{competicion_slug(fila['liga']['nombre'])}/{slug_partido(fila)}/"


def _seguro(nombre: str, funcion):
    try:
        return funcion()
    except FutbolNoDisponible:
        raise
    except Exception as e:   # base caída, tabla ausente…: las páginas responden 503, no 404
        log.warning("fútbol: %s falló: %s", nombre, e)
        raise FutbolNoDisponible(str(e)) from e


def secciones_activas() -> dict[str, bool]:
    """`estadisticas` y `h2h` de la configuración de la app: si están apagadas la web tampoco las enseña."""
    from . import mobile
    feats = _seguro("configuración", mobile.features)
    return {k: bool((feats.get(k) or {}).get("enabled")) for k in ("estadisticas", "h2h")}


def agenda_dia(d: date) -> list[dict]:
    inicio, fin = dia_utc(d)
    return _seguro("agenda", lambda: fichas._cacheado(("seo_agenda", inicio), 120, lambda: fichas._agenda(inicio, fin, None)))


def ficha(match_id: str) -> dict | None:
    return _seguro("ficha", lambda: fichas._cacheado(("ficha", match_id), 300, lambda: fichas._ficha(match_id)))


def pronosticos(match_ids: list[str]) -> dict[str, dict]:
    """1X2 de cada partido con un pronóstico generado antes de su inicio: {match_id: {probs, modelo, generada}}."""
    if not match_ids:
        return {}
    from ..db import query
    from . import mobile

    def consulta():
        return query(
            "SELECT DISTINCT ON (p.match_id) p.match_id, p.markets, p.market_consensus, "
            "p.data_completeness->>'both_teams_known' AS conocido, p.generated_at "
            "FROM predictions p JOIN matches m ON m.match_id = p.match_id "
            "WHERE p.match_id = ANY(%s) AND p.generated_at < m.kickoff_utc "
            "ORDER BY p.match_id, p.generated_at DESC", (match_ids,))

    filas = _seguro("pronósticos", lambda: fichas._cacheado(("seo_pron", tuple(sorted(match_ids))), 120, consulta))
    salida = {}
    for f in filas:
        probs, del_modelo = mobile.uno_x_dos(f)
        try:
            trio = {k: float(probs[k]) for k in ("home", "draw", "away")}
        except (TypeError, KeyError, ValueError):
            continue
        if sum(trio.values()) <= 0:
            continue
        salida[f["match_id"]] = {"probs": trio, "modelo": del_modelo, "generada": f["generated_at"]}
    return salida


def ventana(hoy: date | None = None) -> dict[date, list[dict]]:
    """Agenda de los días -1..+3 (los que muestra la app), con el pronóstico de cada partido si lo tiene."""
    hoy = hoy or hoy_mx()
    dias = {}
    for i in range(-DIAS_ATRAS, DIAS_ADELANTE + 1):
        d = hoy + timedelta(days=i)
        filas = agenda_dia(d)
        pron = pronosticos([f["match_id"] for f in filas])
        dias[d] = [{**f, "pron": pron.get(f["match_id"])} for f in filas]
    return dias


def buscar_partido(comp: str, slug: str) -> dict | None:
    """El partido de esa URL, solo con pronóstico generado antes de su inicio (si no, la página no existe)."""
    m = SLUG_PARTIDO.match(slug)
    if not m:
        return None
    try:
        dia = date.fromisoformat(m["fecha"])
    except ValueError:
        return None
    for fila in agenda_dia(dia):
        if slug_partido(fila) == slug and competicion_slug(fila["liga"]["nombre"]) == comp:
            pron = pronosticos([fila["match_id"]]).get(fila["match_id"])
            return {**fila, "pron": pron} if pron else None
    return None
