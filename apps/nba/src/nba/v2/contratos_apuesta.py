"""Probabilidades de un contrato con devolución: victoria, push y derrota se conservan por separado."""
from dataclasses import dataclass
import math

import numpy as np


@dataclass(frozen=True)
class ProbabilidadesContrato:
    gana: float
    push: float
    pierde: float

    def __post_init__(self):
        if not all(math.isfinite(p) and 0 <= p <= 1 + 1e-12 for p in (self.gana, self.push, self.pierde)):
            raise ValueError("probabilidades de contrato inválidas")
        if abs(self.gana + self.push + self.pierde - 1) > 1e-9:
            raise ValueError("las probabilidades del contrato no suman uno")

    @property
    def condicionada(self) -> float | None:
        accion = self.gana + self.pierde
        return self.gana / accion if accion > 1e-15 else None

    def salida(self, p_juega: float = 1.0) -> dict:
        if not math.isfinite(p_juega) or not 0 <= p_juega <= 1:
            raise ValueError("probabilidad de participación inválida")
        p = self.condicionada
        return {"p_mas": p, "p_menos": None if p is None else 1 - p,
                "p_gana": p_juega * self.gana, "p_push": p_juega * self.push, "p_pierde": p_juega * self.pierde,
                "p_void": 1 - p_juega, "probabilidad_condicionada_sin_push": True,
                "probabilidad_condicionada_participacion": p_juega != 1.0}

    def ev(self, decimal: float, p_juega: float = 1.0) -> float:
        if not math.isfinite(decimal) or decimal <= 1 or not 0 <= p_juega <= 1:
            raise ValueError("precio o participación inválidos")
        return p_juega * (self.gana * (decimal - 1) - self.pierde)


def desde_masas(valores, pesos, linea: float) -> ProbabilidadesContrato:
    v, w = np.asarray(valores, float), np.asarray(pesos, float)
    if not math.isfinite(linea) or v.ndim != 1 or v.shape != w.shape or not v.size:
        raise ValueError("soporte o línea inválidos")
    if not np.isfinite(v).all() or not np.isfinite(w).all() or (w < 0).any() or abs(w.sum() - 1) > 1e-4:
        raise ValueError("masa probabilística inválida")
    w = w / w.sum()
    return ProbabilidadesContrato(float(w[v > linea].sum()), float(w[v == linea].sum()), float(w[v < linea].sum()))


def liquidar(observado: float | None, linea: float, lado: str, decimal: float, *, jugo: bool | None = True) -> dict:
    """Una unidad: DNP explícito se devuelve; un resultado desconocido queda pendiente, nunca se inventa un cero."""
    if lado not in ("over", "under") or not math.isfinite(linea) or not math.isfinite(decimal) or decimal <= 1:
        raise ValueError("contrato inválido")
    if jugo is False:
        return {"estado": "void", "beneficio": 0.0}
    if jugo is None or observado is None:
        return {"estado": "pendiente", "beneficio": None}
    if not math.isfinite(observado):
        raise ValueError("resultado inválido")
    if observado == linea:
        return {"estado": "push", "beneficio": 0.0}
    gana = observado > linea if lado == "over" else observado < linea
    return {"estado": "ganada" if gana else "perdida", "beneficio": decimal - 1 if gana else -1.0}
