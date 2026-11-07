"""Regresión del parche G-calibración (6-nov): σ_R² del partido en el enlace de R.

- σ_R = 0 reproduce EXACTAMENTE (sha256) las predicciones WTA 2019–2024 anteriores al parche.
- σ_R > 0 (la estimada) acerca a 1 la pendiente de Platt en 2012–2018 (menos sobreconfianza), con el resto igual.
- La convolución coincide con el simulador exacto (Σ_ε + σ_R²·[[1,−1],[−1,1]], cuadratura fina).
"""
import hashlib
import math
from dataclasses import replace

import pandas as pd
import pytest

from tenis.modelo import datos as dm
from tenis.modelo import hiperparametros as hp
from tenis.modelo import tabla
from tenis.modelo.parametros import Psi
from tenis.modelo.rating import filtrar
from tenis.modelo.sintetico import LBAR, RHO_EPS, SIGMA_EPS, psi_prueba, tablas_prueba
from tenis.simulador.formato import Formato
from tenis.simulador.mezcla import Incertidumbre, prob_ganar

MOD = dm.RUTA_EXPORT.parent / "modelo_s3"
HP_ANTES, PRED_ANTES, HP_NUEVO = (MOD / "hiperparametros_antes_parche.json", MOD / "predicciones_wf_antes_parche.parquet",
                                  MOD / "hiperparametros.json")
COLS = ["partido_key", "pi_lado1", "rho", "var_rho", "fatiga_1", "fatiga_2"]


def _sha(df: pd.DataFrame) -> str:
    return hashlib.sha256(df[COLS].to_csv(index=False, float_format="%.12g").encode()).hexdigest()


def _cfg(ruta, c="wta"):
    if not ruta.exists():
        pytest.skip(f"falta {ruta.name}")
    return hp.leer(ruta)["circuitos"][c]


def _tablas(cfg):
    return tabla.construir_todas(tuple(cfg["lbar"]), cfg["psi_r"]["sigma_eps"], cfg["psi_r"]["rho_eps"])


def test_sigma_r_cero_reproduce_el_sha256_anterior():
    cfg = _cfg(HP_ANTES)
    if not PRED_ANTES.exists():
        pytest.skip("faltan las predicciones anteriores al parche")
    p, e = dm.cargar_export(hasta=2024)
    d = dm.preparar(p, e, "wta", 2024)
    s = filtrar(d, replace(Psi.desde_dict(cfg["psi_r"]), sigma_r=0.0), _tablas(cfg))
    nuevo = pd.DataFrame({"partido_key": d.p.partido_key, "temporada": d.p.temporada, "pi_lado1": s.pi, "rho": s.rho,
                          "var_rho": s.var_rho, "fatiga_1": s.f1, "fatiga_2": s.f2})
    nuevo = nuevo[(nuevo.temporada >= 2019) & nuevo.pi_lado1.notna()].reset_index(drop=True)
    viejo = pd.read_parquet(PRED_ANTES, columns=COLS + ["circuito"])
    viejo = viejo[viejo.circuito == "wta"].reset_index(drop=True)
    assert len(nuevo) == len(viejo) and _sha(nuevo) == _sha(viejo)


def test_sigma_r_positiva_acerca_platt_a_uno():
    """Mecanismo: con σ_R = 0,15 (resto igual) la pendiente de Platt 2012–2018 sube hacia 1. La σ_R ESTIMADA por MV
    es ≈ 0 (0,0036 WTA, 0,0010 ATP): la MV no quiere esa varianza en la verosimilitud (ver informe, causa raíz)."""
    cfg_a = _cfg(HP_ANTES)
    p, e = dm.cargar_export(hasta=2018)
    d = dm.preparar(p, e, "wta", 2018)
    psi_a = Psi.desde_dict(cfg_a["psi_r"])
    tabs = _tablas(cfg_a)
    b_a = hp.pendiente_platt(d, filtrar(d, psi_a, tabs).pi)
    b_n = hp.pendiente_platt(d, filtrar(d, replace(psi_a, sigma_r=0.15), tabs).pi)
    assert b_n > b_a and abs(b_n - 1) < abs(b_a - 1)
    if HP_NUEVO.exists():
        assert hp.leer(HP_NUEVO)["circuitos"]["wta"]["psi_r"]["sigma_r"] < 0.05


def test_convolucion_igual_al_simulador_y_cero_es_identidad():
    tb = tablas_prueba()[(0, 2)]
    assert tabla.convolucionar(tb, 0.0) is tb
    s2 = 0.04
    c = tabla.convolucionar(tb, s2)
    inc = Incertidumbre(SIGMA_EPS, RHO_EPS, ((s2, -s2), (-s2, s2)))
    for r in (-0.43, -0.07, 0.0, 0.21, 0.6):
        ex = prob_ganar(float(tabla.expit(LBAR + r)), float(tabla.expit(LBAR - r)), Formato(3, "tiebreak_7"), inc, q=61)
        assert abs(math.exp(c.log_m(r)[0]) - ex) < 1e-6
        assert abs(math.exp(c.log_m(r)[0]) + math.exp(c.log_m(-r)[0]) - 1) < 1e-8
    # más varianza del partido ⇒ π más cerca de 0,5
    assert 0.5 < c.prob(0.2, 0.01) < tb.prob(0.2, 0.01)


def test_sigma_r_negativa_imposible():
    with pytest.raises(ValueError):
        psi_prueba(sigma_r=-0.1)
    with pytest.raises(ValueError):
        psi_prueba(sigma_r_challenger=float("nan"))
