"""Pruebas del factor de inflación de varianza predictiva c_inf (opción A, 7-nov-2026).

Contrato:
- c_inf = 0 reproduce EXACTAMENTE las predicciones anteriores (sin inflar).
- c_inf > 0 acerca π a 0,5 (menos sobreconfianza) de forma monotónica con c_inf.
- c_inf no afecta la actualización (log_m sin cambio).
- Psi con c_inf negativo lanza ValueError.
- El script estimar_c_inf.py es importable y psi_desde_vector funciona con c_inf.
"""
import math
from dataclasses import replace

import numpy as np
import pytest

from tenis.modelo import datos as dm
from tenis.modelo import hiperparametros as hp
from tenis.modelo import tabla
from tenis.modelo.parametros import Psi
from tenis.modelo.rating import filtrar
from tenis.modelo.sintetico import mundo, psi_prueba, tablas_prueba

MOD = dm.RUTA_EXPORT.parent / "modelo_s3"


# ---------------------------------------------------------------------------
# Pruebas de Tabla.prob con c_inf
# ---------------------------------------------------------------------------

def test_cinf_cero_reproduce_exacto():
    """c_inf = 0 debe dar exactamente el mismo π que sin c_inf."""
    tb = tablas_prueba()[(0, 2)]
    for rho, v in [(-0.5, 0.0), (0.0, 0.01), (0.3, 0.05), (1.2, 0.0)]:
        assert tb.prob(rho, v, 0.0) == tb.prob(rho, v), f"rho={rho}, v={v}"


def test_cinf_positivo_acerca_a_medio():
    """c_inf > 0 reduce la distancia al 0,5 (aplanamiento)."""
    tb = tablas_prueba()[(0, 2)]
    for rho in (0.2, 0.5, 1.0, -0.3):
        p0 = tb.prob(rho, 0.01, 0.0)
        p1 = tb.prob(rho, 0.01, 0.02)
        # Si rho > 0 → p > 0.5; con c_inf mayor debe bajar hacia 0.5
        if rho > 0:
            assert p1 < p0, f"rho={rho}: esperaba p1 < p0, p0={p0:.6f}, p1={p1:.6f}"
        else:
            assert p1 > p0, f"rho={rho}: esperaba p1 > p0, p0={p0:.6f}, p1={p1:.6f}"


def test_cinf_monotono_en_cinf():
    """Mayor c_inf → π más cerca de 0,5 (monotónico)."""
    tb = tablas_prueba()[(0, 2)]
    rho, v = 0.6, 0.02
    vals = [tb.prob(rho, v, c) for c in (0.0, 0.01, 0.05, 0.10, 0.20)]
    for i in range(len(vals) - 1):
        assert vals[i] > vals[i + 1], f"no monotónico en paso {i}: {vals}"


def test_cinf_simetria_a_b():
    """π(ρ, v, c_inf) + π(−ρ, v, c_inf) = 1 exacto."""
    tb = tablas_prueba()[(0, 2)]
    for rho, v, c in [(0.3, 0.02, 0.05), (-0.7, 0.0, 0.1), (0.0, 0.03, 0.03)]:
        assert abs(tb.prob(rho, v, c) + tb.prob(-rho, v, c) - 1) < 1e-9


def test_cinf_no_afecta_log_m():
    """La actualización (log_m) no depende de c_inf — Tabla no tiene estado de c_inf."""
    tb = tablas_prueba()[(0, 2)]
    rho = 0.4
    l0, l1, l2 = tb.log_m(rho)
    # log_m es idéntico independientemente de cómo se llame a prob
    tb.prob(rho, 0.01, 0.1)   # llamada con c_inf
    assert tb.log_m(rho) == (l0, l1, l2)


# ---------------------------------------------------------------------------
# Pruebas de Psi con c_inf
# ---------------------------------------------------------------------------

def test_psi_cinf_invalido():
    """c_inf negativo lanza ValueError."""
    with pytest.raises(ValueError, match="c_inf"):
        psi_prueba(c_inf=-0.01)


def test_psi_cinf_cero_valido():
    """c_inf = 0 (valor por omisión) no lanza."""
    psi = psi_prueba()
    assert psi.c_inf == 0.0


def test_psi_cinf_positivo_valido():
    """c_inf > 0 no lanza y se conserva."""
    psi = psi_prueba(c_inf=0.03)
    assert math.isclose(psi.c_inf, 0.03)


def test_psi_desde_dict_sin_cinf():
    """Psi.desde_dict sin la clave c_inf asigna 0 (retrocompatibilidad)."""
    d = psi_prueba().como_dict()
    del d["c_inf"]
    psi = Psi.desde_dict(d)
    assert psi.c_inf == 0.0


