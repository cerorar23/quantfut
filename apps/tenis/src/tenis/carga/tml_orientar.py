"""Análisis de una fila → filas de la base, con el orden canónico jugador_1 < jugador_2 (puro, sin base).

TML pone primero al ganador. Aquí se reordena por id de `jugador` para que el orden nunca revele el resultado.
Los sets, las estadísticas y las entradas se reorientan con el mismo criterio.
"""
from .tml_parseo import Analisis
from .tml_reglas import visible_desde_partido, visible_desde_ronda

ESTADISTICA_CAMPOS = ("aces", "dobles_faltas", "puntos_saque", "primeros_dentro", "primeros_ganados",
                      "segundos_ganados", "juegos_saque", "bp_salvados", "bp_afrontados")


def _sets(sets, gana_1: bool):
    if sets is None:
        return None
    return [[a, b, ta, tb] if gana_1 else [b, a, tb, ta] for (a, b, ta, tb) in sets]


def _resultado(a: Analisis, gana_1: bool, lado_w: int, visible) -> dict:
    m = a.marcador
    ganador = lado_w if m.estado in ("completado", "retirada") else None
    retira = (3 - lado_w) if m.estado == "retirada" else None
    return {"estado": m.estado, "ganador": ganador, "retira": retira,
            "sets": _sets(m.sets, gana_1), "sets_completos": m.sets_completos,
            "duracion_min": a.duracion, "visible_desde": visible}


def _estadisticas(a: Analisis, gana_1: bool, visible) -> list[dict]:
    if a.stats is None:
        return []
    w, l = a.stats
    lados = ((1, w), (2, l)) if gana_1 else ((2, w), (1, l))
    filas = []
    for lado, e in lados:
        if all(v is None for v in e.values()):
            continue
        filas.append({"lado": lado, **{k: e[k] for k in ESTADISTICA_CAMPOS}, "visible_desde": visible})
    return filas


def _ranking(a: Analisis, jug_w: int, jug_l: int) -> list[tuple]:
    ids = {a.ids[0]: jug_w, a.ids[1]: jug_l}
    return [(ids[id_tml], pos, pts) for (id_tml, pos, pts) in a.ranking]


def orientar(a: Analisis, jug_w: int, jug_l: int, edicion_id: int, inicio_edicion, dias_edicion: int,
             rondas_edicion: frozenset = frozenset()) -> dict:
    """Filas de una fila aceptada: partido, resultado, estadísticas, ranking. Ids de jugador ya resueltos.

    `visible_desde` del RESULTADO y de las estadísticas = fin conservador de su ronda; el del PARTIDO (la pareja) = fin de
    la ronda anterior de la edición (o el inicio): así se puede pronosticar con corte = visible_desde_partido + 1 s."""
    gana_1 = jug_w < jug_l
    j1, j2 = (jug_w, jug_l) if gana_1 else (jug_l, jug_w)
    lado_w = 1 if gana_1 else 2
    visible = visible_desde_ronda(a.ronda, inicio_edicion, dias_edicion)
    visible_pareja = visible_desde_partido(a.ronda, inicio_edicion, dias_edicion, set(rondas_edicion))
    ent_w, ent_l = a.entradas
    partido = {"edicion_id": edicion_id, "ronda": a.ronda, "jugador_1": j1, "jugador_2": j2,
               "mejor_de": a.mejor_de,
               "entrada_1": ent_w if gana_1 else ent_l, "entrada_2": ent_l if gana_1 else ent_w,
               "visible_desde": visible_pareja}
    lunes_rk = a.lunes
    return {
        "partido": partido,
        "resultado": _resultado(a, gana_1, lado_w, visible),
        "estadisticas": _estadisticas(a, gana_1, visible),
        "ranking": [(lunes_rk, jug, pos, pts) for (jug, pos, pts) in _ranking(a, jug_w, jug_l)],
    }
