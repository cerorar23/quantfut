from datetime import UTC, date, datetime, timedelta
import json
from pathlib import Path

import pytest

from nba.v2 import carga, identidad
from nba.v2.carga import DatoNuevo
from nba.v2.fuentes import nba_cdn as cdn

FIX = Path(__file__).parent / "fixtures"
BOX = (FIX / "cdn_boxscore_0022600001.json").read_text(encoding="utf-8")
PBP = (FIX / "cdn_playbyplay_0022600001.json").read_text(encoding="utf-8")
MARCADOR = (FIX / "cdn_scoreboard.json").read_text(encoding="utf-8")
T = datetime(2026, 10, 20, 22, 30, tzinfo=UTC)


def test_minutos_iso():
    assert cdn.minutos("PT33M15.00S") == 33.25 and cdn.minutos("PT12M00.00S") == 12
    assert cdn.minutos("PT00M30.50S") == pytest.approx(0.5083, abs=1e-3)
    assert cdn.minutos("") is None and cdn.minutos(None) is None and cdn.minutos("PT") is None


def test_parsear_marcador():
    p = cdn.parsear_marcador(MARCADOR)
    assert [(x.game_id, x.local, x.visitante, x.estado) for x in p] == [
        ("0022600158", "CLE", "OKC", 1), ("0022600159", "CHA", "DET", 1), ("0022600160", "IND", "ATL", 1)]
    assert {x.fecha_et for x in p} == {date(2026, 11, 2)}


def valor(db, metrica, entidad_nombre, periodo=0):
    return db.execute("SELECT d.valor, d.etiqueta FROM nba.dato d JOIN nba.metrica m USING (metrica_id) JOIN nba.entidad e "
                      "ON e.entidad_id = d.entidad_id WHERE m.nombre = %s AND e.nombre = %s AND d.periodo = %s "
                      "AND d.fuente = 'nba_oficial'", (metrica, entidad_nombre, periodo)).fetchone()


def test_cargar_boxscore(base_migrada):
    db = base_migrada
    captura = carga.registrar_captura(db, fuente="nba_oficial", objetivo="x", fase="final", solicitado_en=T, ok=True)
    assert cdn.cargar_boxscore(db, BOX, T, captura) > 200
    game = json.loads(BOX)["game"]
    assert valor(db, "puntos", "Detroit Pistons") == (121.0, None)
    assert valor(db, "puntos", "Detroit Pistons", periodo=1) == (27.0, None)
    assert valor(db, "puntos", "Ausar Thompson") == (11.0, None) and valor(db, "minutos", "Ausar Thompson") == (33.25, None)
    assert valor(db, "mas_menos", "Ausar Thompson") == (12.0, None) and valor(db, "rebotes", "Ausar Thompson") == (11.0, None)
    assert valor(db, "jugo", "Chaz Lanier") == (0.0, None) and valor(db, "minutos", "Chaz Lanier") is None   # no se imputa
    assert valor(db, "arbitro_asignado", "Kevin Scott") == (1.0, None)
    pistons = db.execute("SELECT entidad_id FROM nba.entidad WHERE nombre = 'Detroit Pistons'").fetchone()[0]
    assert valor(db, "equipo_del_jugador", "Ausar Thompson")[0] == pistons == valor(db, "equipo_del_jugador", "Chaz Lanier")[0]
    assert valor(db, "rebotes", "Detroit Pistons")[0] == game["homeTeam"]["statistics"]["reboundsPersonal"]
    assert valor(db, "rebotes_equipo", "Detroit Pistons")[0] == game["homeTeam"]["statistics"]["reboundsTeam"]
    partido = db.execute("SELECT entidad_id FROM nba.entidad WHERE tipo = 'partido'").fetchone()[0]
    assert db.execute("SELECT valor FROM nba.dato d JOIN nba.metrica m USING (metrica_id) WHERE m.nombre = 'prorrogas' "
                      "AND d.partido_id = %s", (partido,)).fetchone()[0] == 0
    assert db.execute("SELECT etiqueta FROM nba.dato d JOIN nba.metrica m USING (metrica_id) WHERE m.nombre = 'estado_partido' "
                      "AND d.partido_id = %s", (partido,)).fetchone()[0] == "final"


def test_boxscore_de_un_partido_no_final_se_rechaza(base_migrada):
    d = json.loads(BOX)
    d["game"]["gameStatus"] = 2
    with pytest.raises(ValueError, match="final"):
        cdn.cargar_boxscore(base_migrada, json.dumps(d), T, 1)
    assert base_migrada.execute("SELECT count(*) FROM nba.dato").fetchone()[0] == 0


