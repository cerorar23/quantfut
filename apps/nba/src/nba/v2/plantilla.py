"""Jugadores dentro del rating de equipo (fichas 1, 9, 18): impacto por jugador estimado con una regresión ridge sobre minutos
y minutos esperados de la plantilla de un partido, que combinan las capas de disponibilidad y minutos del Sprint 2.

* Impacto: cada jugador aporta `beta · minutos / 48` al margen de su equipo (positivo en casa, negativo fuera) y `tau · minutos / 48`
  al total. Se estima por mínimos cuadrados ponderados con ridge hacia 0 (= nivel de reemplazo) y peso que decae con la antigüedad
  del partido. Intercepto (localía / nivel de la liga) y covariable de descanso sin penalizar.
* Minutos esperados: `p(juega) × minutos si juega` por candidato, reescalados a los 240 minutos del equipo (lo que no juega un
  ausente se reparte en proporción entre quienes sí juegan).
"""
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np

MINUTOS_EQUIPO = 240.0
MINUTOS_COMPLETOS = 48.0


@dataclass(frozen=True)
class PartidoFila:
    dia: int                              # día ordinal (para el decaimiento)
    margen: float                         # puntos local - visitante
    total: float
    local: Mapping[int, float]            # jugador -> minutos jugados
    visit: Mapping[int, float]
    descanso: float = 0.0                 # +1 si el visitante juega en la noche siguiente, -1 si es el local, 0 si ninguno/ambos


@dataclass
class Impacto:
    beta: dict[int, float] = field(default_factory=dict)       # margen por 48 minutos del jugador
    tau: dict[int, float] = field(default_factory=dict)        # total por 48 minutos del jugador
    c_margen: float = 0.0
    d_margen: float = 0.0                                      # efecto de la covariable de descanso en el margen
    c_total: float = 0.0
    d_total: float = 0.0

    def margen(self, local: Mapping[int, float], visit: Mapping[int, float], descanso: float = 0.0) -> float:
        s = sum(self.beta.get(j, 0.0) * m for j, m in local.items()) - sum(self.beta.get(j, 0.0) * m for j, m in visit.items())
        return self.c_margen + self.d_margen * descanso + s / MINUTOS_COMPLETOS

    def total(self, local: Mapping[int, float], visit: Mapping[int, float], descanso: float = 0.0) -> float:
        s = sum(self.tau.get(j, 0.0) * m for j, m in local.items()) + sum(self.tau.get(j, 0.0) * m for j, m in visit.items())
        return self.c_total + self.d_total * descanso + s / MINUTOS_COMPLETOS


def ajustar(partidos: Sequence[PartidoFila], lam_margen: float, lam_total: float, vida_media_dias: float,
            dia_corte: int | None = None, prior_beta: Mapping[int, float] | None = None) -> Impacto:
    """Ridge ponderado. Solo usa partidos con `dia < dia_corte` (o todos si es None). `prior_beta` centra el ridge del margen
    en un impacto previo por jugador (en vez de 0)."""
    filas = [p for p in partidos if dia_corte is None or p.dia < dia_corte]
    if not filas:
        return Impacto()
    jugadores = sorted({j for p in filas for j in (*p.local, *p.visit)})
    idx = {j: i for i, j in enumerate(jugadores)}
    n, k = len(filas), len(jugadores)
    X_m = np.zeros((n, k + 2))
    X_t = np.zeros((n, k + 2))
    for r, p in enumerate(filas):
        for j, m in p.local.items():
            X_m[r, idx[j]] += m / MINUTOS_COMPLETOS
            X_t[r, idx[j]] += m / MINUTOS_COMPLETOS
        for j, m in p.visit.items():
            X_m[r, idx[j]] -= m / MINUTOS_COMPLETOS
            X_t[r, idx[j]] += m / MINUTOS_COMPLETOS
        X_m[r, k], X_m[r, k + 1] = 1.0, p.descanso
        X_t[r, k], X_t[r, k + 1] = 1.0, p.descanso
    ultimo = max(p.dia for p in filas) if dia_corte is None else dia_corte
    w = 0.5 ** ((ultimo - np.array([p.dia for p in filas])) / vida_media_dias)
    resultado = []
    for X, y, lam in ((X_m, np.array([p.margen for p in filas]), lam_margen), (X_t, np.array([p.total for p in filas]), lam_total)):
        Xw = X * w[:, None]
        penal = np.full(k + 2, lam)
        penal[k:] = 1e-8
        # el total se centra en su media ponderada para que el ridge no tire del intercepto
        mu = np.zeros(k + 2)
        if prior_beta is not None and X is X_m:
            mu[:k] = [prior_beta.get(j, 0.0) for j in jugadores]
        theta = np.linalg.solve(Xw.T @ X + np.diag(penal), Xw.T @ (y - X @ mu) + 0.0) + mu
        resultado.append(theta)
    tm, tt = resultado
    return Impacto(beta=dict(zip(jugadores, tm[:k])), tau=dict(zip(jugadores, tt[:k])), c_margen=float(tm[k]),
                   d_margen=float(tm[k + 1]), c_total=float(tt[k]), d_total=float(tt[k + 1]))


def minutos_esperados(candidatos: Mapping[int, tuple[float, float]]) -> dict[int, float]:
    """{jugador: (minutos si juega, prob. de jugar)} → minutos esperados que suman 240 (vacío si nadie puede jugar)."""
    crudos = {j: m * p for j, (m, p) in candidatos.items() if m > 0 and p > 0}
    suma = sum(crudos.values())
    if suma <= 0:
        return {}
    k = MINUTOS_EQUIPO / suma
    return {j: v * k for j, v in crudos.items()}
