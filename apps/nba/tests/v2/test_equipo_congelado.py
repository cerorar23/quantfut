"""Regresiones del modelo operativo: exposición, temporalidad, OT y prohibición de ajustar en inferencia."""
from datetime import date, datetime, UTC, timedelta
from types import SimpleNamespace
import json

import numpy as np
import pytest

from nba.v2 import estado_equipo, motor_equipo, nucleo
from nba.v2.duracion import minutos_partido, prorrogas


def instancia():
    return SimpleNamespace(local='BOS', visitante='NYK', fecha=date(2026, 1, 15),
        corte=datetime(2026, 1, 15, 12, tzinfo=UTC), partido_id=17,
        historia=((date(2026, 1, 14), 1, 'BOS', 'NYK', 110., 109.),))


def cambiar(monkeypatch, tmp_path, **campos):
    a = dict(estado_equipo.artefacto()[0]); a.update(campos)
    p = tmp_path / 'otro.json'; p.write_text(json.dumps(a), encoding='utf8')
    monkeypatch.setenv('NBA_ESTADO_EQUIPO_JSON', str(p))


@pytest.mark.parametrize('valor,esperado', [(48, 0), (240, 0), (53, 1), (265, 1), (58, 2), (290, 2), (35, None), (None, None)])
def test_duracion_y_suma_de_minutos_son_equivalentes(valor, esperado):
    assert prorrogas(valor) == esperado


def test_inferencia_no_entrena_y_proyecta_posesiones(monkeypatch, tmp_path):
    monkeypatch.setattr(nucleo, 'actualizar', lambda *a, **k: pytest.fail('entrenamiento en inferencia'))
    i = instancia(); e = estado_equipo.estimar(i)
    ritmo = dict(estado_equipo.artefacto()[0]['ritmo']); ritmo.update(BOS=110., NYK=110.)
    cambiar(monkeypatch, tmp_path, ritmo=ritmo)
    e2 = estado_equipo.estimar(i)
    assert e2.posesiones == 110. and e2.mu_local / e.mu_local == pytest.approx(1.1)
    esc, dist = motor_equipo.pronosticar(i)
    assert esc['posesiones_regulacion'] == 110.
    assert dist['tratamiento_ot'] == 'regulacion_mas_prorroga'


@pytest.mark.parametrize('campos,mensaje', [
    ({'conocido_en_utc':'2026-01-16T00:00:00+00:00'}, 'posterior'),
    ({'datos_hasta':'2026-01-15'}, 'día objetivo'),
    ({'vigencia_horas':1}, 'caducado'),
])
def test_no_acepta_estado_futuro_o_caducado(monkeypatch, tmp_path, campos, mensaje):
    cambiar(monkeypatch, tmp_path, **campos)
    with pytest.raises(ValueError, match=mensaje):
        estado_equipo.estimar(instancia())


def test_ot_suma_puntos_y_repite_periodos_sin_empate_final():
    m = nucleo.simular_con_ot(112., 110., 14., 18., 100., .07, n=200000, semilla=91)
    ot = m.prorrogas > 0
    assert ot.mean() == pytest.approx(.07, abs=.002)
    assert (m.regulacion[ot, 0] == m.regulacion[ot, 1]).all()
    assert (m.muestras[:, 0] != m.muestras[:, 1]).all()
    assert np.array_equal(m.muestras[~ot], m.regulacion[~ot])
    extras = (m.muestras - m.regulacion).sum(axis=1)
    assert extras[ot].mean() > 20 and extras[ot].mean() < 30
    assert (m.prorrogas > 1).any()


def test_ot_cero_no_anade_prorroga():
    m = nucleo.simular_con_ot(112., 110., 14., 18., 100., 0., n=1000)
    assert not m.prorrogas.any() and np.array_equal(m.muestras, m.regulacion)


def test_probabilidades_participacion_suman_uno():
    from nba.v2.contratos_apuesta import ProbabilidadesContrato
    r = ProbabilidadesContrato(.6, .1, .3).salida(.8)
    assert sum(r[k] for k in ('p_gana','p_push','p_pierde','p_void')) == pytest.approx(1.)
    assert r['p_mas'] == pytest.approx(2/3)


def test_cuantiles_y_masas_comparten_una_cdf_en_niveles_exactos():
    from nba.v2.salida_equipo import serializar
    from nba.contratos.validar import validar_equipo
    m = nucleo.simular_con_ot(112.,110.,14.,18.,100.,.06,n=100000,semilla=4)
    d = serializar(m,*m.muestras.mean(axis=0),np.arange(1,200)/200)
    validar_equipo(d)
    for nombre, ley in d['masas'].items():
        cdf=np.cumsum(ley['pmf']); soporte=np.array(ley['soporte'])
        for q,x in zip(np.arange(1,200)/200,d[nombre]):
            assert sum(p for k,p in zip(soporte,ley['pmf']) if k<x) <= q+1e-9
            assert sum(p for k,p in zip(soporte,ley['pmf']) if k<=x) >= q-1e-9


def test_impacto_no_validado_no_entra_en_la_prediccion(monkeypatch):
    from nba.v2 import equipo_jugadores, parametros
    monkeypatch.setattr(equipo_jugadores,'minutos_esperados_plantilla',lambda *a:pytest.fail('impacto sin validar'))
    imp=parametros.cargar_impacto()
    assert not imp.aprobado_regulacion
    v,esc,dist=equipo_jugadores.pronosticar(instancia(),None,imp,None)
    assert v==motor_equipo.version() and dist==motor_equipo.pronosticar(instancia())[1]
    assert 'impacto_bloqueado' in esc


def test_una_bandera_no_promueve_un_modelo_con_empeoramiento(tmp_path):
    from nba.v2 import parametros
    a=json.loads(parametros.RUTA_IMPACTO.read_text(encoding='utf8'))
    a.update(objetivo='margen_regulacion',aprobado_para_mezcla=True,
             validacion={'ganador':{'n':1235,'dif_ic95':[.001,.008]}},
             ot={'intercepto':-2.6,'abs_margen':-.04},conocido_en_utc='2025-12-01T00:00:00+00:00')
    p=tmp_path/'impacto.json';p.write_text(json.dumps(a),encoding='utf8')
    assert not parametros.cargar_impacto(p).aprobado_regulacion


def test_huella_de_estado_no_depende_de_los_saltos_de_linea(tmp_path,monkeypatch):
    a=dict(estado_equipo.artefacto()[0])
    p=tmp_path/'lineas.json'
    texto=json.dumps(a,indent=2)
    p.write_bytes(texto.encode());monkeypatch.setenv('NBA_ESTADO_EQUIPO_JSON',str(p))
    h=estado_equipo.artefacto()[1]
    p.write_bytes(texto.replace('\n','\r\n').encode())
    assert estado_equipo.artefacto()[1]==h