def test_cargar_pbp(base_migrada):
    db = base_migrada
    partido = identidad.partido(db, "nba_oficial", "0022600001", date(2026, 10, 20), identidad.equipo(db, "DET"),
                                identidad.equipo(db, "BOS"), "2026-27")
    n = len(json.loads(PBP)["game"]["actions"])
    assert cdn.cargar_pbp(db, PBP, partido, T, None) == n
    assert cdn.cargar_pbp(db, PBP, partido, T, None) == 0
    inicio = db.execute("SELECT tipo, periodo, reloj_s, marcador_local FROM nba.evento WHERE tipo = 'period' "
                        "ORDER BY secuencia LIMIT 1").fetchone()
    assert inicio == ("period", 1, 720.0, 0)
    tiro = db.execute("SELECT tipo, acierto, puntos, reloj_s, marcador_local, marcador_visit FROM nba.evento "
                      "WHERE secuencia = 15").fetchone()
    assert tiro == ("2pt", True, 2, 669.0, 2, 0)
    assert db.execute("SELECT count(*) FROM nba.evento WHERE tipo = 'freethrow' AND acierto IS NOT NULL").fetchone()[0] >= 1


def preparar_final(db, game_id="0022600001"):
    """Un partido ya dado por final por ESPN, con su id de la NBA conocido (como tras bajar el marcador del día)."""
    local, visitante = identidad.equipo(db, "DET"), identidad.equipo(db, "BOS")
    espn = identidad.partido(db, "espn", "401", date(2026, 10, 20), local, visitante, "2026-27")
    identidad.partido(db, "nba_oficial", game_id, date(2026, 10, 20), local, visitante, "2026-27")
    carga.guardar_datos(db, [DatoNuevo(partido_id=espn, entidad_id=espn, metrica="estado_partido", fase="final",
                                       fuente="espn", recibido_en=T, etiqueta="final")])
    return espn


def servidor(cuerpos, creditos=1.0):
    visitas = []

    def obtener(url):
        visitas.append(url)
        if url in cuerpos:
            return 200, cuerpos[url].encode(), creditos
        return 403, b"", creditos

    return obtener, visitas


CUERPOS = {cdn.url_box("0022600001"): BOX, cdn.url_pbp("0022600001"): PBP}


def test_capturar_baja_box_y_luego_jugada_a_jugada(base_migrada, tmp_path):
    db = base_migrada
    preparar_final(db)
    obtener, visitas = servidor(CUERPOS)
    r = cdn.capturar(db, obtener, tmp_path, T + timedelta(minutes=30))
    assert r["box"] == 1 and r["pbp"] == 1 and r["creditos"] == 2 and r["eventos"] > 0 and r["ok"]
    assert visitas == [cdn.url_box("0022600001"), cdn.url_pbp("0022600001")]
    obtener2, visitas2 = servidor(CUERPOS)
    r2 = cdn.capturar(db, obtener2, tmp_path, T + timedelta(minutes=45))
    assert visitas2 == [] and r2["creditos"] == 0


def test_espera_antes_de_pedir_un_final_recien_terminado(base_migrada, tmp_path):
    preparar_final(base_migrada)
    obtener, visitas = servidor(CUERPOS)
    cdn.capturar(base_migrada, obtener, tmp_path, T + timedelta(minutes=5))
    assert visitas == []


def test_el_tope_diario_de_creditos_se_respeta(base_migrada, tmp_path):
    preparar_final(base_migrada)
    obtener, visitas = servidor(CUERPOS)
    r = cdn.capturar(base_migrada, obtener, tmp_path, T + timedelta(minutes=30), tope_diario=1)
    assert visitas == [cdn.url_box("0022600001")] and r["sin_presupuesto"] and r["pbp"] == 0
    assert cdn.gastado_hoy(base_migrada, T + timedelta(minutes=30)) == 1


def test_fallos_cobrados_se_registran_y_se_reintentan_solo_dos_veces(base_migrada, tmp_path):
    preparar_final(base_migrada)
    obtener, visitas = servidor({})
    for minutos in (30, 60, 90):
        cdn.capturar(base_migrada, obtener, tmp_path, T + timedelta(minutes=minutos))
    assert len(visitas) == 2                                          # el tercer intento ya no se hace
    assert base_migrada.execute("SELECT count(*), sum(creditos) FROM nba.captura WHERE NOT ok").fetchone() == (2, 2)
    assert base_migrada.execute("SELECT count(*) FROM nba.dato WHERE fuente = 'nba_oficial'").fetchone()[0] == 0


