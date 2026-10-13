"""Disponibilidad temporal del xG observado de API-Football."""
from __future__ import annotations

import numpy as np
import pandas as pd


def xg_at_cutoff(df: pd.DataFrame, as_of) -> tuple[np.ndarray, np.ndarray]:
    """Excluye la nueva fuente hasta su captura real, sin modificar el frame.

    El histórico anterior conserva su tratamiento existente: su primera
    recepción no se conoce y no se convierte en evidencia point-in-time.
    """
    arrays = [pd.to_numeric(df[c], errors="coerce").to_numpy(dtype=float, copy=True)
              if c in df else np.full(len(df), np.nan)
              for c in ("home_xg", "away_xg")]
    if "xg_source" in df:
        api = df["xg_source"].eq("api_football").fillna(False).to_numpy()
        captured = pd.to_datetime(
            df.get("xg_recorded_at", pd.Series(pd.NaT, index=df.index)),
            utc=True, errors="coerce")
        cutoff = pd.Timestamp(as_of)
        cutoff = (cutoff.tz_localize("UTC") if cutoff.tzinfo is None
                  else cutoff.tz_convert("UTC"))
        unavailable = api & (captured.isna() | (captured > cutoff)).to_numpy()
        for values in arrays:
            values[unavailable] = np.nan
    return arrays[0], arrays[1]
