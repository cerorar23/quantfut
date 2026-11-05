from datetime import datetime, timedelta, UTC
import json

import pytest

from nba.v2 import identidad, motor, motor_equipo, sellado
from nba.v2.carga import DatoNuevo, guardar_datos
from test_sellado_pit import liga


def con_horas(db, n=30, sin_hora=(), extra_marzo=False):
    """Liga de prueba con hora de salto a las 00:30 UTC del día siguiente a su fecha (19:30 ET)."""
    reloj = datetime.now(UTC)
    fecha_et = reloj.astimezone(motor.ET).date()
    ids, partidos = liga(db, n, fecha_et - timedelta(days=20))
    inicio = {}
    for i, (pid, fecha, a, _) in enumerate(partidos):
        if i in sin_hora:
            continue
        t = reloj + timedelta(minutes=30, days=(fecha-fecha_et).days)
        inicio[pid] = t
        guardar_datos(db, [DatoNuevo(partido_id=pid, entidad_id=ids[a], metrica="inicio_programado_utc", fase="pre", fuente="nba_oficial",
                                     recibido_en=datetime(2025, 12, 1, tzinfo=UTC), valor=t.timestamp())])
    db.commit()                      # el motor termina sus lecturas con rollback: lo sembrado debe estar confirmado
    return ids, partidos, inicio


def n_sellos(db):
    return db.execute("SELECT count(*) FROM nba.pronostico").fetchone()[0]


def test_sella_dentro_de_la_hora_previa_y_no_antes_ni_despues(base_migrada):
    db = base_migrada
    _, partidos, inicio = con_horas(db)
    pid = partidos[20][0]
    r0 = motor.ejecutar(db, inicio[pid] - timedelta(minutes=90))
    assert r0["sellados"] == [] and n_sellos(db) == 0                       # todavía falta más de una hora
    r1 = motor.ejecutar(db, inicio[pid] - timedelta(minutes=30))
    assert [s["partido"] for s in r1["sellados"]] == [pid] and r1["errores"] == []
    assert r1["omitidos"] == []                                                # el de la víspera empezó hace 23 h: ya no se repite en el informe
    obj = db.execute("SELECT objetivo_en FROM nba.pronostico").fetchone()[0]
    assert obj == inicio[pid] - timedelta(minutes=60)                       # el corte es fijo: salto − 60 min, no la hora del cron
    assert sellado.verificar_cadena(db) == 1


def test_es_idempotente_y_un_cron_atrasado_usa_los_mismos_datos(base_migrada):
    db = base_migrada
    _, partidos, inicio = con_horas(db)
    pid = partidos[20][0]
    a = motor.ejecutar(db, inicio[pid] - timedelta(minutes=55))
    h = db.execute("SELECT hash, version_datos FROM nba.pronostico").fetchone()
    b = motor.ejecutar(db, inicio[pid] - timedelta(minutes=5))              # corre 50 minutos más tarde
    assert len(a["sellados"]) == 1 and b["sellados"] == [] and n_sellos(db) == 1
    assert db.execute("SELECT hash, version_datos FROM nba.pronostico").fetchone() == h


def test_nunca_sella_despues_del_salto(base_migrada):
    db = base_migrada
    _, partidos, inicio = con_horas(db)
    pid = partidos[20][0]
    r = motor.ejecutar(db, inicio[pid] + timedelta(minutes=1))
    assert r["sellados"] == [] and n_sellos(db) == 0
    assert {"partido": pid, "razon": "ya_empezo_sin_sello"} in r["omitidos"]


def test_simulacro_no_escribe(base_migrada):
    db = base_migrada
    _, partidos, inicio = con_horas(db)
    pid = partidos[20][0]
    r = motor.ejecutar(db, inicio[pid] - timedelta(minutes=30), simulacro=True)
    assert r["simulacro"] and len(r["sellados"]) == 1 and 0 < r["sellados"][0]["p_local"] < 1 and n_sellos(db) == 0


