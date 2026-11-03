from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from nba.v2.fuentes import parte_oficial as po

PDF = (Path(__file__).parent / "fixtures" / "parte_oficial_2025-10-21_06PM.pdf").read_bytes()
URL = po.BASE + "Injury-Report_2025-10-21_06PM.pdf"
AHORA = datetime(2025, 10, 21, 23, 0, tzinfo=UTC)          # 19:00 ET


def test_extraer_parte_real():
    r = po.extraer(PDF, AHORA)
    assert r.emitido_utc == datetime(2025, 10, 21, 22, 30, tzinfo=UTC)          # «06:30 PM» ET
    assert len(r.filas) == 69 and sum(not f.enviado for f in r.filas) == 6
    assert {f.estado for f in r.filas if f.enviado} == {"Out", "Doubtful", "Questionable", "Probable", "Available"}
    crawford = next(f for f in r.filas if f.jugador == "Isaiah Crawford")
    assert (crawford.visitante, crawford.local, crawford.estado, crawford.fecha_juego) == (
        "HOU", "OKC", "Out", date(2025, 10, 21))
    assert crawford.motivo.startswith("Injury/Illness")


def test_nombre_directo():
    assert po.nombre_directo("Williams III, Jaylin") == "Jaylin Williams III"
    assert po.nombre_directo("Murray, Keegan") == "Keegan Murray"


def test_extraer_rechaza_lo_que_no_es_un_parte_valido():
    with pytest.raises(ValueError, match="PDF"):
        po.extraer(b"<html>403</html>", AHORA)
    with pytest.raises(ValueError, match="después"):
        po.extraer(PDF, datetime(2025, 10, 21, 20, 0, tzinfo=UTC))          # llegó antes de emitirse
    with pytest.raises(ValueError, match="ilegible"):
        po.extraer(b"%PDF-1.4 roto", AHORA)


def test_urls_candidatas_son_las_horas_recientes_del_dia_et():
    urls = po.urls_candidatas(datetime(2026, 11, 2, 22, 40, tzinfo=UTC))           # 17:40 ET
    assert [u.rsplit("_", 1)[-1] if u.endswith("_30PM.pdf") else u.rsplit("Report_", 1)[1] for u in urls] == [
        "2026-11-02_04PM.pdf", "30PM.pdf", "2026-11-02_05PM.pdf", "30PM.pdf"]
    assert po.urls_candidatas(datetime(2026, 11, 2, 12, 0, tzinfo=UTC)) == []        # 07:00 ET: aún no hay partes


def servir(db_pdf=PDF):
    def obtener(url):
        return (200, db_pdf) if url == URL else (403, b"<Error/>")
    return obtener


def test_capturar_carga_el_parte_y_es_idempotente(base_migrada, tmp_path):
    db = base_migrada
    r = po.capturar(db, servir(), tmp_path, AHORA)
    assert r["partes_nuevos"] == 1 and r["datos"] > 100 and r["fallidos"] == 0
    por = dict(db.execute("SELECT m.nombre, count(*) FROM nba.dato d JOIN nba.metrica m USING (metrica_id) "
                          "WHERE d.fuente = 'nba_oficial' GROUP BY 1").fetchall())
    assert por["estado_disponibilidad"] == 63 and por["motivo_disponibilidad"] == 63 and por["reporte_no_enviado"] == 6
    assert db.execute("SELECT count(*) FROM nba.captura WHERE ok").fetchone()[0] == 1
    r2 = po.capturar(db, servir(), tmp_path, AHORA)
    assert r2["partes_nuevos"] == 0 and r2["datos"] == 0
    assert (tmp_path / "nba_oficial").is_dir()


def test_partes_aun_no_publicados_no_son_error(base_migrada, tmp_path):
    r = po.capturar(base_migrada, lambda url: (403, b"<Error/>"), tmp_path, AHORA)
    assert r["ok"] and r["partes_nuevos"] == 0
    assert base_migrada.execute("SELECT count(*) FROM nba.captura WHERE NOT ok AND http_status = 403").fetchone()[0] > 0
    # no se vuelve a pedir lo mismo antes de la espera
    antes = base_migrada.execute("SELECT count(*) FROM nba.captura").fetchone()[0]
    po.capturar(base_migrada, lambda url: (403, b"<Error/>"), tmp_path, AHORA + timedelta(minutes=5))
    assert base_migrada.execute("SELECT count(*) FROM nba.captura").fetchone()[0] == antes


def test_pdf_con_diseno_distinto_queda_como_captura_fallida_sin_datos(base_migrada, tmp_path):
    r = po.capturar(base_migrada, servir(b"%PDF-1.4\n%%EOF"), tmp_path, AHORA)
    assert not r["ok"] and r["fallidos"] == 1
    assert base_migrada.execute("SELECT count(*) FROM nba.dato").fetchone()[0] == 0
    assert base_migrada.execute("SELECT error FROM nba.captura WHERE sha256 IS NOT NULL").fetchone()[0]


def test_el_mismo_jugador_del_parte_se_une_al_de_otras_fuentes(base_migrada, tmp_path):
    from nba.v2 import identidad
    db = base_migrada
    espn = identidad.jugador(db, "espn", "4433255", "Isaiah Crawford")
    po.capturar(db, servir(), tmp_path, AHORA)
    oficial = db.execute("SELECT canonica_id FROM nba.entidad WHERE fuente = 'nba_oficial' AND tipo = 'jugador' "
                         "AND nombre = 'Isaiah Crawford'").fetchone()[0]
    assert oficial == espn
