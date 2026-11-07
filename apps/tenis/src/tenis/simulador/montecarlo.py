"""Simulador punto a punto con semilla fija (plan G.5): SOLO verificación independiente del cálculo exacto y para
lo que no tenga forma cerrada (p. ej. incertidumbre no gaussiana). Nunca es el camino del pronóstico.

Camino de código distinto del analítico: cada partido avanza punto a punto, el saque alterna juego a juego
(el tiebreak cuenta como un juego), así que la regla de «quién saca el set siguiente» NO se usa: emerge sola.
Vectorizado sobre N partidos con numpy. Error estándar de una frecuencia: √(p(1−p)/N).
"""
from dataclasses import dataclass

import numpy as np

from ._comun import validar_p
from .formato import Formato, validar_formato
from .mezcla import Incertidumbre, raiz

MAX_PUNTOS = 5000


@dataclass(frozen=True)
class Simulacion:
    formato: Formato
    sets: np.ndarray      # (N, mejor_de, 3): juegos A, juegos B, tiebreak (−1 = set no jugado)

    @property
    def n(self) -> int:
        return len(self.sets)

    def _jugado(self):
        return self.sets[:, :, 0] >= 0

    def _ganados(self):
        j = self._jugado()
        a = ((self.sets[:, :, 0] > self.sets[:, :, 1]) & j).sum(axis=1)
        return a, j.sum(axis=1) - a

    def total_juegos(self) -> np.ndarray:
        return np.where(self._jugado(), self.sets[:, :, 0] + self.sets[:, :, 1], 0).sum(axis=1)

    def frecuencia(self, mascara) -> tuple[float, float]:
        """(estimación, error estándar)."""
        p = float(np.mean(mascara))
        return p, float(np.sqrt(max(p * (1 - p), 0.0) / self.n))

    def gana_a(self):
        a, b = self._ganados()
        return self.frecuencia(a > b)

    def primer_set_a(self):
        return self.frecuencia(self.sets[:, 0, 0] > self.sets[:, 0, 1])

    def juegos_mas_de(self, linea: float):
        return self.frecuencia(self.total_juegos() > linea)

    def marcadores(self) -> dict:
        out: dict = {}
        for fila in self.sets.tolist():
            k = tuple((a, b, bool(t)) for a, b, t in fila if a >= 0)
            out[k] = out.get(k, 0) + 1
        return {k: v / self.n for k, v in out.items()}


def simular(p_a: float, p_b: float, formato: Formato, n: int, semilla: int, inc: Incertidumbre | None = None,
            saca_primero: str = "desconocido", max_puntos: int = MAX_PUNTOS) -> Simulacion:
    formato = validar_formato(formato)
    rng = np.random.default_rng(semilla)
    pa = np.full(n, float(validar_p(p_a, "p_a")))
    pb = np.full(n, float(validar_p(p_b, "p_b")))
    if inc is not None and inc.matriz().any():                    # forma del día sorteada por partido
        u = raiz(inc.matriz()) @ rng.standard_normal((2, n))
        pa = 1 / (1 + np.exp(-(np.log(pa / (1 - pa)) + u[0])))
        pb = 1 / (1 + np.exp(-(np.log(pb / (1 - pb)) + u[1])))
    if saca_primero == "desconocido":
        srv = rng.integers(0, 2, n)
    elif saca_primero in ("A", "B"):
        srv = np.full(n, 0 if saca_primero == "A" else 1)
    else:
        raise ValueError(f"saca_primero «{saca_primero}» desconocido")
    md, need, dec = formato.mejor_de, formato.sets_para_ganar, formato.mejor_de - 1
    pts, gms, sts = np.zeros((n, 2), int), np.zeros((n, 2), int), np.zeros((n, 2), int)
    set_i, tb_k, tb_1 = np.zeros(n, int), np.zeros(n, int), np.zeros(n, int)
    en_tb, hecho = np.zeros(n, bool), np.zeros(n, bool)
    rec = np.full((n, md, 3), -1)
    act = np.arange(n)
    for _ in range(max_puntos):
        if act.size == 0:
            return Simulacion(formato, rec)
        tb = en_tb[act]
        k = pts[act, 0] + pts[act, 1]
        saca = np.where(tb, np.where(((k + 1) // 2) % 2 == 0, tb_1[act], 1 - tb_1[act]), srv[act])
        gana = rng.random(act.size) < np.where(saca == 0, pa[act], 1 - pb[act])
        pts[act, 0] += gana
        pts[act, 1] += ~gana
        x, y = pts[act, 0], pts[act, 1]
        obj = np.where(tb, tb_k[act], 4)
        fin = ((x >= obj) & (x - y >= 2)) | ((y >= obj) & (y - x >= 2))
        g = act[fin]
        if g.size:
            _fin_de_juego(g, x[fin] > y[fin], formato, pts, gms, sts, srv, set_i, en_tb, tb_k, tb_1, rec, hecho,
                          need, dec)
            act = act[~hecho[act]]
    raise RuntimeError(f"{act.size} partidos sin terminar tras {max_puntos} puntos (set de ventaja eterno)")


def _fin_de_juego(g, gana_a, formato, pts, gms, sts, srv, set_i, en_tb, tb_k, tb_1, rec, hecho, need, dec):
    gms[g, 0] += gana_a
    gms[g, 1] += ~gana_a
    pts[g] = 0
    fue_tb = en_tb[g].copy()
    srv[g] = 1 - srv[g]
    ga, gb = gms[g, 0], gms[g, 1]
    hi, lo = np.maximum(ga, gb), np.minimum(ga, gb)
    es_dec = set_i[g] == dec
    ventaja = es_dec & (formato.decisivo == "ventaja")
    fin_set = fue_tb | (~ventaja & (((hi == 6) & (lo <= 4)) | (hi == 7))) | (ventaja & (hi >= 6) & (hi - lo >= 2))
    a_tb = ~fin_set & ~ventaja & (ga == 6) & (gb == 6)
    t = g[a_tb]
    en_tb[t], tb_1[t] = True, srv[t]
    tb_k[t] = np.where(es_dec[a_tb] & (formato.decisivo == "tiebreak_10"), 10, 7)
    s = g[fin_set]
    rec[s, set_i[s], 0], rec[s, set_i[s], 1], rec[s, set_i[s], 2] = gms[s, 0], gms[s, 1], fue_tb[fin_set]
    sts[s, 0] += gms[s, 0] > gms[s, 1]
    sts[s, 1] += gms[s, 0] < gms[s, 1]
    gms[s], en_tb[s] = 0, False
    set_i[s] += 1
    hecho[s] = sts[s].max(axis=1) >= need
    if formato.decisivo == "super_tiebreak_10":
        st = s[~hecho[s] & (set_i[s] == dec)]
        en_tb[st], tb_k[st], tb_1[st] = True, 10, srv[st]