def test_partido_que_la_nba_aun_no_da_por_final_no_escribe_datos(base_migrada, tmp_path):
    preparar_final(base_migrada)
    d = json.loads(BOX)
    d["game"]["gameStatus"] = 2
    obtener, _ = servidor({cdn.url_box("0022600001"): json.dumps(d)})
    r = cdn.capturar(base_migrada, obtener, tmp_path, T + timedelta(minutes=30))
    assert not r["ok"] and r["box"] == 0
    assert base_migrada.execute("SELECT count(*) FROM nba.dato WHERE fuente = 'nba_oficial'").fetchone()[0] == 0
    assert base_migrada.execute("SELECT error FROM nba.captura WHERE NOT ok").fetchone()[0].startswith("el partido aún")


def test_marcador_del_dia_crea_los_id_de_la_nba_una_vez(base_migrada, tmp_path):
    db = base_migrada
    for codigo, (loc, vis) in {"401x": ("CLE", "OKC"), "401y": ("CHA", "DET"), "401z": ("IND", "ATL")}.items():
        identidad.partido(db, "espn", codigo, date(2026, 11, 2), identidad.equipo(db, loc), identidad.equipo(db, vis),
                          "2026-27")
    ahora = datetime(2026, 11, 2, 18, 0, tzinfo=UTC)                  # 13:00 ET
    obtener, visitas = servidor({cdn.URL_MARCADOR: MARCADOR})
    r = cdn.capturar(db, obtener, tmp_path, ahora)
    assert r["marcador"] == 1 and visitas == [cdn.URL_MARCADOR]
    assert db.execute("SELECT count(*) FROM nba.entidad WHERE tipo = 'partido' AND canonica_id = entidad_id").fetchone()[0] == 3
    assert db.execute("SELECT count(*) FROM nba.entidad WHERE fuente = 'nba_oficial' AND tipo = 'partido'").fetchone()[0] == 3
    obtener2, visitas2 = servidor({cdn.URL_MARCADOR: MARCADOR})
    cdn.capturar(db, obtener2, tmp_path, ahora + timedelta(hours=1))
    assert visitas2 == []


def test_marcador_no_se_pide_antes_de_las_10_et(base_migrada, tmp_path):
    db = base_migrada
    identidad.partido(db, "espn", "401x", date(2026, 11, 2), identidad.equipo(db, "CLE"), identidad.equipo(db, "OKC"),
                      "2026-27")
    obtener, visitas = servidor({cdn.URL_MARCADOR: MARCADOR})
    cdn.capturar(db, obtener, tmp_path, datetime(2026, 11, 2, 12, 0, tzinfo=UTC))             # 07:00 ET
    assert visitas == []


def test_un_alias_sintetico_del_parte_no_cuenta_como_id_de_la_nba(base_migrada, tmp_path):
    db = base_migrada
    loc, vis = identidad.equipo(db, "CLE"), identidad.equipo(db, "OKC")
    identidad.partido(db, "espn", "401x", date(2026, 11, 2), loc, vis, "2026-27")
    identidad.partido(db, "nba_oficial", "2026-11-02:OKC@CLE", date(2026, 11, 2), loc, vis, "2026-27")   # del PDF de lesiones
    obtener, visitas = servidor({cdn.URL_MARCADOR: MARCADOR})
    cdn.capturar(db, obtener, tmp_path, datetime(2026, 11, 2, 18, 0, tzinfo=UTC))
    assert visitas == [cdn.URL_MARCADOR]                                                              # igual se pide el marcador
    assert db.execute("SELECT count(*) FROM nba.entidad WHERE id_en_fuente = '0022600158'").fetchone()[0] == 1


def test_un_final_solo_con_alias_sintetico_no_pide_ningun_box(base_migrada, tmp_path):
    db = base_migrada
    local, visitante = identidad.equipo(db, "DET"), identidad.equipo(db, "BOS")
    espn = identidad.partido(db, "espn", "401", date(2026, 10, 20), local, visitante, "2026-27")
    identidad.partido(db, "nba_oficial", "2026-10-20:BOS@DET", date(2026, 10, 20), local, visitante, "2026-27")
    carga.guardar_datos(db, [DatoNuevo(partido_id=espn, entidad_id=espn, metrica="estado_partido", fase="final",
                                       fuente="espn", recibido_en=T, etiqueta="final")])
    obtener, visitas = servidor(CUERPOS)
    cdn.capturar(db, obtener, tmp_path, T + timedelta(minutes=30))
    assert all("boxscore" not in u and "playbyplay" not in u for u in visitas)         # solo intenta el marcador del día
