"""Reglas ESCRITAS de la exportación PIT (puras, sin base de datos): superficie del modelo, formato del set decisivo,
contextos (§F), corte del pronóstico y fecha del ranking. Cada regla está aquí y en el manifiesto (`REGLAS`).
"""
import re
from datetime import timedelta

# Corte del pronóstico (plan §C.6): con hora real (SofaScore) = inicio − 60 min. Sin hora (protocolo retro de TML,
# LEEME y `tml_reglas.visible_desde_partido`): instante en que se conoce la pareja + 1 s.
MARGEN_CORTE = timedelta(minutes=60)
PASO_RETRO = timedelta(seconds=1)
HISTORIA_CORTA = 20   # plan §D.6: n_prev < 20 → historia corta (se marca, no se descarta)

# ---------------------------------------------------------------- superficie (plan §B.2)
SUPERFICIES_MODELO = ("Clay", "Grass", "Hard", "Indoor")


def superficie_modelo(superficie: str | None, indoor) -> tuple[str | None, object, str | None]:
    """(categoría del modelo, indoor efectivo, motivo). La tierra bajo techo queda en Clay con indoor=True; la dura
    bajo techo es Indoor; la moqueta es Indoor salvo prueba en contra (indoor=False ⇒ sin categoría). Indoor
    desconocido conserva la categoría de su superficie con indoor=NULL (nivel propio, plan §B.2) y se marca."""
    ind = None if indoor is None or indoor != indoor else bool(indoor)   # NaN → None
    if superficie is None or superficie != superficie:
        return None, ind, "superficie_desconocida"
    if superficie == "clay":
        return "Clay", ind, ("indoor_desconocido" if ind is None else None)
    if superficie == "grass":
        return "Grass", ind, ("indoor_desconocido" if ind is None else None)
    if superficie == "hard":
        if ind is None:
            return "Hard", None, "indoor_desconocido"
        return ("Indoor" if ind else "Hard"), ind, None
    if superficie == "carpet":
        if ind is False:
            return None, False, "moqueta_exterior"
        return "Indoor", True, (None if ind else "moqueta_indoor_supuesto")
    return None, ind, "superficie_desconocida"


# ---------------------------------------------------------------- formato del set decisivo (plan §F.3)
FORMATOS = ("tiebreak_7", "tiebreak_10", "ventaja", "supertiebreak_10", "desconocido")
_GS = (
    ("ao", re.compile(r"australian (open|championships|chps)", re.I)),   # TML guarda el nombre de 1968
    ("rg", re.compile(r"roland.garros|french open", re.I)),
    ("wim", re.compile(r"wimbledon", re.I)),
    ("uso", re.compile(r"\bus open\b|u\.s\. open", re.I)),
)
_NEXTGEN = re.compile(r"next.?gen", re.I)
_LAVER = re.compile(r"laver cup", re.I)
_JJOO = re.compile(r"olymp", re.I)
_EQUIPOS = re.compile(r"davis|billie jean|bjk|fed cup|united cup|laver cup|hopman|atp cup", re.I)
CATEGORIAS_GIRA = {"M1000", "WTA1000", "500", "250", "Challenger"}
DESDE_REGLA_GIRA = 1990


def grand_slam(nombre: str | None) -> str | None:
    for codigo, patron in _GS:
        if patron.search(nombre or ""):
            return codigo
    return None


def formato_decisivo(categoria: str | None, nombre: str | None, temporada: int, ronda: str) -> tuple[str, str]:
    """(formato del set decisivo, regla aplicada). Regla escrita por torneo y año; sin regla → `desconocido`.

    Grand Slams, cuadro principal (individual, ambos circuitos):
      Australian Open: ventaja hasta 2018; tiebreak a 10 en 6-6 desde 2019.
      Roland Garros: ventaja hasta 2021; tiebreak a 10 desde 2022.
      Wimbledon: ventaja hasta 2018; 2019-2021 tiebreak a 7 en 12-12 (no está en el catálogo ni lo soporta el
        simulador, §F.3) → desconocido; tiebreak a 10 desde 2022.
      US Open: tiebreak a 7 hasta 2021; tiebreak a 10 desde 2022.
      Previas de Grand Slam: tiebreak a 10 desde 2022 (regla unificada); antes, sin verificar → desconocido.
    Gira (M1000, WTA1000, 500, 250, Challenger) desde 1990: tiebreak a 7. Finales: tiebreak a 7 (NextGen → desconocido,
    sets a 4). Laver Cup: supertiebreak a 10 en lugar del 3.er set. Resto de equipos, JJOO y años anteriores a 1990 →
    desconocido.
    Categoría vacía (TML la deja vacía cuando el nivel del torneo cambió entre años): se decide por el nombre: GS por
    nombre → reglas de GS; JJOO o equipos por nombre → sus reglas; NextGen → desconocido; cualquier otro torneo
    individual desde 1990 → tiebreak a 7 (como la gira)."""
    if categoria is None:
        if grand_slam(nombre):
            categoria = "GS"
        elif _JJOO.search(nombre or ""):
            categoria = "JJOO"
        elif _EQUIPOS.search(nombre or ""):
            categoria = "equipos"
        elif _NEXTGEN.search(nombre or ""):
            return "desconocido", "nextgen"
        elif temporada >= DESDE_REGLA_GIRA:
            return "tiebreak_7", "individual_sin_categoria_tb7"
    if categoria == "GS":
        gs = grand_slam(nombre)
        if ronda.startswith("Q"):
            return ("tiebreak_10", "gs_previa_desde_2022") if temporada >= 2022 else ("desconocido", "gs_previa_sin_regla")
        if gs is None:
            return "desconocido", "gs_no_identificado"
        if temporada >= 2022:
            return "tiebreak_10", "gs_unificado_desde_2022"
        if gs == "ao":
            return ("tiebreak_10", "ao_2019_2021") if temporada >= 2019 else ("ventaja", "ao_hasta_2018")
        if gs == "rg":
            return "ventaja", "rg_hasta_2021"
        if gs == "wim":
            return ("desconocido", "wim_tb7_en_12_12") if temporada >= 2019 else ("ventaja", "wim_hasta_2018")
        return "tiebreak_7", "uso_hasta_2021"
    if categoria == "equipos":
        if _LAVER.search(nombre or ""):
            return "supertiebreak_10", "laver_cup"
        return "desconocido", "equipos_sin_regla"
    if categoria == "Finales":
        if _NEXTGEN.search(nombre or ""):
            return "desconocido", "nextgen"
        return "tiebreak_7", "finales"
    if categoria in CATEGORIAS_GIRA and temporada >= DESDE_REGLA_GIRA:
        return "tiebreak_7", "gira_tb7"
    return "desconocido", f"sin_regla:{categoria}"


# ---------------------------------------------------------------- contextos (plan §F.1, §F.2)
# Semana previa a un Grand Slam: edición de gira (no GS, no equipos, no JJOO) del mismo circuito cuyo inicio cae entre
# 3 y 9 días antes del inicio del cuadro principal de un GS. El inicio del GS es CALENDARIO PUBLICADO con meses de
# antelación (excepción declarada a la regla de visibilidad, ver manifiesto): no depende de ningún resultado.
PREVIA_GS_DIAS = (3, 9)
CATEGORIAS_SIN_PREVIA = {"GS", "equipos", "JJOO"}


def es_jjoo(categoria: str | None, nombre: str | None) -> bool:
    return categoria == "JJOO" or bool(_JJOO.search(nombre or ""))


def es_equipos(categoria: str | None, nombre: str | None) -> bool:
    return categoria == "equipos" or bool(_EQUIPOS.search(nombre or ""))
