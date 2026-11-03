from datetime import UTC, datetime
import json
import shutil
from pathlib import Path

from nba.v2.fuentes import historico_partidos as hp

FIX = Path(__file__).parent / "fixtures"
JUGADORES = [json.loads(x) for x in (FIX / "historico_jugadores.jsonl").read_text(encoding="utf-8").splitlines()]
JUEGOS = json.loads((FIX / "historico_juegos_completos.json").read_text(encoding="utf-8"))


def valor(db, metrica, entidad_nombre, fase="final"):
    return db.execute("SELECT d.valor, d.etiqueta FROM nba.dato d JOIN nba.metrica m USING (metrica_id) JOIN nba.entidad e "
                      "ON e.entidad_id = d.entidad_id WHERE m.nombre = %s AND e.nombre = %s AND d.fase = %s",
                      (metrica, entidad_nombre, fase)).fetchone()


def carpeta_cajas(tmp_path):
    shutil.copy(FIX / "historico_juegos_completos.json", tmp_path / "games.json")
    shutil.copy(FIX / "historico_jugadores.jsonl", tmp_path / "players.jsonl")
    return tmp_path


def test_cajas_de_equipos_y_jugadores(base_migrada, tmp_path):
    db = base_migrada
    r = hp.cargar_cajas(db, carpeta_cajas(tmp_path))
    assert r["ok"] and r["nuevas"] == r["leidas"] > 300
    local = JUEGOS[0]["home"]
    assert valor(db, "puntos", {"DEN": "Denver Nuggets"}["DEN"])[0] == float(local["points"])
    jug = next(x for x in JUGADORES if x["participated"] and x["points"] > 10)
    assert valor(db, "puntos", jug["name"])[0] == float(jug["points"]) and valor(db, "minutos", jug["name"])[0] == jug["minutes"]
    assert valor(db, "mas_menos", jug["name"])[0] == float(jug["plus_minus"])
    dnp = next(x for x in JUGADORES if not x["participated"])
    assert valor(db, "jugo", dnp["name"])[0] == 0.0 and valor(db, "minutos", dnp["name"]) is None      # sin minutos no se inventan
    assert db.execute("SELECT DISTINCT pit FROM nba.dato").fetchall() == [("reconstruido",)]
    assert db.execute("SELECT count(*) FROM nba.entidad WHERE tipo = 'partido' AND canonica_id = entidad_id").fetchone()[0] == 2
    # el equipo con el que figura cada jugador queda como dato (también para quien no jugó)
    equipo_de = lambda nombre: db.execute(  # noqa: E731
        "SELECT t.nombre FROM nba.dato d JOIN nba.metrica m USING (metrica_id) JOIN nba.entidad e ON e.entidad_id = d.entidad_id "
        "JOIN nba.entidad t ON t.entidad_id = d.valor::bigint WHERE m.nombre = 'equipo_del_jugador' AND e.nombre = %s",
        (nombre,)).fetchone()
    assert equipo_de(jug["name"]) is not None and equipo_de(dnp["name"]) is not None
    assert db.execute("SELECT count(*) FROM nba.dato d JOIN nba.metrica m USING (metrica_id) WHERE m.nombre = 'equipo_del_jugador'"
                      ).fetchone()[0] == len(JUGADORES)


def test_cajas_son_idempotentes_y_dejan_la_captura_historica(base_migrada, tmp_path):
    db = base_migrada
    carpeta = carpeta_cajas(tmp_path)
    hp.cargar_cajas(db, carpeta)
    n = db.execute("SELECT count(*) FROM nba.dato").fetchone()[0]
    assert hp.cargar_cajas(db, carpeta)["nuevas"] == 0 and db.execute("SELECT count(*) FROM nba.dato").fetchone()[0] == n
    assert db.execute("SELECT count(*) FROM nba.captura WHERE fase = 'historico' AND ok").fetchone()[0] == 2


def partes(tmp_path):
    shutil.copy(FIX / "historico_partes.jsonl", tmp_path / "partes.jsonl")
    return tmp_path / "partes.jsonl"


def test_partes_con_la_hora_del_propio_parte(base_migrada, tmp_path):
    db = base_migrada
    r = hp.cargar_partes(db, [partes(tmp_path)])
    assert r["ok"] and r["partes"] == 2 and r["nuevas"] > 10
    primero = db.execute("SELECT d.etiqueta, d.recibido_en, d.pit, d.fase FROM nba.dato d JOIN nba.metrica m USING (metrica_id) "
                         "JOIN nba.entidad e ON e.entidad_id = d.entidad_id WHERE m.nombre = 'estado_disponibilidad' "
                         "AND e.nombre = 'Colin Castleton'").fetchone()
    assert primero == ("Out", datetime(2023, 10, 24, 22, 30, tzinfo=UTC), "reconstruido", "pre")
    motivo = db.execute("SELECT d.etiqueta FROM nba.dato d JOIN nba.metrica m USING (metrica_id) JOIN nba.entidad e "
                        "ON e.entidad_id = d.entidad_id WHERE m.nombre = 'motivo_disponibilidad' AND e.nombre = 'Colin Castleton'").fetchone()
    assert motivo[0] == "G League - Two-Way"


def test_partes_repetidos_en_dos_archivos_no_se_duplican_y_solo_cambios(base_migrada, tmp_path):
    db = base_migrada
    uno = partes(tmp_path)
    dos = tmp_path / "copia.jsonl"
    shutil.copy(uno, dos)
    r = hp.cargar_partes(db, [uno, dos])
    assert r["partes"] == 2
    n = db.execute("SELECT count(*) FROM nba.dato").fetchone()[0]
    assert hp.cargar_partes(db, [uno])["nuevas"] == 0 and db.execute("SELECT count(*) FROM nba.dato").fetchone()[0] == n
    # el segundo parte (2 h después) repite el estado de quienes no cambiaron: no añade filas para ellos
    cambios = db.execute("SELECT count(*) FROM nba.dato d JOIN nba.entidad e ON e.entidad_id = d.entidad_id "
                         "WHERE e.nombre = 'Colin Castleton'").fetchone()[0]
    assert cambios == 2                                                       # estado + motivo, una sola vez
