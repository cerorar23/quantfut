"""Props de jugador (fichas 12, 13, 62): estadística = minutos × tasa por minuto, con conteo binomial negativo.

* Tasa por minuto: media con decaimiento de los últimos partidos del jugador, encogida hacia la tasa típica de su nivel de minutos
  (jerarquía por rol, ficha 62) con un peso de `k` minutos de evidencia previa.
* Minutos: muestras de la distribución condicionada a jugar del módulo `minutos` (las casas anulan la apuesta si no juega).
* Conteo: dado el minuto, binomial negativa con media `tasa · minutos` y sobredispersión `alfa` estimada con temporadas anteriores;
  la distribución final es la mezcla sobre las muestras de minutos, así la incertidumbre de minutos queda dentro de la cuota.
"""
import numpy as np
from scipy.special import gammaln

ESTADISTICAS = ("puntos", "rebotes", "asistencias", "triples")
TECHO = {"puntos": 70, "rebotes": 35, "asistencias": 30, "triples": 15}
BORDES_ROL = (10.0, 16.0, 22.0, 28.0, 34.0)       # minutos esperados que separan los niveles de rol


def nivel(minutos_esperados) -> np.ndarray:
    return np.searchsorted(np.asarray(BORDES_ROL), np.asarray(minutos_esperados), side="right")


def prior_por_nivel(min_esperados, minutos, stats) -> np.ndarray:
    """Tasa típica por minuto de cada nivel de rol: (n_niveles, n_estadísticas); `stats` es (n, n_estadísticas)."""
    niv = nivel(min_esperados)
    n_niv = len(BORDES_ROL) + 1
    salida = np.zeros((n_niv, stats.shape[1]))
    for i in range(n_niv):
        sel = niv == i
        total_min = minutos[sel].sum()
        salida[i] = stats[sel].sum(axis=0) / total_min if total_min > 0 else stats.sum(axis=0) / minutos.sum()
    return salida


def tasa_por_minuto(m_hist: np.ndarray, s_hist: np.ndarray, prior: np.ndarray, k: float, decaimiento: float) -> np.ndarray:
    """m_hist (N, V) minutos y s_hist (N, E, V) estadísticas de los V últimos partidos (NaN = no existe), del más antiguo al más
    reciente; prior (N, E). Devuelve (N, E): (Σ w·s + k·prior) / (Σ w·m + k)."""
    V = m_hist.shape[1]
    w = decaimiento ** np.arange(V - 1, -1, -1)
    # un dato que falta NO vale 0: ese partido sale de la tasa de esa estadística (ni sus puntos ni sus minutos cuentan)
    validos = ~np.isnan(s_hist) & ~np.isnan(m_hist)[:, None, :]
    num = np.where(validos, s_hist, 0.0) * w
    den = np.where(validos, m_hist[:, None, :], 0.0) * w
    return (num.sum(axis=2) + k * prior) / (den.sum(axis=2) + k)


def estimar_alfa(mu: np.ndarray, y: np.ndarray, minimo_mu: float = 0.5) -> float:
    """Sobredispersión por momentos (var = mu + alfa·mu²) con la media dada."""
    sel = mu > minimo_mu
    return float(max(0.001, np.mean(((y[sel] - mu[sel]) ** 2 - mu[sel]) / mu[sel] ** 2)))


def pmf_mezcla(tasa: np.ndarray, muestras_min: np.ndarray, alfa: float, techo: int) -> np.ndarray:
    """tasa (R,), muestras_min (R, S) → pmf (R, techo+1) de la mezcla binomial negativa sobre las S muestras de minutos."""
    mu = np.maximum(tasa[:, None] * muestras_min, 1e-9)[:, :, None]            # (R, S, 1)
    k = np.arange(techo + 1)[None, None, :]
    n = 1.0 / alfa
    logp = (gammaln(k + n) - gammaln(n) - gammaln(k + 1) + n * np.log(n / (n + mu)) + k * np.log(mu / (n + mu)))
    return np.exp(logp).mean(axis=1)


def prob_mas_de(pmf: np.ndarray, linea: np.ndarray) -> np.ndarray:
    """P(X > línea) por fila; en líneas enteras el empate exacto se reparte a mitades. Acotada a [0,001; 0,999]."""
    k = np.arange(pmf.shape[1])[None, :]
    linea = np.asarray(linea)[:, None]
    p = (pmf * (k > linea)).sum(axis=1) + 0.5 * (pmf * (k == linea)).sum(axis=1)
    return np.clip(p / pmf.sum(axis=1), 0.001, 0.999)


def pit_medio(pmf: np.ndarray, y: np.ndarray) -> np.ndarray:
    """F(y-1) + pmf(y)/2 por fila: uniforme en [0,1] si la distribución está calibrada."""
    acum = np.cumsum(pmf, axis=1) / pmf.sum(axis=1)[:, None]
    idx = np.clip(y.astype(int), 0, pmf.shape[1] - 1)
    r = np.arange(len(y))
    previo = np.where(idx > 0, acum[r, np.maximum(idx - 1, 0)], 0.0)
    masa = acum[r, idx] - previo
    return previo + masa / 2


def pit_aleatorio(pmf: np.ndarray, y: np.ndarray, semilla: int = 0) -> np.ndarray:
    """F(y-1) + U·pmf(y) con U uniforme: exactamente uniforme en [0,1] si la distribución discreta está calibrada
    (el PIT de punto medio no lo es en conteos bajos y sesga la cobertura)."""
    u = np.random.default_rng(semilla).random(len(y))
    acum = np.cumsum(pmf, axis=1) / pmf.sum(axis=1)[:, None]
    idx = np.clip(y.astype(int), 0, pmf.shape[1] - 1)
    r = np.arange(len(y))
    previo = np.where(idx > 0, acum[r, np.maximum(idx - 1, 0)], 0.0)
    return previo + u * (acum[r, idx] - previo)
