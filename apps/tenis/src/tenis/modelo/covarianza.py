"""Estado conjunto de θ con COVARIANZA COMPLETA entre jugadores activos (variante «filtro completo», 6-nov).

- θ de los jugadores activos ~ N(m, C) conjunta (C densa, índices por «hueco»); la covarianza cruzada nace de los
  partidos compartidos y la predicción usa Var(θ_A − θ_B) = C_AA + C_BB − 2·C_AB.
- d_i (superficie, 4) y su covarianza con el propio θ_i (X_i) quedan por jugador: se descartan cov(d_i, θ_j≠i) y
  cov(d_i, d_j) (parte de campo medio, declarada).
- Paseo aleatorio, inactividad y paseo de d solo en la diagonal (como en el filtro anterior).
- Ventana de activos: un jugador sin actualizaciones en `ventana` años sale de C (marginalizar una gaussiana = quitar
  su fila y columna, exacto para el resto) y guarda su marginal; si vuelve, entra con covarianza cruzada 0.
"""
import numpy as np

from .estado import ruido
from .superficie import omega


class EstadoConjunto:
    def __init__(self, n_jugadores: int, psi, cruzadas: bool = True, capacidad: int = 256):
        self.psi, self.cruzadas, self.om = psi, cruzadas, np.array(omega(psi.r_omega))
        self.hueco = np.full(n_jugadores, -1)
        self.jugador_de = np.full(capacidad, -1)
        self.c = np.zeros((capacidad, capacidad))
        self.m = np.zeros(capacidad)                      # media de θ por hueco
        self.m_fuera = np.zeros(n_jugadores)              # marginal guardada al salir de la ventana
        self.v_fuera = np.zeros(n_jugadores)
        self.md = np.zeros((n_jugadores, 4))
        self.x = np.zeros((n_jugadores, 4))               # cov(θ_i, d_i)
        self.dd = np.zeros((n_jugadores, 4, 4))
        self.existe = np.zeros(n_jugadores, bool)
        self.t = np.zeros(n_jugadores, dtype=np.int64)
        self.libres = list(range(capacidad - 1, -1, -1))

    # ---- alta, salida y compactación ----
    def _hueco_libre(self) -> int:
        if not self.libres:
            n = len(self.m)
            c = np.zeros((2 * n, 2 * n)); c[:n, :n] = self.c; self.c = c
            self.m = np.r_[self.m, np.zeros(n)]
            self.jugador_de = np.r_[self.jugador_de, np.full(n, -1)]
            self.libres = list(range(2 * n - 1, n - 1, -1))
        return self.libres.pop()

    def entrar(self, j: int, media: float, var: float):
        h = self._hueco_libre()
        self.c[h, :] = 0.0; self.c[:, h] = 0.0; self.c[h, h] = var
        self.m[h] = media
        self.hueco[j], self.jugador_de[h] = h, j

    def alta(self, j: int, media: float, var: float, dd: np.ndarray, t_ns: int):
        self.entrar(j, media, var)
        self.md[j] = 0.0; self.x[j] = 0.0; self.dd[j] = dd; self.existe[j] = True; self.t[j] = t_ns

    def asegurar_activo(self, j: int):
        if self.hueco[j] < 0:
            self.entrar(j, self.m_fuera[j], self.v_fuera[j])

    def barrer(self, ahora_ns: int, ventana_ns: int):
        """Saca de C a los jugadores sin actualizaciones en la ventana (guarda su marginal)."""
        act = np.flatnonzero(self.jugador_de >= 0)
        viejos = act[self.t[self.jugador_de[act]] < ahora_ns - ventana_ns]
        for h in viejos:
            j = self.jugador_de[h]
            self.m_fuera[j], self.v_fuera[j] = self.m[h], self.c[h, h]
            self.c[h, :] = 0.0; self.c[:, h] = 0.0
            self.hueco[j], self.jugador_de[h] = -1, -1
            self.libres.append(int(h))
        if len(self.libres) > max(256, len(self.m) // 2):
            self._compactar()

    def _compactar(self):
        act = np.flatnonzero(self.jugador_de >= 0)
        n = max(256, 2 * len(act))
        c = np.zeros((n, n)); c[:len(act), :len(act)] = self.c[np.ix_(act, act)]
        m = np.zeros(n); m[:len(act)] = self.m[act]
        jd = np.full(n, -1); jd[:len(act)] = self.jugador_de[act]
        self.c, self.m, self.jugador_de = c, m, jd
        self.hueco[:] = -1
        self.hueco[jd[:len(act)]] = np.arange(len(act))
        self.libres = list(range(n - 1, len(act) - 1, -1))

    # ---- propagación (diagonal) y varianza del diferencial ----
    def propagar(self, j: int, ahora_ns: int):
        dt = ahora_ns - self.t[j]
        if dt > 0:
            q_th, q_d = ruido(int(dt), self.psi)
            h = self.hueco[j]
            self.c[h, h] += q_th
            if q_d > 0.0:
                self.dd[j] += q_d * self.om
        self.t[j] = ahora_ns

    def var_diferencial(self, a: int, b: int, k: float, s: int, ahora_ns: int) -> float:
        """aᵀ V a con a = k(e_θA − e_θB) + e_dA,s − e_dB,s, propagado a `ahora` sin modificar el estado."""
        ha, hb = self.hueco[a], self.hueco[b]
        qa, qda = ruido(int(ahora_ns - self.t[a]), self.psi)
        qb, qdb = ruido(int(ahora_ns - self.t[b]), self.psi)
        vt = self.c[ha, ha] + qa + self.c[hb, hb] + qb - 2.0 * self.c[ha, hb]
        return float(k * k * vt + 2.0 * k * (self.x[a, s] + self.x[b, s]) + self.dd[a, s, s] + qda + self.dd[b, s, s] + qdb)

    def rho(self, a: int, b: int, k: float, s: int) -> float:
        return float(k * (self.m[self.hueco[a]] - self.m[self.hueco[b]]) + self.md[a, s] - self.md[b, s])

    # ---- actualización conjunta de un bloque (Laplace, Woodbury de rango K) ----
    def actualizar_bloque(self, ev: list):
        """ev: [(a, b, k, s, g, h)] simultáneos, con g, h en el estado previo al bloque.
        V⁺ = V − U (I + H S)⁻¹ H Uᵀ, m⁺ = m + U (I + H S)⁻¹ g, con U = V·A y S = Aᵀ V A."""
        n = len(ev)
        ha = np.array([self.hueco[e[0]] for e in ev]); hb = np.array([self.hueco[e[1]] for e in ev])
        kk = np.array([e[2] for e in ev]); ss = np.array([e[3] for e in ev])
        g = np.array([e[4] for e in ev]); hh = np.array([e[5] for e in ev])
        u = (self.c[:, ha] - self.c[:, hb]) * kk                     # parte θ de V·A
        u[ha, np.arange(n)] += self.x[[e[0] for e in ev], ss]
        u[hb, np.arange(n)] -= self.x[[e[1] for e in ev], ss]
        ud = {}                                                      # parte d: solo de los jugadores de cada partido
        for col, (a, b, k, s, _, _) in enumerate(ev):
            for j, sg in ((a, 1.0), (b, -1.0)):
                ud.setdefault(j, np.zeros((4, n)))[:, col] = sg * (k * self.x[j] + self.dd[j][:, s])
        smat = kk[:, None] * (u[ha, :] - u[hb, :])
        for row, (a, b, k, s, _, _) in enumerate(ev):
            for j, sg in ((a, 1.0), (b, -1.0)):
                smat[row] += sg * ud[j][s]
        smat = 0.5 * (smat + smat.T)
        mm = np.linalg.solve(np.eye(n) + hh[:, None] * smat, np.diag(hh))
        mm = 0.5 * (mm + mm.T)
        paso = np.linalg.solve(np.eye(n) + hh[:, None] * smat, g)
        self.m += u @ paso
        for j, uj in ud.items():
            self.md[j] += uj @ paso
        if self.cruzadas:
            self.c -= (u @ mm) @ u.T
        else:                                                         # cruzadas forzadas a 0: solo la diagonal
            dia = np.einsum("ik,kl,il->i", u, mm, u)
            self.c[np.diag_indices_from(self.c)] -= dia
        for j, uj in ud.items():
            fila = u[self.hueco[j]]
            self.x[j] -= uj @ mm @ fila
            self.dd[j] -= uj @ mm @ uj.T
