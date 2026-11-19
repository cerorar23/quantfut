import json

import pytest

from nba.v2 import parametros, props


def _copia(tmp_path, **cambios):
    a = json.loads(parametros.RUTA_PROPS.read_text(encoding="utf8"))
    a.update(cambios)
    ruta = tmp_path / "props.json"
    ruta.write_text(json.dumps(a), encoding="utf8")
    return ruta


def test_formato_1_conserva_una_alfa_por_estadistica(tmp_path):
    par = parametros.cargar_props(_copia(tmp_path, formato=1))
    assert all(isinstance(a, float) for a in par.alfa)


def test_formato_2_usa_la_alfa_de_cada_nivel_de_rol(tmp_path):
    por_nivel = {e: [0.6, 0.3, 0.19, 0.14, 0.1, 0.07] for e in props.ESTADISTICAS}
    par = parametros.cargar_props(_copia(tmp_path, formato=2, alfa_por_nivel=por_nivel))
    i = par.estadisticas.index("puntos")
    assert props.alfa_para(par.alfa[i], 36.0) == pytest.approx(0.07)
    assert props.alfa_para(par.alfa[i], 12.0) == pytest.approx(0.3)


def test_formato_2_parcial_deja_la_alfa_global_en_las_demas(tmp_path):
    par = parametros.cargar_props(_copia(tmp_path, formato=2, alfa_por_nivel={"puntos": [0.6, 0.3, 0.19, 0.14, 0.1, 0.07]}))
    i, r = par.estadisticas.index("puntos"), par.estadisticas.index("rebotes")
    assert isinstance(par.alfa[i], tuple) and isinstance(par.alfa[r], float)


def test_formato_2_con_niveles_que_no_cuadran_se_rechaza(tmp_path):
    with pytest.raises(ValueError):
        parametros.cargar_props(_copia(tmp_path, formato=2, alfa_por_nivel={e: [0.2, 0.1] for e in props.ESTADISTICAS}))
