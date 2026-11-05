from datetime import datetime, UTC
import json
from pathlib import Path
import re

import numpy as np
import psycopg
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from nba.api import app as api
from nba.v2 import motor_equipo, pit, sellado
from nba.v2.sellado import PronosticoNuevo
from test_sellado_pit import liga

ESTATICOS = Path(api.__file__).parent / "static"


@pytest.fixture
def cliente(base_migrada_dsn, monkeypatch):
    with psycopg.connect(base_migrada_dsn) as db:
        ids, partidos = liga(db, 25)
        db.commit()
        sellados = {}
        for pid, fecha, _, _ in partidos[15:18]:
            corte = datetime(fecha.year, fecha.month, fecha.day, 12, tzinfo=UTC)
            inst = pit.instantanea(db, pid, corte)
            esc, dist = motor_equipo.pronosticar(inst)
            sellados[pid] = sellado.sellar(db, PronosticoNuevo(pid, "equipo", motor_equipo.VERSION_MODELO, inst.version_datos, corte, esc, dist))
        db.commit()
    monkeypatch.setenv('NBA_VERSION_MODELO_ACTIVA', motor_equipo.VERSION_MODELO)
    return TestClient(api.crear_app(base_migrada_dsn)), partidos, sellados


def test_prob_mas_de_con_cuantiles_normales():
    from statistics import NormalDist
    q = [NormalDist(0, 1).inv_cdf(i * 0.005) for i in range(1, 200)]
    p0, extremo = api.prob_mas_de(q, 0.0)
    assert p0 == pytest.approx(0.5, abs=0.01) and not extremo
    assert api.prob_mas_de(q, 1.0)[0] == pytest.approx(0.1587, abs=0.01)
    assert api.prob_mas_de(q, 9.0) == (0.005, True) and api.prob_mas_de(q, -9.0) == (0.995, True)
    assert api.prob_mas_de([5.0] * 199, 5.0)[1] is True                       # distribución degenerada: nunca NaN


def test_cartelera_muestra_el_sello_o_la_espera(cliente):
    c, partidos, sellados = cliente
    r = c.get("/nba/v1/cartelera", params={"fecha": partidos[15][1].isoformat()})
    assert r.status_code == 200
    juego = r.json()["partidos"][0]
    assert juego["id"] == partidos[15][0] and juego["pronostico"]["hash"] == sellados[partidos[15][0]]
    assert 0 < juego["pronostico"]["p_local"] < 1 and juego["resultado"]["local"] is not None
    sin = c.get("/nba/v1/cartelera", params={"fecha": partidos[3][1].isoformat()}).json()["partidos"][0]
    assert sin["pronostico"] is None
    assert c.get("/nba/v1/cartelera", params={"fecha": "2030-01-01"}).json()["partidos"] == []
    assert c.get("/nba/v1/cartelera", params={"fecha": "no-es-fecha"}).status_code == 422


def test_partido_y_linea_son_coherentes(cliente):
    c, partidos, _ = cliente
    pid = partidos[16][0]
    d = c.get(f"/nba/v1/partido/{pid}").json()
    assert len(d["distribuciones"]["margen"]) == 199 and d["distribuciones"]["paso_cuantil"] == 0.005
    ps = [c.get(f"/nba/v1/partido/{pid}/linea", params={"mercado": "total", "valor": v}).json() for v in (200.5, 220.5, 240.5)]
    assert ps[0]["p_mas"] > ps[1]["p_mas"] > ps[2]["p_mas"]
    assert all(x["p_mas"] + x["p_menos"] == pytest.approx(1.0, abs=1e-3) for x in ps)
    fuera = c.get(f"/nba/v1/partido/{pid}/linea", params={"mercado": "total", "valor": 999}).json()
    assert fuera["extremo"] is True and fuera["p_mas"] == 0.0 and fuera['aproximada'] is False
    assert c.get(f"/nba/v1/partido/{pid}/linea", params={"mercado": "otro", "valor": 1}).json()["detail"]["codigo"] == "mercado_desconocido"
    assert c.get("/nba/v1/partido/999999").json()["detail"]["codigo"] == "partido_inexistente"
    sin = c.get(f"/nba/v1/partido/{partidos[3][0]}/linea", params={"mercado": "total", "valor": 220.5})
    assert sin.status_code == 404 and sin.json()["detail"]["codigo"] == "sin_pronostico"


def test_jugador_sin_pronostico_devuelve_codigo(cliente):
    c, partidos, _ = cliente
    r = c.get(f"/nba/v1/partido/{partidos[15][0]}/jugador/1")
    assert r.status_code == 404 and r.json()["detail"]["codigo"] == "sin_pronostico_jugador"


