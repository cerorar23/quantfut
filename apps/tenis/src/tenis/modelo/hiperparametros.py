"""Selección de hiperparámetros por máxima verosimilitud predictiva UN PASO ADELANTE (plan D.5, D.8).

Solo con temporadas ≤ 2018 (el filtro arranca en 2005; la verosimilitud cuenta desde 2007, dos años de calentamiento).
Después se CONGELAN para 2019–2024. L-BFGS-B con gradiente por diferencias hacia delante evaluadas en paralelo (cada
evaluación es una pasada completa del filtro). Priors débiles declarados: ln κ ~ N(0, 0,5²), γ ~ N(0, 0,1²).
La fatiga entra como φ = softplus(u) ≥ 0; si los datos no tienen señal, el óptimo lleva φ → 0 (no se fuerza nada).
"""
import hashlib
import json
import math
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from scipy.optimize import minimize

from .parametros import Psi, softplus
from .puntos import PsiP, filtrar_p
from .rating import filtrar

VENTANA = (2007, 2018)
S_LOG_KAPPA, S_GAMMA = 0.5, 0.1
NOMBRES_R = ("ln_tau_theta", "ln_tau_inact", "ln_sigma_theta0", "b_rank", "ln_kappa_clay", "ln_kappa_grass",
             "ln_kappa_indoor", "ln_sigma_d", "ln_tau_d", "x_r_omega", "u_phi1", "u_phi2", "gamma_pregs",
             "ln_sigma_r", "ln_sigma_r_challenger")
NOMBRES_P = ("ln_sigma_alpha0", "ln_sigma_beta0", "ln_tau_alpha", "ln_tau_beta", "ln_sigma_ab", "ln_kappa_clay",
             "ln_kappa_grass", "ln_kappa_indoor", "ln_sigma_eps", "x_rho_eps", "ln_tau_mu")


def _expit(x):
    return 1 / (1 + math.exp(-x))


def psi_desde_vector(x, fijo: dict, ablacion: str = "") -> Psi:
    """`fijo`: sigma_eps, rho_eps, lbar, lam, f90. ablación: '' | 'sin_superficie' | 'sin_fatiga'."""
    sin_sup, sin_fat = ablacion == "sin_superficie", ablacion == "sin_fatiga"
    kap = (1.0, 1.0, 1.0, 1.0) if sin_sup else (math.exp(x[4]), math.exp(x[5]), 1.0, math.exp(x[6]))
    return Psi(tau_theta=math.exp(x[0]), tau_inact=math.exp(x[1]), sigma_theta0=math.exp(x[2]), b_rank=x[3],
               kappa=kap, sigma_d=0.0 if sin_sup else math.exp(x[7]), tau_d=0.0 if sin_sup else math.exp(x[8]),
               r_omega=-0.2 + 1.19 * _expit(x[9]),
               phi=(0.0, 0.0) if sin_fat else (softplus(x[10]), softplus(x[11])),
               gamma=(x[12], 0.0, 0.0), lam=fijo["lam"], f90=fijo["f90"], sigma_eps=fijo["sigma_eps"],
               rho_eps=fijo["rho_eps"], lbar=tuple(fijo["lbar"]),
               sigma_r=math.exp(x[13]) if len(x) > 13 else 0.0,           # parche G-calibración
               sigma_r_challenger=math.exp(x[14]) if len(x) > 14 else None)


def psip_desde_vector(x) -> PsiP:
    e = [math.exp(v) for v in x]
    return PsiP(e[0], e[1], e[2], e[3], e[4], (e[5], e[6], 1.0, e[7]), e[8], math.tanh(x[9]), e[10])


def loglik(d, pi, ventana=VENTANA) -> float:
    temp = d.p.temporada.to_numpy()
    sel = np.isfinite(pi) & d.liquida & (temp >= ventana[0]) & (temp <= ventana[1])
    y, q = d.y1[sel], pi[sel]
    return float(np.sum(np.where(y == 1, np.log(q), np.log1p(-q))))


def penalizacion(x, ablacion: str = "") -> float:
    pen = 0.5 * (x[12] / S_GAMMA) ** 2
    if ablacion != "sin_superficie":
        pen += 0.5 * sum((x[i] / S_LOG_KAPPA) ** 2 for i in (4, 5, 6))
    return pen


# ---- evaluación en procesos (cada trabajador guarda sus datos una vez) ----
_G = {}


def _iniciar(datos: dict):
    _G.update(datos)


def _obj_r(x) -> float:
    psi = psi_desde_vector(x, _G["fijo"], _G["ablacion"])
    sal = filtrar(_G["d"], psi, _G["tablas"])
    return -loglik(_G["d"], sal.pi) + penalizacion(x, _G["ablacion"])


def pendiente_platt(d, pi, ventana=(2012, 2018)) -> float:
    """Pendiente de Platt de π en las temporadas de la ventana (diagnóstico del parche; dentro del ajuste)."""
    from .recalibracion import ajustar_pendiente
    t = d.p.temporada.to_numpy()
    sel = np.isfinite(pi) & d.liquida & (t >= ventana[0]) & (t <= ventana[1])
    return ajustar_pendiente(pi[sel], d.y1[sel])


def _obj_p(x) -> float:
    ll, _, _ = filtrar_p(_G["d"], _G["obs"], psip_desde_vector(x), VENTANA, predecir=False)
    return -ll


def ajustar(objetivo, x0, datos: dict, libres=None, maxiter: int = 30, trabajadores: int = 6, h: float = 1e-3,
            registro=print):
    """L-BFGS-B sobre las coordenadas `libres` (el resto queda en x0). Devuelve (x, f, historial)."""
    x0 = np.asarray(x0, dtype=float)
    libres = list(range(len(x0))) if libres is None else list(libres)
    hist = []
    with ProcessPoolExecutor(trabajadores, initializer=_iniciar, initargs=(datos,)) as ex:
        def fg(z):
            x = x0.copy(); x[libres] = z
            puntos = [x] + [x + h * np.eye(len(x))[i] for i in libres]
            vals = list(ex.map(objetivo, puntos))
            g = np.array([(v - vals[0]) / h for v in vals[1:]])
            hist.append((vals[0], z.tolist()))
            registro(f"  f = {vals[0]:.3f}  |g| = {np.linalg.norm(g):.3f}")
            return vals[0], g
        res = minimize(fg, x0[libres], jac=True, method="L-BFGS-B", options={"maxiter": maxiter, "ftol": 1e-9})
    x = x0.copy(); x[libres] = res.x
    return x, float(res.fun), hist


def huella(contenido: dict) -> str:
    return hashlib.sha256(json.dumps(contenido, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def escribir(ruta, contenido: dict) -> str:
    """Escribe el JSON con `sha256_contenido` = sha256 del JSON canónico de todo lo demás."""
    sha = huella(contenido)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(contenido | {"sha256_contenido": sha}, indent=1, ensure_ascii=False), encoding="utf-8")
    return sha


def leer(ruta) -> dict:
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    sha = datos.pop("sha256_contenido")
    if huella(datos) != sha:
        raise ValueError("hiperparametros.json alterado: la huella sha256 no coincide")
    return datos
