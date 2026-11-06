"""Pieza C (plan D.4): une la suma de P con el ganador de R por inversión exacta del simulador.

δ* resuelve M̄_f(Ŝ/2 + δ, Ŝ/2 − δ; Σ_m) = π con la MISMA Σ_m que usó R (forma del día + v·[[1,−1],[−1,1]]), así el
ganador de la conjunta coincide con π por construcción. π fuera del rango alcanzable con p ∈ [0,02; 0,98] ⇒ rechazo
(`ValueError` del simulador; el partido no se sella).
"""
from dataclasses import dataclass

from tenis.simulador.formato import Formato
from tenis.simulador.inversion import invertir
from tenis.simulador.mezcla import Incertidumbre

from .datos import FORMATOS


@dataclass(frozen=True)
class Union:
    p_a: float
    p_b: float
    delta: float
    pi_logrado: float


def sigma_m(sigma_eps: float, rho_eps: float, var_rho: float) -> Incertidumbre:
    v = float(var_rho)
    return Incertidumbre(sigma_eps, rho_eps, ((v, -v), (-v, v)))


def unir(s_hat: float, pi: float, fmt: int, sigma_eps: float, rho_eps: float, var_rho: float) -> Union:
    if fmt < 0:
        raise ValueError("formato desconocido: no se une ni se sella")
    mejor_de, decisivo = FORMATOS[fmt]
    inv = invertir(s_hat, pi, Formato(mejor_de, decisivo), sigma_m(sigma_eps, rho_eps, var_rho))
    return Union(inv.p_a, inv.p_b, inv.delta, inv.pi_logrado)
