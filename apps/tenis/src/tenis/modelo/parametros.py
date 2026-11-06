"""Ψ de la pieza R por circuito (plan D.3, D.8). Validación estricta: φ < 0, κ_Hard ≠ 1 o escalas negativas = error."""
import math
from dataclasses import asdict, dataclass

from .datos import HARD, SUPERFICIES


@dataclass(frozen=True)
class Psi:
    tau_theta: float      # DE del paseo aleatorio de θ por √año
    tau_inact: float      # DE extra por √año de inactividad por encima de 60 días (Glicko)
    sigma_theta0: float   # DE del prior de θ de un jugador nuevo (prior=ranking)
    b_rank: float         # θ₀ = b_rank · (ln rank − ln 100)
    kappa: tuple          # κ^R por superficie (Clay, Grass, Hard ≡ 1, Indoor): multiplicador de θ_A − θ_B
    sigma_d: float        # DE a priori de la desviación de superficie d_{i,s}
    tau_d: float          # DE del paseo de d por √año
    r_omega: float        # correlación común de d entre superficies (Ω equicorrelada)
    phi: tuple            # (φ1, φ2) ≥ 0: horas ponderadas y bisagra sobre F90
    gamma: tuple          # (semana previa GS, equipos, JJOO): modifican el multiplicador
    lam: float            # descuento diario de la fatiga
    f90: float            # bisagra de g2 en minutos ponderados (percentil 90 del entrenamiento)
    sigma_eps: float      # forma del día (logit), de la pieza P
    rho_eps: float
    lbar: tuple           # ℓ̄_{c,s} por superficie, de la pieza P
    # Parche G-calibración (6-nov): varianza extra del partido en el enlace, Σ_m += σ_R²·[[1,−1],[−1,1]] (entra en la
    # verosimilitud y en la predicción). 0 = modelo anterior exacto. Variante registrada: otra σ_R para Challenger.
    sigma_r: float = 0.0
    sigma_r_challenger: float | None = None

    def __post_init__(self):
        if not (math.isfinite(self.sigma_r) and self.sigma_r >= 0) or (
                self.sigma_r_challenger is not None and not (math.isfinite(self.sigma_r_challenger) and self.sigma_r_challenger >= 0)):
            raise ValueError("σ_R debe ser finita y ≥ 0")
        escalas = (self.tau_theta, self.tau_inact, self.sigma_theta0, self.sigma_d, self.tau_d, self.sigma_eps, self.f90)
        if not all(math.isfinite(x) and x >= 0 for x in escalas):
            raise ValueError("las escalas de Ψ deben ser finitas y ≥ 0")
        if len(self.phi) != 2 or not all(math.isfinite(f) and f >= 0 for f in self.phi):
            raise ValueError("φ debe ser ≥ 0 (la fatiga solo penaliza)")
        if len(self.kappa) != len(SUPERFICIES) or self.kappa[HARD] != 1.0 or min(self.kappa) <= 0:
            raise ValueError("κ: 4 valores > 0 con κ_Hard ≡ 1")
        if not (0.0 < self.lam <= 1.0) or not (-0.2 < self.r_omega < 1.0) or not (-1 < self.rho_eps < 1):
            raise ValueError("λ ∈ (0, 1], r_Ω ∈ (−0,2; 1), ρ_ε ∈ (−1, 1)")
        if len(self.gamma) != 3 or len(self.lbar) != len(SUPERFICIES):
            raise ValueError("γ: 3 contextos; ℓ̄: 4 superficies")

    def como_dict(self) -> dict:
        return {k: (list(v) if isinstance(v, tuple) else v) for k, v in asdict(self).items()}

    @classmethod
    def desde_dict(cls, d: dict) -> "Psi":
        return cls(**{k: (tuple(v) if isinstance(v, list) else v) for k, v in d.items()})


def softplus(u: float) -> float:
    """φ = softplus(u) ≥ 0 por construcción (plan D.3)."""
    return u + math.log1p(math.exp(-u)) if u > 0 else math.log1p(math.exp(u))
