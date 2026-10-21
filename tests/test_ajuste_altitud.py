"""El ajuste de altitud solo mueve lo que la altitud explica y nunca puede romper el sellado."""
import numpy as np
import pandas as pd
import pytest

from qf.model import ajuste_altitud as aa
from qf.model import contexto as cx


def _marco(n=2400, seed=5, efecto=0.12):
    rng = np.random.default_rng(seed)
    salto = np.where(rng.random(n) < 0.06, rng.uniform(0.8, 2.6, n), 0.0)       # pocos partidos con salto de altura
    sede = np.where(salto > 0, salto + rng.uniform(0.0, 0.2, n), rng.uniform(0.0, 0.3, n))
    cols = {c: rng.normal(size=n) for cs in cx.BLOQUES_CONTEXTO.values() for c in cs}
    cols["alt_sede_km"], cols["alt_dif_km"] = sede, salto
    return pd.DataFrame({
        "match_id": [f"m{i}" for i in range(n)], "league_id": ["A", "B", "C"] * (n // 3),
        "kickoff_utc": pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC"),
        "base_lam": 1.4, "base_mu": 1.1, "rho": -0.05, **cols,
        "home_goals": rng.poisson(1.4 * np.exp(efecto * salto)), "away_goals": rng.poisson(1.1 * np.exp(-0.6 * efecto * salto))})


def test_aprende_que_con_salto_de_altura_el_local_marca_mas_y_el_visitante_menos():
    a = aa.ajustar(_marco(), "synthetic")
    fl, fv = a.factores(2.3)
    assert fl > 1.03 and fv < 1.0
    assert a.factores(0.0) == pytest.approx((1.0, 1.0))                  # sin salto de altura, exactamente neutro


def test_dato_ausente_es_neutro_y_el_factor_esta_acotado():
    a = aa.ajustar(_marco(), "synthetic")
    assert a.factores(float("nan")) == pytest.approx((1.0, 1.0))
    grande = aa.AjusteAltitud([0.0], [1.0], [5.0], [-5.0], 1.0, 10, "x")
    fl, fv = grande.factores(10.0)
    assert fl == pytest.approx(np.e) and fv == pytest.approx(1 / np.e)   # clip a ±1 en log


def test_aplicar_mueve_lambdas_con_constancia_y_sin_ajuste_no_toca_nada():
    a = aa.ajustar(_marco(), "synthetic")
    lam, mu, info = aa.aplicar(a, 1.5, 1.0, 2660.0, 30.0)
    assert lam > 1.5 and mu < 1.0 and info["factor_local"] > 1 and info["oos_version"] == "synthetic"
    assert info["sede_km"] == pytest.approx(2.66) and info["dif_km"] == pytest.approx(2.63)
    assert aa.aplicar(None, 1.5, 1.0, 2660.0, 30.0) == (1.5, 1.0, None)


def test_un_fallo_devuelve_los_lambdas_intactos():
    roto = aa.AjusteAltitud([0.0, 0.0], [1.0, 1.0], [0.1], [0.1], 0.5, 1, "malo")   # forma equivocada: revienta adentro
    assert aa.aplicar(roto, 1.5, 1.0, 2660.0, 30.0) == (1.5, 1.0, None)


def test_guardar_y_cargar_dan_los_mismos_factores(tmp_path):
    a = aa.ajustar(_marco(), "synthetic")
    ruta = str(tmp_path / "ajuste_altitud_synthetic.pkl")
    a.guardar(ruta)
    assert aa.cargar_ultimo(str(tmp_path)).factores(1.8) == a.factores(1.8)
    assert aa.cargar_ultimo(str(tmp_path / "vacia")) is None


# --- integración con la predicción diaria (modo sombra / activo / apagado) ---
def _ajuste_fijo():
    return aa.AjusteAltitud([0.0], [1.0], [0.10], [-0.10], 1.0, 10, "fijo")


def test_en_sombra_los_lambdas_publicados_no_cambian_pero_queda_constancia():
    from qf.publish import daily
    lam, mu, info = daily._aplicar_altitud(_ajuste_fijo(), {"m1": (2660.0, 30.0)}, "m1", 1.5, 1.0, "sombra")
    assert (lam, mu) == (1.5, 1.0)                                   # lo sellado no cambia
    assert info["aplicado"] is False and info["factor_local"] > 1 and info["factor_visita"] < 1


def test_en_activo_si_se_aplica_y_sin_ajuste_o_sin_salto_no_toca_nada():
    from qf.publish import daily
    lam, mu, info = daily._aplicar_altitud(_ajuste_fijo(), {"m1": (2660.0, 30.0)}, "m1", 1.5, 1.0, "activo")
    assert lam > 1.5 and mu < 1.0 and info["aplicado"] is True
    assert daily._aplicar_altitud(None, {}, "m1", 1.5, 1.0, "activo") == (1.5, 1.0, None)
    lam0, mu0, info0 = daily._aplicar_altitud(_ajuste_fijo(), {"m2": (50.0, 50.0)}, "m2", 1.5, 1.0, "activo")
    assert (lam0, mu0) == pytest.approx((1.5, 1.0)) and info0["factor_local"] == pytest.approx(1.0)


def test_el_contexto_de_altitud_solo_se_carga_si_el_modo_lo_pide(monkeypatch):
    from dataclasses import replace
    from qf.config import settings
    from qf.publish import daily
    monkeypatch.setattr(daily.ajuste_altitud, "cargar_ultimo", lambda carpeta: _ajuste_fijo())
    monkeypatch.setattr(daily.contexto, "altitudes_de", lambda ids: pd.DataFrame(
        {"match_id": ids, "sede_m": [100.0] * len(ids), "hab_visita_m": [50.0] * len(ids)}))
    for modo, esperado in (("off", None), ("sombra", "fijo"), ("activo", "fijo"), ("raro", None)):
        monkeypatch.setattr(daily, "settings", replace(settings, ajuste_altitud_modo=modo))
        ajuste, alts = daily._contexto_altitud([{"match_id": "m1"}])
        assert (ajuste.oos_version if ajuste else None) == esperado, modo
    monkeypatch.setattr(daily.ajuste_altitud, "cargar_ultimo", lambda carpeta: None)       # sin artefacto: no-op
    monkeypatch.setattr(daily, "settings", replace(settings, ajuste_altitud_modo="sombra"))
    assert daily._contexto_altitud([{"match_id": "m1"}]) == (None, {})
    monkeypatch.setattr(daily.ajuste_altitud, "cargar_ultimo", lambda carpeta: (_ for _ in ()).throw(OSError("roto")))
    assert daily._contexto_altitud([{"match_id": "m1"}]) == (None, {})                      # un fallo no impide sellar
