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
# Revisión del 5-nov: los desfases de las rondas principales y de las previas crecen ESTRICTAMENTE con la ronda
# (antes R64 y R32 compartían día en la tabla de 7): sin eso, el corte de evaluación «fin de la ronda anterior» vería el
# resultado de la propia ronda. 7 días: ≤ L+7 = fecha_fin + 1 (invariante comprobado en la base).
#
# CALIBRACIÓN CON DATOS REALES (5-nov): el calendario inicial (días «razonables») dejaba el resultado visible ANTES del
# fin real en el 9,1 % de 12.924 partidos comparados con las horas de SofaScore (2023-2026). Estas tablas son el
# percentil 99,9 del fin real por ronda (días desde el inicio L de la edición, 00:00 UTC) + 1 día, con cadena estrictamente
# creciente; fuga residual medida: 1 de 3.757 partidos (edición de 7 días) y 1 de 8.369 (14 días), ≈ 0,01 %. Validación
# FUERA DE MUESTRA (calibrar con 2023-2024, comprobar con 2025-2026): 0,05 % en 7 días; en 14 días 2 % pero casi todo es UNA
# edición (US Open 2026) cuyo `tourney_date` apunta a la semana del clasificatorio, no del cuadro. Hay 3 ediciones así de
# ~100 (2023-04, 2024-07, 2026-08): LIMITACIÓN DECLARADA, no detectable sin horas reales; para partidos con hora real
# (SofaScore, 2023→) el PIT debe usar sus tiempos y no este calendario. Los finales acaban pasada la fecha nominal de fin
# (husos horarios), de ahí F > L+7 y L+14. Fuera de 2023-2026 el calendario no es verificable hacia atrás.
DESFASE_7 = {"R128": 2, "R64": 3, "R32": 6, "R16": 7, "QF": 8, "SF": 9, "F": 10, "RR": 10,
             "Q1": 2, "Q2": 4, "Q3": 6}
DESFASE_14 = {"R128": 6, "R64": 8, "R32": 10, "R16": 12, "QF": 13, "SF": 15, "F": 16, "RR": 16,
              "Q1": 2, "Q2": 4, "Q3": 6}
ORDEN_PRINCIPAL = ("R128", "R64", "R32", "R16", "QF", "SF", "F")
ORDEN_PREVIAS = ("Q1", "Q2", "Q3")


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


def visible_desde_partido(ronda: str, inicio: date, dias: int, rondas_edicion: set) -> datetime | None:
    """Instante desde el que el PARTIDO (la pareja) es conocible, para pronosticarlo: el fin conservador de la ronda
    anterior que haya en esa edición (la pareja se conoce al acabar la anterior) o el inicio de la edición si es la
    primera. Es estrictamente anterior al `visible_desde` de su propio resultado.

    Protocolo de corte retro de un partido de TML: corte = visible_desde_partido + 1 s. En ese corte se ven la pareja y
    los resultados de las rondas anteriores, y NO el propio resultado. RR (grupos) y las rondas fuera de tabla: sin
    instante propio (None ⇒ regla por semana), salvo RR que se ve desde el inicio. Sin ronda en tabla → None.
    """
    if ronda == "RR":
        return inicio_visible(inicio)
    for orden in (ORDEN_PRINCIPAL, ORDEN_PREVIAS):
        if ronda in orden:
            previas = [r for r in orden[: orden.index(ronda)] if r in rondas_edicion]
            if not previas:
                return inicio_visible(inicio)
            return visible_desde_ronda(previas[-1], inicio, dias)
    return None


def inicio_visible(inicio: date) -> datetime:
    return datetime(inicio.year, inicio.month, inicio.day, tzinfo=timezone.utc)
