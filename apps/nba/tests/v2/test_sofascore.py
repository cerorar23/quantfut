from datetime import date, datetime, UTC
import gzip
import json
from pathlib import Path

import pytest

from nba.v2 import equipos, identidad
from nba.v2.carga import DatoNuevo, guardar_datos
from nba.v2.fuentes import sofascore

FIX = Path(__file__).parent / "fixtures" / "sofascore_eventos.jsonl"
EVENTOS = [json.loads(x) for x in FIX.read_text(encoding="utf-8").splitlines()]
OFICIAL = datetime(2026, 11, 2, tzinfo=UTC)


def archivo(tmp_path, eventos=None):
    ruta = tmp_path / "eventos.jsonl.gz"
    with gzip.open(ruta, "wt", encoding="utf8") as f:
        for e in eventos or EVENTOS:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    return ruta


def con_caja_oficial(db, ev):
    """El primer partido ya tiene caja de nba_oficial, con jugadores de OTRO nombre: solo la huella de la caja permite emparejarlos."""
    local, visita = (identidad.equipo(db, equipos.canonico("sofascore", ev[k]["codigo"])) for k in ("local", "visitante"))
    pid = identidad.partido(db, "nba_oficial", "0022500999", date.fromisoformat(ev["fecha_et"]), local, visita, ev["temporada"])
    oficiales = {}
    filas = []
    for j in ev["jugadores"]:
        s = j["stats"]
        jug = identidad.jugador(db, "nba_oficial", str(900000 + j["id"]), f"Oficial {j['id']}")
        oficiales[j["id"]] = jug
        base = dict(partido_id=pid, entidad_id=jug, fase="final", fuente="nba_oficial", recibido_en=OFICIAL, pit="reconstruido")
        filas += [DatoNuevo(metrica="minutos", valor=s["secondsPlayed"] / 60, **base), DatoNuevo(metrica="puntos", valor=float(s.get("points", 0)), **base),
                  DatoNuevo(metrica="rebotes", valor=float(s.get("rebounds", 0)), **base), DatoNuevo(metrica="asistencias", valor=float(s.get("assists", 0)), **base),
                  DatoNuevo(metrica="equipo_del_jugador", valor=float(local if j["equipo"] == "local" else visita), **base)]
    guardar_datos(db, filas)
    db.commit()
    return pid, oficiales


def test_carga_partidos_nuevos_y_existentes_y_empareja_jugadores_por_huella(base_migrada, tmp_path):
    db = base_migrada
    pid_oficial, oficiales = con_caja_oficial(db, EVENTOS[0])
    r = sofascore.cargar(db, archivo(tmp_path))
    assert r["partidos_existentes"] == 1 and r["partidos_nuevos"] == 1 and r["eventos"] == 2 and r["filas_nuevas"] == r["filas_leidas"] > 200
    # los jugadores del primer partido se emparejan con los oficiales aunque se llamen distinto
    por_huella = db.execute("SELECT count(*) FROM nba.entidad WHERE fuente = 'sofascore' AND tipo = 'jugador' AND atributos->>'alias_por_huella' = 'true'").fetchone()[0]
    assert por_huella >= 0.8 * len(EVENTOS[0]["jugadores"]) and r["jugadores_por_huella"] == por_huella
    sid = EVENTOS[0]["jugadores"][0]["id"]
    canon = db.execute("SELECT canonica_id FROM nba.entidad WHERE fuente = 'sofascore' AND id_en_fuente = %s", (str(sid),)).fetchone()[0]
    assert canon == oficiales[sid]
    # el segundo partido no existía: se crea con jugadores nuevos
    assert db.execute("SELECT count(*) FROM nba.entidad WHERE tipo = 'partido' AND canonica_id = entidad_id").fetchone()[0] == 2


