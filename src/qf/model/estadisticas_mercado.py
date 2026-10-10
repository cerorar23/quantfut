"""
Córners y tarjetas por estadística, sin cuotas (decisión del usuario,
2026-10-08: "de acuerdo al histórico, no a las cuotas").

EL MODELO
---------
Para cada equipo, con pesos que se reducen a la mitad cada `MEDIA_VIDA_DIAS`:
  - ataque  = lo que produce (córners a favor / tarjetas que recibe) frente a
    la media de la liga en ese campo (local o visitante);
  - defensa = lo que concede o provoca en el rival, igual normalizado.
Cada factor se encoge hacia 1 con `PRIOR_PARTIDOS` partidos ficticios: un
equipo con 3 partidos no se aleja mucho de la media de la liga.

  λ_local     = media_local_liga     × ataque_local     × defensa_visitante
  λ_visitante = media_visitante_liga × ataque_visitante × defensa_local

En tarjetas se multiplica además por el factor del árbitro (sus tarjetas por
partido frente a la media de la liga, encogido con `PRIOR_ARBITRO`).

El total sigue una binomial negativa con media λ_local + λ_visitante y
varianza φ·media; φ sale de la prueba histórica (`eval/escalera_estadistica`).

PUNTO EN EL TIEMPO: `Acumulador.prob(...)` solo ve lo que se le añadió antes
con `agregar`; la prueba histórica pregunta SIEMPRE antes de añadir el partido.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from scipy.stats import nbinom, poisson

MEDIA_VIDA_DIAS = 180.0
PRIOR_PARTIDOS = 6.0
PRIOR_ARBITRO = 10.0
MIN_PARTIDOS = 5          # partidos con dato de cada equipo para dar probabilidad
MIN_LIGA = 20             # partidos de la liga antes de medir equipos contra su media
_K = math.log(2) / MEDIA_VIDA_DIAS
_T0 = datetime(2010, 1, 1)


def _dias(t: datetime) -> float:
    return (t.replace(tzinfo=None) - _T0).total_seconds() / 86400.0


@dataclass
class _Suma:
    """Media ponderada con decaimiento, guardada en escala de tiempo fija."""
    w: float = 0.0
    x: float = 0.0
    n: int = 0
    k: float = _K

    def add(self, valor: float, dias: float) -> None:
        peso = math.exp(self.k * dias)
        self.w += peso
        self.x += peso * valor
        self.n += 1

    def media(self, defecto: float) -> float:
        return self.x / self.w if self.w > 0 else defecto

    def encogida(self, prior: float, dias: float) -> float:
        """(Σw·x + prior·1) / (Σw + prior), con los pesos llevados a `dias`."""
        escala = math.exp(-self.k * dias)
        return (self.x * escala + prior) / (self.w * escala + prior)


@dataclass
class Acumulador:
    """
    Un acumulador por liga y por estadística ('corners' o 'cards'). `valor_*`
    son los conteos de cada equipo en el partido (córners a favor, o tarjetas
    que recibe).
    """
    usar_arbitro: bool = False
    prior: float = PRIOR_PARTIDOS
    media_vida: float = MEDIA_VIDA_DIAS

    def __post_init__(self) -> None:
        k = math.log(2) / self.media_vida
        nueva = lambda: _Suma(k=k)  # noqa: E731
        self.media_local, self.media_visit, self.total = nueva(), nueva(), nueva()
        self.ataque, self.defensa, self.arbitro = (defaultdict(nueva), defaultdict(nueva),
                                                   defaultdict(nueva))

    def agregar(self, fecha: datetime, local, visitante, valor_local: int,
                valor_visit: int, arbitro: str | None = None) -> None:
        d = _dias(fecha)
        # Hasta tener una media de liga estable solo se acumula esa media: con
        # pocos partidos puede valer 0 y los cocientes se dispararían.
        if self.media_local.n >= MIN_LIGA:
            ml = max(self.media_local.media(0), 0.1)
            mv = max(self.media_visit.media(0), 0.1)
            mt = max(self.total.media(0), 0.1)
            self._ratios(d, local, visitante, valor_local, valor_visit, ml, mv, mt, arbitro)
        self.media_local.add(valor_local, d)
        self.media_visit.add(valor_visit, d)
        self.total.add(valor_local + valor_visit, d)

    def _ratios(self, d, local, visitante, valor_local, valor_visit, ml, mv, mt, arbitro):
        # Ratios frente a la media ANTERIOR de la liga: el propio partido no se
        # mide contra sí mismo.
        self.ataque[local].add(valor_local / ml, d)
        self.defensa[visitante].add(valor_local / ml, d)
        self.ataque[visitante].add(valor_visit / mv, d)
        self.defensa[local].add(valor_visit / mv, d)
        if self.usar_arbitro and arbitro:
            self.arbitro[arbitro].add((valor_local + valor_visit) / mt, d)

    def lambdas(self, fecha: datetime, local, visitante,
                arbitro: str | None = None) -> tuple[float, float] | None:
        if (self.ataque[local].n < MIN_PARTIDOS or self.ataque[visitante].n < MIN_PARTIDOS
                or self.media_local.n < MIN_LIGA + 10):
            return None
        d = _dias(fecha)
        lam_l = (self.media_local.media(0) * self.ataque[local].encogida(self.prior, d)
                 * self.defensa[visitante].encogida(self.prior, d))
        lam_v = (self.media_visit.media(0) * self.ataque[visitante].encogida(self.prior, d)
                 * self.defensa[local].encogida(self.prior, d))
        if self.usar_arbitro and arbitro and arbitro in self.arbitro:
            f = self.arbitro[arbitro].encogida(PRIOR_ARBITRO, d)
            lam_l, lam_v = lam_l * f, lam_v * f
        return lam_l, lam_v


def prob_total(media: float, phi: float, linea: float) -> dict[str, float]:
    """P(total > línea) y P(total < línea) para líneas medias (sin devolución)."""
    if abs(linea * 2 - round(linea * 2)) > 1e-9 or linea == round(linea):
        raise ValueError(f"Solo líneas medias: {linea}")
    k = math.floor(linea)
    if phi <= 1.0 + 1e-9:
        p_under = float(poisson.cdf(k, media))
    else:
        r = media / (phi - 1.0)                    # varianza = media + media²/r = φ·media
        p_under = float(nbinom.cdf(k, r, r / (r + media)))
    return {"over": 1.0 - p_under, "under": p_under}


# Parámetros y líneas que pasaron la prueba histórica del 2026-10-08
# (eval/escalera_estadistica.py, football-data 7 ligas, firma d5cbc3151164):
# φ con 2019-2021, encogimiento y media vida elegidos por pérdida logarítmica
# en 2021/22, criterio de calibración solo en 2022-2025. Córners: pasan más de
# 7,5 (73,8→74,3), 8,5 (65,8→67,8), 9,5 (61,7→61,3) y menos de 9,5, 10,5
# (64,5→64,7) y 11,5 (70,8→70,6); menos de 12,5 no pasa (−0,76, tramo 70-80
# −1,9 puntos). Tarjetas (amarillas + rojas): prometen de 1 a 3 puntos de más
# en casi todas las líneas (sin árbitro fuera de la Premier); solo pasa menos
# de 6,5. Cambiar parámetros o líneas exige repetir la prueba.
#
# Ampliación 2026-10-09 (pedido del usuario; `--fijos`, mismos parámetros):
# más de 6,5 córners pasa (83,36→84,47). Córners de CADA equipo, del mismo
# acumulador y con su propio φ (1,5455, con 2019-21): calibración irregular,
# pasan local más de 1,5 (93,60→93,30), 4,5 (63,92→70,68), 5,5 (n=25) y menos
# de 5,5 (62,88→70,85); visitante más de 3,5 (63,72→69,88), 4,5 (n=7), menos de
# 4,5 (62,51→74,64) y 7,5 (87,43→88,07). No pasan (tramo 60-70 o 70-80 por
# debajo): local más de 2,5 y 3,5, menos de 6,5 y 7,5; visitante más de 1,5 y
# 2,5, menos de 5,5 y 6,5.
PARAMETROS = {"corners": {"prior": 120.0, "media_vida": 365.0, "phi": 1.175},
              "cards": {"prior": 50.0, "media_vida": 180.0, "phi": 1.0956},
              "corners_equipo": {"phi": 1.5455}}
LINEAS_HABILITADAS: dict[str, tuple[tuple[str, float], ...]] = {
    "corners": (("over", 6.5), ("over", 7.5), ("over", 8.5), ("over", 9.5),
                ("under", 9.5), ("under", 10.5), ("under", 11.5)),
    "cards": (("under", 6.5),),
    "corners_home": (("over", 1.5), ("over", 4.5), ("over", 5.5), ("under", 5.5)),
    "corners_away": (("over", 3.5), ("over", 4.5), ("under", 4.5), ("under", 7.5)),
}
# De qué acumulador sale cada mercado.
FUENTE = {"corners": "corners", "cards": "cards",
          "corners_home": "corners", "corners_away": "corners"}


def prob(mercado: str, lam: tuple[float, float], lado: str, linea: float) -> float:
    """Probabilidad de `lado` en `linea` desde las lambdas (local, visitante)."""
    if mercado == "corners_home":
        return prob_total(lam[0], PARAMETROS["corners_equipo"]["phi"], linea)[lado]
    if mercado == "corners_away":
        return prob_total(lam[1], PARAMETROS["corners_equipo"]["phi"], linea)[lado]
    return prob_total(lam[0] + lam[1], PARAMETROS[mercado]["phi"], linea)[lado]


def acumulador(mercado: str) -> Acumulador:
    p = PARAMETROS[mercado]
    return Acumulador(usar_arbitro=mercado == "cards", prior=p["prior"],
                      media_vida=p["media_vida"])
