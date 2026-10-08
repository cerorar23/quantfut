"""
Normalización de las estadísticas de partido de API-Football
(`/fixtures/statistics`) para `matches.stats` y las fichas de la web.

Vive en `ingest` y no en `api` porque la escribe `results.py` al cerrar cada
partido, con la misma respuesta que ya pedía: guardarla entera no cuesta
ninguna petición más.
"""
from __future__ import annotations

from typing import Any

# Tipos del proveedor -> claves de la web.
TIPOS = {
    "Shots on Goal": "tiros_puerta", "Shots off Goal": "tiros_fuera",
    "Total Shots": "tiros", "Blocked Shots": "tiros_bloqueados",
    "Shots insidebox": "tiros_dentro_area", "Shots outsidebox": "tiros_fuera_area",
    "Fouls": "faltas", "Corner Kicks": "corners", "Offsides": "fueras_de_juego",
    "Ball Possession": "posesion", "Yellow Cards": "amarillas", "Red Cards": "rojas",
    "Goalkeeper Saves": "paradas", "Total passes": "pases",
    "Passes accurate": "pases_precisos", "Passes %": "pct_pases",
    "expected_goals": "xg",
}
SIN_CERO = {"xg"}   # null en xG es "no hay dato", no "cero"


def _numero(v: Any) -> float | int | None:
    if v is None:
        return None
    if isinstance(v, str):
        v = v.strip().rstrip("%")
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return int(f) if f.is_integer() else f


def normalizar_estadisticas(crudo: list[dict], home_af_id: int, away_af_id: int) -> dict:
    """
    Respuesta de `/fixtures/statistics` -> {"home": {...}, "away": {...}}. El
    proveedor manda `null` en los conteos que valen cero (tarjetas): se
    guardan como 0. En xG, `null` es ausencia y se queda en None.
    """
    out: dict[str, dict] = {"home": {}, "away": {}}
    for bloque in crudo or []:
        tid = bloque.get("team", {}).get("id")
        lado = "home" if tid == home_af_id else "away" if tid == away_af_id else None
        if not lado:
            continue
        for item in bloque.get("statistics", []):
            clave = TIPOS.get(item.get("type"))
            if not clave:
                continue
            valor = _numero(item.get("value"))
            if valor is None and clave not in SIN_CERO:
                valor = 0
            out[lado][clave] = valor
    return out


def arbitro(v) -> str | None:
    """
    Nombre del árbitro en una sola forma para las dos fuentes, porque es la
    clave de su promedio de tarjetas: API-Football manda "Michael Oliver,
    England" y football-data "M Oliver". Ambas quedan "M Oliver": inicial del
    nombre y último apellido.
    """
    if not isinstance(v, str) or not v.strip():
        return None
    partes = v.split(",")[0].replace(".", " ").split()
    if not partes:
        return None
    if len(partes) == 1:
        return partes[0]
    return f"{partes[0][0].upper()} {partes[-1]}"
