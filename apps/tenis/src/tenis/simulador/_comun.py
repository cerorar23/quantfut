"""Validaciones compartidas del simulador: probabilidades de punto en (0, 1), lado del sacador y salida escalar."""
import numpy as np

LADOS = ("A", "B")


def validar_p(p, nombre: str = "p") -> np.ndarray:
    """Probabilidad de ganar un punto: número finito en el intervalo ABIERTO (0, 1). Devuelve un ndarray float."""
    if isinstance(p, (str, bytes, bool, np.bool_)) or p is None:
        raise TypeError(f"{nombre} debe ser un número, no {type(p).__name__}")
    arr = np.asarray(p, dtype=float)
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{nombre} no es finita (NaN o infinito)")
    if np.any(arr <= 0.0) or np.any(arr >= 1.0):
        raise ValueError(f"{nombre} debe estar en el intervalo abierto (0, 1): con p = 0 o p = 1 "
                         "un tiebreak o un set de ventaja entre dos sacadores perfectos no termina")
    return arr


def validar_lado(lado: str) -> bool:
    """'A' o 'B'; devuelve True si es A."""
    if lado not in LADOS:
        raise ValueError(f"sacador «{lado}» desconocido: debe ser 'A' o 'B'")
    return lado == "A"


def salida(x):
    """Escalar numpy → float de Python; arrays tal cual. Nunca deja pasar NaN ni infinitos."""
    arr = np.asarray(x, dtype=float)
    if not np.all(np.isfinite(arr)):
        raise FloatingPointError("el simulador produjo un valor no finito")
    return float(arr) if arr.ndim == 0 else arr
