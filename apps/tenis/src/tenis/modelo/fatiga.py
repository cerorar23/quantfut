"""Fatiga acumulada (plan D.3, C.5): F = Σ λ^Δ · minutos de los partidos visibles terminados en las 96 h previas.

- Instante de fin de un partido previo = su `visible_resultado_utc` (cota superior del fin real; en TML es el fin
  conservador de la ronda) y el del partido = su corte. Δ en días. Aproximación declarada en el informe.
- Walkover: no se jugó ⇒ aporta 0 minutos (dato conocido, no faltante).
- Minutos faltantes en cualquier partido jugado de la ventana ⇒ la fatiga del jugador es DESCONOCIDA (None); nunca 0.
- Solo se mira lo ya visible: el historial se llena al aplicar cada evento, y aquí se ignora todo lo que tenga vis ≥ corte.
"""
import math

DIA_NS = 86_400 * 10**9
VENTANA_NS = 96 * 3_600 * 10**9


def fatiga(historial: list, corte_ns: int, lam: float):
    """historial: [(vis_ns, minutos (nan si falta), walkover)] en orden de visibilidad. Devuelve F (minutos) o None."""
    total = 0.0
    for vis, minutos, walk in reversed(historial):
        if vis >= corte_ns:
            continue
        dt = corte_ns - vis
        if dt > VENTANA_NS:
            break
        if walk:
            continue
        if minutos != minutos:          # NaN: minutos faltantes
            return None
        total += lam ** (dt / DIA_NS) * minutos
    return total


def g1(f: float) -> float:
    return f / 60.0


def g2(f: float, f90: float) -> float:
    return max(0.0, f - f90) / 60.0


def termino(f_a, f_b, phi: tuple, f90: float):
    """φ1·(g1(F_A) − g1(F_B)) + φ2·(g2(F_A) − g2(F_B)), que se RESTA de ρ. None si alguna fatiga es desconocida."""
    if f_a is None or f_b is None:
        return None
    if phi[0] < 0 or phi[1] < 0 or not (math.isfinite(phi[0]) and math.isfinite(phi[1])):
        raise ValueError("φ debe ser ≥ 0")
    return phi[0] * (g1(f_a) - g1(f_b)) + phi[1] * (g2(f_a, f90) - g2(f_b, f90))
