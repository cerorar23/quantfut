from datetime import UTC, date, datetime
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from nba.v2.fuentes import espn

FIX = Path(__file__).parent / "fixtures"
SCOREBOARD = (FIX / "espn_scoreboard.json").read_bytes()
LESIONES = (FIX / "espn_lesiones.json").read_bytes()
T = datetime(2026, 11, 2, 18, 34, tzinfo=UTC)   # 13:34 ET del 2-nov


def test_parsear_scoreboard_equipos_hora_y_fecha_et():
    partidos = espn.parsear_scoreboard(SCOREBOARD.decode())
    assert [(p.id, p.visitante, p.local, p.estado) for p in partidos] == [
        ("401909907", "OKC", "CLE", "programado"), ("401909908", "DET", "CHA", "programado"),
        ("401909999", "DET", "CHA", "final")]
    p = partidos[0]
    assert p.inicio_utc == datetime(2026, 11, 3, 0, 0, tzinfo=UTC)
    assert p.fecha_et == date(2026, 11, 2)                 # 00:00Z del 3-nov es 19:00 ET del 2-nov
    assert partidos[2].asistencia == 19432 and partidos[2].puntos == {"CHA": 104, "DET": 99}
    assert partidos[0].puntos is None


def test_parsear_lesiones_id_por_enlace_y_equipo():
    lesiones = espn.parsear_lesiones(LESIONES.decode())
    assert len(lesiones) == 9
    sorber = next(x for x in lesiones if x.nombre == "Thomas Sorber")
    assert (sorber.id_espn, sorber.equipo, sorber.estado) == ("5061603", "OKC", "Out")
    assert {x.estado for x in lesiones} == {"Out", "Day-To-Day"}


def ledger(tmp_path, eventos):
    """Crea un ledger SQLite como el de run57 y su carpeta de cuerpos."""
    blobs = tmp_path / "blobs"
    blobs.mkdir()
    con = sqlite3.connect(tmp_path / "receipts.sqlite")
    con.execute("CREATE TABLE events (seq INTEGER PRIMARY KEY, received_at TEXT NOT NULL, kind TEXT NOT NULL, "
                "payload TEXT NOT NULL, previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL UNIQUE)")
    for seq, (url, status, cuerpo, recibido) in enumerate(eventos, start=1):
        huella = hashlib.sha256(cuerpo).hexdigest()
        if cuerpo:
            (blobs / huella).write_bytes(cuerpo)
        payload = {"url": url, "http_status": status, "raw_sha256": huella, "raw_bytes": len(cuerpo),
                   "first_received_at_utc": recibido.isoformat()}
        con.execute("INSERT INTO events VALUES (?,?,?,?,?,?)",
                    (seq, recibido.isoformat(), "public_response_received", json.dumps(payload), "0", f"h{seq}"))
    con.commit()
    con.close()
    return tmp_path / "receipts.sqlite", blobs


SB = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=20261102"
INJ = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries?limit=1000"
ROS = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/5/roster?season=2027"


def test_cargar_ledger_calendario_y_lesiones(base_migrada, tmp_path):
    db = base_migrada
    ruta, blobs = ledger(tmp_path, [(SB, 200, SCOREBOARD, T), (INJ, 200, LESIONES, T), (ROS, 200, b"{}", T),
                                    ("https://sports.caliente.mx/x", 403, b"", T), (INJ, 500, b"", T)])
    ultimo, r = espn.cargar_ledger(db, ruta, blobs, desde_seq=0)
    assert ultimo == 5 and r["calendario"] == 1 and r["lesiones"] == 1 and r["omitidos"] == 3
    assert db.execute("SELECT count(*) FROM nba.entidad WHERE tipo = 'partido'").fetchone()[0] == 3
    estados = dict(db.execute(
        "SELECT e.nombre, d.etiqueta FROM nba.dato d JOIN nba.metrica m USING (metrica_id) JOIN nba.entidad e "
        "ON e.entidad_id = d.entidad_id WHERE m.nombre = 'estado_disponibilidad' AND d.fuente = 'espn'").fetchall())
    assert estados["Thomas Sorber"] == "Out" and estados["Peyton Watson"] == "Day-To-Day" and len(estados) == 9
    # inicio y estado del partido
    q = db.execute("SELECT d.valor FROM nba.dato d JOIN nba.metrica m USING (metrica_id) JOIN nba.entidad e "
                   "ON e.entidad_id = d.partido_id WHERE m.nombre = 'inicio_programado_utc' AND e.id_en_fuente = %s "
                   "AND d.entidad_id = d.partido_id", ("401909907",)).fetchall()
    assert q == [(datetime(2026, 11, 3, tzinfo=UTC).timestamp(),)]
    # puntos y asistencia solo del partido final
    assert db.execute("SELECT count(*) FROM nba.dato d JOIN nba.metrica m USING (metrica_id) "
                      "WHERE m.nombre = 'puntos' AND d.fase = 'final'").fetchone()[0] == 2
    # un recibo de ESPN ≠ 200 queda como captura fallida; fuentes ajenas (Caliente) y plantillas se omiten
    assert db.execute("SELECT count(*) FROM nba.captura WHERE NOT ok").fetchone()[0] == 1


