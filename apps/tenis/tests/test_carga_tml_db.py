"""Carga TML contra Postgres en esquema aislado: rechazos, orientación, idempotencia, PIT y sha del manifiesto."""
import csv
import hashlib
import io
import json
from datetime import datetime, timezone

from test_carga_tml_parseo import BASE, COLUMNAS
from tenis.carga.tml_cli import ejecutar


def fila(**c) -> dict:
    return {**BASE, **c}


def _csv(filas: list[dict]) -> bytes:
    buf = io.StringIO()
    escritor = csv.DictWriter(buf, fieldnames=COLUMNAS, lineterminator="\n")
    escritor.writeheader()
    escritor.writerows(filas)
    return buf.getvalue().encode("utf-8")


def filas_2025() -> list[dict]:
    """17 filas de Roland Garros (14 días) + 2 de un 250 (7 días). Ver el recuento esperado en los tests."""
    gs = dict(tourney_id="2025-9900", tourney_name="Roland Garros", tourney_level="G", tourney_date="20250526")
    p250 = dict(tourney_id="2025-1000", tourney_name="Lyon", tourney_level="250", tourney_date="20250505")
    r1 = fila(**gs, winner_id="AA10", winner_name="Ana Uno", loser_id="BB20", loser_name="Bea Dos",
              round="R32", score="6-3 6-4")
    return [
        r1,
        fila(**gs, winner_id="CC30", winner_name="Carla Tres", loser_id="AA10", loser_name="Ana Uno",
             round="R16", score="6-4 7-6(5)", loser_rank="5"),
        fila(**gs, winner_id="AA10", winner_name="Ana Uno", loser_id="DD40", loser_name="Dora Cuatro",
             round="R64", score="W/O"),
        fila(**gs, winner_id="EE50", winner_name="Eva Cinco", loser_id="FF60", loser_name="Fe Seis",
             round="R32", score="6-3 2-1 RET", minutes="45"),
        fila(**gs, winner_id="GG70", winner_name="Gi Siete", loser_id="HH80", loser_name="Hu Ocho",
             round="R32", score="6-3 3-1 DEF"),
        fila(**gs, winner_id="II90", winner_name="Io Nueve", loser_id="JJ91", loser_name="Ju Diez",
             round="QF", score=""),
        fila(**gs, winner_id="KK01", winner_name="Ka Uno", loser_id="LL02", loser_name="Le Dos",
             round="R32", score="6-3"),
        fila(**gs, winner_id="MM03", winner_name="Mi Tres", loser_id="NN04", loser_name="No Cuatro",
             round="R32", score="7-4 6-3"),
        fila(**gs, winner_id="OO05", winner_name="Oc Cinco", loser_id="PP06", loser_name="Pe Seis",
             round="R32", score="6-3 6-4", best_of="4"),
        fila(**gs, winner_id="AA10", winner_name="Ana Uno", loser_id="AA10", loser_name="Ana Uno",
             round="R32", score="6-3 6-4"),
        fila(**gs, winner_id="AB11", winner_name="Ana/Eva", loser_id="BB20", loser_name="Bea Dos",
             round="R32", score="6-3 6-4"),
        dict(r1),
        fila(**gs, winner_id="QQ07", winner_name="Qu Siete", loser_id="RR08", loser_name="Ro Ocho",
             round="R64", score="6-1 6-1", minutes="0"),
        fila(**gs, winner_id="SS09", winner_name="Su Nueve", loser_id="TT10", loser_name="Ti Diez",
             round="R64", score="6-1 6-1", minutes="700"),
        fila(**gs, winner_id="UU11", winner_name="Un Once", loser_id="VV12", loser_name="Ve Doce",
             round="R32", score="6-2 6-2", w_1stWon="50"),
        fila(**gs, winner_id="WW13", winner_name="We Trece", loser_id="XY14", loser_name="Xi Catorce",
             round="R32", score="6-2 6-2", winner_entry="XX", loser_entry="WC"),
        fila(**gs, winner_id="ZZ15", winner_name="Zo Quince", loser_id="ZY16", loser_name="Zy Dieciseis",
             round="3rd/4th", score="6-2 6-2"),
        fila(**p250, winner_id="EE50", winner_name="Eva Cinco", loser_id="AA10", loser_name="Ana Uno",
             round="R32", score="6-1 6-2"),
        fila(**p250, winner_id="CC30", winner_name="Carla Tres", loser_id="EE50", loser_name="Eva Cinco",
             round="F", score="6-4 6-4"),
    ]


