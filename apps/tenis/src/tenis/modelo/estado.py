"""Estado de un jugador en la pieza R: x = (θ, d_Clay, d_Grass, d_Hard, d_Indoor) ~ N(m, V) (plan D.3).

Propagación: θ recibe τ_θ²·Δt (años) + τ_I²·max(0, días − 60)/365,25 (inactividad); d recibe τ_d²·Δt·Ω.
Actualización Newton/Laplace (Glicko es un paso de Newton desde el prior, B03): con ρ = aᵀx + c lineal en el estado,
la verosimilitud ℓ(ρ) aporta gradiente g·a y hessiano h·a·aᵀ (h = −ℓ'' ≥ 0) ⇒ V⁺ = (V⁻¹ + Σ h a aᵀ)⁻¹, m⁺ = m + V⁺ Σ g a.
La incertidumbre del rival entra como en Glicko: h_ef = h/(1 + h·q_rival), g_ef = g/(1 + h·q_rival) (es la
actualización conjunta exacta de Sherman–Morrison proyectada en cada jugador; se descarta la covarianza cruzada).
"""
import numpy as np

from .fatiga import DIA_NS
from .superficie import omega

ANIO_NS = 365.25 * DIA_NS
INACTIVIDAD_DIAS = 60.0


def ruido(dt_ns: int, psi) -> tuple[float, float]:
    """(varianza añadida a θ, varianza añadida a d por unidad de Ω) en un intervalo dt."""
    dt_a, dias = dt_ns / ANIO_NS, dt_ns / DIA_NS
    q_th = psi.tau_theta ** 2 * dt_a + psi.tau_inact ** 2 * max(0.0, dias - INACTIVIDAD_DIAS) / 365.25
    return q_th, psi.tau_d ** 2 * dt_a


def var_dir(v: list, dt_ns: int, psi, k: float, s: int) -> float:
    """aᵀ V(t) a con a = k·e_θ + e_{d_s}, propagando sin modificar el estado (para predecir)."""
    q_th, q_d = ruido(dt_ns, psi)
    i = s + 1
    return k * k * (v[0][0] + q_th) + 2.0 * k * v[0][i] + v[i][i] + q_d


def propagar(v: list, dt_ns: int, psi) -> None:
    if dt_ns <= 0:
        return
    q_th, q_d = ruido(dt_ns, psi)
    v[0][0] += q_th
    if q_d > 0.0:
        om = omega(psi.r_omega)
        for i in range(4):
            for j in range(4):
                v[i + 1][j + 1] += q_d * om[i][j]


def actualizar_uno(m: list, v: list, signo: int, k: float, s: int, g: float, h: float) -> None:
    """Un solo término (Sherman–Morrison): m⁺ = m + V a g/(1 + h q), V⁺ = V − h/(1 + h q)·(Va)(Va)ᵀ."""
    i = s + 1
    w = [k * v[r][0] + v[r][i] for r in range(5)]
    den = 1.0 + h * (k * w[0] + w[i])
    a, c = signo * g / den, h / den
    for r in range(5):
        m[r] += w[r] * a
        fila, wr = v[r], c * w[r]
        for col in range(5):
            fila[col] -= wr * w[col]


def actualizar_varios(m: list, v: list, terminos: list) -> None:
    """Varios resultados del mismo instante de visibilidad (simultáneos): todos desde el estado previo al bloque.
    terminos: [(signo, k, s, g, h)] en orden canónico. Woodbury: V⁺ = V − V A_h (D⁻¹ + A_hᵀ V A_h)⁻¹ A_hᵀ V."""
    vm = np.array(v)
    a = np.zeros((5, len(terminos)))
    for j, (signo, k, s, _, _) in enumerate(terminos):
        a[0, j], a[s + 1, j] = signo * k, signo
    g = np.array([t[3] for t in terminos])
    h = np.array([t[4] for t in terminos])
    pos = h > 0
    if pos.any():
        ah = a[:, pos]
        va = vm @ ah
        nueva = vm - va @ np.linalg.solve(np.diag(1.0 / h[pos]) + ah.T @ va, va.T)
    else:
        nueva = vm.copy()
    nueva = 0.5 * (nueva + nueva.T)
    mm = np.array(m) + nueva @ (a @ g)
    m[:] = mm.tolist()
    for r in range(5):
        v[r][:] = nueva[r].tolist()
