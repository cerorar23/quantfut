"""Qué cuenta como cierre de Pinnacle.

Las cuotas de `oddspapi_reconstructed` se cortaron, en el 74 % de los partidos, 60 minutos antes
del inicio: son el precio a la hora del XI, no el cierre. Contra un mercado de hace una hora el
modelo parece mejor de lo que es y el CLV sale inflado. Solo se aceptan las cortadas al inicio.
"""
FUENTE_RECONSTRUIDA = "oddspapi_reconstructed"
MAX_MIN_RECONSTRUIDO = 5
# El cierre de PropLine se carga DESPUÉS del partido (el recolector lo pide a las >= 6 h del saque y
# `propline_cierres` lo pasa cada 3 h). Una liquidación con CLV es inmutable: liquidar antes dejaría el
# CLV vacío para siempre. Se espera al cierre hasta este plazo; después se liquida sin él.
ESPERA_CIERRE_H = 48


def es_cierre_real(alias: str = "") -> str:
    """Condición SQL que se añade a toda lectura de `window_tag = 'close'`."""
    p = f"{alias}." if alias else ""
    return f"NOT ({p}source = '{FUENTE_RECONSTRUIDA}' AND {p}mins_to_kickoff > {MAX_MIN_RECONSTRUIDO})"


def cierre_o_vencido(alias: str = "m") -> str:
    """Condición SQL sobre `matches`: ya tiene cierre sharp del 1X2, o pasó ESPERA_CIERRE_H desde el saque."""
    from ..config import settings
    return (f"(EXISTS (SELECT 1 FROM odds_snapshots c WHERE c.match_id = {alias}.match_id"
            f" AND c.window_tag = 'close' AND c.market = 'h2h' AND c.bookmaker = '{settings.sharp_book}'"
            f" AND {es_cierre_real('c')})"
            f" OR {alias}.kickoff_utc < now() - interval '{ESPERA_CIERRE_H} hours')")