def _archivos_base() -> dict:
    dos_mil_veintitres = [
        fila(tourney_id="2023-1234", tourney_name="Lyon", tourney_level="250", tourney_date="20230102",
             winner_id="AA10", winner_name="Ana Uno", loser_id="BB20", loser_name="Bea Dos",
             round="R32", score="6-4 6-4"),
        fila(tourney_id="2023-1234", tourney_name="Lyon", tourney_level="250", tourney_date="20230102",
             winner_id="CC30", winner_name="Carla Tres", loser_id="DD40", loser_name="Dora Cuatro",
             round="F", score="7-5 6-3"),
    ]
    return {"2025.csv": _csv(filas_2025()), "2023.csv": _csv(dos_mil_veintitres)}


def _manifiesto(tmp_path, archivos: dict, sha_falso=frozenset()):
    original = tmp_path / "tml" / "originals"
    original.mkdir(parents=True)
    entradas = []
    for nombre, cuerpo in archivos.items():
        (original / nombre).write_bytes(cuerpo)
        sha = "0" * 64 if nombre in sha_falso else hashlib.sha256(cuerpo).hexdigest()
        entradas.append({"source": "tml", "name": nombre, "bytes": len(cuerpo), "sha256": sha,
                         "received_at": "2026-11-02T10:00:00+00:00"})
    manifiesto = tmp_path / "download_manifest.json"
    manifiesto.write_text(json.dumps({"snapshot_created_at": "2026-11-02T10:00:06+00:00", "files": entradas}),
                          encoding="utf-8")
    return original, manifiesto


def _ejecutar(tmp_path, esquema, archivos, sha_falso=frozenset()):
    original, manifiesto = _manifiesto(tmp_path, archivos, sha_falso)
    return ejecutar(original, esquema.dsn, esquema.nombre, manifiesto, tmp_path / "almacen",
                    tmp_path / "rechazos.csv", equivalencias=tmp_path / "no_existe.csv")


def _partidos(db, clave: str, ronda: str):
    """Partido + resultado de una edición (por la clave de torneo) y ronda."""
    return db.execute("SELECT p.partido_id, p.jugador_1, p.jugador_2, r.estado, r.ganador, r.retira, r.sets, "
                      "r.sets_completos, r.duracion_min, r.visible_desde FROM partido p "
                      "JOIN edicion e ON e.edicion_id = p.edicion_id JOIN torneo t ON t.torneo_id = e.torneo_id "
                      "JOIN resultado r ON r.partido_id = p.partido_id WHERE t.clave = %s AND p.ronda = %s",
                      (clave, ronda)).fetchall()


def _id_tml(db, id_fuente: str) -> int:
    return db.execute("SELECT jugador_id FROM jugador_alias WHERE fuente = 'tml' AND id_fuente = %s",
                      (id_fuente,)).fetchone()[0]


def _nombre(db, jugador: int) -> str:
    return db.execute("SELECT valor FROM jugador_asercion WHERE jugador_id = %s AND campo = 'nombre' "
                      "ORDER BY recibido_en DESC LIMIT 1", (jugador,)).fetchone()[0]


def test_carga_tml_recuentos_y_motivos(tmp_path, esquema):
    res = _ejecutar(tmp_path, esquema, _archivos_base())
    c = res["contadores"]
    assert res["leidas"] == 21 and res["cuadra"] is True
    assert c["cargado"] == 14 and c["duplicado"] == 1 and c["doble"] == 1
    assert c["rechazo:completado_de_un_set"] == 1 and c["rechazo:set_invalido"] == 1
    assert c["rechazo:formato_no_valido"] == 1 and c["rechazo:mismo_jugador"] == 1
    assert c["rechazo:ronda_no_valida"] == 1 and c["estadistica:estadistica_incoherente"] == 1
    motivos = (tmp_path / "rechazos.csv").read_text(encoding="utf-8")
    assert "partido_duplicado" in motivos and "completado_de_un_set" in motivos


def test_carga_tml_estados_y_retirada(tmp_path, esquema):
    _ejecutar(tmp_path, esquema, _archivos_base())
    db = esquema.conectar()
    estados = dict(db.execute("SELECT estado, count(*) FROM resultado GROUP BY estado").fetchall())
    assert estados == {"completado": 10, "walkover": 1, "retirada": 1, "descalificado": 1, "cancelado": 1}
    (retirada,) = [r for r in _partidos(db, "9900", "R32") if r[3] == "retirada"]
    assert retirada[7] == 1 and retirada[5] is not None


def test_carga_tml_orientacion_con_perdedor_como_jugador_1(tmp_path, esquema):
    _ejecutar(tmp_path, esquema, _archivos_base())
    db = esquema.conectar()
    ana = _id_tml(db, "AA10")
    (r16,) = _partidos(db, "9900", "R16")
    assert r16[1] == ana and r16[2] > ana          # Ana (perdedora en TML) es jugador_1
    assert r16[4] == 2 and _nombre(db, r16[2]) == "Carla Tres"
    assert r16[6][0][1] == 6 and r16[6][0][0] == 4  # sets orientados: juegos de Ana primero


