"""
Valor por jugador (fuerza por jugador, Fase B1).

Diseño: docs/superpowers/specs/2026-09-29-fuerza-por-jugador-design.md.
Tasas por 90 minutos de cada estadística, con decaimiento temporal y
encogidas hacia la media de la posición del jugador. Punto en el tiempo por
construcción: el llamador AVANZA el reloj al inicio de un partido, LEE los
valores y solo después AÑADE las estadísticas de ese partido.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

OFENSIVAS = ("tiros", "tiros_puerta", "pases_clave", "goles", "asistencias")
DEFENSIVAS = ("entradas", "intercepciones", "duelos_ganados", "paradas")
ESTADISTICAS = OFENSIVAS + DEFENSIVAS
MINUTOS_PREVIA = 450.0      # la media de la posición pesa como 5 partidos
POSICIONES = ("G", "D", "M", "F")
_N = len(ESTADISTICAS)
# Vector: [minutos, estadísticas..., minutos_con_nota, nota·minutos]


class Acumulador:
    def __init__(self, vida_media_dias: float = 180.0):
        self.h = float(vida_media_dias)
        self.t: pd.Timestamp | None = None
        self._jug: dict[int, tuple[pd.Timestamp, np.ndarray]] = {}
        self._pos = {p: np.zeros(_N + 3) for p in POSICIONES}
        self.posicion: dict[int, str] = {}

    def _factor(self, desde: pd.Timestamp) -> float:
        dias = (self.t - desde).total_seconds() / 86400.0
        return 0.5 ** (dias / self.h)

    def avanzar(self, t: pd.Timestamp) -> None:
        if self.t is not None and t > self.t:
            f = 0.5 ** ((t - self.t).total_seconds() / 86400.0 / self.h)
            for p in POSICIONES:
                self._pos[p] *= f
        if self.t is None or t > self.t:
            self.t = t

    def _vector(self, player_id: int) -> np.ndarray:
        if player_id not in self._jug:
            return np.zeros(_N + 3)
        desde, v = self._jug[player_id]
        return v * self._factor(desde)

    def anadir(self, fila: dict) -> None:
        pid = int(fila["player_id"])
        pos = fila.get("posicion") if fila.get("posicion") in POSICIONES else None
        pos = pos or self.posicion.get(pid) or "M"
        self.posicion[pid] = pos
        minutos = float(fila["minutos"] or 0)
        if minutos <= 0:
            return
        nota = fila.get("nota_proveedor")
        add = np.zeros(_N + 3)
        add[0] = minutos
        add[1:_N + 1] = [float(fila.get(e) or 0) for e in ESTADISTICAS]
        if nota is not None and not pd.isna(nota):
            add[_N + 1] = minutos
            add[_N + 2] = float(nota) * minutos
        self._jug[pid] = (self.t, self._vector(pid) + add)
        self._pos[pos] += add

    def conocido(self, player_id: int) -> bool:
        return self._vector(player_id)[0] > 0

    def _pos_de(self, player_id: int, posicion: str | None) -> str:
        if posicion in POSICIONES:
            return posicion
        return self.posicion.get(player_id, "M")

    def tasas(self, player_id: int, posicion: str | None) -> np.ndarray:
        """Por 90 minutos, en el orden de ESTADISTICAS."""
        v = self._vector(player_id)
        p = self._pos[self._pos_de(player_id, posicion)]
        previa = p[1:_N + 1] / p[0] if p[0] > 0 else np.zeros(_N)
        return (v[1:_N + 1] + MINUTOS_PREVIA * previa) / (v[0] + MINUTOS_PREVIA) * 90.0

    def nota(self, player_id: int, posicion: str | None) -> float:
        v = self._vector(player_id)
        p = self._pos[self._pos_de(player_id, posicion)]
        if p[_N + 1] <= 0 and v[_N + 1] <= 0:
            return float("nan")
        previa = p[_N + 2] / p[_N + 1] if p[_N + 1] > 0 else v[_N + 2] / v[_N + 1]
        return float((v[_N + 2] + MINUTOS_PREVIA * previa) / (v[_N + 1] + MINUTOS_PREVIA))
