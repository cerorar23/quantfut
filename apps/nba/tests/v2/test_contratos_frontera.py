from datetime import datetime, timedelta, UTC

import psycopg
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from nba.api import app as api
from nba.contratos.validar import ContratoIncumplido, validar_equipo, validar_jugador
from nba.v2 import equipo_jugadores, motor, motor_equipo, motor_jugadores, sellado
from nba.v2.sellado import PronosticoNuevo
from test_motor_props import con_horas


def test_el_validador_da_mensajes_cortos_y_acepta_lo_real():
    with pytest.raises(ContratoIncumplido) as e:
        validar_equipo({"p_local": 1.5})
    assert len(str(e.value)) <= 300 and "distribución de equipo" in str(e.value)
    with pytest.raises(ContratoIncumplido):
        validar_jugador({"pmf": [1.0], "media": 0, "p10": 0, "p50": 0, "p90": 0, "p_juega": 1, "minutos_esperados": 10})


def test_el_motor_no_sella_un_equipo_que_incumple_el_contrato(base_migrada, monkeypatch):
    db = base_migrada
    _, partidos, _, inicio = con_horas(db)
    pid = partidos[25][0]
    original = equipo_jugadores.pronosticar

    def roto(*args):
        version, esc, dist = original(*args)
        return version, esc, dict(dist, p_local=1.5)

    monkeypatch.setattr(equipo_jugadores, "pronosticar", roto)
    r = motor.ejecutar(db, inicio[pid] - timedelta(minutes=30))
    assert r["sellados"] == [] and len(r["errores"]) == 1 and "ContratoIncumplido" in r["errores"][0]["error"]
    assert db.execute("SELECT count(*) FROM nba.pronostico").fetchone()[0] == 0                # ni el equipo ni los jugadores de ese partido
    monkeypatch.setattr(equipo_jugadores, "pronosticar", original)
    assert motor.ejecutar(db, inicio[pid] - timedelta(minutes=25))["errores"] == []             # al corregirse, el siguiente cron sella


def test_un_jugador_invalido_se_descarta_y_se_avisa_sin_frenar_a_los_demas(base_migrada, monkeypatch):
    db = base_migrada
    _, partidos, _, inicio = con_horas(db)
    pid = partidos[25][0]
    original = motor_jugadores.pronosticar

    def con_uno_roto(pl, par):
        items = original(pl, par)
        items[0] = dict(items[0], distribucion=dict(items[0]["distribucion"], pmf=[0.5] + items[0]["distribucion"]["pmf"][1:]))
        return items

    monkeypatch.setattr(motor_jugadores, "pronosticar", con_uno_roto)
    r = motor.ejecutar(db, inicio[pid] - timedelta(minutes=30))
    assert len(r["errores"]) == 1 and "ContratoIncumplido: jugador" in r["errores"][0]["error"] and r["sellados"]
    sellados = db.execute("SELECT count(*) FROM nba.pronostico WHERE entidad_id IS NOT NULL").fetchone()[0]
    assert sellados == r["props"][0]["pronosticos"] > 20 and sellado.verificar_cadena(db) == sellados + 1


def test_la_api_no_sirve_un_sello_que_incumple_el_contrato(base_migrada_dsn):
    with psycopg.connect(base_migrada_dsn) as db:
        _, partidos, jugadores, inicio = con_horas(db)
        buena, mala = partidos[25][0], partidos[26][0]
        motor.ejecutar(db, inicio[buena] - timedelta(minutes=30))
        corte = datetime(2026, 1, 26, 12, tzinfo=UTC)
        sellado.sellar(db, PronosticoNuevo(mala, "equipo", motor_equipo.VERSION_MODELO, "d" * 64, corte, {}, {"p_local": 0.5}))
        db.commit()
    c = TestClient(api.crear_app(base_migrada_dsn))
    assert c.get(f"/nba/v1/partido/{buena}").status_code == 200
    r = c.get(f"/nba/v1/partido/{mala}")
    assert r.status_code == 502 and r.json()["detail"]["codigo"] == "datos_invalidos"
    assert c.get(f"/nba/v1/partido/{mala}/linea", params={"mercado": "total", "valor": 220.5}).status_code == 502
