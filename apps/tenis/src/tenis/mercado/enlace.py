"""Enlace de cuotas de mercado con partidos del motor (plan tcnico tenis, B.4, I.0, S5).

Enlace punto en el tiempo:
  - Mismo circuito (ATP con ATP, WTA con WTA);
  - Jugadores normalizados mediante claves apellido/inicial (normalizar.py);
  - Ventana temporal estricta (+-1 da; extensible a +-2 das para reprogramaciones);
  - Excluye eventos con dobles, parejas repetidas o ambigedades no resueltas;
  - Orienta las probabilidades sin margen de mercado respecto al lado 1 del modelo.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Callable, Sequence

import pandas as pd

from ..identidad.normalizar import claves_apellido, nombre_clave


def extraer_claves_jugador(nombre: str | None) -> frozenset[tuple[str, str]]:
    """Extrae claves (apellido, inicial) para bsqueda y matching."""
    if not nombre or not isinstance(nombre, str):
        return frozenset()
    return claves_apellido(nombre)


def son_jugadores_compatibles(nombre_a: str, nombre_b: str) -> bool:
    """Verifica si dos representaciones de nombre corresponden a la misma persona."""
    if not nombre_a or not nombre_b:
        return False
    # Igualdad exacta normalizada
    if nombre_clave(nombre_a) == nombre_clave(nombre_b):
        return True
    # Claves apellido + inicial
    ca, cb = claves_apellido(nombre_a), claves_apellido(nombre_b)
    if ca and cb and (ca & cb):
        return True
    return False


def construir_indice_cuotas(cuotas_partidos: Sequence[dict]) -> dict:
    """Indexa cuotas de mercado por (circuito, clave_jugador_a, clave_jugador_b)."""
    idx = defaultdict(list)
    for q in cuotas_partidos:
        circ = str(q.get("circuito", "")).lower()
        w_claves = extraer_claves_jugador(q.get("ganador"))
        l_claves = extraer_claves_jugador(q.get("perdedor"))
        if not w_claves or not l_claves:
            continue
        for kw in w_claves:
            for kl in l_claves:
                par_ordenado = tuple(sorted([kw, kl]))
                idx[(circ, par_ordenado)].append(q)
    return idx


def enlazar_partido_con_cuotas(
    circuito: str,
    fecha_partido: date | str,
    jugador_1_nombre: str,
    jugador_2_nombre: str,
    indice_cuotas: dict,
    ventana_dias: int = 1,
    fuente_tiempo: str | None = None,
) -> dict | None:
    """Enlaza un partido del motor con su cuota de mercado correspondiente.

    Para TML (donde la fecha es el inicio de la edicin semanal), se adapta la ventana
    a la duracin del torneo (hasta 16 das). Para SofaScore (hora real), ventana +-2 das.
    Orienta la probabilidad de cierre del ganador hacia el lado 1.
    Retorna dict con datos del enlace o None si no hay cruce o es ambiguo.
    """
    circ = str(circuito).lower()
    c1 = extraer_claves_jugador(jugador_1_nombre)
    c2 = extraer_claves_jugador(jugador_2_nombre)
    if not c1 or not c2:
        return None

    if isinstance(fecha_partido, str):
        fecha_p = date.fromisoformat(fecha_partido)
    elif hasattr(fecha_partido, "date"):
        fecha_p = fecha_partido.date()
    else:
        fecha_p = fecha_partido

    # Adaptar ventana segn fuente de tiempo
    if fuente_tiempo == "tml":
        v_dias = max(ventana_dias, 16)
    elif fuente_tiempo == "sofascore":
        v_dias = max(ventana_dias, 2)
    else:
        v_dias = ventana_dias

    # Buscar candidatos en el ndice
    candidatos = []
    vistos = set()
    for k1 in c1:
        for k2 in c2:
            par = tuple(sorted([k1, k2]))
            for q in indice_cuotas.get((circ, par), []):
                # Usar id de memoria o clave de objeto para deduplicar
                q_id = id(q)
                if q_id not in vistos:
                    vistos.add(q_id)
                    q_fecha = q.get("fecha")
                    if isinstance(q_fecha, str):
                        q_fecha = date.fromisoformat(q_fecha)
                    elif hasattr(q_fecha, "date"):
                        q_fecha = q_fecha.date()
                    dif_dias = abs((q_fecha - fecha_p).days) if q_fecha and fecha_p else 999
                    if dif_dias <= v_dias:
                        candidatos.append((dif_dias, q))

    if not candidatos:
        return None

    # Ordenar por menor diferencia de das
    candidatos.sort(key=lambda x: x[0])
    mejor_dif, mejor_q = candidatos[0]

    # Desambiguacin: si hay mltiples candidatos con la misma mnima diferencia de das
    mejores = [q for d, q in candidatos if d == mejor_dif]
    if len(mejores) > 1:
        # Conflicto irresoluble de misma pareja en la misma fecha -> ambiguo, no enlazar
        return None

    # Determinar si el ganador de la cuota es jugador_1 o jugador_2
    w_claves = extraer_claves_jugador(mejor_q.get("ganador"))
    l_claves = extraer_claves_jugador(mejor_q.get("perdedor"))

    gana_lado1 = bool(c1 & w_claves)
    gana_lado2 = bool(c2 & w_claves)

    if gana_lado1 and not gana_lado2:
        p_cierre_lado1 = mejor_q.get("ref_p_winner")
        p_cierre_lado2 = mejor_q.get("ref_p_loser")
    elif gana_lado2 and not gana_lado1:
        p_cierre_lado1 = mejor_q.get("ref_p_loser")
        p_cierre_lado2 = mejor_q.get("ref_p_winner")
    else:
        # No se puede determinar la orientacin con certeza
        return None

    return {
        "cuota_encontrada": True,
        "ref_casa": mejor_q.get("ref_casa"),
        "clase_cierre": mejor_q.get("clase_cierre", "b"),
        "p_cierre_lado1": p_cierre_lado1,
        "p_cierre_lado2": p_cierre_lado2,
        "margen_cierre": mejor_q.get("ref_margen"),
        "cuota_ganador": mejor_q.get("ps_w") if mejor_q.get("ref_casa") == "PS" else mejor_q.get("avg_w"),
        "cuota_perdedor": mejor_q.get("ps_l") if mejor_q.get("ref_casa") == "PS" else mejor_q.get("avg_l"),
        "dif_dias": mejor_dif,
        "mercado_fecha": mejor_q.get("fecha"),
        "torneo_mercado": mejor_q.get("torneo"),
    }
