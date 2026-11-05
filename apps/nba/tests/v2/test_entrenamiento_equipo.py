from datetime import date, timedelta
from pathlib import Path

import pytest


@pytest.fixture
def entrenador(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / 'ops'))
    import entrenar_equipo
    return entrenar_equipo


def test_predicciones_del_dia_preceden_a_todos_sus_resultados(entrenador):
    juegos=[]
    for i in range(8):
        juegos.append(dict(pid=i,fecha=(date(2026,1,1)+timedelta(days=i)).isoformat(),temporada='2025-26',
            local='BOS',visit='NYK',pl=110.,pv=105.,posesiones=100.,duracion=48.,ot=0))
    juegos.append(dict(juegos[-1],pid=99,pl=150.,pv=80.))
    antes=entrenador.recorrer(juegos)[-1]
    cambiados=[dict(g,pl=200.) if g['pid']==7 else dict(g) for g in juegos]
    despues=entrenador.recorrer(cambiados)[-1]
    assert [(g['pid'],g['mu_l'],g['mu_v']) for g in antes] == [(g['pid'],g['mu_l'],g['mu_v']) for g in despues]


@pytest.mark.parametrize('fecha,recibido', [('2026-11-04','2026-11-03T10:00:00+00:00'),
                                          ('2026-11-02','2026-11-05T10:00:00+00:00')])
def test_entrenamiento_rechaza_eventos_y_recepciones_futuros(entrenador,fecha,recibido):
    m=dict(minutos=48.,posesiones=100.,puntos=110.)
    obj=dict(captured_at_utc='2026-11-04T10:00:00+00:00',
             rows=[[1,fecha,'2026-27','BOS','NYK',m,dict(m,puntos=109.),recibido,recibido]])
    with pytest.raises(ValueError):
        entrenador.preparar(obj)


def test_conflictos_de_identidad_no_se_promedian_como_si_fueran_dos_partidos(entrenador):
    m=dict(minutos=48.,posesiones=100.,puntos=110.)
    fila=[1,'2026-11-02','2026-27','BOS','NYK',m,dict(m,puntos=109.),
          '2026-11-03T10:00:00+00:00','2026-11-03T10:00:00+00:00']
    otra=list(fila); otra[0]=2; otra[5]=dict(m,puntos=150.)
    juegos,descartes=entrenador.preparar(dict(captured_at_utc='2026-11-04T10:00:00+00:00',rows=[fila,otra]))
    assert juegos == [] and descartes['conflicto_identidad'] == 1


def test_minutos_objetivo_no_entran_en_la_proyeccion_hibrida(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]/'ops'))
    from entrenar_hibrido import registrar,predecir
    from nba.v2.plantilla import Impacto
    juegos=[];filas=[]
    for i in range(7):
        juegos.append(dict(pid=i,fecha=(date(2026,1,1)+timedelta(days=i)).isoformat(),temporada='2025-26',
            local='BOS',visit='NYK',pl=110.,pv=105.,posesiones=100.,duracion=48.,ot=0,mu_l=112.,mu_v=110.))
        for eq,base in (('BOS',100),('NYK',200)):
            filas.extend([[i,base+j,eq,240/9,0.,'2026-01-10T00:00:00+00:00'] for j in range(9)])
    a,_=registrar(juegos,filas)
    modificadas=[list(r) for r in filas]
    for r in modificadas:
        if r[0]==6:r[3]=1.
    b,_=registrar(juegos,modificadas)
    imp=Impacto(beta={100:5.},c_margen=2.)
    assert predecir(juegos[-1],a[6],imp,{0:.84,1:.84,2:.84}) == predecir(juegos[-1],b[6],imp,{0:.84,1:.84,2:.84})
