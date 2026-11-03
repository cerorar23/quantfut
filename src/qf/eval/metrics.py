"""
Métricas de evaluación probabilística.

El % de aciertos es inútil aquí. Lo que importa:

- RPS (Ranked Probability Score): la métrica estándar para 1X2 porque respeta
  el orden Local > Empate > Visitante. Constantinou & Fenton (2012).
- Log-loss: penaliza fuerte la sobreconfianza.
- Brier: interpretable, menos sensible que log-loss.
- Reliability diagram: el diagnóstico visual que va al dashboard público.

BASELINE OBLIGATORIO: el cierre sin margen del mercado. Si no le ganas en RPS,
no tienes un producto de picks. Publícalo aunque salga mal; es lo que hace
creíble el resto.
"""
from __future__ import annotations

import numpy as np

EPS = 1e-15


def rps(probs: np.ndarray, outcomes: np.ndarray) -> float:
    """
    Ranked Probability Score para resultados ordenados.
    probs: (n, k) en orden [home, draw, away]
    outcomes: (n,) índice del resultado real (0, 1, 2)
    Menor es mejor. Rango [0, 1].
    """
    probs = np.asarray(probs, dtype=float)
    n, k = probs.shape
    onehot = np.zeros_like(probs)
    onehot[np.arange(n), outcomes] = 1.0
    cum_p = np.cumsum(probs, axis=1)
    cum_o = np.cumsum(onehot, axis=1)
    return float(np.sum((cum_p[:, :-1] - cum_o[:, :-1]) ** 2) / (n * (k - 1)))


def log_loss(probs: np.ndarray, outcomes: np.ndarray) -> float:
    probs = np.clip(np.asarray(probs, dtype=float), EPS, 1.0)
    return float(-np.mean(np.log(probs[np.arange(len(outcomes)), outcomes])))


def brier(probs: np.ndarray, outcomes: np.ndarray) -> float:
    probs = np.asarray(probs, dtype=float)
    onehot = np.zeros_like(probs)
    onehot[np.arange(len(outcomes)), outcomes] = 1.0
    return float(np.mean(np.sum((probs - onehot) ** 2, axis=1)))


def reliability(probs_flat: np.ndarray, hits_flat: np.ndarray,
                n_bins: int = 10) -> list[dict]:
    """
    Reliability diagram. probs_flat y hits_flat aplanados sobre todas las
    selecciones. Un modelo bien calibrado tiene observed ≈ predicted en cada bin.
    """
    probs_flat = np.asarray(probs_flat, dtype=float)
    hits_flat = np.asarray(hits_flat, dtype=float)
    edges = np.linspace(0, 1, n_bins + 1)
    out = []
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        m = (probs_flat >= lo) & (probs_flat < hi if i < n_bins - 1 else probs_flat <= hi)
        n = int(m.sum())
        if n == 0:
            out.append({"bin": f"{lo:.1f}-{hi:.1f}", "n": 0,
                        "predicted": None, "observed": None, "gap": None})
            continue
        pred, obs = float(probs_flat[m].mean()), float(hits_flat[m].mean())
        # Error estándar binomial: sin esto, un bin con n=8 parece una señal
        se = float(np.sqrt(max(obs * (1 - obs), 1e-9) / n))
        out.append({"bin": f"{lo:.1f}-{hi:.1f}", "n": n,
                    "predicted": round(pred, 4), "observed": round(obs, 4),
                    "gap": round(obs - pred, 4), "se": round(se, 4),
                    "within_2se": bool(abs(obs - pred) <= 2 * se)})
    return out


def ece(probs_flat: np.ndarray, hits_flat: np.ndarray, n_bins: int = 10) -> float:
    """Expected Calibration Error: promedio ponderado del desajuste por bin."""
    bins = reliability(probs_flat, hits_flat, n_bins)
    total = sum(b["n"] for b in bins)
    if total == 0:
        return 0.0
    return float(sum(b["n"] * abs(b["gap"]) for b in bins if b["n"]) / total)


