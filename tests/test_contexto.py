"""Los bloques de contexto solo entran a la capa de ajuste si ganan fuera de muestra."""
import numpy as np
import pandas as pd
import pytest

from qf.model import ajuste as aj
from qf.model import contexto as cx


def test_log_descanso_topa_en_14_dias_y_no_inventa():
    assert cx.log_descanso(3) == pytest.approx(np.log1p(3))
    assert cx.log_descanso(40) == cx.log_descanso(14)
    assert cx.log_descanso(0) == 0.0                      # jugar dos días seguidos es un dato real
    for malo in (None, float("nan"), -2):
        assert np.isnan(cx.log_descanso(malo))


def test_relativo_de_bajas_va_de_0_a_1_y_sin_valor_del_once_es_nan():
    assert cx.relativo_bajas(0, 100e6) == 0.0
    assert cx.relativo_bajas(100e6, 100e6) == pytest.approx(0.5)
    assert cx.relativo_bajas(None, 100e6) == 0.0          # sin bajas registradas
    assert np.isnan(cx.relativo_bajas(10e6, None)) and np.isnan(cx.relativo_bajas(10e6, 0))


def test_altitud_solo_cuenta_lo_que_sube_sobre_lo_habitual_del_visitante():
    assert cx.altitud_features(2281, 30) == (pytest.approx(2.281), pytest.approx(2.251))
    assert cx.altitud_features(100, 2200)[1] == 0.0       # el visitante baja de altura: no hay ventaja extra
    sede, dif = cx.altitud_features(2281, None)
    assert sede == pytest.approx(2.281) and np.isnan(dif)
    assert all(np.isnan(v) for v in cx.altitud_features(None, 10))


def test_clima_cero_lluvia_es_un_dato_y_lo_ausente_es_nan():
    c = cx.clima_features(15.0, 60.0, 3.0, 0.0)
    assert c["lluvia_log"] == 0.0 and c["temp_desv2"] == 0.0
    ausente = cx.clima_features(None, None, None, None)
    assert all(np.isnan(v) for v in ausente.values())


def _marco(n=1600, seed=3, efecto=0.30):
    rng = np.random.default_rng(seed)
    columnas = {c: rng.normal(size=n) for cols in cx.BLOQUES_CONTEXTO.values() for c in cols}
    columnas["alt_sede_km"] = rng.normal(size=n)         # esta sí mueve los goles del local
    return pd.DataFrame({
        "match_id": [f"m{i}" for i in range(n)], "league_id": ["A", "B", "C"] * (n // 3) + ["A"] * (n % 3),
        "kickoff_utc": pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC"),
        "base_lam": 1.4, "base_mu": 1.1, "rho": -0.05, **columnas,
        "home_goals": rng.poisson(1.4 * np.exp(efecto * columnas["alt_sede_km"])), "away_goals": rng.poisson(1.1, n)})


def test_solo_el_bloque_con_senal_pasa_y_los_de_ruido_no(monkeypatch):
    monkeypatch.setattr(aj, "BLOQUES", {})
    res = cx.evaluar(_marco())
    assert res["individuales"]["altitud"]["ok"] is True
    for ruido in ("descanso", "clima", "bajas", "xi_valor"):
        assert res["individuales"][ruido]["ok"] is False, ruido
    assert res["aceptados"] == ["altitud"] and res["conjunto"]["ok"] is True
    r = cx.resumen(res)
    assert r["aceptados"] == ["altitud"] and r["altitud"]["cobertura"] == 1.0
    assert r["altitud"]["ligas_que_mejoran"] in {"2/3", "3/3"}


def test_sin_senal_en_ningun_bloque_no_entra_nada(monkeypatch):
    monkeypatch.setattr(aj, "BLOQUES", {})
    res = cx.evaluar(_marco(efecto=0.0, seed=11))
    assert res["aceptados"] == [] and res["conjunto"] is None


def test_con_pocos_partidos_no_se_decide_nada(monkeypatch):
    monkeypatch.setattr(aj, "BLOQUES", {})
    res = cx.evaluar(_marco(n=300))
    assert res["aceptados"] == [] and "Muestra insuficiente" in res["individuales"]["clima"]["reason"]
