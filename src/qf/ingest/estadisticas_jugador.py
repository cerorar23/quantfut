"""
Estadísticas por jugador y partido (fuerza por jugador, Fase A).

Diseño: docs/superpowers/specs/2026-09-29-fuerza-por-jugador-design.md.
Fuente: /fixtures/players de API-Football (1 petición por partido). Solo se
guardan jugadores que jugaron; la Fase B calcula su valor usando, para un
partido del día D, únicamente partidos anteriores a D.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def _n(valor) -> int:
    """Recuento del proveedor: null significa 0."""
    try:
        return int(valor or 0)
    except (TypeError, ValueError):
        return 0


def _nota(valor) -> float | None:
    try:
        return float(valor) if valor is not None else None
    except (TypeError, ValueError):
        return None


def parse_jugadores(resp: list[dict], home_af: int | None,
                    away_af: int | None) -> list[dict]:
    """
    Filas para `estadisticas_jugador`. El lado se decide por el id de equipo
    de API-Football; si no se conocen los ids, por el orden del proveedor
    (local primero, el mismo contrato que usa `ingest/lineups.py`).
    """
    filas = []
    for i, bloque in enumerate(resp[:2]):
        tid = (bloque.get("team") or {}).get("id")
        if home_af is not None and tid == home_af:
            side = "home"
        elif away_af is not None and tid == away_af:
            side = "away"
        else:
            side = ("home", "away")[i]
        for j in bloque.get("players") or []:
            s = (j.get("statistics") or [{}])[0]
            juego = s.get("games") or {}
            minutos = _n(juego.get("minutes"))
            if minutos <= 0:
                continue
            goles = s.get("goals") or {}
            tiros = s.get("shots") or {}
            entradas = s.get("tackles") or {}
            filas.append({
                "side": side,
                "player_id": int(j["player"]["id"]),
                "nombre": j["player"].get("name"),
                "posicion": (juego.get("position") or "")[:1] or None,
                "minutos": minutos,
                "titular": not bool(juego.get("substitute")),
                "goles": _n(goles.get("total")),
                "asistencias": _n(goles.get("assists")),
                "tiros": _n(tiros.get("total")),
                "tiros_puerta": _n(tiros.get("on")),
                "pases_clave": _n((s.get("passes") or {}).get("key")),
                "regates": _n((s.get("dribbles") or {}).get("success")),
                "entradas": _n(entradas.get("total")),
                "intercepciones": _n(entradas.get("interceptions")),
                "duelos_ganados": _n((s.get("duels") or {}).get("won")),
                "paradas": _n(goles.get("saves")),
                "nota_proveedor": _nota(juego.get("rating")),
            })
    return filas
