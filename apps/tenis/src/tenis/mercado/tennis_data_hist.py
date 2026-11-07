"""Cargador y normalizador de cuotas histricas de Tennis-Data (plan tcnico tenis, B.4, I.0, S5).

Procesa odds_raw.parquet (o los xls/xlsx originales si se especifica).
Calcula mrgenes y probabilidades des-marginadas (proporcionales) para PS (Pinnacle), B365 y Avg.
Selecciona la referencia de cierre segn la regla I.0:
  - PS hasta enero de 2026;
  - Desde febrero de 2026, media de casas (Avg) o Bet365;
  - Todas marcadas clase 'b' (cierre declarado sin instante).
Permite verificar independientemente el margen mediano de Pinnacle (2.46 %).
"""
from __future__ import annotations

import math
from datetime import date, datetime
from pathlib import Path
from statistics import median
from typing import Sequence

import pandas as pd
import pyarrow.parquet as pq

from .devig import devig_dos_vias

RUTA_ODDS_DEFECTO = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\tennis_data_manual_processed\odds_raw.parquet")


def _fnum(val) -> float | None:
    if val is None or pd.isna(val):
        return None
    try:
        x = float(val)
        return x if not math.isnan(x) and not math.isinf(x) and x > 1.0 else None
    except (ValueError, TypeError):
        return None


def cargar_tennis_data_raw(ruta: Path = RUTA_ODDS_DEFECTO, desde_anio: int = 2005) -> pd.DataFrame:
    """Carga odds_raw.parquet y filtra por ao mnimo."""
    if not ruta.exists():
        raise FileNotFoundError(f"No existe el archivo de cuotas Tennis-Data en {ruta}")

    df = pq.read_table(ruta).to_pandas()
    if "file_year" in df.columns:
        df = df[df["file_year"] >= desde_anio].copy()
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df


def procesar_cuotas_partidos(df: pd.DataFrame) -> list[dict]:
    """Extrae y des-margina cuotas de ganador para cada partido de Tennis-Data.

    Aplica regla I.0 para elegir la cuota de cierre de referencia.
    """
    partidos = []
    fecha_corte_ps = pd.Timestamp("2026-02-01")

    for r in df.itertuples():
        circuito = str(getattr(r, "circuit", "")).lower()
        ganador_nombre = getattr(r, "Winner", None)
        perdedor_nombre = getattr(r, "Loser", None)
        fecha = getattr(r, "Date", None)
        torneo = getattr(r, "Tournament", None)
        superficie = getattr(r, "Surface", None)
        comentario = str(getattr(r, "Comment", "") or "")

        if not ganador_nombre or not perdedor_nombre or pd.isna(fecha):
            continue

        # Extraer cuotas PS (Pinnacle)
        ps_w, ps_l = _fnum(getattr(r, "PSW", None)), _fnum(getattr(r, "PSL", None))
        prob_ps_w, prob_ps_l, marg_ps = devig_dos_vias(ps_w, ps_l)

        # Extraer cuotas B365
        b365_w, b365_l = _fnum(getattr(r, "B365W", None)), _fnum(getattr(r, "B365L", None))
        prob_b365_w, prob_b365_l, marg_b365 = devig_dos_vias(b365_w, b365_l)

        # Extraer cuotas Avg
        avg_w, avg_l = _fnum(getattr(r, "AvgW", None)), _fnum(getattr(r, "AvgL", None))
        prob_avg_w, prob_avg_l, marg_avg = devig_dos_vias(avg_w, avg_l)

        # Seleccin de cierre de referencia (I.0)
        es_post_ps = fecha >= fecha_corte_ps
        ref_casa = None
        ref_p_winner = None
        ref_p_loser = None
        ref_margen = None

        if not es_post_ps and prob_ps_w is not None:
            ref_casa = "PS"
            ref_p_winner = prob_ps_w
            ref_p_loser = prob_ps_l
            ref_margen = marg_ps
        elif prob_avg_w is not None:
            ref_casa = "Avg"
            ref_p_winner = prob_avg_w
            ref_p_loser = prob_avg_l
            ref_margen = marg_avg
        elif prob_b365_w is not None:
            ref_casa = "B365"
            ref_p_winner = prob_b365_w
            ref_p_loser = prob_b365_l
            ref_margen = marg_b365
        elif prob_ps_w is not None:
            ref_casa = "PS"
            ref_p_winner = prob_ps_w
            ref_p_loser = prob_ps_l
            ref_margen = marg_ps

        partidos.append({
            "circuito": circuito,
            "fecha": fecha.date() if isinstance(fecha, pd.Timestamp) else fecha,
            "anio": getattr(r, "file_year", fecha.year if hasattr(fecha, "year") else None),
            "torneo": torneo,
            "superficie": superficie,
            "ganador": str(ganador_nombre),
            "perdedor": str(perdedor_nombre),
            "comentario": comentario,
            # PS
            "ps_w": ps_w, "ps_l": ps_l, "prob_ps_w": prob_ps_w, "prob_ps_l": prob_ps_l, "margen_ps": marg_ps,
            # B365
            "b365_w": b365_w, "b365_l": b365_l, "prob_b365_w": prob_b365_w, "prob_b365_l": prob_b365_l, "margen_b365": marg_b365,
            # Avg
            "avg_w": avg_w, "avg_l": avg_l, "prob_avg_w": prob_avg_w, "prob_avg_l": prob_avg_l, "margen_avg": marg_avg,
            # Referencia elegida
            "ref_casa": ref_casa,
            "ref_p_winner": ref_p_winner,
            "ref_p_loser": ref_p_loser,
            "ref_margen": ref_margen,
            "clase_cierre": "b",
        })

    return partidos


def calcular_margen_mediano_pinnacle(partidos: Sequence[dict]) -> dict:
    """Calcula la distribucin y mediana del margen de Pinnacle (PS) sobre los partidos con cuota ambas caras."""
    margenes = [p["margen_ps"] for p in partidos if p.get("margen_ps") is not None]
    if not margenes:
        return {"n": 0, "mediana": None}
    s = sorted(margenes)
    n = len(s)
    med = median(s)
    return {
        "n": n,
        "mediana": med,
        "mediana_pct": round(med * 100, 2),
        "min": s[0],
        "max": s[-1],
    }