# ---------------------------------------------------------------------------
# Prueba de integración con filtrar (datos sintéticos)
# ---------------------------------------------------------------------------

def test_filtrar_cinf_cero_sin_cambio():
    """filtrar con c_inf=0 produce las mismas π que sin c_inf en datos sintéticos."""
    p, e = mundo(n_jugadores=10, n_semanas=20, semilla=42)
    d = dm.preparar(p, e, "atp", 2030)
    psi = psi_prueba()
    tabs = tablas_prueba()
    sal0 = filtrar(d, psi, tabs)
    sal1 = filtrar(d, replace(psi, c_inf=0.0), tabs)
    np.testing.assert_array_equal(sal0.pi, sal1.pi)


def test_filtrar_cinf_aplan_pronosticos():
    """filtrar con c_inf>0 produce π más cercanas a 0,5 que con c_inf=0."""
    p, e = mundo(n_jugadores=10, n_semanas=30, semilla=99)
    d = dm.preparar(p, e, "atp", 2030)
    psi = psi_prueba()
    tabs = tablas_prueba()
    pi0 = filtrar(d, psi, tabs).pi
    pi1 = filtrar(d, replace(psi, c_inf=0.05), tabs).pi
    sel = np.isfinite(pi0) & np.isfinite(pi1)
    # distancia media al 0,5 debe bajar
    d0 = np.abs(pi0[sel] - 0.5).mean()
    d1 = np.abs(pi1[sel] - 0.5).mean()
    assert d1 < d0, f"c_inf>0 no aplana: d0={d0:.5f}, d1={d1:.5f}"


# ---------------------------------------------------------------------------
# Prueba contra datos reales (si están disponibles)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not MOD.exists(), reason="carpeta modelo_s3 no disponible")
def test_cinf_real_reproduce_base_con_cero():
    """Con c_inf=0 las predicciones WTA 2019–2024 son idénticas a las del hiperparametros vigente."""
    hpj_path = MOD / "hiperparametros.json"
    if not hpj_path.exists():
        pytest.skip("hiperparametros.json no disponible")
    hpj = hp.leer(hpj_path)
    cfg = hpj["circuitos"]["wta"]
    p, e = dm.cargar_export(hasta=2024)
    d = dm.preparar(p, e, "wta", 2024)
    psi_base = Psi.desde_dict(cfg["psi_r"])
    tabs = tabla.construir_todas(tuple(cfg["lbar"]), psi_base.sigma_eps, psi_base.rho_eps)
    # c_inf=0 debe dar las mismas predicciones que c_inf por omisión (0.0 por defecto de la dataclass)
    d_sin_cinf = {k: v for k, v in cfg["psi_r"].items() if k != "c_inf"}
    pi_omision = filtrar(d, Psi.desde_dict(d_sin_cinf), tabs).pi
    pi_zero = filtrar(d, replace(psi_base, c_inf=0.0), tabs).pi
    np.testing.assert_array_equal(pi_omision, pi_zero)


@pytest.mark.skipif(not MOD.exists(), reason="carpeta modelo_s3 no disponible")
def test_cinf_diagnostico_02_acerca_pendiente():
    """Con c_inf=0,02 la pendiente de Platt en 2012–2018 se acerca a 1 respecto a c_inf=0.

    Este valor está documentado en el diagnóstico del traspaso (§4, punto 3): +0,02 lleva la
    pendiente 2012–2018 de ~0,87 a ~0,99-1,00.
    """
    hpj_path = MOD / "hiperparametros.json"
    if not hpj_path.exists():
        pytest.skip("hiperparametros.json no disponible")
    hpj = hp.leer(hpj_path)
    for c in ("atp", "wta"):
        if c not in hpj.get("circuitos", {}):
            continue
        cfg = hpj["circuitos"][c]
        p, e = dm.cargar_export(hasta=2018)
        d = dm.preparar(p, e, c, 2018)
        psi = Psi.desde_dict(cfg["psi_r"])
        tabs = tabla.construir_todas(tuple(cfg["lbar"]), psi.sigma_eps, psi.rho_eps)
        pi0 = filtrar(d, replace(psi, c_inf=0.0), tabs).pi
        pi1 = filtrar(d, replace(psi, c_inf=0.02), tabs).pi
        b0 = hp.pendiente_platt(d, pi0)
        b1 = hp.pendiente_platt(d, pi1)
        assert abs(b1 - 1) < abs(b0 - 1), (
            f"{c}: c_inf=0,02 no acercó la pendiente a 1; b0={b0:.4f}, b1={b1:.4f}"
        )
