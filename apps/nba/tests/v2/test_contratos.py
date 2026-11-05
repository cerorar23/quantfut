from datetime import datetime, timedelta, UTC
import json
import math

import pytest
from pydantic import ValidationError

from nba.contratos import (DistribucionEquipo, DistribucionJugador, EntradaMonteCarlo, EstimacionJugador, ParametrosConteo, ParametrosMarcador,
                           SalidaMonteCarlo, SalidaPasoA, SalidaPasoB)
from nba.v2 import motor, motor_equipo, motor_jugadores, parametros, pit
from nba.v2.plantilla_pit import plantilla
from test_motor_props import con_horas

CORTE = datetime(2026, 11, 3, 1, 0, tzinfo=UTC)
HASH = "a" * 64


def jugador(**cambios):
    base = dict(jugador_id=7, nombre="Jugador Siete", equipo="BOS", estado=None, p_juega=0.9, minutos=dict(p10=20.0, p50=30.0, p90=38.0),
                tasa_por_minuto=dict(puntos=0.5, rebotes=0.2, asistencias=0.1, triples=0.05), partidos_en_historia=30)
    base.update(cambios)
    return base


def paso_a(**cambios):
    base = dict(partido_id=1, corte=CORTE, version_datos=HASH, local="BOS", visitante="NYK", margen_equipo=3.0, margen_jugadores=2.0, total_equipo=224.0,
                descanso_dias=dict(local=2, visitante=1), jugadores=[jugador()])
    base.update(cambios)
    return base


def marcador(**cambios):
    base = dict(mu_local=113.0, mu_visitante=110.0, sigma_margen=14.0, sigma_total=18.4, margen_equipo=3.0, margen_jugadores=2.0)
    base.update(cambios)
    return base


def conteo(**cambios):
    base = dict(jugador_id=7, estadistica="puntos", tasa_por_minuto=0.5, alfa=0.22, minutos_muestras=[25.0, 28.0, 30.0, 32.0, 35.0], techo=70, p_juega=0.9)
    base.update(cambios)
    return base


def cuantiles(centro, paso=0.1):
    return [centro + (i - 99) * paso for i in range(199)]


def dist_equipo(**cambios):
    base = dict(p_local=0.6, mu=[113.0, 110.0], paso_cuantil=0.005, margen=cuantiles(3.0, 0.2), total=cuantiles(224.0, 0.3),
                puntos_local=cuantiles(113.0, 0.2), puntos_visitante=cuantiles(110.0, 0.2))
    base.update(cambios)
    return base


def dist_jugador(**cambios):
    base = dict(pmf=[0.1, 0.2, 0.4, 0.2, 0.05, 0.05], media=2.05, p10=0, p50=2, p90=3, p_juega=0.9, minutos_esperados=30.0)
    base.update(cambios)
    return base


def test_la_cadena_a_b_c_acepta_datos_validos_y_viaja_en_json():
    a = SalidaPasoA(**paso_a())
    b = SalidaPasoB(partido_id=a.partido_id, corte=a.corte, version_datos=a.version_datos, version_modelo="equipo-2.1", marcador=marcador(), jugadores=[conteo()])
    entrada = EntradaMonteCarlo(parametros=b, n_simulaciones=20_000, semilla=a.partido_id)
    salida = SalidaMonteCarlo(partido_id=1, corte=CORTE, version_datos=HASH, version_modelo="equipo-2.1", n_simulaciones=entrada.n_simulaciones,
                              equipo=dist_equipo(), jugadores={"7:puntos": dist_jugador()})
    for objeto in (a, b, entrada, salida):
        assert type(objeto).model_validate_json(objeto.model_dump_json()) == objeto


@pytest.mark.parametrize("cambios", [
    dict(margen_equipo=math.nan), dict(margen_equipo=math.inf), dict(margen_equipo=75.0), dict(total_equipo=20.0), dict(local="NYK"),
    dict(version_datos="xyz"), dict(corte=datetime(2026, 11, 3, 1, 0)), dict(partido_id=0), dict(extra=1), dict(descanso_dias=dict(local=1)),
    dict(jugadores=[jugador(p_juega=1.5)]), dict(jugadores=[jugador(p_juega=-0.1)]), dict(jugadores=[jugador(minutos=dict(p10=30.0, p50=20.0, p90=38.0))]),
    dict(jugadores=[jugador(minutos=dict(p10=10.0, p50=20.0, p90=61.0))]), dict(jugadores=[jugador(partidos_en_historia=4)]),
    dict(jugadores=[jugador(tasa_por_minuto=dict(puntos=-0.1, rebotes=0.2, asistencias=0.1, triples=0.0))]),
    dict(jugadores=[jugador(tasa_por_minuto=dict(puntos=0.5))]), dict(jugadores=[jugador(equipo="boston")]),
])
def test_paso_a_rechaza_lo_absurdo(cambios):
    with pytest.raises(ValidationError):
        SalidaPasoA(**paso_a(**cambios))


