"""Ajuste por el once confirmado: factor 1 con el once habitual, a prueba de fallos, y misma cuenta en medición y producción."""
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from qf.model import ajuste_xi as ax
from qf.model import jugadores as jg

T0 = datetime(2026, 1, 1, 20, tzinfo=timezone.utc)


def _partido(mid, dia, equipo, once, estrella_ausente=False):
    filas = []
    for j in range(1, 12):
        if j == 11 and estrella_ausente:
            j = 99
        pos = 11 if j == 1 else (34 if j <= 5 else (64 if j <= 8 else 104))
        filas.append({"match_id": mid, "kickoff_utc": T0 + timedelta(days=dia), "side": "home", "equipo_id": equipo,
                      "jugador_id": j, "titular": True, "posicion_id": pos, "valor_mercado": 50.0 if j == 11 else 5.0,
                      "rating": 6.0 if j == 99 else (8.5 if j == 11 else 6.5)})
    for j in range(201, 212):
        filas.append({"match_id": mid, "kickoff_utc": T0 + timedelta(days=dia), "side": "away", "equipo_id": 2,
                      "jugador_id": j, "titular": True, "posicion_id": 64, "valor_mercado": 5.0, "rating": 6.5})
    return filas


def _historia(extra_final):
    filas = []
    for i in range(5):
        filas += _partido(f"m{i}", i, 1, None)
    return pd.DataFrame(filas + extra_final)


def _ajuste(beta_l=(0.1, -0.05), beta_v=(-0.04, 0.12), shrink=0.5):
    return ax.AjusteXI([1.0, 1.0], list(beta_l), list(beta_v), shrink, 1000, "test")


def test_once_habitual_o_dato_ausente_da_factor_exactamente_uno():
    a = _ajuste()
    assert a.factores(0.0, 0.0) == (1.0, 1.0)
    assert a.factores(np.nan, None) == (1.0, 1.0)


def test_mejor_once_sube_el_lambda_propio_y_el_factor_esta_acotado():
    a = _ajuste()
    fl, fv = a.factores(2.0, 0.0)
    assert fl > 1.0 and fv < 1.0
    assert a.factores(1e9, 1e9) == (pytest.approx(np.e), pytest.approx(np.e))     # clip(−1, 1)


def test_sin_artefacto_no_hay_ajuste(tmp_path):
    assert ax.cargar_ultimo(str(tmp_path)) is None
    assert ax.calcular("m1", str(tmp_path)) is None


def test_guardar_y_cargar(tmp_path):
    a = _ajuste()
    ruta = str(tmp_path / "ajuste_xi_t.pkl")
    a.guardar(ruta)
    assert ax.cargar_ultimo(str(tmp_path)).factores(1.0, 1.0) == a.factores(1.0, 1.0)


def test_produccion_y_medicion_calculan_lo_mismo():
    """El estado hasta el partido anterior + el once del partido da la misma fila que recorrer el histórico completo."""
    completo = _historia(_partido("m5", 5, 1, None, estrella_ausente=True))
    medicion = jg.features_xi(completo).set_index("match_id").loc["m5"]
    previo = completo[completo["match_id"] != "m5"]
    estado = jg.EstadoXI.desde_historial(previo)
    p5 = completo[(completo["match_id"] == "m5") & (completo["side"] == "home")]
    d = estado.delta(1, p5[p5["titular"].astype(bool)])
    assert d["epi_total"] == pytest.approx(medicion["epi_total_local"])
    assert d["epi_ata"] == pytest.approx(medicion["epi_ata_local"])
    assert d["xiv_delta"] == pytest.approx(medicion["xiv_delta_local"])


def test_el_estado_no_incluye_el_partido_que_se_calcula():
    completo = _historia(_partido("m5", 5, 1, None))
    estado = jg.EstadoXI.desde_historial(completo[completo["match_id"] != "m5"])
    antes = dict(estado.suma)
    p5 = completo[(completo["match_id"] == "m5") & (completo["side"] == "home")]
    estado.delta(1, p5[p5["titular"].astype(bool)])
    assert estado.suma == antes                       # `delta` solo lee
