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


# Las mismas claves de la web desde SofaScore (`statistics` de rl1987) y FotMob (`stat_pairs`), que sustituyen a
# API-Football desde el 22-oct-2026. Los centros (precisos y totales) son nuevos: el Motor C los pide.
CLAVES_SOFASCORE = {
    "shotsOnGoal": "tiros_puerta", "shotsOffGoal": "tiros_fuera", "totalShotsOnGoal": "tiros",
    "blockedScoringAttempt": "tiros_bloqueados", "totalShotsInsideBox": "tiros_dentro_area",
    "totalShotsOutsideBox": "tiros_fuera_area", "fouls": "faltas", "cornerKicks": "corners",
    "offsides": "fueras_de_juego", "ballPossession": "posesion", "yellowCards": "amarillas", "redCards": "rojas",
    "goalkeeperSaves": "paradas", "passes": "pases", "accuratePasses": "pases_precisos",
    "expectedGoals": "xg", "accurateCross": "centros_precisos",
}
CLAVES_FOTMOB = {
    "ShotsOnTarget": "tiros_puerta", "ShotsOffTarget": "tiros_fuera", "total_shots": "tiros",
    "blocked_shots": "tiros_bloqueados", "shots_inside_box": "tiros_dentro_area",
    "shots_outside_box": "tiros_fuera_area", "fouls": "faltas", "corners": "corners", "Offsides": "fueras_de_juego",
    "BallPossesion": "posesion", "yellow_cards": "amarillas", "red_cards": "rojas", "keeper_saves": "paradas",
    "passes": "pases", "accurate_passes": "pases_precisos", "expected_goals": "xg",
    "accurate_crosses": "centros_precisos",
}
CERO_SI_FALTA = ("amarillas", "rojas")   # ambos proveedores omiten la tarjeta que no hubo


def _cerrar(out: dict) -> dict | None:
    """Completa tarjetas a cero y el % de pases; None si no quedó ninguna estadística."""
    if not out["home"] and not out["away"]:
        return None
    for lado in out.values():
        for clave in CERO_SI_FALTA:
            lado.setdefault(clave, 0)
        if lado.get("pases") and lado.get("pases_precisos") is not None:
            lado["pct_pases"] = round(100 * lado["pases_precisos"] / lado["pases"])
    return out


def desde_sofascore(statistics: list | None) -> dict | None:
    """`statistics` de SofaScore (periodos ALL/1ST/2ND) -> {"home": {...}, "away": {...}} del partido completo."""
    out: dict[str, dict] = {"home": {}, "away": {}}
    vistos: dict[str, set] = {}
    for seccion in statistics or []:
        if seccion.get("period") != "ALL":
            continue
        for grupo in seccion.get("groups") or []:
            for item in grupo.get("statisticsItems") or []:
                clave = CLAVES_SOFASCORE.get(item.get("key"))
                if not clave:
                    continue
                par = (_numero(item.get("homeValue")), _numero(item.get("awayValue")))
                if None in par:
                    continue
                vistos.setdefault(clave, set()).add(par)
                if item.get("key") == "accurateCross":
                    tot = (_numero(item.get("homeTotal")), _numero(item.get("awayTotal")))
                    if None not in tot:
                        vistos.setdefault("centros", set()).add(tot)
    for clave, pares in vistos.items():
        if len(pares) == 1:              # una repetición con otro valor no se adivina
            out["home"][clave], out["away"][clave] = next(iter(pares))
    return _cerrar(out)


def desde_fotmob(pares: dict) -> dict | None:
    """`stat_pairs` de una página posterior de FotMob -> {"home": {...}, "away": {...}}."""
    out: dict[str, dict] = {"home": {}, "away": {}}
    for origen, clave in CLAVES_FOTMOB.items():
        valor = pares.get(origen)
        if not isinstance(valor, (list, tuple)) or len(valor) != 2:
            continue
        h, a = _numero(valor[0]), _numero(valor[1])
        if h is None or a is None:
            continue
        out["home"][clave], out["away"][clave] = h, a
    return _cerrar(out)


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
