"""Simulación del reto al 80 % en 7 días (eval/escalera_multideporte.py) con datos inventados."""
import pandas as pd

from qf.eval import escalera_multideporte as em


def _c(filas):
    return pd.DataFrame([{"fecha": pd.Timestamp(f), "deporte": dep, "evento": ev, "p": p, "price": q,
                          "won": w} for f, dep, ev, p, q, w in filas])


def test_dos_el_mismo_dia_completa_y_sin_segundo_en_7_dias_expira():
    c = _c([("2025-01-01", "tenis", "a", 0.95, 1.06, True),
            ("2025-01-01", "futbol", "b", 0.90, 1.10, True),      # 0,95 · 0,90 ≥ 0,80
            ("2025-01-03", "tenis", "c", 0.92, 1.07, True),       # nada más en 7 días
            ("2025-01-03", "tenis", "c", 0.08, 9.00, False)])     # el otro lado, mismo partido
    r = em.simular(c, ("futbol", "tenis"), "2025-01-01", "2025-01-20")
    assert (r["retos"], r["completados_pct"], r["expirados_pct"]) == (2, 50.0, 50.0)
    assert r["cobro_completado"] == round(1.06 * 1.10, 3)


def test_el_tope_por_deporte_y_la_cuota_minima_dejan_fuera():
    c = _c([("2025-01-01", "futbol", "a", 0.96, 1.05, True),      # fútbol > 95 %
            ("2025-01-01", "tenis", "b", 0.96, 1.02, True),       # cuota < 1,03
            ("2025-01-02", "nba", "c", 0.90, 1.08, False)])
    r = em.simular(c, ("futbol", "nba", "tenis"), "2025-01-01", "2025-01-10")
    assert (r["retos"], r["fallidos_pct"]) == (1, 100.0)
