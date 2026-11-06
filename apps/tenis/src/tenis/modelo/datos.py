"""Lee la exportación punto en el tiempo y la convierte en arrays por circuito para el filtro.

- Entradas y etiquetas van en campos separados: el filtro solo lee las etiquetas de los EVENTOS (en su instante de
  visibilidad) y la evaluación lee `y1`/`liquida` aparte.
- Los ids de jugador se cambian por índices internos 0..n−1 (`indice_jugador`): son claves, nunca rasgos.
- La reserva (temporada > `hasta`) no se carga: ni partidos ni eventos.
"""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

RUTA_EXPORT = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\rediseno_20261104\export_pit")
SUPERFICIES = ("Clay", "Grass", "Hard", "Indoor")
HARD = 2
FORMATOS = ((3, "tiebreak_7"), (3, "tiebreak_10"), (3, "ventaja"), (5, "tiebreak_7"), (5, "tiebreak_10"), (5, "ventaja"))
COL_P = ["partido_key", "circuito", "temporada", "categoria", "ronda", "superficie", "mejor_de", "formato_decisivo",
         "por_equipos", "jjoo", "semana_previa_gs", "jugador_1", "jugador_2", "rank_1", "rank_2", "n_prev_1", "n_prev_2",
         "corte_utc", "excluir_motivo"]
COL_Y = ["partido_key", "y_estado", "y_ganador", "y_sets_completos"]
COL_E = ["partido_key", "temporada", "circuito", "jugador_1", "jugador_2", "estado", "ganador", "minutos_1", "minutos_2",
         "actualiza_rating", "visible_resultado_utc"]


@dataclass
class DatosCircuito:
    circuito: str
    n_jugadores: int
    p: pd.DataFrame        # partidos (entradas), orden (corte, partido_key); columnas internas j1, j2, sup, fmt, ...
    y1: np.ndarray         # etiqueta: 1 si gana el lado 1, 0 si pierde, −1 sin ganador
    liquida: np.ndarray    # regla de liquidación §I.3
    e: pd.DataFrame        # eventos de resultado, orden (visible, partido_key); columna pidx → fila de `p`


def indice_formato(mejor_de, decisivo) -> int:
    try:
        return FORMATOS.index((int(mejor_de), str(decisivo)))
    except (ValueError, TypeError):
        return -1


def _ns(serie: pd.Series) -> np.ndarray:
    """Instante en ns UTC (entero: las comparaciones visible < corte son exactas)."""
    idx = pd.DatetimeIndex(serie)
    return (idx.tz_convert("UTC") if idx.tz is not None else idx.tz_localize("UTC")).asi8.copy()


def liquidacion(estado: pd.Series, sets_completos: pd.Series) -> np.ndarray:
    """Plan §I.3: completado liquida; retirada liquida con ≥ 1 set completo; walkover, cancelado, descalificado: nulo."""
    sc = pd.to_numeric(sets_completos, errors="coerce").fillna(0).to_numpy()
    return ((estado == "completado") | ((estado == "retirada") & (sc >= 1))).to_numpy()


def preparar(partidos: pd.DataFrame, eventos: pd.DataFrame, circuito: str, hasta: int) -> DatosCircuito:
    """Arrays del circuito con temporada ≤ `hasta`. `partidos` debe traer COL_P + COL_Y; `eventos` COL_E."""
    p = partidos[(partidos.circuito == circuito) & (partidos.temporada <= hasta)].copy()
    e = eventos[(eventos.circuito == circuito) & (eventos.temporada <= hasta)].copy()
    ids = np.unique(np.r_[p.jugador_1, p.jugador_2, e.jugador_1, e.jugador_2])
    for df in (p, e):
        df["j1"], df["j2"] = np.searchsorted(ids, df.jugador_1), np.searchsorted(ids, df.jugador_2)
    p["corte_ns"] = _ns(p.corte_utc)
    p = p.sort_values(["corte_ns", "partido_key"], kind="mergesort").drop_duplicates("partido_key").reset_index(drop=True)
    p["sup"] = p.superficie.map({s: i for i, s in enumerate(SUPERFICIES)}).fillna(-1).astype(int)
    p["fmt"] = [indice_formato(m, d) for m, d in zip(p.mejor_de, p.formato_decisivo)]
    p["equipos"] = p.por_equipos.fillna(False).astype(bool) | p.jjoo.fillna(False).astype(bool)
    p["pregs"] = p.semana_previa_gs.fillna(False).astype(float)
    p["nivel"] = (p.categoria == "Challenger").astype(int)          # solo para la variante σ_R por nivel
    p["rank1"] = pd.to_numeric(p.rank_1, errors="coerce").astype(float)
    p["rank2"] = pd.to_numeric(p.rank_2, errors="coerce").astype(float)
    g = pd.to_numeric(p.y_ganador, errors="coerce")
    y1 = np.where(g == 1, 1, np.where(g == 2, 0, -1))
    liq = liquidacion(p.y_estado, p.y_sets_completos) & (y1 >= 0)
    e["vis_ns"] = _ns(e.visible_resultado_utc)
    # El mismo resultado entregado dos veces se aplica UNA vez (el primero en visibilidad; empate por clave).
    e = e.sort_values(["vis_ns", "partido_key"], kind="mergesort").drop_duplicates("partido_key").reset_index(drop=True)
    pos = pd.Series(np.arange(len(p)), index=p.partido_key)
    e["pidx"] = e.partido_key.map(pos).fillna(-1).astype(int)
    e["gan"] = pd.to_numeric(e.ganador, errors="coerce").fillna(0).astype(int)
    e["min1"] = pd.to_numeric(e.minutos_1, errors="coerce").astype(float)
    e["min2"] = pd.to_numeric(e.minutos_2, errors="coerce").astype(float)
    e["walk"] = (e.estado == "walkover").to_numpy()
    e["actualiza"] = e.actualiza_rating.fillna(False).astype(bool)
    p = p.drop(columns=["y_estado", "y_ganador", "y_sets_completos"])
    return DatosCircuito(circuito, len(ids), p, y1, liq, e)


def cargar_export(ruta: Path = RUTA_EXPORT, hasta: int = 2024) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Lee partidos (entradas + etiquetas mínimas) y eventos con temporada ≤ `hasta` (la reserva no se lee)."""
    filtro = [("temporada", "<=", int(hasta))]
    p = pd.read_parquet(ruta / "partidos.parquet", columns=list(dict.fromkeys(COL_P + COL_Y)), filters=filtro)
    e = pd.read_parquet(ruta / "eventos_resultado.parquet", columns=COL_E, filters=filtro)
    return p, e
