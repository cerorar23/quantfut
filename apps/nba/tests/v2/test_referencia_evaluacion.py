import numpy as np
import pytest

from nba.v2 import evaluacion, props, referencia


@pytest.mark.parametrize("metodo", referencia.METODOS)
def test_quitar_margen_suma_uno_y_mantiene_el_orden(metodo):
    p = referencia.quitar_margen([1.50, 2.80], metodo)
    assert sum(p) == pytest.approx(1.0) and p[0] > p[1] > 0
    assert referencia.quitar_margen([1.90, 1.90], metodo) == pytest.approx([0.5, 0.5])
    tres = referencia.quitar_margen([2.0, 3.4, 3.8], metodo)
    assert sum(tres) == pytest.approx(1.0) and tres[0] > tres[1] > tres[2]


def test_potencia_y_shin_cargan_el_margen_en_el_improbable():
    cuotas = [1.30, 4.0]
    prop, pot, shin = (referencia.quitar_margen(cuotas, m) for m in referencia.METODOS)
    assert pot[1] < prop[1] and shin[1] < prop[1]                 # sesgo favorito-improbable (ficha 22)


def test_cuotas_invalidas_se_rechazan_y_la_publicacion_se_acota():
    for malas in ([1.9], [1.0, 2.0], [0.8, 3.0]):
        with pytest.raises(ValueError):
            referencia.quitar_margen(malas)
    assert referencia.limitar_publicacion(0.97) == 0.90 and referencia.limitar_publicacion(0.02) == 0.10
    assert referencia.limitar_publicacion(0.55) == 0.55


def test_informe_binario_de_probabilidades_calibradas():
    rng = np.random.default_rng(0)
    p = rng.uniform(0.2, 0.8, 20000)
    y = (rng.random(20000) < p).astype(float)
    r = evaluacion.informe_binario(p, y, base=np.full(20000, y.mean()), estratos={"mitad": np.arange(20000) % 2},
                                  grupos=np.arange(20000))  # las Bernoulli de esta simulación son independientes
    assert r["pendiente"] == pytest.approx(1.0, abs=0.1) and r["intercepto"] == pytest.approx(0.0, abs=0.06)
    assert r["dif_brier"] < 0 and r["dif_ic95"][1] < 0                  # mejor que la base constante, con intervalo
    assert set(r["estratos"]["mitad"]) == {"0", "1"} and r["estratos"]["mitad"]["0"]["n"] == 10000


def test_informe_conteo_con_distribucion_correcta():
    rng = np.random.default_rng(1)
    mu, alfa = np.full(5000, 8.0), 0.2
    y = rng.negative_binomial(1 / alfa, (1 / alfa) / (1 / alfa + mu)).astype(float)
    pmf = props.pmf_mezcla(mu[:1], np.full((1, 1), 1.0) * 8.0 / mu[0], alfa, 60)
    r = evaluacion.informe_conteo(np.repeat(pmf, len(y), axis=0), y, base_media=np.full(len(y), 8.0) + rng.normal(0, 2, len(y)))
    assert r["cobertura80"] == pytest.approx(0.8, abs=0.02) and r["cobertura50"] == pytest.approx(0.5, abs=0.02)
    assert r["MASE"] < 1.0
    assert set(r["mincer_zarnowitz"]) == {"pendiente", "intercepto"}
