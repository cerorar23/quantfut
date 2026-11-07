"""Distribución conjunta del partido y sus mercados (plan G.4). Todos los mercados salen de la MISMA conjunta.

Cada fila es un marcador completo (códigos de set: los del set normal y, desplazados, los del decisivo; −1 = set
no jugado). Las filas «cola» solo existen con set decisivo de ventaja: la masa de los sets que pasan de
`max_juegos` juegos, con ganador exacto, diferencia de juegos exacta (±2 en ese set), total de juegos esperado
(`juegos`) y mínimo (`juegos_min`). Masa de filas normales + cola = 1 (salvo redondeo de coma flotante).
Las etiquetas de los marcadores se construyen solo cuando se piden (`marcadores()`), para que la conjunta de
un mejor de 5 (≈ 217 mil marcadores) se calcule en decenas de milisegundos.
"""
from dataclasses import dataclass

import numpy as np

from .formato import Formato
from .set_ import Catalogo


@dataclass(frozen=True)
class DistPartido:
    formato: Formato
    codigos: np.ndarray     # (filas, mejor_de)
    etiqueta_set: tuple     # código → (juegos_a, juegos_b, tiebreak) o None si es cola
    prob: np.ndarray
    sets_a: np.ndarray
    sets_b: np.ndarray
    juegos: np.ndarray      # total de juegos (media en las filas cola)
    juegos_min: np.ndarray
    dif_juegos: np.ndarray  # juegos A − juegos B (exacta también en la cola)
    n_tb: np.ndarray
    primer_set_a: np.ndarray
    cola: np.ndarray

    @classmethod
    def desde_finales(cls, formato: Formato, cat_r: Catalogo, cat_d: Catalogo, finales: list[dict]) -> "DistPartido":
        es_cola = np.concatenate([cat_r.cola, cat_d.cola])
        cola_min = 2 * int(cat_d.ga[~cat_d.cola].max()) if cat_d.cola.any() else 0

        def col(c, defecto=None):
            return np.concatenate([f.get(c, defecto if defecto is None else np.zeros(len(f["prob"])))
                                   for f in finales])

        cod = np.concatenate([np.pad(f["cod"], ((0, 0), (0, formato.mejor_de - f["cod"].shape[1])),
                                     constant_values=-1) for f in finales])
        prob, jt, jcola = col("prob"), col("jt"), col("jcola", 0)
        cola = es_cola[cod[:, -1]] & (cod[:, -1] >= 0)
        juegos, con_masa = jt.copy(), cola & (prob > 0)
        juegos[con_masa] += jcola[con_masa] / prob[con_masa]
        juegos[cola & ~con_masa] += cola_min
        ga = np.concatenate([cat_r.ga, cat_d.ga]); gb = np.concatenate([cat_r.gb, cat_d.gb])
        tb = np.concatenate([cat_r.tb, cat_d.tb])
        etiqueta = tuple(None if es_cola[x] else (int(ga[x]), int(gb[x]), bool(tb[x])) for x in range(len(ga)))
        return cls(formato, cod, etiqueta, prob, col("sa"), col("sb"), juegos, jt + np.where(cola, cola_min, 0),
                   col("dif"), col("ntb"), col("ps"), cola)

    # --- mercados (plan G.4) ---
    def _p(self, mascara) -> float:
        return float(self.prob[mascara].sum())

    @property
    def masa_total(self) -> float:
        return float(self.prob.sum())

    @property
    def masa_cola(self) -> float:
        return self._p(self.cola)

    @property
    def gana_a(self) -> float:
        return self._p(self.sets_a > self.sets_b)

    @property
    def primer_set_a_prob(self) -> float:
        return self._p(self.primer_set_a)

    def sets_mas_de(self, linea: float) -> float:
        return self._p(self.sets_a + self.sets_b > linea)

    def handicap_sets(self, h: float) -> float:
        return self._p(self.sets_a - self.sets_b + h > 0)

    def handicap_juegos(self, h: float) -> float:
        return self._p(self.dif_juegos + h > 0)

    def juegos_mas_de(self, linea: float) -> float:
        if np.any(self.cola & (self.prob > 0) & (self.juegos_min <= linea)):
            raise ValueError(f"línea {linea} dentro de la cola del set de ventaja: sube max_juegos")
        return self._p(self.juegos > linea)

    @property
    def tiebreak_si(self) -> float:
        return self._p(self.n_tb >= 1)

    @property
    def media_juegos(self) -> float:
        return float((self.prob * self.juegos).sum() / self.prob.sum())

    def marcadores(self) -> dict:
        """marcador (tupla de sets (juegos_a, juegos_b, tiebreak)) → probabilidad; sin las filas cola."""
        et = self.etiqueta_set
        return {tuple(et[x] for x in fila if x >= 0): float(p)
                for fila, p, c in zip(self.codigos.tolist(), self.prob.tolist(), self.cola.tolist()) if not c}

    def resumen(self) -> dict:
        """Conjunta comprimida del plan G.3/G.4: (sets_a, sets_b, juegos_a, juegos_b, n_tb) → probabilidad (sin cola)."""
        ok = ~self.cola
        jt = self.juegos[ok].round().astype(int)
        ga = (jt + self.dif_juegos[ok]) // 2
        claves = np.stack([self.sets_a[ok], self.sets_b[ok], ga, jt - ga, self.n_tb[ok]], axis=1)
        unicas, inv = np.unique(claves, axis=0, return_inverse=True)
        masa = np.bincount(inv.ravel(), weights=self.prob[ok], minlength=len(unicas))
        return {tuple(int(x) for x in u): float(m) for u, m in zip(unicas, masa)}
