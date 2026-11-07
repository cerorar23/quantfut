"""Comprobación de una matriz de covarianza 2x2 o 3x3 sin numpy: simétrica y definida positiva (Cholesky)."""
import math


def validar_covarianza(m: list[list[float]]) -> None:
    n = len(m)
    if n not in (2, 3):
        raise ValueError("la covarianza debe ser de 2x2 o 3x3")
    if any(len(fila) != n for fila in m):
        raise ValueError("la covarianza debe ser cuadrada")
    if any(not math.isfinite(x) for fila in m for x in fila):
        raise ValueError("la covarianza tiene valores no finitos")
    for i in range(n):
        for j in range(i + 1, n):
            if abs(m[i][j] - m[j][i]) > 1e-12 * (1.0 + abs(m[i][j])):
                raise ValueError("la covarianza no es simétrica")
    _cholesky(m)


def _cholesky(m: list[list[float]]) -> None:
    n = len(m)
    l = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = sum(l[i][k] * l[j][k] for k in range(j))
            if i == j:
                v = m[i][i] - s
                if v <= 0.0:
                    raise ValueError("la covarianza no es definida positiva")
                l[i][i] = math.sqrt(v)
            else:
                l[i][j] = (m[i][j] - s) / l[j][j]
