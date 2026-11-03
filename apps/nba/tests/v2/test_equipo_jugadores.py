from datetime import datetime, timedelta, UTC

import pytest

from nba.v2 import equipo_jugadores, motor, motor_equipo, parametros, pit
from nba.v2.parametros import ParametrosImpacto
from nba.v2.plantilla import Impacto
from nba.v2.plantilla_pit import plantilla
from test_motor_props import con_horas
from test_plantilla_pit import con_jugadores


def impacto_de_prueba(jugadores, estrella, valor=6.0):
    """Impacto con un solo jugador distinto de cero: sirve para comprobar la aritmética de la mezcla."""
    beta = {j: 0.0 for lista in jugadores.values() for j in lista}
    beta[estrella] = valor
    return ParametrosImpacto(Impacto(beta=beta, tau={}, c_margen=2.0, d_margen=0.0, c_total=224.0, d_total=0.0), 14.0, "2026-04-12", "abc123def456")


def test_el_margen_es_la_media_de_equipo_y_jugadores_y_el_total_no_cambia(base_migrada):
    db = base_migrada
    ids, partidos, jugadores = con_jugadores(db)
    pid, fecha, a, b = partidos[25]
    corte = datetime(fecha.year, fecha.month, fecha.day, 12, tzinfo=UTC)
    inst = pit.instantanea(db, pid, corte)
    pl = plantilla(db, inst)
    par = parametros.cargar_props()
    imp = impacto_de_prueba(jugadores, jugadores[inst.local][0])
    version, esc, dist = equipo_jugadores.pronosticar(inst, pl, imp, par)
    _, dist_equipo = motor_equipo.pronosticar(inst)
    assert version.startswith("equipo-2.1") and "impacto=abc123def456" in version
    mu_l, mu_v = dist["mu"]
    base_l, base_v = dist_equipo["mu"]
    assert mu_l + mu_v == pytest.approx(base_l + base_v, abs=1e-3)                          # el total no se toca
    assert mu_l - mu_v == pytest.approx((esc["margen_equipo"] + esc["margen_jugadores"]) / 2, abs=1e-3)
    assert esc["margen_equipo"] == pytest.approx(base_l - base_v, abs=1e-3)
    assert esc["jugadores"]["local"] >= 8 and esc["jugadores"]["visitante"] >= 8
    # sin jugadores distintos de cero, el margen de jugadores es solo el intercepto y la localía
    sin = impacto_de_prueba(jugadores, jugadores[inst.local][0], valor=0.0)
    _, esc0, _ = equipo_jugadores.pronosticar(inst, pl, sin, par)
    assert esc0["margen_jugadores"] == pytest.approx(2.0, abs=1e-6) and esc["margen_jugadores"] > esc0["margen_jugadores"]
    # determinista
    assert equipo_jugadores.pronosticar(inst, pl, imp, par) == (version, esc, dist)


def test_sin_plantilla_suficiente_vuelve_al_nucleo_2_0_y_lo_dice(base_migrada):
    db = base_migrada
    ids, partidos, jugadores = con_jugadores(db, n=8)
    pid, fecha, a, b = partidos[7]
    inst = pit.instantanea(db, pid, datetime(fecha.year, fecha.month, fecha.day, 12, tzinfo=UTC))
    version, esc, dist = equipo_jugadores.pronosticar(inst, plantilla(db, inst), impacto_de_prueba(jugadores, jugadores["BOS"][0]), parametros.cargar_props())
    assert version == motor_equipo.VERSION_MODELO and dist == motor_equipo.pronosticar(inst)[1]


def test_el_artefacto_de_impacto_real_se_carga_con_huella_estable():
    imp = parametros.cargar_impacto()
    assert len(imp.impacto.beta) > 500 and 12 < imp.sigma_margen < 16 and len(imp.version) == 12
    assert parametros.cargar_impacto().version == imp.version


def test_el_motor_sella_el_equipo_con_jugadores_y_la_api_lo_muestra(base_migrada):
    db = base_migrada
    ids, partidos, jugadores, inicio = con_horas(db)
    pid = partidos[25][0]
    r = motor.ejecutar(db, inicio[pid] - timedelta(minutes=30))
    assert r["errores"] == [] and r["sellados"][0]["version"] == "equipo-2.1"
    fila = db.execute("SELECT version_modelo, escenarios FROM nba.pronostico WHERE mercado = 'equipo'").fetchone()
    assert fila[0] == motor.VERSION_EQUIPO_JUGADORES and fila[1]["jugadores"]["local"] >= 8
    # un partido ya sellado con otra versión de equipo no se vuelve a sellar
    assert motor.ejecutar(db, inicio[pid] - timedelta(minutes=10))["sellados"] == []
