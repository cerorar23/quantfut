"""Estadísticas de equipo de un partido de la NBA a partir de los marcadores finales de la temporada regular.

Función pura: recibe los marcadores ya leídos de la base y devuelve el contrato que consume la web
(`teams[2]` + `h2h`). Regla de punto en el tiempo: un partido solo ve marcadores de fechas ANTERIORES a la suya
(un equipo juega como mucho una vez al día, así que la fecha ET basta para ordenar). Pretemporada, play-in y
playoffs no cuentan.
"""
from datetime import date
from typing import NamedTuple

from ..v2.equipos import TRICODES

ESTE = {"ATL", "BKN", "BOS", "CHA", "CHI", "CLE", "DET", "IND", "MIA", "MIL", "NYK", "ORL", "PHI", "TOR", "WAS"}
H2H_MAXIMO = 10
FORMA = 6

# Temporada regular en hora del Este (primer y último día). La pretemporada, el play-in y los playoffs quedan fuera.
# Una temporada sin fila usa el calendario típico (del 15-oct al 13-abr): hay que añadirla antes de que empiece.
REGULAR = {
    "2021-22": (date(2021, 10, 19), date(2022, 4, 10)),
    "2022-23": (date(2022, 10, 18), date(2023, 4, 9)),
    "2023-24": (date(2023, 10, 24), date(2024, 4, 14)),
    "2024-25": (date(2024, 10, 22), date(2025, 4, 13)),
    "2025-26": (date(2025, 10, 21), date(2026, 4, 12)),
    "2026-27": (date(2026, 10, 20), date(2027, 4, 13)),
}


class Marcador(NamedTuple):
    fecha: date
    temporada: str
    local: str
    visitante: str
    puntos_local: float
    puntos_visitante: float


def ventana_regular(temporada: str) -> tuple[date, date]:
    if temporada in REGULAR:
        return REGULAR[temporada]
    inicio = int(temporada[:4])
    return date(inicio, 10, 15), date(inicio + 1, 4, 13)


def es_regular(m: Marcador) -> bool:
    inicio, fin = ventana_regular(m.temporada)
    return inicio <= m.fecha <= fin


def temporada_anterior(temporada: str) -> str:
    inicio = int(temporada[:4]) - 1
    return f"{inicio}-{(inicio + 1) % 100:02d}"


def _entero(valor: float) -> int:
    return int(valor)


def _promedio(total: float, n: int) -> float | None:
    return round(total / n, 1) if n else None


def _registro(filas: list[dict]) -> dict:
    ganados = sum(1 for f in filas if f["won"])
    return {"won": ganados, "lost": len(filas) - ganados, "rate": round(ganados / len(filas), 4) if filas else None}


def _promedios(filas: list[dict]) -> dict:
    return {"points_for": _promedio(sum(f["points"] for f in filas), len(filas)),
            "points_against": _promedio(sum(f["opponent_points"] for f in filas), len(filas))}


def _filas_de(marcadores: list[Marcador], codigo: str) -> list[dict]:
    """Partidos de un equipo vistos desde él, del más reciente al más antiguo."""
    filas = []
    for m in sorted(marcadores, key=lambda x: x.fecha, reverse=True):
        if codigo not in (m.local, m.visitante):
            continue
        casa = m.local == codigo
        pf, pc = (m.puntos_local, m.puntos_visitante) if casa else (m.puntos_visitante, m.puntos_local)
        rival = m.visitante if casa else m.local
        filas.append({"date": m.fecha.isoformat(), "opponent": TRICODES[rival], "home": casa,
                      "points": _entero(pf), "opponent_points": _entero(pc), "won": pf > pc})
    return filas


def clasificacion(marcadores: list[Marcador], codigo: str) -> dict:
    """Puesto en su conferencia por porcentaje de victorias y, a igualdad, por diferencial. Sin partidos jugados no hay puesto."""
    este = codigo in ESTE
    tabla = []
    for c in TRICODES:
        if (c in ESTE) != este:
            continue
        ganados = jugados = diferencia = 0
        for m in marcadores:
            if c == m.local:
                pf, pc = m.puntos_local, m.puntos_visitante
            elif c == m.visitante:
                pf, pc = m.puntos_visitante, m.puntos_local
            else:
                continue
            jugados += 1
            ganados += pf > pc
            diferencia += pf - pc
        tabla.append((-(ganados / jugados if jugados else 0.0), -(diferencia / jugados if jugados else 0.0), c, jugados))
    tabla.sort()
    puesto = next((i + 1 for i, t in enumerate(tabla) if t[2] == codigo and t[3]), None)
    return {"rank": puesto, "of": len(tabla), "conference": "este" if este else "oeste"}


def _equipo(temporada_actual: list[Marcador], pasada: list[Marcador], codigo: str, fecha: date) -> dict:
    filas = _filas_de(temporada_actual, codigo)
    ultimos = filas[:FORMA]
    racha = 0
    for f in filas:
        if racha == 0 or f["won"] == (racha > 0):
            racha += 1 if f["won"] else -1
        else:
            break
    descanso = (fecha - date.fromisoformat(filas[0]["date"])).days - 1 if filas else None
    anterior = _filas_de(pasada, codigo)
    en_casa, fuera = [f for f in filas if f["home"]], [f for f in filas if not f["home"]]
    return {"name": TRICODES[codigo], "conference": "este" if codigo in ESTE else "oeste",
            "season": _registro(filas), "home": _registro(en_casa), "away": _registro(fuera),
            "scoring": {"games": len(filas), **_promedios(filas)},
            "last6": {**_registro(ultimos), "games": len(ultimos), **_promedios(ultimos)},
            "streak": racha, "rest_days": descanso, "back_to_back": None if descanso is None else descanso == 0,
            "last_season": {**_registro(anterior), "games": len(anterior), **_promedios(anterior)},
            "form": {"all": ultimos, "home": en_casa[:FORMA], "away": fuera[:FORMA]},
            "standing": clasificacion(temporada_actual, codigo)}


def estadisticas(temporada: str, fecha: date, local: str, visitante: str, previos: list[Marcador]) -> dict:
    """`previos`: marcadores finales de cualquier temporada con fecha anterior a `fecha` (se filtra aquí: solo regular y solo anteriores)."""
    validos = [m for m in previos if m.fecha < fecha and es_regular(m)]
    actual = [m for m in validos if m.temporada == temporada]
    pasada = [m for m in validos if m.temporada == temporada_anterior(temporada)]
    duelos = sorted((m for m in validos if {m.local, m.visitante} == {local, visitante}), key=lambda m: m.fecha, reverse=True)[:H2H_MAXIMO]
    victorias_local = sum(1 for m in duelos if (m.puntos_local > m.puntos_visitante) == (m.local == local))
    return {"temporada": temporada, "fecha": fecha.isoformat(), "games_used": len(actual),
            "teams": [_equipo(actual, pasada, local, fecha), _equipo(actual, pasada, visitante, fecha)],
            "h2h": {"matches": [{"date": m.fecha.isoformat(), "home": TRICODES[m.local], "away": TRICODES[m.visitante],
                                 "home_points": _entero(m.puntos_local), "away_points": _entero(m.puntos_visitante)} for m in duelos],
                    "home_wins": victorias_local, "away_wins": len(duelos) - victorias_local,
                    "average_total": _promedio(sum(m.puntos_local + m.puntos_visitante for m in duelos), len(duelos))}}