def test_verificacion_publica_del_sello(cliente):
    c, partidos, sellados = cliente
    h = sellados[partidos[16][0]]
    v = c.get(f"/nba/v1/sello/{h}", params={"cadena": "true"}).json()
    assert v["valido"] and v["contenido_integro"] and v["enlazado"] and v["posicion"] == 2 and v["cadena_verificada"] == 3
    assert c.get("/nba/v1/sello/" + "0" * 64).json()["detail"]["codigo"] == "sello_inexistente"
    assert c.get("/nba/v1/sello/xyz").status_code == 422


def test_calibracion_cuenta_lo_sellado_y_calcula_brier(cliente):
    c, _, _ = cliente
    d = c.get("/nba/v1/calibracion").json()
    assert d["historico"]["equipo"]["modelo"]["brier_ganador"] > 0
    p = d["prospectivo"]
    assert p["sellados"] == 3 and p["con_resultado"] == 3 and 0 <= p["brier_ganador"] <= 1
    assert sum(b["n"] for b in p["fiabilidad"]) == 3


def test_calibracion_identifica_el_artefacto_activo_sin_variable_manual(cliente, monkeypatch):
    c,_,_=cliente
    monkeypatch.delenv('NBA_VERSION_MODELO_ACTIVA',raising=False)
    d=c.get('/nba/v1/calibracion').json()
    assert d['prospectivo']['version_modelo']==motor_equipo.version()
    assert d['prospectivo']['sellados']==0  # los tres sellos fixture llevan otra versión explícita
    assert d['por_version'][motor_equipo.VERSION_MODELO]['con_resultado']==3


def test_la_web_estatica_se_sirve(cliente):
    c, _, _ = cliente
    assert c.get("/nba/v2/").status_code == 200 and "app.js" in c.get("/nba/v2/").text
    assert c.get("/nba/v2/i18n.json").status_code == 200


def test_traducciones_completas_y_sin_textos_fijos():
    i18n = json.loads((ESTATICOS / "i18n.json").read_text(encoding="utf-8"))
    assert set(i18n) == {"es", "en", "pt", "fr", "it", "de"}
    claves = set(i18n["es"])
    for lang, tabla in i18n.items():
        assert set(tabla) == claves, (lang, set(tabla) ^ claves)
        assert all(v.strip() for v in tabla.values()), lang
    usadas = set(re.findall(r'\bt\("([a-z_0-9]+)"\)', (ESTATICOS / "app.js").read_text(encoding="utf-8")))
    assert usadas - claves == set()
    codigos = set(re.findall(r'"codigo": "([a-z_]+)"', Path(api.__file__).read_text(encoding="utf-8")))
    assert {f"err_{k}" for k in codigos} <= claves                           # cada error del servidor tiene texto en los 6 idiomas
    assert {f"m_{m}" for m in api.MERCADOS_LINEA} <= claves and {"tab_equipo", "tab_jugador", "tab_especiales"} <= claves


def test_endpoints_de_jugador_con_props_sellados(base_migrada_dsn):
    from datetime import timedelta
    from nba.v2 import motor
    from test_motor_props import con_horas
    with psycopg.connect(base_migrada_dsn) as db:
        ids, partidos, jugadores, inicio = con_horas(db)
        pid = partidos[25][0]
        motor.ejecutar(db, inicio[pid] - timedelta(minutes=30))
        db.commit()
    c = TestClient(api.crear_app(base_migrada_dsn))
    lista = c.get(f"/nba/v1/partido/{pid}/jugadores").json()["jugadores"]
    assert len(lista) >= 10 and lista == sorted(lista, key=lambda j: -j["minutos_esperados"])
    j = lista[0]
    assert set(j["mercados"]) == {"puntos", "rebotes", "asistencias", "triples"} and j["nombre"] and j["lado"] in ("local", "visitante") and 0 < j["p_juega"] <= 1
    ps = [c.get(f"/nba/v1/partido/{pid}/jugador/{j['id']}/linea", params={"mercado": "puntos", "valor": v}).json() for v in (5.5, 15.5, 30.5)]
    assert ps[0]["p_mas"] > ps[1]["p_mas"] > ps[2]["p_mas"] and all(x["p_mas"] + x["p_menos"] == pytest.approx(1.0, abs=1e-3) for x in ps)
    assert c.get(f"/nba/v1/partido/{pid}/jugador/{j['id']}").json()["mercados"]["jugador:puntos"]["distribucion"]["pmf"]
    assert c.get(f"/nba/v1/partido/{pid}/jugador/{j['id']}/linea", params={"mercado": "otro", "valor": 1}).status_code == 422
    assert c.get(f"/nba/v1/partido/{pid}/jugador/99999/linea", params={"mercado": "puntos", "valor": 1}).json()["detail"]["codigo"] == "sin_pronostico_jugador"
    assert c.get(f"/nba/v1/partido/{partidos[3][0]}/jugadores").json()["jugadores"] == []
