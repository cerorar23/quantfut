"""Campos sueltos de una fila de TML: entradas, mano, altura, país, estadísticas. Puro.

Las estadísticas se devuelven con la clave de la columna de `estadistica` (plan §A.3). Un valor faltante es None,
nunca 0. Si el conjunto viola un CHECK de la base, la estadística de ese partido se rechaza entera.
"""
import re

ENTRADAS = {"Q", "LL", "WC", "PR", "SE"}
MANO = {"R": "D", "L": "Z", "U": "U"}      # 'A' (ambidiestro) no existe en el CHECK: no se escribe
MAPA_STAT = {"ace": "aces", "df": "dobles_faltas", "svpt": "puntos_saque", "1stIn": "primeros_dentro",
             "1stWon": "primeros_ganados", "2ndWon": "segundos_ganados", "SvGms": "juegos_saque",
             "bpSaved": "bp_salvados", "bpFaced": "bp_afrontados"}
ENTERO = re.compile(r"^\d+$")


def entero(valor: str) -> int | None:
    """None para vacío o no numérico (la validación de rango la hace quien llama)."""
    v = (valor or "").strip()
    return int(v) if ENTERO.match(v) else None


def entrada(valor: str) -> str | None:
    v = (valor or "").strip()
    return v if v in ENTRADAS else None


def mano(valor: str) -> str | None:
    return MANO.get((valor or "").strip())


def altura(valor: str) -> str | None:
    v = (valor or "").strip()
    return v if re.fullmatch(r"\d{2,3}", v) else None


def pais(valor: str) -> str | None:
    v = (valor or "").strip()
    return v if re.fullmatch(r"[A-Z]{3}", v) else None


def estadisticas(fila: dict, prefijo: str) -> dict:
    """Estadísticas de servicio de un jugador: `prefijo` es 'w' (ganador) o 'l' (perdedor) de TML."""
    return {MAPA_STAT[k]: entero(fila.get(f"{prefijo}_{k}", "")) for k in MAPA_STAT}


def violacion_estadistica(e: dict) -> str | None:
    """Motivo si el lado viola un CHECK de `estadistica` (no-negativos y orden de los contadores)."""
    if any(v is not None and v < 0 for v in e.values()):
        return "estadistica_negativa"
    d, s, pg = e["primeros_dentro"], e["puntos_saque"], e["primeros_ganados"]
    if d is not None and s is not None and d > s:
        return "estadistica_incoherente"
    if pg is not None and d is not None and pg > d:
        return "estadistica_incoherente"
    if e["bp_salvados"] is not None and e["bp_afrontados"] is not None and e["bp_salvados"] > e["bp_afrontados"]:
        return "estadistica_incoherente"
    return None


def sin_datos(e: dict) -> bool:
    return all(v is None for v in e.values())