def test_extremos_validos_de_paso_a_se_aceptan():
    SalidaPasoA(**paso_a(margen_jugadores=None, jugadores=[], margen_equipo=-60.0))                  # sin plantilla: se admite y se dice
    SalidaPasoA(**paso_a(jugadores=[jugador(p_juega=0.0), jugador(jugador_id=8, p_juega=1.0, minutos=dict(p10=0.0, p50=0.0, p90=0.0))]))


@pytest.mark.parametrize("cambios", [dict(sigma_margen=0.0), dict(sigma_total=100.0), dict(mu_local=-5.0), dict(mu_visitante=300.0), dict(margen_equipo=math.nan)])
def test_marcador_rechaza_parametros_imposibles(cambios):
    with pytest.raises(ValidationError):
        ParametrosMarcador(**marcador(**cambios))


@pytest.mark.parametrize("cambios", [dict(alfa=0.0), dict(alfa=9.0), dict(tasa_por_minuto=-1.0), dict(minutos_muestras=[30.0]), dict(minutos_muestras=[70.0] * 5),
                                     dict(techo=2), dict(estadistica="robos"), dict(p_juega=2.0)])
def test_conteo_rechaza_parametros_imposibles(cambios):
    with pytest.raises(ValidationError):
        ParametrosConteo(**conteo(**cambios))


def test_paso_b_rechaza_un_jugador_y_estadistica_repetidos():
    with pytest.raises(ValidationError):
        SalidaPasoB(partido_id=1, corte=CORTE, version_datos=HASH, version_modelo="equipo-2.1", marcador=marcador(), jugadores=[conteo(), conteo()])


@pytest.mark.parametrize("n", [0, 999, 2_000_000])
def test_monte_carlo_exige_un_numero_razonable_de_simulaciones(n):
    b = SalidaPasoB(partido_id=1, corte=CORTE, version_datos=HASH, version_modelo="equipo-2.1", marcador=marcador(), jugadores=[])
    with pytest.raises(ValidationError):
        EntradaMonteCarlo(parametros=b, n_simulaciones=n, semilla=1)
    with pytest.raises(ValidationError):
        EntradaMonteCarlo(parametros=b, n_simulaciones=20_000, semilla=-1)


@pytest.mark.parametrize("cambios", [dict(p_local=1.2), dict(margen=cuantiles(3.0)[::-1]), dict(total=cuantiles(224.0)[:-1]), dict(paso_cuantil=0.01),
                                     dict(mu=[1.0]), dict(puntos_local=cuantiles(-50.0, 0.05)), dict(margen=[math.nan] * 199)])
def test_distribucion_de_equipo_rechaza_lo_incoherente(cambios):
    with pytest.raises(ValidationError):
        DistribucionEquipo(**dist_equipo(**cambios))


@pytest.mark.parametrize("cambios", [dict(pmf=[0.5, 0.2, 0.1, 0.1, 0.05, 0.0]), dict(pmf=[-0.1, 0.5, 0.2, 0.2, 0.1, 0.1]), dict(p10=3, p50=2), dict(p90=9),
                                     dict(p_juega=1.5), dict(minutos_esperados=80.0), dict(media=-1.0)])
def test_distribucion_de_jugador_rechaza_lo_incoherente(cambios):
    with pytest.raises(ValidationError):
        DistribucionJugador(**dist_jugador(**cambios))


def test_lo_que_el_motor_real_produce_cumple_los_contratos(base_migrada):
    db = base_migrada
    ids, partidos, jugadores, inicio = con_horas(db)
    pid, fecha = partidos[25][0], partidos[25][1]
    corte = datetime(fecha.year, fecha.month, fecha.day, 12, tzinfo=UTC)
    inst = pit.instantanea(db, pid, corte)
    _, dist = motor_equipo.pronosticar(inst)
    DistribucionEquipo.model_validate(dist)
    items = motor_jugadores.pronosticar(plantilla(db, inst), parametros.cargar_props())
    assert items
    for x in items:
        DistribucionJugador.model_validate(x["distribucion"])
    # y lo que ya quedó sellado en la base
    motor.ejecutar(db, inicio[pid] - timedelta(minutes=30))
    sellados = db.execute("SELECT mercado, distribucion FROM nba.pronostico").fetchall()
    assert len(sellados) > 10
    for mercado, d in sellados:
        (DistribucionEquipo if mercado == "equipo" else DistribucionJugador).model_validate(json.loads(json.dumps(d)))
