"""Capa de edad: recuperación de coeficientes, simetría de lados, edad desconocida, no fuga y validaciones."""
import numpy as np
import pytest

from tenis.modelo import capa_edad as ce
from tenis.modelo.recalibracion import logit


def _mundo(n=20000, beta=-0.15, b=0.95, semilla=7, tasa_edad=0.8):
    rng = np.random.default_rng(semilla)
    pi = np.clip(rng.beta(2.2, 2.2, n), 0.03, 0.97)
    e1, e2 = rng.normal(26, 4, n), rng.normal(26, 4, n)
    conocida = rng.random(n) < tasa_edad
    dedad = np.where(conocida, ce.diferencia_edad(e1, e2), np.nan)
    escala = np.nanstd(dedad)
    z = b * logit(pi) + beta * np.nan_to_num(dedad) / escala
    y = (rng.random(n) < 1 / (1 + np.exp(-z))).astype(float)
    temp = np.sort(rng.integers(2013, 2025, n))
    return pi, dedad, y, temp, escala


def test_recupera_coeficientes():
    pi, dedad, y, _, escala = _mundo()
    capa = ce.ajustar(pi, dedad, y, 2013, 2024)
    assert capa.pendiente == pytest.approx(0.95, abs=0.04)
    assert capa.beta == pytest.approx(-0.15, abs=0.04)
    assert capa.escala == pytest.approx(escala, rel=1e-6)


def test_simetria_de_lados():
    pi, dedad, y, _, _ = _mundo(n=5000)
    capa = ce.ajustar(pi, dedad, y)
    a = ce.aplicar(pi, dedad, capa)
    b = ce.aplicar(1 - pi, -dedad, capa)           # mismo partido con los lados intercambiados
    assert np.allclose(a + b, 1.0, atol=1e-12)


def test_edad_desconocida_solo_aplica_pendiente():
    pi, dedad, y, _, _ = _mundo(n=5000)
    capa = ce.ajustar(pi, dedad, y)
    sin_edad = ce.aplicar(pi[:50], np.full(50, np.nan), capa)
    solo_pendiente = 1 / (1 + np.exp(-capa.pendiente * logit(pi[:50])))
    assert np.allclose(sin_edad, solo_pendiente)


def test_diferencia_edad_rangos_y_recorte():
    d = ce.diferencia_edad([20.0, 13.9, 50.1, np.nan, 40.0, 49.0], [30.0, 25.0, 25.0, 25.0, np.nan, 14.0])
    assert d[0] == -10.0
    assert np.isnan(d[1]) and np.isnan(d[2]) and np.isnan(d[3]) and np.isnan(d[4])
    assert d[5] == ce.DIF_MAX                       # 35 años de diferencia se recorta a 20


def test_pi_nan_se_conserva():
    capa = ce.CapaEdad(1.0, -0.1, 5.0, 3000, 2013, 2018)
    out = ce.aplicar(np.array([0.6, np.nan]), np.array([2.0, 2.0]), capa)
    assert np.isfinite(out[0]) and np.isnan(out[1])


def test_por_temporada_no_usa_el_futuro():
    pi, dedad, y, temp, _ = _mundo(n=30000)
    liq = np.ones(len(pi), bool)
    base, capas = ce.por_temporada(temp, pi, dedad, y, liq, range(2019, 2025), 2013)
    y_alt = y.copy()
    y_alt[temp >= 2022] = 1 - y_alt[temp >= 2022]   # se destruyen las etiquetas desde 2022
    alt, _ = ce.por_temporada(temp, pi, dedad, y_alt, liq, range(2019, 2025), 2013)
    pasado = temp <= 2022                           # π' de 2019-2022 solo depende de etiquetas ≤ 2021
    assert np.allclose(base[pasado & (temp >= 2019)], alt[pasado & (temp >= 2019)], equal_nan=True)
    assert capas[2019].hasta == 2018 and capas[2024].hasta == 2023


def test_por_temporada_sin_datos_suficientes_deja_nan():
    pi, dedad, y, temp, _ = _mundo(n=30000)
    out, capas = ce.por_temporada(temp, pi, dedad, y, np.ones(len(pi), bool), [2013], 2013)
    assert capas[2013] is None and np.isnan(out[temp == 2013]).all()


def test_serializacion_y_validaciones():
    capa = ce.CapaEdad(0.96, -0.12, 4.9, 12345, 2013, 2024)
    assert ce.CapaEdad.desde_dict(capa.como_dict()) == capa
    for malo in (dict(pendiente=0.0), dict(pendiente=3.5), dict(beta=2.5), dict(escala=0.0), dict(beta=float("nan"))):
        with pytest.raises(ValueError):
            ce.CapaEdad(**(dict(pendiente=0.96, beta=-0.12, escala=4.9, n=1, desde=0, hasta=0) | malo))


def test_ajuste_exige_muestra_y_edades():
    rng = np.random.default_rng(1)
    with pytest.raises(ValueError):
        ce.ajustar(np.full(100, 0.6), np.zeros(100), rng.integers(0, 2, 100).astype(float))
    pi = np.full(3000, 0.6)
    with pytest.raises(ValueError):                  # ninguna edad conocida
        ce.ajustar(pi, np.full(3000, np.nan), rng.integers(0, 2, 3000).astype(float))
