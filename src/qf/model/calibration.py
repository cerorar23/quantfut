"""
Calibración de probabilidades. La capa que hace que cuando digas 65%, gane
el 65%.

DÓNDE SE CALIBRA Y POR QUÉ AHÍ
------------------------------
La tentación es calibrar el 1X2 con una isotónica y listo. El problema es que
en este sistema el 1X2 no es un modelo aparte: los ~150 mercados salen TODOS de
la misma matriz de marcadores. Si corriges el 1X2 por un lado, el over/under y
el hándicap asiático siguen saliendo de la matriz sin corregir, y acabas
publicando un 1X2 que no cuadra con tu propio total de goles. Un comprador que
compare las dos cosas ve la incoherencia.

Por eso el calibrador primario actúa sobre las INTENSIDADES (lambda_local,
lambda_visitante) con una corrección afín en log-espacio:

    log lambda' = a0 + a1 * log lambda
    log mu'     = b0 + b1 * log mu

Cuatro parámetros ajustados maximizando la verosimilitud del MARCADOR EXACTO
fuera de muestra. Hasta el 2026-10-21 se minimizaba el log-loss del 1X2, que
casi no cambia si se escalan juntas las dos intensidades: el nivel de goles
quedaba sin identificar y el calibrador activo bajaba mu un 6 % y dejaba el
«más de 2,5» 4,3 puntos por debajo de lo real (auditoría del 21-oct). El
marcador sí lo identifica, y la puerta exige que el 1X2 no empeore.
a1 < 1 comprime las predicciones hacia el centro (el caso típico: el modelo es
demasiado confiado en los extremos); a0 corrige un sesgo sistemático de nivel
de goles. Como todo se deriva después de la matriz recalculada, los 150
mercados siguen siendo coherentes entre sí.

La isotónica queda como diagnóstico y como opción para el 1X2 puro: es más
flexible que la corrección afín, pero rompe la coherencia entre mercados, así
que NO se aplica al pipeline de pricing.

REGLA INNEGOCIABLE: se ajusta sobre predicciones FUERA DE MUESTRA
(`eval.backtest.walk_forward_oos`). Calibrar sobre predicciones dentro de
muestra aprende a corregir un error que en producción no existe y empeora el
resultado real mientras el backtest mejora. Es la fuga más silenciosa de todas.

Venn-ABERS daría además intervalos de confianza sobre la propia probabilidad
calibrada. Es el siguiente paso; la isotónica/afín cubre el 95% del beneficio
con una fracción de la complejidad.
"""
from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass, asdict

import numpy as np
from scipy.optimize import minimize
from scipy.stats import poisson

from ..eval.metrics import log_loss, rps

log = logging.getLogger(__name__)

EPS = 1e-12


# ---------------------------------------------------------------------------
# 1X2 vectorizado desde (lambda, mu, rho). Mismo cálculo que pricing, pero
# sobre arrays: el ajuste evalúa miles de partidos por iteración.
# ---------------------------------------------------------------------------

def score_matrices(lam: np.ndarray, mu: np.ndarray, rho: float,
                   max_goals: int = 10) -> np.ndarray:
    """Matrices de marcadores (n, G, G) normalizadas, con la corrección tau."""
    lam = np.clip(np.asarray(lam, dtype=float), 1e-6, 25.0)
    mu = np.clip(np.asarray(mu, dtype=float), 1e-6, 25.0)
    g = np.arange(max_goals + 1)

    ph = poisson.pmf(g[None, :], lam[:, None])      # (n, G)
    pa = poisson.pmf(g[None, :], mu[:, None])       # (n, G)
    m = ph[:, :, None] * pa[:, None, :]             # (n, G, G)

    # Corrección tau de Dixon-Coles: solo toca los cuatro marcadores bajos.
    m[:, 0, 0] *= 1.0 - lam * mu * rho
    m[:, 0, 1] *= 1.0 + lam * rho
    m[:, 1, 0] *= 1.0 + mu * rho
    m[:, 1, 1] *= 1.0 - rho
    m = np.clip(m, 0.0, None)
    m /= np.clip(m.sum(axis=(1, 2), keepdims=True), EPS, None)
    return m


def probs_1x2(lam: np.ndarray, mu: np.ndarray, rho: float,
              max_goals: int = 10) -> np.ndarray:
    m = score_matrices(lam, mu, rho, max_goals)
    idx = np.arange(max_goals + 1)
    home_mask = idx[:, None] > idx[None, :]
    away_mask = idx[:, None] < idx[None, :]
    home = m[:, home_mask].sum(axis=1)
    draw = np.trace(m, axis1=1, axis2=2)
    away = m[:, away_mask].sum(axis=1)
    out = np.stack([home, draw, away], axis=1)
    return out / np.clip(out.sum(axis=1, keepdims=True), EPS, None)


