"""Pasa a `matches` lo ya archivado de FotMob (F0 de la spec 2026-10-14).

Solo rellena columnas en NULL, nunca inventa un valor ausente y nunca sobrescribe.
La procedencia de cada campo queda en `matches_enriquecimiento`.
"""
from __future__ import annotations

import math

# columna_local, columna_visita, clave en `statistics`, ¿entero?
CAMPOS_PARES = {
    "amarillas": ("home_yellow", "away_yellow", "yellow_cards", True),
    "rojas": ("home_red", "away_red", "red_cards", True),
    "corners": ("home_corners", "away_corners", "corners", True),
    "tiros": ("home_shots", "away_shots", "total_shots", True),
    "tiros_puerta": ("home_shots_target", "away_shots_target", "ShotsOnTarget", True),
    "xgot": ("home_xgot", "away_xgot", "expected_goals_on_target", False),
}


def _numero(valor) -> float | None:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    if not math.isfinite(valor) or valor < 0:
        return None
    return float(valor)


def _par(statistics: dict, clave: str, entero: bool):
    """(local, visita) válidos los dos, o (None, None): nunca una mitad."""
    valor = (statistics or {}).get(clave)
    if not isinstance(valor, (list, tuple)) or len(valor) != 2:
        return None, None
    a, b = _numero(valor[0]), _numero(valor[1])
    if a is None or b is None:
        return None, None
    if entero:
        if a != int(a) or b != int(b):
            return None, None
        return int(a), int(b)
    return a, b


def _descanso(payload: dict, goles_local: int, goles_visita: int):
    hechos = ((payload.get("content") or {}).get("matchFacts") or {})
    eventos = hechos.get("events")
    eventos = eventos.get("events") if isinstance(eventos, dict) else None
    for e in eventos or []:
        if e.get("type") == "Half" and e.get("halfStrShort") == "HT":
            h, a = e.get("homeScore"), e.get("awayScore")
            validos = all(isinstance(x, int) and not isinstance(x, bool) and x >= 0 for x in (h, a))
            if validos and h <= goles_local and a <= goles_visita:
                return h, a
    return None, None


def _info(payload: dict) -> dict:
    return (((payload.get("content") or {}).get("matchFacts") or {}).get("infoBox")) or {}


def _texto(valor) -> str | None:
    if isinstance(valor, str) and valor.strip() and len(valor.strip()) <= 160:
        return valor.strip()
    return None


def _estadio(payload: dict) -> dict | None:
    bruto = _info(payload).get("Stadium")
    nombre = _texto((bruto or {}).get("name")) if isinstance(bruto, dict) else None
    if not nombre:
        return None
    lat, lon = bruto.get("lat"), bruto.get("long")
    en_rango = (isinstance(lat, (int, float)) and isinstance(lon, (int, float))
                and not isinstance(lat, bool) and not isinstance(lon, bool)
                and -90 <= lat <= 90 and -180 <= lon <= 180)
    capacidad = bruto.get("capacity")
    return {"name": nombre, "city": _texto(bruto.get("city")), "country": _texto(bruto.get("country")),
            "lat": float(lat) if en_rango else None, "lon": float(lon) if en_rango else None,
            "capacity": int(capacidad) if isinstance(capacidad, int) and not isinstance(capacidad, bool)
            and capacidad > 0 else None,
            "surface": _texto(bruto.get("surface"))}


def extraer(payload: dict, statistics: dict, goles_local: int, goles_visita: int) -> dict:
    """Campos validados de un original FotMob. Dato ausente o inválido: None."""
    out: dict = {}
    for local, visita, clave, entero in CAMPOS_PARES.values():
        out[local], out[visita] = _par(statistics, clave, entero)
    out["home_goals_ht"], out["away_goals_ht"] = _descanso(payload, goles_local, goles_visita)
    arbitro = _info(payload).get("Referee")
    out["referee_fotmob"] = _texto(arbitro.get("text")) if isinstance(arbitro, dict) else None
    out["estadio"] = _estadio(payload)
    return out
