"""
Primera mitad a partir de los goles esperados del partido.

Los goles del 1T son Poisson independientes con media `PROPORCION_1T · (lambda, mu)`.
La proporción (local, visitante) se ajustó con football-data 2019/20-2021/22 y se midió
en 2022-2025 (`eval/primer_tiempo.py`, 6.236 partidos, cuotas de Pinnacle): solo
PASAN «ambos anotan 1T: no» y «gol en 1T: sí», por el lado y en el tramo medido
(62-95 %). Cambiar la proporción, el modelo o los mercados exige repetir esa prueba.

9-nov-2026 (decisión del titular tras `docs/backtest_mercados_ligas_nuevas_20261109.md`): el backtest de los mercados en las 21 competiciones
midió que, por encima del 85 %, la primera mitad promete de más (franja 0,85-0,95: +2,4 puntos en el conjunto y +7,1 en LaLiga 2). Desde
entonces se PUBLICA solo hasta el 85 % (`PROB_MAX_VALIDADA`); la prueba histórica original conserva su rango en `PROB_MAX_PRUEBA_ORIGINAL`.
Pendiente aparte: Liga MX y Champions sobreprometen 5-6 puntos entre 0,75 y 0,85, por debajo de este tope.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import poisson

try:   # generado por `qf.eval.ajuste_primer_tiempo`; sin él, todas las competiciones usan la proporción fija
    from .ajuste_1t_datos import AJUSTE as AJUSTE_1T
except ImportError:  # pragma: no cover - solo mientras no se ha generado el módulo
    AJUSTE_1T = {"pendiente": {}, "intercepto": {}}

PROPORCION_1T = (0.4366, 0.4588)
MAX_GOLES_1T = 8
# Rango de probabilidad en el que se midió y, por tanto, el único donde se publica.
PROB_MIN_VALIDADA, PROB_MAX_VALIDADA = 0.62, 0.85
PROB_MAX_PRUEBA_ORIGINAL = 0.95   # rango de la prueba histórica de 2022-2025 (`eval/primer_tiempo.py`); no se publica por encima de 0,85


def ajustar_probs(p: dict[str, float], liga: str | None, ajuste: dict | None = None) -> dict[str, float]:
    """
    Recalibración por competición de «gol en 1T» y «ambos anotan 1T» (9-nov-2026, titular):
    logit(p') = pendiente · logit(p) + intercepto[liga]. Sin liga, o con una competición que no figura en el ajuste, devuelve `p` tal cual.
    «Ambos anotan» nunca supera a «gol en 1T». El resto de mercados (ganador, más de 1,5) no se tocan.
    """
    ajuste = AJUSTE_1T if ajuste is None else ajuste
    a = (ajuste.get("intercepto") or {}).get(liga) if liga else None
    if not a:
        return p
    out = dict(p)
    for clave, nombre in (("gol", "gol_1t_si"), ("ambos", "ambos_1t_si")):
        if clave in a and clave in (ajuste.get("pendiente") or {}):
            q = min(max(p[nombre], 1e-6), 1 - 1e-6)
            z = ajuste["pendiente"][clave] * float(np.log(q / (1 - q))) + a[clave]
            out[nombre] = float(1.0 / (1.0 + np.exp(-z)))
    out["ambos_1t_si"] = min(out["ambos_1t_si"], out["gol_1t_si"])
    return out


def probs(lam: float, mu: float, proporcion: tuple[float, float] = PROPORCION_1T,
          liga: str | None = None) -> dict[str, float]:
    """Mercados de 1ª mitad desde los goles esperados del partido. Con `liga`, aplica el ajuste por competición (`ajustar_probs`)."""
    lh, la = proporcion[0] * lam, proporcion[1] * mu
    g = np.arange(MAX_GOLES_1T + 1)
    m = np.outer(poisson.pmf(g, lh), poisson.pmf(g, la))
    m = m / m.sum()
    total = np.add.outer(g, g)
    p = {
        "gol_1t_si": float(1 - m[0, 0]),
        "ambos_1t_si": float(m[1:, 1:].sum()),
        "ganador_1t_local": float(np.tril(m, -1).sum()),
        "ganador_1t_empate": float(np.trace(m)),
        "ganador_1t_visita": float(np.triu(m, 1).sum()),
        "mas_1_5_1t": float(m[total > 1].sum()),
    }
    return ajustar_probs(p, liga) if liga else p