def score_log_loss(lam: np.ndarray, mu: np.ndarray, rho: float,
                   home_goals: np.ndarray, away_goals: np.ndarray,
                   max_goals: int = 10) -> float:
    """Log-loss medio del marcador exacto (goles por encima de `max_goals` se truncan)."""
    m = score_matrices(lam, mu, rho, max_goals)
    hg = np.clip(np.asarray(home_goals, dtype=int), 0, max_goals)
    ag = np.clip(np.asarray(away_goals, dtype=int), 0, max_goals)
    return float(-np.mean(np.log(np.clip(m[np.arange(len(hg)), hg, ag], EPS, None))))


# ---------------------------------------------------------------------------
# Calibrador de intensidades
# ---------------------------------------------------------------------------

@dataclass
class CalParams:
    a0: float = 0.0
    a1: float = 1.0
    b0: float = 0.0
    b1: float = 1.0
    rho: float = 0.0
    n_train: int = 0
    fitted_at: str = ""
    validated: bool = False
    val_metrics: dict = None

    @property
    def is_identity(self) -> bool:
        return (abs(self.a0) < 1e-9 and abs(self.a1 - 1) < 1e-9
                and abs(self.b0) < 1e-9 and abs(self.b1 - 1) < 1e-9)


class LambdaCalibrator:
    """
    Corrección afín en log-espacio sobre (lambda_local, lambda_visitante).

    Si no se ha ajustado (o el ajuste no superó la validación) se comporta como
    la identidad: el pipeline sigue funcionando sin calibrar, que es el estado
    correcto por defecto antes de tener datos suficientes.
    """

    def __init__(self, params: CalParams | None = None):
        self.params = params or CalParams()

    # ---------------- aplicación ----------------

    def apply(self, lam: float, mu: float) -> tuple[float, float]:
        p = self.params
        if p.is_identity:
            return lam, mu
        lam_c = float(np.exp(p.a0 + p.a1 * np.log(max(lam, EPS))))
        mu_c = float(np.exp(p.b0 + p.b1 * np.log(max(mu, EPS))))
        return float(np.clip(lam_c, 0.05, 6.0)), float(np.clip(mu_c, 0.05, 6.0))

    def apply_vec(self, lam: np.ndarray, mu: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        p = self.params
        if p.is_identity:
            return np.asarray(lam, dtype=float), np.asarray(mu, dtype=float)
        lam_c = np.exp(p.a0 + p.a1 * np.log(np.clip(lam, EPS, None)))
        mu_c = np.exp(p.b0 + p.b1 * np.log(np.clip(mu, EPS, None)))
        return np.clip(lam_c, 0.05, 6.0), np.clip(mu_c, 0.05, 6.0)

    # ---------------- ajuste ----------------

    def fit(self, lam: np.ndarray, mu: np.ndarray, home_goals: np.ndarray,
            away_goals: np.ndarray, rho: float = 0.0,
            weights: np.ndarray | None = None) -> "LambdaCalibrator":
        """
        lam, mu: intensidades del modelo SIN calibrar, fuera de muestra.
        home_goals, away_goals: marcador real de cada partido.
        """
        lam = np.asarray(lam, dtype=float)
        mu = np.asarray(mu, dtype=float)
        hg = np.clip(np.asarray(home_goals, dtype=int), 0, 10)
        ag = np.clip(np.asarray(away_goals, dtype=int), 0, 10)
        if len(lam) < 200:
            raise ValueError(
                f"Muestra insuficiente para calibrar: {len(lam)} partidos. "
                "Con menos de ~200 la calibración ajusta ruido."
            )
        w = np.ones(len(lam)) if weights is None else np.asarray(weights, dtype=float)
        w = w / w.mean()
        log_lam, log_mu = np.log(np.clip(lam, EPS, None)), np.log(np.clip(mu, EPS, None))

        def objective(x: np.ndarray) -> float:
            a0, a1, b0, b1 = x
            l2 = np.exp(a0 + a1 * log_lam)
            m2 = np.exp(b0 + b1 * log_mu)
            m = score_matrices(l2, m2, rho)
            picked = np.clip(m[np.arange(len(hg)), hg, ag], EPS, 1.0)
            return float(-np.sum(w * np.log(picked)) / np.sum(w))

        res = minimize(objective, np.array([0.0, 1.0, 0.0, 1.0]),
                       method="L-BFGS-B",
                       bounds=[(-1.5, 1.5), (0.2, 2.0), (-1.5, 1.5), (0.2, 2.0)],
                       options={"maxiter": 500})
        a0, a1, b0, b1 = res.x
        from datetime import datetime, timezone
        self.params = CalParams(
            a0=float(a0), a1=float(a1), b0=float(b0), b1=float(b1),
            rho=float(rho), n_train=int(len(lam)),
            fitted_at=datetime.now(timezone.utc).isoformat(),
        )
        return self

    # ---------------- persistencia ----------------

    def save(self, path: str) -> None:
        with open(path, "wb") as f:
            pickle.dump(asdict(self.params), f)

    @classmethod
    def load(cls, path: str) -> "LambdaCalibrator":
        with open(path, "rb") as f:
            return cls(CalParams(**pickle.load(f)))

    @classmethod
    def identity(cls) -> "LambdaCalibrator":
        return cls(CalParams())


# ---------------------------------------------------------------------------
# Ajuste con puerta de validación
# ---------------------------------------------------------------------------

def fit_and_validate(lam: np.ndarray, mu: np.ndarray, home_goals: np.ndarray,
                     away_goals: np.ndarray, rho: float = 0.0,
                     holdout_frac: float = 0.3) -> tuple[LambdaCalibrator, dict]:
    """
    Ajusta en la parte antigua y valida en la reciente. SOLO marca el
    calibrador como utilizable si mejora el log-loss del MARCADOR y no empeora
    ni el RPS ni el log-loss del 1X2 en la parte de validación, que el ajuste
    nunca vio.

    Las entradas deben venir ORDENADAS POR FECHA: el corte es temporal, no
    aleatorio. Un corte aleatorio aquí mezcla futuro y pasado y te dice que
    todo mejora.

    Devuelve (calibrador, informe). Si no pasa la puerta, el calibrador
    devuelto es la identidad: preferimos no calibrar a calibrar mal.
    """
    lam = np.asarray(lam, dtype=float)
    mu = np.asarray(mu, dtype=float)
    home_goals = np.asarray(home_goals, dtype=int)
    away_goals = np.asarray(away_goals, dtype=int)
    outcomes = np.where(home_goals > away_goals, 0, np.where(home_goals == away_goals, 1, 2))

    n = len(lam)
    cut = int(n * (1.0 - holdout_frac))
    if cut < 200 or n - cut < 100:
        return LambdaCalibrator.identity(), {
            "ok": False,
            "reason": (f"Datos insuficientes para validar: {cut} de ajuste y "
                       f"{n - cut} de validación. Hacen falta >=200 y >=100."),
        }

    cal = LambdaCalibrator().fit(lam[:cut], mu[:cut], home_goals[:cut],
                                 away_goals[:cut], rho=rho)

    p_before = probs_1x2(lam[cut:], mu[cut:], rho)
    l2, m2 = cal.apply_vec(lam[cut:], mu[cut:])
    p_after = probs_1x2(l2, m2, rho)
    oc = outcomes[cut:]

    report = {
        "n_fit": int(cut),
        "n_val": int(n - cut),
        "params": asdict(cal.params),
        "log_loss_before": round(log_loss(p_before, oc), 5),
        "log_loss_after": round(log_loss(p_after, oc), 5),
        "rps_before": round(rps(p_before, oc), 5),
        "rps_after": round(rps(p_after, oc), 5),
        "score_log_loss_before": round(score_log_loss(lam[cut:], mu[cut:], rho,
                                                      home_goals[cut:], away_goals[cut:]), 5),
        "score_log_loss_after": round(score_log_loss(l2, m2, rho,
                                                     home_goals[cut:], away_goals[cut:]), 5),
    }
    improves_score = report["score_log_loss_after"] < report["score_log_loss_before"]
    # Margen de tolerancia en el 1X2: un empeoramiento de 1e-4 es ruido, pero no
    # aceptamos mejorar el marcador a costa del 1X2 que ve la app.
    keeps_rps = report["rps_after"] <= report["rps_before"] + 1e-4
    keeps_ll = report["log_loss_after"] <= report["log_loss_before"] + 1e-4
    report["ok"] = bool(improves_score and keeps_rps and keeps_ll)

    if not report["ok"]:
        report["reason"] = (
            "La calibración no mejora fuera de muestra "
            f"(marcador {report['score_log_loss_before']} -> {report['score_log_loss_after']}, "
            f"log-loss 1X2 {report['log_loss_before']} -> {report['log_loss_after']}, "
            f"RPS {report['rps_before']} -> {report['rps_after']}). "
            "Se deja el modelo SIN calibrar, que es el resultado correcto: "
            "significa que el modelo ya estaba razonablemente calibrado."
        )
        log.warning(report["reason"])
        return LambdaCalibrator.identity(), report

    cal.params.validated = True
    cal.params.val_metrics = {k: report[k] for k in
                              ("log_loss_before", "log_loss_after",
                               "rps_before", "rps_after", "score_log_loss_before",
                               "score_log_loss_after", "n_val")}
    log.info("Calibración validada: log-loss %.5f -> %.5f",
             report["log_loss_before"], report["log_loss_after"])
    return cal, report


def fit_from_oos(oos, rho: float = 0.0, holdout_frac: float = 0.3):
    """
    Atajo desde el DataFrame de `eval.backtest.walk_forward_oos`.

    Reconstruye las intensidades implícitas a partir de las probabilidades
    guardadas no: usa directamente las columnas de lambda si están, y si no,
    trabaja sobre el 1X2. Se espera que `oos` traiga `lam` y `mu`.
    """
    oos = oos.sort_values("kickoff_utc")
    if "lam" not in oos.columns or "mu" not in oos.columns:
        raise ValueError(
            "El DataFrame fuera de muestra no trae columnas lam/mu. "
            "Usa walk_forward_oos(), que las incluye."
        )
    return fit_and_validate(oos["lam"].to_numpy(), oos["mu"].to_numpy(),
                            oos["home_goals"].to_numpy(), oos["away_goals"].to_numpy(),
                            rho=rho,
                            holdout_frac=holdout_frac)
