"""Respaldo de las estadísticas públicas de tenis cuando API-Tennis ya no responde (T3).

`publicar_tenis_estadisticas.py` pide a API-Tennis `get_standings`, `get_players` y `get_H2H`. Al vencer el plan:
  * Clasificación: SportsAPIPro `/api/rankings` (ATP) y `/api/rankings/wta`, convertida a las filas de `get_standings`
    (`place`, `points`, `movement`, `player_key`…). La clave de jugador es la de API-Tennis si la tabla de
    `tenis_equivalencias` la conoce y 9.000.000.000 + id de SofaScore si no (igual que el conversor de partidos).
  * H2H y forma reciente: sin peticiones, del archivo propio de partidos (originales del motor, que ya guardan los de
    API-Tennis y los convertidos de SportsAPIPro con el mismo formato), unidos al H2H en caché de cuando API-Tennis
    respondía, que trae más historia.
  * Perfiles (`get_players`): no hay equivalente; se sigue usando el último perfil en caché y los jugadores nuevos
    salen sin temporada ni carrera (nombre y país vienen del partido y la clasificación).

Solo biblioteca estándar y sin red: recibe los datos ya descargados.
"""
from __future__ import annotations

from collections import defaultdict

SINTETICO = 9_000_000_000
H2H_MAX = 10
RESULTADOS_MAX = 10


def movimiento(actual, previo) -> str:
    if actual is None or previo is None or actual == previo:
        return "same"
    return "up" if actual < previo else "down"


def clasificacion(rankings: list[dict], circuito: str, jugadores: dict) -> list[dict]:
    """Filas de `/api/rankings` -> filas de `get_standings` de API-Tennis (`jugadores`: id SofaScore -> player_key)."""
    out = []
    for r in rankings or []:
        equipo = r.get("team") or {}
        if r.get("ranking") is None or not equipo.get("id"):
            continue
        out.append({"place": int(r["ranking"]), "player": equipo.get("name") or r.get("rowName"),
                    "player_key": jugadores.get(equipo["id"], SINTETICO + equipo["id"]), "league": circuito,
                    "movement": movimiento(r.get("ranking"), r.get("previousRanking")),
                    "country": (r.get("country") or equipo.get("country") or {}).get("name") or None,
                    "points": str(r.get("points")) if r.get("points") is not None else None})
    return out


def _clave_orden(fila: dict):
    return (str(fila.get("event_date", "")), str(fila.get("event_time", "")), str(fila.get("event_key", "")))


def _union(*listas) -> list[dict]:
    """Une listas de partidos sin repetir `event_key`; si hay dos versiones manda la última de la lista."""
    por_clave = {}
    for lista in listas:
        for fila in lista or []:
            por_clave[fila.get("event_key")] = fila
    return sorted(por_clave.values(), key=_clave_orden, reverse=True)


def indice_partidos(filas) -> dict:
    """`archivo` (event_key -> fila) -> {player_key: [partidos individuales terminados], pares: {(a, b): [...]}}."""
    por_jugador, pares = defaultdict(list), defaultdict(list)
    for f in filas:
        if "singles" not in str(f.get("event_type_type", "")).lower() or f.get("event_status") not in ("Finished", "Retired"):
            continue
        a, b = f.get("first_player_key"), f.get("second_player_key")
        if not a or not b:
            continue
        por_jugador[a].append(f)
        por_jugador[b].append(f)
        pares[frozenset((a, b))].append(f)
    return {"jugador": por_jugador, "pares": pares}


def h2h_local(ix: dict, primero, segundo, cache: dict | None = None) -> dict:
    """Respuesta con la forma de `get_H2H` (`result.H2H`, `firstPlayerResults`, `secondPlayerResults`).

    Une el archivo propio con lo que hubiera en la caché del H2H (`cache` = la respuesta antigua de API-Tennis).
    """
    viejo = (cache or {}).get("result") or {}
    h2h = _union(viejo.get("H2H"), ix["pares"].get(frozenset((primero, segundo)), []))[:H2H_MAX]
    p1 = _union(viejo.get("firstPlayerResults"), ix["jugador"].get(primero, []))[:RESULTADOS_MAX]
    p2 = _union(viejo.get("secondPlayerResults"), ix["jugador"].get(segundo, []))[:RESULTADOS_MAX]
    return {"success": 1, "result": {"H2H": h2h, "firstPlayerResults": p1, "secondPlayerResults": p2}}