def evaluate(model_probs: np.ndarray, market_probs: np.ndarray | None,
             outcomes: np.ndarray) -> dict:
    """Paquete completo, listo para calibration_runs.bins y para el dashboard."""
    n = len(outcomes)
    onehot = np.zeros_like(model_probs)
    onehot[np.arange(n), outcomes] = 1.0

    res = {
        "n_obs": int(n),
        "rps": round(rps(model_probs, outcomes), 5),
        "log_loss": round(log_loss(model_probs, outcomes), 5),
        "brier": round(brier(model_probs, outcomes), 5),
        "ece": round(ece(model_probs.ravel(), onehot.ravel()), 5),
        "bins": reliability(model_probs.ravel(), onehot.ravel()),
    }

    if market_probs is not None:
        res["rps_market"] = round(rps(market_probs, outcomes), 5)
        res["rps_delta"] = round(res["rps_market"] - res["rps"], 5)
        res["beats_market"] = res["rps"] < res["rps_market"]
        # Nota honesta: un delta positivo diminuto en pocas observaciones es ruido.
        res["delta_is_meaningful"] = bool(res["rps_delta"] > 0.002 and n > 1000)
    return res


def blend_logit(model_p: np.ndarray, market_p: np.ndarray, w_model: float) -> np.ndarray:
    """
    Mezcla modelo y mercado en espacio logit y renormaliza.

    w_model debe salir de una regresión logística ajustada en validación, no
    de tu intuición. Si el ajuste dice w_model = 0.15, ese es el número.
    Un peso bajo NO es un fracaso: significa que el mercado ya sabe casi todo,
    que es el estado normal del mundo.
    """
    a = np.log(np.clip(model_p, EPS, 1))
    b = np.log(np.clip(market_p, EPS, 1))
    z = np.exp(w_model * a + (1 - w_model) * b)
    return z / z.sum(axis=1, keepdims=True)


def pav(y: np.ndarray, pesos: np.ndarray | None = None) -> np.ndarray:
    """Regresión isotónica creciente (pool-adjacent-violators) de `y`, ya ordenada por el pronóstico."""
    y = np.asarray(y, dtype=float)
    w_in = np.ones_like(y) if pesos is None else np.asarray(pesos, dtype=float)
    vals, ws, largos = [], [], []
    for v, w in zip(y, w_in):
        vals.append(v); ws.append(w); largos.append(1)
        while len(vals) > 1 and vals[-2] > vals[-1]:
            w2 = ws[-2] + ws[-1]
            vals[-2] = (vals[-2] * ws[-2] + vals[-1] * ws[-1]) / w2
            ws[-2] = w2; largos[-2] += largos[-1]
            vals.pop(); ws.pop(); largos.pop()
    return np.repeat(vals, largos)


def _puntuacion(p: np.ndarray, y: np.ndarray, score: str) -> float:
    if score == "brier":
        return float(np.mean((p - y) ** 2))
    p = np.clip(p, EPS, 1 - EPS)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def murphy(p: np.ndarray, y: np.ndarray, score: str = "brier") -> dict:
    """
    Descomposición de Murphy de un pronóstico binario (Dimitriadis-Gneiting-Jordan, CORP; Pohle 2020):
    puntuación = UNC − DSC + MCB. MCB (descalibración) y DSC (resolución) salen de recalibrar con PAV; UNC es la
    puntuación de la climatología. Un pronóstico calibrado pero sin resolución es climatología con otro nombre.
    """
    p = np.asarray(p, dtype=float); y = np.asarray(y, dtype=float)
    # Los pronósticos iguales se recalibran juntos (CORP): se agrupan antes del PAV.
    unicos, inv = np.unique(p, return_inverse=True)
    cuenta = np.bincount(inv)
    recal = pav(np.bincount(inv, weights=y) / cuenta, cuenta)[inv]
    s, s_rc = _puntuacion(p, y, score), _puntuacion(recal, y, score)
    unc = _puntuacion(np.full_like(p, y.mean()), y, score)
    return {"score": s, "mcb": s - s_rc, "dsc": unc - s_rc, "unc": unc, "n": int(len(y))}


def diebold_mariano(perdida_a: np.ndarray, perdida_b: np.ndarray, bloques: np.ndarray | None = None) -> dict:
    """
    Diferencia media de pérdidas A − B (positiva = A peor) con error estándar robusto por bloques (jornada o
    semana): los partidos de un mismo bloque comparten información y no son independientes.
    """
    d = np.asarray(perdida_a, dtype=float) - np.asarray(perdida_b, dtype=float)
    b = np.arange(len(d)) if bloques is None else np.asarray(bloques)
    _, inv = np.unique(b, return_inverse=True)
    sumas = np.bincount(inv, weights=d - d.mean())
    var = float(np.sum(sumas ** 2)) / len(d) ** 2
    se = float(np.sqrt(var)) if var > 0 else float("nan")
    delta = float(d.mean())
    return {"delta": delta, "se": se, "t": delta / se if se else float("nan"),
            "ic95": (delta - 1.96 * se, delta + 1.96 * se), "n": int(len(d)), "bloques": int(inv.max() + 1)}