def test_sin_hora_conocida_no_se_sella_y_se_informa(base_migrada):
    db = base_migrada
    _, partidos, inicio = con_horas(db, sin_hora=(20,))
    pid = partidos[20][0]
    r = motor.ejecutar(db, datetime.now(UTC))
    assert r["sin_hora"] == [pid] and r["sellados"] == [] and n_sellos(db) == 0


def test_con_la_historia_atrasada_no_se_pronostica(base_migrada):
    db = base_migrada
    ids, partidos, _ = con_horas(db)
    from datetime import date
    pid = identidad.partido(db, "nba_oficial", "0022599999", date(2026, 3, 1), ids["BOS"], ids["NYK"], identidad.temporada(date(2026, 3, 1)))
    t = datetime(2026, 3, 2, 0, 30, tzinfo=UTC)
    guardar_datos(db, [DatoNuevo(partido_id=pid, entidad_id=ids["BOS"], metrica="inicio_programado_utc", fase="pre", fuente="nba_oficial",
                                 recibido_en=datetime(2026, 1, 1, tzinfo=UTC), valor=t.timestamp())])
    db.commit()
    r = motor.ejecutar(db, t - timedelta(minutes=30))
    assert r["omitidos"] == [{"partido": pid, "razon": "historia_atrasada"}] and r["sellados"] == [] and n_sellos(db) == 0


def test_un_partido_roto_no_impide_sellar_los_demas(base_migrada, monkeypatch):
    db = base_migrada
    ids, partidos, inicio = con_horas(db)
    a, b = partidos[20][0], partidos[21][0]
    # fuerza dos partidos en la ventana: el de la fecha 21 sale 24 h más tarde, se acerca el reloj ajustando su hora
    guardar_datos(db, [DatoNuevo(partido_id=b, entidad_id=ids[partidos[21][2]], metrica="inicio_programado_utc", fase="pre", fuente="nba_oficial",
                                 recibido_en=datetime(2025, 12, 2, tzinfo=UTC), valor=(inicio[a] + timedelta(minutes=10)).timestamp())])
    db.commit()
    original = motor_equipo.pronosticar

    def roto(inst):
        if inst.partido_id == a:
            raise RuntimeError("fallo simulado")
        return original(inst)

    monkeypatch.setattr(motor_equipo, "pronosticar", roto)
    r = motor.ejecutar(db, inicio[a] - timedelta(minutes=20))
    assert [e["partido"] for e in r["errores"]] == [a] and [s["partido"] for s in r["sellados"]] == [b], r
    assert n_sellos(db) == 1 and sellado.verificar_cadena(db) == 1


def test_cli_exige_dsn(monkeypatch, capsys):
    monkeypatch.delenv("NBA_DB_DSN", raising=False)
    assert motor.main([]) == 2


def test_cli_ahora_solo_en_simulacro(monkeypatch):
    monkeypatch.setenv("NBA_DB_DSN", "postgresql://no-se-usa")
    assert motor.main(["--ahora", "2026-01-21T23:30:00+00:00"]) == 2          # sin --simulacro: no se puede fingir la hora
    assert motor.main(["--simulacro", "--ahora", "2026-01-21T23:30:00"]) == 2   # sin zona horaria


def test_un_juego_duplicado_en_la_base_no_se_lista_dos_veces(base_migrada):
    db = base_migrada
    ids, partidos, inicio = con_horas(db)
    pid, fecha, a, b = partidos[20]
    original = db.execute("SELECT atributos, temporada FROM nba.entidad WHERE entidad_id = %s", (pid,)).fetchone()
    db.execute("INSERT INTO nba.entidad (tipo, fuente, id_en_fuente, nombre, fecha_juego_et, temporada, atributos) "
               "VALUES ('partido', 'nba_oficial', 'sintetico-dup', 'dup', %s, %s, %s::jsonb)", (fecha, original[1], json.dumps(original[0])))
    db.commit()
    dup = db.execute("SELECT entidad_id, canonica_id FROM nba.entidad WHERE id_en_fuente = 'sintetico-dup'").fetchone()
    assert dup[0] > pid
    r = motor.ejecutar(db, inicio[pid] - timedelta(minutes=30))
    assert [s["partido"] for s in r["sellados"]] == [pid] and dup[0] not in r["sin_hora"]