def test_cargar_ledger_es_idempotente_y_reanuda(base_migrada, tmp_path):
    db = base_migrada
    ruta, blobs = ledger(tmp_path, [(SB, 200, SCOREBOARD, T), (INJ, 200, LESIONES, T)])
    espn.cargar_ledger(db, ruta, blobs, desde_seq=0)
    datos, capturas = (db.execute(f"SELECT count(*) FROM nba.{t}").fetchone()[0] for t in ("dato", "captura"))
    ultimo, _ = espn.cargar_ledger(db, ruta, blobs, desde_seq=0)             # reproceso completo
    assert (db.execute("SELECT count(*) FROM nba.dato").fetchone()[0],
            db.execute("SELECT count(*) FROM nba.captura").fetchone()[0]) == (datos, capturas)
    assert espn.cargar_ledger(db, ruta, blobs, desde_seq=ultimo) == (ultimo, {"calendario": 0, "lesiones": 0, "omitidos": 0})


def test_jugador_que_deja_de_ser_reportado_queda_sin_reporte(base_migrada, tmp_path):
    db = base_migrada
    datos = json.loads(LESIONES)
    recortado = json.loads(LESIONES)
    for equipo in recortado["injuries"]:
        equipo["injuries"] = [i for i in equipo["injuries"] if i["athlete"]["displayName"] != "Thomas Sorber"]
    mas_tarde = datetime(2026, 11, 2, 19, 34, tzinfo=UTC)
    ruta, blobs = ledger(tmp_path, [(SB, 200, SCOREBOARD, T), (INJ, 200, LESIONES, T),
                                    (INJ, 200, json.dumps(recortado).encode(), mas_tarde)])
    espn.cargar_ledger(db, ruta, blobs, desde_seq=0)
    filas = db.execute(
        "SELECT d.etiqueta, d.recibido_en FROM nba.dato d JOIN nba.metrica m USING (metrica_id) JOIN nba.entidad e "
        "ON e.entidad_id = d.entidad_id WHERE m.nombre = 'estado_disponibilidad' AND e.nombre = 'Thomas Sorber' "
        "ORDER BY d.recibido_en").fetchall()
    assert [f[0] for f in filas] == ["Out", "sin_reporte"] and filas[1][1] == mas_tarde
    assert len(datos["injuries"]) == 4


def test_lesiones_sin_partido_proximo_no_escriben_datos(base_migrada, tmp_path):
    ruta, blobs = ledger(tmp_path, [(INJ, 200, LESIONES, T)])            # sin calendario cargado
    _, r = espn.cargar_ledger(base_migrada, ruta, blobs, desde_seq=0)
    assert r["lesiones"] == 1
    assert base_migrada.execute("SELECT count(*) FROM nba.dato").fetchone()[0] == 0


def test_partido_con_rival_que_no_es_de_la_nba_se_omite():
    datos = json.loads(SCOREBOARD)
    datos["events"][0]["competitions"][0]["competitors"][1]["team"].update(id="9999", abbreviation="LON")
    ids = [p.id for p in espn.parsear_scoreboard(json.dumps(datos))]
    assert "401909907" not in ids and len(ids) == 2
