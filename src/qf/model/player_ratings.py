"""
Valor por jugador (fuerza por jugador, Fase B1).

Diseño: docs/superpowers/specs/2026-09-29-fuerza-por-jugador-design.md.
Tasas por 90 minutos de cada estadística, con decaimiento temporal y
encogidas hacia la media de la posición del jugador. Punto en el tiempo por
construcción: el llamador AVANZA el reloj al inicio de un partido, LEE los
valores y solo después AÑADE las estadísticas de ese partido.
"""
from __future__ import annotations

from collections import defaultdict, deque

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


LADOS = ("home", "away")
VALOR_FEATURES = [f"{lado}_d_{e}" for lado in LADOS for e in ESTADISTICAS]
NOTA_FEATURES = ["home_d_nota", "away_d_nota"]


def _xi(starters) -> dict[int, str | None]:
    out = {}
    for p in starters or []:
        if p.get("player_id"):
            out[int(p["player_id"])] = (str(p.get("pos") or "").upper()[:1] or None)
    return out


def _habitual(historia: deque) -> dict[int, str | None]:
    """Los 11 más frecuentes en los últimos XI; a igualdad, el más reciente."""
    cuenta: dict[int, int] = defaultdict(int)
    ultimo: dict[int, int] = {}
    pos: dict[int, str | None] = {}
    for i, xi in enumerate(historia):
        for pid, p in xi.items():
            cuenta[pid] += 1
            ultimo[pid] = i
            pos[pid] = p or pos.get(pid)
    orden = sorted(cuenta, key=lambda pid: (-cuenta[pid], -ultimo[pid]))[:11]
    return {pid: pos[pid] for pid in orden}


def _suma(acc: Acumulador, xi: dict[int, str | None]) -> tuple[np.ndarray, float]:
    tasas = [acc.tasas(pid, pos) for pid, pos in xi.items()]
    notas = [acc.nota(pid, pos) for pid, pos in xi.items()]
    notas = [n for n in notas if not np.isnan(n)]
    return (np.sum(tasas, axis=0) if tasas else np.zeros(len(ESTADISTICAS)),
            float(np.mean(notas)) if notas else float("nan"))


def build_value_features(matches: pd.DataFrame, lineups: pd.DataFrame,
                         stats: pd.DataFrame, vida_media_dias: float = 180.0,
                         lookback: int = 5, max_desconocidos: int = 3) -> pd.DataFrame:
    """
    Por partido y lado: valor del XI de hoy menos el del XI habitual, por
    estadística, más la diferencia de nota media. Recorre el calendario en
    orden: LEE a la hora de inicio y AÑADE el partido después, así un
    partido nunca ve estadísticas ni alineaciones suyas ni posteriores.
    """
    cols = ["match_id", *VALOR_FEATURES, *NOTA_FEATURES]
    if matches.empty or lineups.empty:
        return pd.DataFrame(columns=cols)
    ms = matches.copy()
    ms["kickoff_utc"] = pd.to_datetime(ms["kickoff_utc"], utc=True)
    xi_de = {(r["match_id"], r["side"]): _xi(r["starters"]) for _, r in lineups.iterrows()}
    stats_de = ({mid: g.to_dict("records") for mid, g in stats.groupby("match_id")}
                if not stats.empty else {})
    historias: dict[object, deque] = defaultdict(lambda: deque(maxlen=lookback))
    acc = Acumulador(vida_media_dias)
    filas = []
    for ko, grupo in ms.sort_values(["kickoff_utc", "match_id"]).groupby("kickoff_utc", sort=True):
        acc.avanzar(ko)
        pendientes = []
        for _, m in grupo.iterrows():
            valores, completo = {"match_id": m["match_id"]}, True
            for lado in LADOS:
                hoy = xi_de.get((m["match_id"], lado))
                equipo = m[f"{lado}_team_id"]
                if not hoy:
                    completo = False
                    continue
                pendientes.append((equipo, hoy))
                historia = historias[equipo]
                if len(historia) < 3:
                    completo = False
                    continue
                if sum(not acc.conocido(pid) for pid in hoy) > max_desconocidos:
                    completo = False
                    continue
                t_hoy, n_hoy = _suma(acc, hoy)
                t_hab, n_hab = _suma(acc, _habitual(historia))
                for e, d in zip(ESTADISTICAS, t_hoy - t_hab):
                    valores[f"{lado}_d_{e}"] = float(d)
                valores[f"{lado}_d_nota"] = n_hoy - n_hab
            if completo:
                filas.append(valores)
        for equipo, hoy in pendientes:
            historias[equipo].append(hoy)
        for _, m in grupo.iterrows():
            for fila in stats_de.get(m["match_id"], []):
                acc.anadir(fila)
    return pd.DataFrame(filas, columns=cols)
