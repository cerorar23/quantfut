"""
Estadísticas por jugador y partido (fuerza por jugador, Fase A).

Diseño: docs/superpowers/specs/2026-09-29-fuerza-por-jugador-design.md.
Fuente: /fixtures/players de API-Football (1 petición por partido). Solo se
guardan jugadores que jugaron; la Fase B calcula su valor usando, para un
partido del día D, únicamente partidos anteriores a D.
"""
from __future__ import annotations

import logging

from ..db import execute, executemany, query
from . import api_football as af
from .lineups_historicas import RESERVA_CUOTA, _cuota

log = logging.getLogger(__name__)

COLUMNAS = ("side", "player_id", "nombre", "posicion", "minutos", "titular",
            "goles", "asistencias", "tiros", "tiros_puerta", "pases_clave",
            "regates", "entradas", "intercepciones", "duelos_ganados",
            "paradas", "nota_proveedor")


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


def capturar(match_id: str, af_fixture: int, home_af: int | None,
             away_af: int | None) -> tuple[int, dict]:
    """Descarga y guarda un partido. Registra el intento aunque venga vacío."""
    resp, meta = af.get("fixtures/players", {"fixture": af_fixture})
    filas = parse_jugadores(resp, home_af, away_af)
    if filas:
        executemany(
            f"""INSERT INTO estadisticas_jugador (match_id, {", ".join(COLUMNAS)})
                VALUES (%s, {", ".join(["%s"] * len(COLUMNAS))})
                ON CONFLICT (match_id, player_id) DO NOTHING""",
            [(match_id, *(f[c] for c in COLUMNAS)) for f in filas],
        )
    execute(
        """INSERT INTO estadisticas_jugador_log (match_id, n_jugadores)
           VALUES (%s, %s) ON CONFLICT (match_id) DO NOTHING""",
        (match_id, len(filas)),
    )
    return len(filas), meta


def run_historico(reserva: int = RESERVA_CUOTA) -> dict:
    """
    Partidos con XI histórico (db/034) aún sin intento registrado.
    Reanudable: se detiene al llegar a la reserva de cuota y sigue otro día.
    """
    pendientes = query(
        """SELECT DISTINCT h.match_id, h.af_fixture_id,
                  th.af_team_id AS home_af, ta.af_team_id AS away_af
           FROM lineups_historicas h
           JOIN matches m USING (match_id)
           JOIN teams th ON th.team_id = m.home_team_id
           JOIN teams ta ON ta.team_id = m.away_team_id
           LEFT JOIN estadisticas_jugador_log g USING (match_id)
           WHERE g.match_id IS NULL
           ORDER BY h.match_id""")
    partidos = jugadores = 0
    for p in pendientes:
        n, meta = capturar(p["match_id"], p["af_fixture_id"], p["home_af"], p["away_af"])
        partidos += 1
        jugadores += n
        restante = _cuota(meta)
        if restante is not None and restante < reserva:
            log.warning("Reserva de cuota alcanzada (%s): se sigue otro día", restante)
            break
    resultado = {"pendientes": len(pendientes), "partidos": partidos,
                 "jugadores": jugadores}
    af.record_health("estadisticas_jugador", jugadores, True, resultado)
    log.info("Estadísticas por jugador (histórico): %s", resultado)
    return resultado


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    print(run_historico())
