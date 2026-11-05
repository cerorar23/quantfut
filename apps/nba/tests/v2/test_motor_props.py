from datetime import datetime, timedelta, UTC
from pathlib import Path

import pytest

from nba.v2 import alertas, motor, sellado
from nba.v2.carga import DatoNuevo, guardar_datos
from test_plantilla_pit import con_jugadores


def con_horas(db):
    reloj = datetime.now(UTC)
    fecha_et = reloj.astimezone(motor.ET).date()
    ids, partidos, jugadores = con_jugadores(db, fecha_base=fecha_et - timedelta(days=25))
    inicio = {}
    for pid, fecha, a, _ in partidos:
        t = reloj + timedelta(minutes=30, days=(fecha-fecha_et).days)
        inicio[pid] = t
        guardar_datos(db, [DatoNuevo(partido_id=pid, entidad_id=ids[a], metrica="inicio_programado_utc", fase="pre", fuente="nba_oficial",
                                     recibido_en=datetime(2025, 12, 1, tzinfo=UTC), valor=t.timestamp())])
    db.commit()
    return ids, partidos, jugadores, inicio


def test_sella_equipo_y_props_en_una_cadena_verificable_e_idempotente(base_migrada):
    db = base_migrada
    _, partidos, jugadores, inicio = con_horas(db)
    pid = partidos[25][0]
    ahora = inicio[pid] - timedelta(minutes=30)
    r = motor.ejecutar(db, ahora)
    assert r["errores"] == [] and len(r["sellados"]) == 1 and r["props"][0]["partido"] == pid and r["props"][0]["jugadores"] >= 10
    n = db.execute("SELECT count(*) FROM nba.pronostico").fetchone()[0]
    assert n == 1 + r["props"][0]["pronosticos"] and sellado.verificar_cadena(db) == n
    mercados = {m for (m,) in db.execute("SELECT DISTINCT mercado FROM nba.pronostico WHERE entidad_id IS NOT NULL").fetchall()}
    assert mercados == {"jugador:puntos", "jugador:rebotes", "jugador:asistencias", "jugador:triples"}
    assert db.execute("SELECT count(DISTINCT objetivo_en) FROM nba.pronostico").fetchone()[0] == 1       # un solo corte para todo el partido
    b = motor.ejecutar(db, ahora + timedelta(minutes=10))
    assert b["sellados"] == [] and b["props"] == [] and db.execute("SELECT count(*) FROM nba.pronostico").fetchone()[0] == n


def test_si_fallan_los_props_el_equipo_queda_sellado_y_no_quedan_props_a_medias(base_migrada, monkeypatch):
    db = base_migrada
    _, partidos, _, inicio = con_horas(db)
    pid = partidos[25][0]
    ahora = inicio[pid] - timedelta(minutes=30)
    original = sellado.sellar
    llamadas = {"n": 0}

    def inestable(db_, p):
        llamadas["n"] += 1
        if p.entidad_id is not None and llamadas["n"] == 5:
            raise RuntimeError("fallo a mitad de los props")
        return original(db_, p)

    monkeypatch.setattr(sellado, "sellar", inestable)
    r = motor.ejecutar(db, ahora)
    assert len(r["errores"]) == 1 and len(r["sellados"]) == 1
    assert db.execute("SELECT count(*) FROM nba.pronostico").fetchone()[0] == 1                 # solo el equipo; ningún jugador a medias
    monkeypatch.setattr(sellado, "sellar", original)
    r2 = motor.ejecutar(db, ahora + timedelta(minutes=5))                                       # el siguiente cron completa los props
    assert r2["errores"] == [] and r2["sellados"] == [] and r2["props"][0]["jugadores"] >= 10
    assert sellado.verificar_cadena(db) == 1 + r2["props"][0]["pronosticos"]


def test_alertas_se_mandan_una_vez_al_dia_y_sin_canal_solo_se_devuelven(tmp_path):
    resumen = {"errores": [{"partido": 7, "error": "RuntimeError: x"}], "omitidos": [{"partido": 9, "razon": "historia_atrasada"}], "sin_hora": [1]}
    enviados = []
    estado = tmp_path / "estado.json"
    hoy = datetime(2026, 11, 3, 5, tzinfo=UTC)
    a = alertas.procesar(resumen, estado, "tok", "chat", enviar=lambda t, c, m: enviados.append((t, c, m)), ahora=hoy)
    assert len(a) == 2 and len(enviados) == 2 and enviados[0][:2] == ("tok", "chat") and "partido 7" in enviados[0][2]
    assert alertas.procesar(resumen, estado, "tok", "chat", enviar=lambda *x: enviados.append(x), ahora=hoy + timedelta(hours=2)) == [] and len(enviados) == 2
    assert len(alertas.procesar(resumen, estado, "tok", "chat", enviar=lambda *x: enviados.append(x), ahora=hoy + timedelta(days=1))) == 2    # al día siguiente
    solo = alertas.procesar(resumen, None, None, None, ahora=hoy)
    assert len(solo) == 2 and len(enviados) == 4                                               # sin canal: no envía
    assert alertas.procesar({"errores": [], "omitidos": [], "sin_hora": []}, estado, "t", "c", ahora=hoy) == []
