"""Qué cuenta como cierre de Pinnacle.

Las cuotas de `oddspapi_reconstructed` se cortaron, en el 74 % de los partidos, 60 minutos antes
del inicio: son el precio a la hora del XI, no el cierre. Contra un mercado de hace una hora el
modelo parece mejor de lo que es y el CLV sale inflado. Solo se aceptan las cortadas al inicio.
"""
FUENTE_RECONSTRUIDA = "oddspapi_reconstructed"
MAX_MIN_RECONSTRUIDO = 5


def es_cierre_real(alias: str = "") -> str:
    """Condición SQL que se añade a toda lectura de `window_tag = 'close'`."""
    p = f"{alias}." if alias else ""
    return f"NOT ({p}source = '{FUENTE_RECONSTRUIDA}' AND {p}mins_to_kickoff > {MAX_MIN_RECONSTRUIDO})"
