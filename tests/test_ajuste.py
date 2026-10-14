"""El ajuste solo acepta un bloque si gana, sobre las mismas filas."""
import numpy as np
import pandas as pd
import pytest

from qf.model import ajuste as aj
from qf.model import lineup_challenger as lc


def marco(n=1600, seed=1, efecto=0.35):
    rng = np.random.default_rng(seed)
    senal, ruido = rng.normal(size=n), rng.normal(size=n)
    return pd.DataFrame({
        "match_id": [f"m{i}" for i in range(n)], "league_id": ["A", "B", "C"] * (n // 3) + ["A"] * (n % 3),
        "kickoff_utc": pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC"),
        "base_lam": 1.4, "base_mu": 1.1, "rho": -0.05, "s1": senal, "s2": ruido, "s3": rng.normal(size=n),
        "home_goals": rng.poisson(1.4 * np.exp(efecto * senal)), "away_goals": rng.poisson(1.1, n)})


@pytest.fixture(autouse=True)
def bloques_de_prueba(monkeypatch):
    monkeypatch.setattr(aj, "BLOQUES", {})
    aj.registrar(aj.Bloque("con_senal", ("s1",)))
    aj.registrar(aj.Bloque("ruido", ("s2", "s3")))


def test_un_bloque_con_senal_pasa_la_puerta():
    r = aj.comparar(marco(), [], ["con_senal"], rho=-0.05)
    assert r["ok"] is True and r["rps_after"] < r["rps_before"]
    assert r["bloques_antes"] == [] and r["bloques_despues"] == ["con_senal"]


def test_un_bloque_de_ruido_no_pasa():
    r = aj.comparar(marco(), [], ["ruido"], rho=-0.05)
    assert r["ok"] is False


def test_el_ruido_puro_casi_nunca_pasa_la_puerta():
    """Sin señal real, la puerta básica sola dejaba pasar ~20 %; con significancia casi nunca."""
    pasan = sum(aj.comparar(marco(seed=100 + s, efecto=0.0), [], ["ruido"], rho=-0.05)["ok"]
                for s in range(30))
    assert pasan <= 3


def test_la_comparacion_incremental_usa_las_mismas_filas():
    frame = marco()
    r = aj.comparar(frame, ["con_senal"], ["con_senal", "ruido"], rho=-0.05)
    assert abs(r["n_val"] - len(frame) * 0.30) <= 1
    assert r["ok"] is False                      # el ruido no mejora a la señal sola


def test_el_modelo_despues_es_el_del_challenger_de_siempre():
    """Mismo ajuste que lc.fit_and_validate; solo cambia la referencia (ver el test siguiente)."""
    frame = marco()
    r = aj.comparar(frame, [], ["con_senal"], rho=-0.05)
    _, ref = lc.fit_and_validate(frame, rho=-0.05, features=["s1"])
    for k in ("n_fit", "n_val", "rps_after", "log_loss_after", "ece_after"):
        assert r[k] == ref[k], k


def test_el_nivel_solo_no_cuenta_como_senal():
    """Una columna constante solo re-nivela las lambdas: no puede pasar la puerta."""
    aj.registrar(aj.Bloque("constante", ("c",)))
    frame = marco()
    frame["c"] = 0.0
    r = aj.comparar(frame, [], ["constante"], rho=-0.05)
    assert r["ok"] is False
    # contra las lambdas base crudas (puerta antigua) sí 'ganaba': eso era re-nivelar
    _, antiguo = lc.fit_and_validate(frame, rho=-0.05, features=["c"])
    assert antiguo["rps_after"] < antiguo["rps_before"]


def test_muestra_insuficiente_es_collecting_no_ok():
    r = aj.comparar(marco(n=300), [], ["con_senal"], rho=-0.05)
    assert r["ok"] is False and r["status"] == "collecting"


def test_columnas_ausentes_dan_un_error_claro():
    frame = marco().drop(columns=["s1"])
    with pytest.raises(ValueError, match="s1"):
        aj.comparar(frame, [], ["con_senal"], rho=-0.05)


def test_construir_acepta_solo_lo_que_gana_y_sin_bloques_deja_las_lambdas_base():
    a = aj.construir_ajuste(marco(), ["ruido", "con_senal"], rho=-0.05)
    assert a.bloques == ["con_senal"] and a.informe["ruido"]["ok"] is False
    vacio = aj.construir_ajuste(marco(), ["ruido"], rho=-0.05)
    frame = marco()
    lam, mu = vacio.aplicar(frame)
    assert vacio.bloques == [] and np.array_equal(lam, frame["base_lam"].to_numpy())
    assert np.array_equal(mu, frame["base_mu"].to_numpy())


def test_guardar_y_cargar_conserva_el_ajuste(tmp_path):
    a = aj.construir_ajuste(marco(), ["con_senal"], rho=-0.05)
    ruta = str(tmp_path / "ajuste_v.pkl")
    a.guardar(ruta)
    b = aj.Ajuste.cargar(ruta)
    assert b.bloques == a.bloques
    l1, m1 = a.aplicar(marco())
    l2, m2 = b.aplicar(marco())
    assert np.allclose(l1, l2) and np.allclose(m1, m2)
