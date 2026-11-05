"""Núcleo del marcador (D3, v2.0 paramétrico): ratings ofensivo/defensivo por equipo + una distribución conjunta
(margen, total) de la que salen ganador, hándicap, totales y total de equipo (fichas 1, 4, 7, 35, 44).

Cada equipo tiene un ataque y una defensa que se actualizan partido a partido con el error de puntos (online, sin mirar
nada del futuro); al empezar una temporada se encogen hacia la media. Los puntos esperados son
    local = liga/2 + localía/2 + ataque_local + defensa_visitante      visitante = liga/2 - localía/2 + ataque_visitante + defensa_local
con «defensa» = puntos concedidos por encima/debajo de la media (positivo = defiende peor).
El margen y el total se simulan como normales independientes (la correlación entre ambos es casi nula).
"""
from dataclasses import dataclass, field

import numpy as np

from .distribucion import Distribucion


@dataclass(frozen=True)
class Parametros:
    eta: float = 0.045            # tasa de aprendizaje de los ratings
    arrastre: float = 0.65        # fracción del rating que se conserva al cambiar de temporada
    eta_localia: float = 0.002    # tasa de la localía (muy lenta)
    eta_liga: float = 0.002       # tasa del nivel medio de puntos de la liga (sigue la deriva de anotación)
    efecto_b2b: float = 0.0       # puntos de margen que cuesta jugar en la noche siguiente a otro partido
    sigma_margen: float = 13.2    # se reemplaza por lo medido en las temporadas de ajuste
    sigma_total: float = 18.5


@dataclass
class Ratings:
    ataque: dict[str, float] = field(default_factory=dict)
    defensa: dict[str, float] = field(default_factory=dict)
    liga: float = 224.0            # total medio de la liga
    localia: float = 2.6           # puntos de ventaja del local (margen)
    partidos: int = 0

    def esperado(self, local: str, visitante: str, ajuste_margen: float = 0.0) -> tuple[float, float]:
        """Puntos esperados; `ajuste_margen` (cansancio, etc.) se reparte mitad y mitad sin tocar el total."""
        a = self.ataque
        d = self.defensa
        pl = self.liga / 2 + (self.localia + ajuste_margen) / 2 + a.get(local, 0.0) + d.get(visitante, 0.0)
        pv = self.liga / 2 - (self.localia + ajuste_margen) / 2 + a.get(visitante, 0.0) + d.get(local, 0.0)
        return pl, pv


def ajuste_descanso(dias_local: int, dias_visitante: int, p: Parametros) -> float:
    """Margen (a favor del local) por jugar en la noche siguiente: el local pierde `efecto_b2b`, el visitante lo gana."""
    return p.efecto_b2b * ((1 if dias_visitante == 1 else 0) - (1 if dias_local == 1 else 0))


def actualizar(r: Ratings, local: str, visitante: str, pts_local: float, pts_visitante: float, p: Parametros,
               ajuste_margen: float = 0.0) -> None:
    """Un partido ya jugado: mueve ataque y defensa de ambos, la media de la liga y la localía."""
    pl, pv = r.esperado(local, visitante, ajuste_margen)
    el, ev = pts_local - pl, pts_visitante - pv
    r.ataque[local] = r.ataque.get(local, 0.0) + p.eta * el
    r.defensa[visitante] = r.defensa.get(visitante, 0.0) + p.eta * el
    r.ataque[visitante] = r.ataque.get(visitante, 0.0) + p.eta * ev
    r.defensa[local] = r.defensa.get(local, 0.0) + p.eta * ev
    r.liga += p.eta_liga * ((pts_local + pts_visitante) - (pl + pv))
    r.localia += p.eta_localia * ((pts_local - pts_visitante) - (pl - pv))   # pl − pv ya incluye el ajuste
    r.partidos += 1


def nueva_temporada(r: Ratings, p: Parametros) -> None:
    for equipo in list(r.ataque):
        r.ataque[equipo] *= p.arrastre
        r.defensa[equipo] *= p.arrastre


