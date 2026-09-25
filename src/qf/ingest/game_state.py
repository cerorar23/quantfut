"""
xG ajustado por estado del partido.

EL PROBLEMA QUE RESUELVE
------------------------
El xG de un partido mide dos cosas mezcladas: lo bueno que es el equipo y en
qué marcador pasó el rato. Un equipo que se pone 2-0 se repliega, cede la
pelota y tira menos; el que va perdiendo se vuelca y acumula remates, muchos
malos y desde lejos. Nada de eso habla de su calidad, pero contamina el dato
que el modelo de fuerza usa como objetivo.

El ajuste normaliza el xG de cada equipo a "lo que habría generado si el
partido hubiera estado empatado todo el tiempo", usando los ratios empíricos
de producción de xG por minuto en cada estado.

POR QUÉ ESTE AJUSTE Y NO "SOLO REMATES CON EMPATE"
---------------------------------------------------
Lo habitual en analítica es quedarse con los remates en empate y tirar el
resto. Es más simple pero tiene mucha más varianza: un equipo que pasó 15
minutos empatado queda estimado con una muestra diminuta. Aquí se usan TODOS
los remates y se divide cada uno por el ratio de su estado, que conserva la
muestra completa.

LA TRAMPA QUE HAY QUE EVITAR: LOS AUTOGOLES
--------------------------------------------
El marcador se reconstruye a partir de los remates que acabaron en gol. Un
AUTOGOL cuenta en el resultado pero no es un remate del equipo que anota, así
que no aparece. Medido sobre Liga MX: 139 de 1.790 partidos (7,8%) tienen al
menos uno, y en todos ellos la reconstrucción se desvía justo desde ese minuto
en adelante.

Por eso `adjusted_xg()` EXIGE el marcador real y devuelve None si no cuadra
con el reconstruido. Es preferible no tener el dato a tenerlo mal: un estado
de partido equivocado ensucia el objetivo del modelo sin dar ningún error.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import pandas as pd

log = logging.getLogger(__name__)

REGULATION_END = 90.0
# Estados desde el punto de vista del equipo que remata.
STATES = ("trailing", "level", "leading")


def parse_minute(minute, half=None) -> float | None:
    """
    '45+2' -> 45.02, '73' -> 73.0.

    El descuento se codifica como fracción para preservar el ORDEN sin
    desplazar el minuto: un gol en el 45+2 sigue siendo anterior al 46.
    """
    if minute is None or (isinstance(minute, float) and minute != minute):
        return None
    s = str(minute).strip()
    m = re.match(r"^(\d+)(?:\+(\d+))?$", s)
    if not m:
        return None
    base = float(m.group(1))
    extra = float(m.group(2) or 0) / 100.0
    # La prórroga (mitades 3 y 4) se descarta: solo ocurre en eliminatorias y
    # es un contexto distinto al de liga, que es lo que modela la fuerza.
    if half is not None and half == half and int(half) > 2:
        return None
    return base + extra


def goal_timeline(shots: pd.DataFrame) -> list[tuple[float, str]]:
    """Minutos de los goles y quién los marcó, ordenados."""
    goles = shots[shots["Outcome"] == "Goal"]
    fuera = []
    for _, r in goles.iterrows():
        m = parse_minute(r["Minute"], r.get("Match_Half"))
        if m is not None:
            fuera.append((m, r["Home_Away"]))
    return sorted(fuera)


def state_segments(timeline: list[tuple[float, str]]) -> list[tuple[float, float, int]]:
    """
    Trocea el partido en intervalos con diferencia de goles constante.

    Devuelve (inicio, fin, diferencia_local). La diferencia se da desde el
    punto de vista del LOCAL; para el visitante se invierte el signo.
    """
    segmentos, inicio, diff = [], 0.0, 0
    for minuto, lado in timeline:
        if minuto > inicio:
            segmentos.append((inicio, minuto, diff))
        diff += 1 if lado == "Home" else -1
        inicio = minuto
    if inicio < REGULATION_END:
        segmentos.append((inicio, REGULATION_END, diff))
    return segmentos


def _state_name(diff: int) -> str:
    return "level" if diff == 0 else ("leading" if diff > 0 else "trailing")


def minutes_by_state(timeline: list[tuple[float, str]]) -> dict[str, dict[str, float]]:
    """Minutos que cada lado pasó en cada estado."""
    fuera = {"Home": dict.fromkeys(STATES, 0.0), "Away": dict.fromkeys(STATES, 0.0)}
    for inicio, fin, diff in state_segments(timeline):
        dur = max(fin - inicio, 0.0)
        fuera["Home"][_state_name(diff)] += dur
        fuera["Away"][_state_name(-diff)] += dur
    return fuera


def _diff_at(timeline: list[tuple[float, str]], minuto: float) -> int:
    """Diferencia de goles del local JUSTO ANTES del minuto dado."""
    diff = 0
    for m, lado in timeline:
        if m >= minuto:
            break
        diff += 1 if lado == "Home" else -1
    return diff


def xg_by_state(shots: pd.DataFrame,
                timeline: list[tuple[float, str]]) -> dict[str, dict[str, float]]:
    """xG que generó cada lado en cada estado."""
    fuera = {"Home": dict.fromkeys(STATES, 0.0), "Away": dict.fromkeys(STATES, 0.0)}
    for _, r in shots.iterrows():
        m = parse_minute(r["Minute"], r.get("Match_Half"))
        xg = r["xG"]
        if m is None or xg is None or xg != xg:
            continue
        lado = r["Home_Away"]
        if lado not in fuera:
            continue
        diff = _diff_at(timeline, m)
        estado = _state_name(diff if lado == "Home" else -diff)
        fuera[lado][estado] += float(xg)
    return fuera


@dataclass
class StateRatios:
    """
    Ratio de producción de xG por minuto en cada estado, relativo al empate.

    Se estiman de los propios datos de la liga, no se fijan a mano: la
    magnitud del efecto varía entre competiciones.
    """
    ratios: dict

    def adjust(self, xg_estado: dict[str, float]) -> float:
        total = 0.0
        for estado, xg in xg_estado.items():
            r = self.ratios.get(estado, 1.0)
            total += xg / r if r > 0 else xg
        return total


def estimate_ratios(muestras: list[tuple[dict, dict]]) -> StateRatios:
    """
    muestras: lista de (xg_por_estado, minutos_por_estado) de cada lado y
    partido. Devuelve los ratios de xG por minuto normalizados al empate.
    """
    xg_tot = dict.fromkeys(STATES, 0.0)
    min_tot = dict.fromkeys(STATES, 0.0)
    for xg_e, min_e in muestras:
        for s in STATES:
            xg_tot[s] += xg_e.get(s, 0.0)
            min_tot[s] += min_e.get(s, 0.0)

    tasas = {s: (xg_tot[s] / min_tot[s] if min_tot[s] > 0 else 0.0) for s in STATES}
    base = tasas["level"]
    if base <= 0:
        log.warning("Sin xG en estado de empate: no se puede normalizar.")
        return StateRatios({s: 1.0 for s in STATES})
    return StateRatios({s: (tasas[s] / base if tasas[s] > 0 else 1.0) for s in STATES})


def match_state_data(shots_partido: pd.DataFrame,
                     home_goals: int, away_goals: int) -> dict | None:
    """
    Calcula xG y minutos por estado de un partido, o None si la reconstrucción
    del marcador no cuadra con el resultado real.

    Esa comprobación es el núcleo de la fiabilidad de este módulo: sin ella,
    los partidos con autogol (7,8% de la muestra) producirían estados
    equivocados en silencio.
    """
    timeline = goal_timeline(shots_partido)
    gh = sum(1 for _, lado in timeline if lado == "Home")
    ga = sum(1 for _, lado in timeline if lado == "Away")
    if gh != home_goals or ga != away_goals:
        return None

    mins = minutes_by_state(timeline)
    xgs = xg_by_state(shots_partido, timeline)
    return {"home_xg_state": xgs["Home"], "away_xg_state": xgs["Away"],
            "home_minutes": mins["Home"], "away_minutes": mins["Away"]}