def test_la_caja_oficial_gana_y_sofascore_completa_lo_que_falta(base_migrada, tmp_path):
    db = base_migrada
    pid_oficial, oficiales = con_caja_oficial(db, EVENTOS[0])
    guardar_datos(db, [DatoNuevo(partido_id=pid_oficial, entidad_id=oficiales[EVENTOS[0]["jugadores"][0]["id"]], metrica="titular", valor=0.0, fase="final",
                                 fuente="nba_oficial", recibido_en=OFICIAL, pit="reconstruido")])
    sofascore.cargar(db, archivo(tmp_path))
    ahora = datetime.now(UTC)
    # puntos del primer jugador: dos filas (una por fuente); dato_a_las devuelve la oficial
    jug = oficiales[EVENTOS[0]["jugadores"][0]["id"]]
    fuentes = {f for (f,) in db.execute("SELECT d.fuente FROM nba.dato d JOIN nba.metrica m USING (metrica_id) WHERE d.partido_id = %s AND d.entidad_id = %s "
                                        "AND m.nombre = 'puntos'", (pid_oficial, jug)).fetchall()}
    assert fuentes == {"nba_oficial", "sofascore"}
    vigente = db.execute("SELECT d.fuente FROM nba.dato_a_las(%s) d JOIN nba.metrica m USING (metrica_id) WHERE d.partido_id = %s AND d.entidad_id = %s "
                         "AND m.nombre = 'puntos'", (ahora, pid_oficial, jug)).fetchone()[0]
    assert vigente == "nba_oficial"
    # los titulares solo los trae SofaScore para el partido nuevo
    nuevo = db.execute("SELECT entidad_id FROM nba.entidad WHERE tipo = 'partido' AND canonica_id = entidad_id AND entidad_id <> %s", (pid_oficial,)).fetchone()[0]
    titulares = db.execute("SELECT count(*) FROM nba.dato d JOIN nba.metrica m USING (metrica_id) WHERE d.partido_id = %s AND m.nombre = 'titular' AND d.valor = 1",
                           (nuevo,)).fetchone()[0]
    assert titulares == 10


def test_es_idempotente_y_la_auditoria_no_ve_diferencias(base_migrada, tmp_path):
    db = base_migrada
    con_caja_oficial(db, EVENTOS[0])
    ruta = archivo(tmp_path)
    sofascore.cargar(db, ruta)
    n = db.execute("SELECT count(*) FROM nba.dato").fetchone()[0]
    assert sofascore.cargar(db, ruta)["filas_nuevas"] == 0 and db.execute("SELECT count(*) FROM nba.dato").fetchone()[0] == n
    auditoria = sofascore.auditar(db)
    assert auditoria["minutos"]["comparables"] > 10 and all(v["distintos"] == 0 for v in auditoria.values())


def test_dos_jugadores_con_la_misma_linea_de_caja_no_se_emparejan_por_huella(base_migrada, tmp_path):
    db = base_migrada
    ev = json.loads(json.dumps(EVENTOS[0]))
    mismo = [j for j in ev["jugadores"] if j["equipo"] == "local"][:2]
    mismo[1]["stats"] = dict(mismo[0]["stats"])                                   # idéntica línea de caja en el mismo equipo
    con_caja_oficial(db, ev)
    sofascore.cargar(db, archivo(tmp_path, [ev]))
    for j in mismo:
        fila = db.execute("SELECT atributos->>'alias_por_huella' FROM nba.entidad WHERE fuente = 'sofascore' AND id_en_fuente = %s", (str(j["id"]),)).fetchone()
        assert fila[0] is None                                                   # ambiguo: se resuelve por nombre, nunca por una huella que no distingue


def test_equipo_desconocido_se_rechaza(base_migrada, tmp_path):
    ev = json.loads(json.dumps(EVENTOS[0]))
    ev["local"]["codigo"] = "XXX"
    with pytest.raises(KeyError):
        sofascore.cargar(base_migrada, archivo(tmp_path, [ev]))