@dataclass(frozen=True)
class Marcador:
    """Muestras conjuntas (puntos local, puntos visitante) de un partido completo."""
    muestras: np.ndarray        # (n, 2)
    regulacion: np.ndarray | None = None
    prorrogas: np.ndarray | None = None

    def margen(self) -> Distribucion:
        return Distribucion.de_muestras(self.muestras[:, 0] - self.muestras[:, 1])

    def total(self) -> Distribucion:
        return Distribucion.de_muestras(self.muestras.sum(axis=1))

    def puntos(self, lado: str) -> Distribucion:
        return Distribucion.de_muestras(self.muestras[:, 0 if lado == "local" else 1])


def simular(mu_local: float, mu_visitante: float, sigma_margen: float, sigma_total: float, n: int = 20000,
            semilla: int = 0) -> Marcador:
    """Puntos enteros; si el margen simulado es 0 se decide con una moneda (la prórroga rompe el empate)."""
    rng = np.random.default_rng(semilla)
    margen = rng.normal(mu_local - mu_visitante, sigma_margen, n)
    total = rng.normal(mu_local + mu_visitante, sigma_total, n)
    local = np.round((total + margen) / 2)
    visitante = np.round((total - margen) / 2)
    empate = local == visitante
    if empate.any():
        gana_local = rng.random(empate.sum()) < 0.5
        local[empate] += np.where(gana_local, 1, 0)
        visitante[empate] += np.where(gana_local, 0, 1)
    return Marcador(np.clip(np.stack([local, visitante], axis=1), 0, None))


def simular_con_ot(mu_local: float, mu_visitante: float, sigma_margen: float, sigma_total: float,
                   posesiones: float, p_ot: float, n: int = 100000, semilla: int = 0) -> Marcador:
    """Ley de REGULACIÓN + OT explícita. Las desviaciones deben ajustarse a finales sin OT.

    Rama OT: regulación empatada y periodos de cinco minutos con posesiones compartidas.
    Rama sin OT: marcador de regulación condicionado a no empate. Ningún bucle recorre simulaciones.
    """
    valores = [mu_local, mu_visitante, sigma_margen, sigma_total, posesiones, p_ot]
    if not np.isfinite(valores).all() or min(valores[:5]) <= 0 or not 0 <= p_ot <= 1 or not isinstance(n, int) or n < 1:
        raise ValueError('parámetros de regulación/OT inválidos')
    rng = np.random.default_rng(semilla)
    total = rng.normal(mu_local + mu_visitante, sigma_total, n)
    margen = rng.normal(mu_local - mu_visitante, sigma_margen, n)
    ot = rng.random(n) < p_ot
    local, visitante = np.round((total + margen) / 2), np.round((total - margen) / 2)
    local[ot] = visitante[ot] = np.maximum(0, np.round(total[ot] / 2))
    for _ in range(32):
        malos = ~ot & ((local == visitante) | (local < 0) | (visitante < 0))
        if not malos.any():
            break
        tm = rng.normal(mu_local + mu_visitante, sigma_total, int(malos.sum()))
        mg = rng.normal(mu_local - mu_visitante, sigma_margen, int(malos.sum()))
        local[malos], visitante[malos] = np.round((tm + mg) / 2), np.round((tm - mg) / 2)
    else:
        raise ValueError('no se pudo obtener regulación válida sin empate')
    regulacion = np.stack([local, visitante], axis=1).copy()
    periodos = np.zeros(n, dtype=int)
    pendientes = ot.copy()
    for _ in range(32):
        if not pendientes.any():
            break
        expo = rng.poisson(posesiones * 5 / 48, int(pendientes.sum()))
        local[pendientes] += rng.poisson(mu_local / posesiones * expo)
        visitante[pendientes] += rng.poisson(mu_visitante / posesiones * expo)
        periodos[pendientes] += 1
        pendientes &= local == visitante
    else:
        raise ValueError('presupuesto de periodos OT agotado')
    return Marcador(np.stack([local, visitante], axis=1), regulacion, periodos)
