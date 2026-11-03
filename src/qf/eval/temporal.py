"""Resúmenes que solo incorporan observaciones disponibles antes del corte consultado."""
from __future__ import annotations

import numpy as np
import pandas as pd


def medias_previas(valores, grupos, cortes, disponibles, vida: float | None = None):
    """(media, n) por fila; los empates de recepción se incorporan juntos, después de su hora.

    `disponibles` es la recepción real en una simulación prospectiva. Una reconstrucción histórica
    debe pasar explícitamente el final reconstruido del partido y etiquetar sus resultados como tales.
    """
    if vida is not None and vida <= 0:
        raise ValueError('La vida media debe ser positiva')
    x = pd.DataFrame({'valor': pd.to_numeric(valores, errors='coerce'), 'grupo': grupos,
                      'corte': pd.to_datetime(cortes, utc=True),
                      'disponible': pd.to_datetime(disponibles, utc=True)})
    media = pd.Series(np.nan, index=x.index, dtype=float)
    cuenta = pd.Series(0, index=x.index, dtype=int)
    decay = 1.0 if vida is None else 2 ** (-1 / vida)
    for _, g in x.groupby('grupo', dropna=False, sort=False):
        obs = g[g.disponible.notna() & np.isfinite(g.valor)].groupby('disponible').valor.agg(['sum', 'count'])
        if obs.empty:
            continue
        n = obs['count'].cumsum().to_numpy()
        if vida is None:
            means = obs['sum'].cumsum().to_numpy() / n
        else:
            means, num, den = [], 0.0, 0.0
            for total, size in obs[['sum', 'count']].itertuples(index=False, name=None):
                factor = decay ** size
                weight = (1 - factor) / (1 - decay)
                num, den = factor * num + total / size * weight, factor * den + weight
                means.append(num / den)
            means = np.asarray(means)
        pos = np.searchsorted(obs.index.asi8, pd.DatetimeIndex(g.corte).asi8, side='left') - 1
        ok = (pos >= 0) & g.corte.notna().to_numpy()
        media.loc[g.index[ok]] = means[pos[ok]]
        cuenta.loc[g.index[ok]] = n[pos[ok]]
    return media, cuenta