def test_carga_tml_duracion_entradas_y_estadisticas(tmp_path, esquema):
    _ejecutar(tmp_path, esquema, _archivos_base())
    db = esquema.conectar()
    cero = db.execute("SELECT r.duracion_min FROM resultado r JOIN partido p USING (partido_id) WHERE p.jugador_1 "
                      "IN (SELECT jugador_id FROM jugador_asercion WHERE campo = 'nombre' AND valor = 'Qu Siete') "
                      "OR p.jugador_2 IN (SELECT jugador_id FROM jugador_asercion WHERE campo = 'nombre' "
                      "AND valor = 'Qu Siete')").fetchall()
    assert cero and cero[0][0] is None
    assert db.execute("SELECT count(*) FROM partido WHERE 'WC' IN (entrada_1, entrada_2)").fetchone()[0] == 1
    assert db.execute("SELECT count(*) FROM partido WHERE 'XX' IN (entrada_1, entrada_2)").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM estadistica").fetchone()[0] == 20


def test_carga_tml_ediciones_y_ranking(tmp_path, esquema):
    _ejecutar(tmp_path, esquema, _archivos_base())
    db = esquema.conectar()
    lunes, fin, cat = db.execute("SELECT e.lunes_semana, e.fecha_fin, t.categoria FROM edicion e JOIN torneo t "
                                 "ON t.torneo_id = e.torneo_id WHERE t.clave = '1000' AND e.temporada = 2025").fetchone()
    assert (str(lunes), str(fin), cat) == ("2025-05-05", "2025-05-11", "250")
    lunes, fin, cat = db.execute("SELECT e.lunes_semana, e.fecha_fin, t.categoria FROM edicion e JOIN torneo t "
                                 "ON t.torneo_id = e.torneo_id WHERE t.clave = '9900'").fetchone()
    assert (str(lunes), str(fin), cat) == ("2025-06-02", "2025-06-08", "GS")
    assert db.execute("SELECT count(*) FROM ranking").fetchone()[0] > 0


def test_carga_tml_pit_visibilidad_por_ronda(tmp_path, esquema):
    _ejecutar(tmp_path, esquema, _archivos_base())
    db = esquema.conectar()
    (final,) = _partidos(db, "1000", "F")
    assert final[9] == datetime(2025, 5, 12, tzinfo=timezone.utc)

    def visible(instante):
        return db.execute("SELECT count(*) FROM resultado_a_las(%s) WHERE partido_id = %s",
                          (instante, final[0])).fetchone()[0]
    assert visible(datetime(2025, 5, 11, 23, tzinfo=timezone.utc)) == 0
    assert visible(datetime(2025, 5, 12, 1, tzinfo=timezone.utc)) == 1


def test_carga_tml_pit_retro_2023_visible_en_su_epoca(tmp_path, esquema):
    _ejecutar(tmp_path, esquema, _archivos_base())
    db = esquema.conectar()
    (r32,) = _partidos(db, "1234", "R32")
    antes = db.execute("SELECT count(*) FROM resultado_a_las(%s) WHERE partido_id = %s",
                       (datetime(2023, 1, 4, tzinfo=timezone.utc), r32[0])).fetchone()[0]
    despues = db.execute("SELECT count(*) FROM resultado_a_las(%s) WHERE partido_id = %s",
                         (datetime(2023, 6, 1, tzinfo=timezone.utc), r32[0])).fetchone()[0]
    assert antes == 0 and despues == 1


def test_carga_tml_idempotencia(tmp_path, esquema):
    res1 = _ejecutar(tmp_path / "uno", esquema, _archivos_base())
    db = esquema.conectar()
    tablas = ("recibo", "jugador", "jugador_alias", "jugador_asercion", "torneo", "edicion", "partido",
              "resultado", "estadistica", "ranking")
    antes = {t: db.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in tablas}
    res2 = _ejecutar(tmp_path / "dos", esquema, _archivos_base())
    despues = {t: db.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in tablas}
    assert antes == despues
    assert res2["contadores"] == res1["contadores"]


def test_carga_tml_sha_que_no_coincide_rechaza_el_fichero_entero(tmp_path, esquema):
    res = _ejecutar(tmp_path, esquema, _archivos_base(), sha_falso={"2023.csv"})
    db = esquema.conectar()
    assert db.execute("SELECT count(*) FROM recibo").fetchone()[0] == 1
    assert res["contadores"]["rechazo:fichero_sha_no_coincide"] == 2
    assert "fichero_sha_no_coincide" in (tmp_path / "rechazos.csv").read_text(encoding="utf-8")
    assert res["cuadra"] is True
