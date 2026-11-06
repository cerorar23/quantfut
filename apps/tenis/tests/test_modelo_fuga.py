"""NO-FUGA: ningún estado usa un evento con visible ≥ corte del partido; el resultado propio nunca entra.

Sobre un mundo sintético y sobre datos REALES de la exportación (WTA 2005–2006; se omite si no está el fichero).
"""
import numpy as np
import pandas as pd
import pytest

from tenis.modelo import datos as dm
from tenis.modelo.linea_base import elo
from tenis.modelo.rating import filtrar
from tenis.modelo.sintetico import mundo, psi_prueba, tablas_prueba


@pytest.fixture(scope="module")
def real():
    if not (dm.RUTA_EXPORT / "partidos.parquet").exists():
        pytest.skip("exportación PIT no disponible")
    p, e = dm.cargar_export(hasta=2006)
    return dm.preparar(p, e, "wta", 2006)


def comprobar(d, s):
    hecho = np.isfinite(s.pi)
    assert hecho.sum() > 100
    assert np.all(s.ult_vis[hecho] < d.p.corte_ns.to_numpy()[hecho])


def test_ultimo_evento_aplicado_es_anterior_al_corte(real):
    comprobar(real, filtrar(real, psi_prueba(), tablas_prueba()))
    p, e = mundo(semilla=21)
    d = dm.preparar(p, e, "atp", 2030)
    comprobar(d, filtrar(d, psi_prueba(), tablas_prueba()))


def test_cambiar_un_resultado_no_altera_nada_anterior_a_su_visibilidad(real):
    """Invertir el ganador del partido m: π_m y todo pronóstico con corte ≤ visible_m quedan idénticos
    (y para Elo igual). Después de su visibilidad, algo cambia (el resultado sí se usa, pero solo entonces)."""
    d = real
    base = filtrar(d, psi_prueba(), tablas_prueba())
    base_elo = elo(d)["p_elo"]
    rng = np.random.default_rng(5)
    candidatos = np.flatnonzero(d.e.actualiza.to_numpy() & (d.e.pidx.to_numpy() >= 0) & (d.e.temporada == 2005).to_numpy())
    for i in rng.choice(candidatos, size=4, replace=False):
        gan = d.e.gan.copy()
        gan.iat[i] = 3 - gan.iat[i]
        s = filtrar(d, psi_prueba(), tablas_prueba(), ganadores=gan)
        antes = d.p.corte_ns.to_numpy() <= d.e.vis_ns.iat[i]
        np.testing.assert_array_equal(s.pi[antes], base.pi[antes])
        assert s.pi[d.e.pidx.iat[i]] == base.pi[d.e.pidx.iat[i]]
        despues = ~antes & np.isfinite(base.pi)
        assert np.any(s.pi[despues] != base.pi[despues])
        e2 = d.e.copy(); e2["gan"] = gan
        d2 = dm.DatosCircuito(d.circuito, d.n_jugadores, d.p, d.y1, d.liquida, e2)
        np.testing.assert_array_equal(elo(d2)["p_elo"][antes], base_elo[antes])


def test_las_etiquetas_de_los_partidos_no_entran_en_el_filtro():
    """Las columnas y_* de los partidos no las lee el filtro: cambiarlas no cambia nada."""
    p, e = mundo(semilla=22)
    d = dm.preparar(p, e, "atp", 2030)
    s = filtrar(d, psi_prueba(), tablas_prueba())
    p2 = p.assign(y_ganador=3 - p.y_ganador, y_estado="walkover")
    d2 = dm.preparar(p2, e, "atp", 2030)
    np.testing.assert_array_equal(filtrar(d2, psi_prueba(), tablas_prueba()).pi, s.pi)
    assert "y_ganador" not in d.p.columns and "y_estado" not in d.p.columns


def test_la_reserva_no_se_carga():
    if not (dm.RUTA_EXPORT / "partidos.parquet").exists():
        pytest.skip("exportación PIT no disponible")
    p, e = dm.cargar_export(hasta=2024)
    assert p.temporada.max() <= 2024 and e.temporada.max() <= 2024
    assert pd.api.types.is_integer_dtype(p.temporada)
