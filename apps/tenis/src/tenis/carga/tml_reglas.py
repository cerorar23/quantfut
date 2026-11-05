"""Reglas puras de TML: categoría, duración de la edición y visible_desde por ronda (plan §A.4, regla fijada).

TML no trae hora ni horario: cada partido y resultado se hace visible en un instante CONSERVADOR (más tarde que el
fin real). Las tablas de desfase son la regla del titular; la elección de 14 días por nivel está en LEEME («Cargador TML»).
"""
import re
from datetime import date, datetime, timedelta, timezone

# (circuito, nivel de TML) -> categoría de la base. Significados verificados por nombres de torneo (LEEME).
# Los niveles sin verificar van a la categoría neutra «250» y se listan en LEEME como «significado no verificado».
CATEGORIA = {
    ("atp", "G"): "GS", ("atp", "M"): "M1000", ("atp", "250"): "250", ("atp", "500"): "500",
    ("atp", "F"): "Finales", ("atp", "O"): "JJOO", ("atp", "D"): "equipos", ("atp", "C"): "Challenger",
    ("atp", "A"): "250", ("atp", "P"): "250",
    ("wta", "G"): "GS", ("wta", "1000"): "WTA1000", ("wta", "PM"): "WTA1000", ("wta", "P5"): "500",
    ("wta", "P"): "250", ("wta", "500"): "500", ("wta", "250"): "250", ("wta", "I"): "250",
    ("wta", "T1"): "WTA1000", ("wta", "T2"): "500", ("wta", "T3"): "250", ("wta", "T4"): "250",
    ("wta", "T5"): "250", ("wta", "D"): "equipos", ("wta", "O"): "JJOO", ("wta", "F"): "Finales",
    ("wta", "YEC"): "Finales", ("wta", "W"): "250", ("wta", "A"): "250",
}
NEUTRA = "250"
NO_VERIFICADOS = {("atp", "A"), ("atp", "P"), ("wta", "P"), ("wta", "P5"), ("wta", "W"), ("wta", "A"),
                  ("wta", "T4"), ("wta", "T5")}
# Niveles de 14 días (o que pueden serlo): GS, M1000, WTA1000 y sus equivalentes históricos, finales y JJOO.
# Un torneo de dos semanas tratado como uno de una deja la final visible antes de jugarse: se elige el desfase largo.
DOS_SEMANAS = {"G", "M", "1000", "PM", "P5", "T1", "F", "YEC", "O", "W"}
EQUIPOS_NOMBRE = re.compile(r"davis|billie jean|bjk|fed cup|united cup|laver cup|hopman", re.IGNORECASE)

# Desfase en días desde el inicio L de la edición (tabla fijada por el titular).
DESFASE_7 = {"R128": 2, "R64": 3, "R32": 3, "R16": 4, "QF": 5, "SF": 6, "F": 7, "RR": 7,
             "Q1": 3, "Q2": 3, "Q3": 3}
DESFASE_14 = {"R128": 3, "R64": 5, "R32": 8, "R16": 10, "QF": 12, "SF": 13, "F": 14, "RR": 14,
              "Q1": 4, "Q2": 4, "Q3": 4}


def categoria(circuito: str, nivel: str, nombre: str) -> tuple[str | None, str | None]:
    """(categoría, aviso). Categoría None si el nivel está vacío; aviso si cae en la neutra sin verificar."""
    if EQUIPOS_NOMBRE.search(nombre or ""):
        return "equipos", None
    if nivel == "":
        return None, None
    if (circuito, nivel) in CATEGORIA and (circuito, nivel) not in NO_VERIFICADOS:
        return CATEGORIA[(circuito, nivel)], None
    if (circuito, nivel) in CATEGORIA:
        return CATEGORIA[(circuito, nivel)], f"nivel_no_verificado:{circuito}:{nivel}"
    return NEUTRA, f"nivel_desconocido:{circuito}:{nivel}"


def dias_de_edicion(nivel: str) -> int:
    return 14 if nivel in DOS_SEMANAS else 7


def por_equipos(nivel: str, nombre: str) -> bool:
    return nivel == "D" or EQUIPOS_NOMBRE.search(nombre or "") is not None


def lunes_de(fecha: date) -> date:
    return fecha - timedelta(days=fecha.weekday())


def fecha_fin(inicio: date, dias: int) -> date:
    return inicio + timedelta(days=dias - 1)


def lunes_semana_fin(inicio: date, dias: int) -> date:
    return lunes_de(fecha_fin(inicio, dias))


def visible_desde_ronda(ronda: str, inicio: date, dias: int) -> datetime | None:
    """Instante (UTC, 00:00) desde el que el partido de esa ronda es conocible; None si la ronda no está en la tabla."""
    tabla = DESFASE_14 if dias == 14 else DESFASE_7
    if ronda not in tabla:
        return None
    dia = inicio + timedelta(days=tabla[ronda])
    return datetime(dia.year, dia.month, dia.day, tzinfo=timezone.utc)


def inicio_visible(inicio: date) -> datetime:
    return datetime(inicio.year, inicio.month, inicio.day, tzinfo=timezone.utc)
