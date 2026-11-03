"""S3c: ¿mejora el impacto por jugador si el a priori sale de tramos de quinteto (RAPM) en vez del más/menos del partido?

    python apps/nba/ops/evaluar_s3c.py CARPETA stints.pkl LAM_RAPM VIDA_RAPM [temporada_prueba=2025-26]

Igual que evaluar_s3b salvo el a priori de `plantilla.ajustar`: ridge ponderado sobre tramos (peso = duración, objetivo = cambio de
margen por 48 minutos, +1 los locales en pista, -1 los visitantes, intercepto de localía sin penalizar), solo con tramos de días
anteriores al corte y con decaimiento. La comparación con el a priori de más/menos es la salida de evaluar_s3b sobre la misma carpeta.
"""
from collections import defaultdict
from pathlib import Path
import pickle
import sys

import numpy as np
import scipy.sparse as sp

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evaluar_s3b as s3b  # noqa: E402


class Rapm:
    def __init__(self, filas, lam, vida):
        filas = sorted(filas, key=lambda f: f[1])
        self.dias = np.array([f[1] for f in filas])
        jugadores = sorted({j for f in filas for j in (*f[4], *f[5])})
        self.idx = {j: i for i, j in enumerate(jugadores)}
        k = len(jugadores)
        r, c, v = [], [], []
        for i, (_, _, dur, _, a, b) in enumerate(filas):
            for j in a:
                r.append(i); c.append(self.idx[j]); v.append(1.0)
            for j in b:
                r.append(i); c.append(self.idx[j]); v.append(-1.0)
            r.append(i); c.append(k); v.append(1.0)          # intercepto de localía
        self.X = sp.csr_matrix((v, (r, c)), shape=(len(filas), k + 1))
        dur = np.array([f[2] for f in filas])
        self.y = np.array([f[3] for f in filas]) / dur * 2880.0      # cambio de margen por 48 minutos
        self.w = dur / 2880.0
        self.lam, self.vida, self.k, self.cache = lam, vida, k, {}

    def beta(self, corte):
        if corte not in self.cache:
            n = int(np.searchsorted(self.dias, corte))              # solo tramos de días anteriores al corte
            w = self.w[:n] * 0.5 ** ((corte - self.dias[:n]) / self.vida)
            X = self.X[:n]
            A = (X.T @ sp.diags(w) @ X).toarray()
            penal = np.full(self.k + 1, self.lam)
            penal[self.k] = 1e-8
            theta = np.linalg.solve(A + np.diag(penal), X.T @ (w * self.y[:n]))
            self.cache[corte] = {j: float(theta[i]) for j, i in self.idx.items()}
        return self.cache[corte]


def main(carpeta, pkl, lam, vida, prueba):
    rapm = Rapm(pickle.load(open(pkl, "rb")), lam, vida)
    print(f"{len(rapm.w)} tramos, {rapm.k} jugadores, lam={lam}, vida={vida}")

    def prior_en(corte, c, n0=0.0, vida_=0.0):
        return {j: c * b for j, b in rapm.beta(corte).items()}

    s3b.prior_en = prior_en
    s3b.main(carpeta, prueba)


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), sys.argv[5] if len(sys.argv) > 5 else "2025-26")
