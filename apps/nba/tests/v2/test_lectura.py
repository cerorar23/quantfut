from decimal import Decimal

import psycopg
import pytest

from ayudas import nueva_captura, nueva_cuota, nueva_entidad, nuevo_dato


@pytest.fixture
def mundo(base_migrada):
    db = base_migrada
    return db, nueva_entidad(db, "partido", "g1"), nueva_entidad(db, "jugador", "p1")


def a_las(db, corte):
    cols = "dato_id, fuente, valor, etiqueta"
    return db.execute(f"SELECT {cols} FROM nba.dato_a_las(%s) ORDER BY dato_id", (corte,)).fetchall()


def test_dato_a_las_no_ve_el_futuro_y_el_corte_es_inclusivo(mundo):
    db, p, j = mundo
    d = nuevo_dato(db, p, j, recibido="2026-11-01T12:00:00Z")
    assert a_las(db, "2026-11-01T11:59:59Z") == []
    assert [f[0] for f in a_las(db, "2026-11-01T12:00:00Z")] == [d]


def test_prioridad_gana_en_metricas_de_prioridad(mundo):
    db, p, j = mundo
    oficial = nuevo_dato(db, p, j, valor=20.0, fuente="nba_oficial", recibido="2026-11-01T12:00:00Z")
    nuevo_dato(db, p, j, valor=21.0, fuente="sofascore", recibido="2026-11-01T13:00:00Z")
    filas = a_las(db, "2026-11-02T00:00:00Z")
    assert [(f[0], f[1]) for f in filas] == [(oficial, "nba_oficial")]


def test_misma_fuente_y_mismo_instante_desempata_por_dato_id(mundo):
    db, p, j = mundo
    c1, c2 = nueva_captura(db), nueva_captura(db)
    nuevo_dato(db, p, j, valor=20.0, captura_id=c1)
    ultimo = nuevo_dato(db, p, j, valor=22.0, captura_id=c2)
    assert [f[0] for f in a_las(db, "2026-11-02T00:00:00Z")] == [ultimo]


def test_por_fuente_devuelve_una_fila_por_fuente_la_mas_reciente(mundo):
    db, p, j = mundo
    kw = dict(nombre="estado_disponibilidad", valor=None, fase="pre")
    nuevo_dato(db, p, j, etiqueta="Questionable", fuente="espn", recibido="2026-11-01T10:00:00Z", **kw)
    espn_nuevo = nuevo_dato(db, p, j, etiqueta="Out", fuente="espn", recibido="2026-11-01T12:00:00Z", **kw)
    rw = nuevo_dato(db, p, j, etiqueta="Ques", fuente="rotowire", recibido="2026-11-01T11:00:00Z", **kw)
    filas = a_las(db, "2026-11-01T13:00:00Z")
    assert {(f[0], f[1], f[3]) for f in filas} == {(espn_nuevo, "espn", "Out"), (rw, "rotowire", "Ques")}
    antes = a_las(db, "2026-11-01T10:30:00Z")
    assert [(f[1], f[3]) for f in antes] == [("espn", "Questionable")]


def test_dato_vigente_equivale_a_dato_a_las_ahora(mundo):
    db, p, j = mundo
    nuevo_dato(db, p, j, recibido="2026-11-01T12:00:00Z")
    nuevo_dato(db, p, j, nombre="minutos", valor=33.0, recibido="2026-11-01T12:00:00Z")
    vigentes = {r[0] for r in db.execute("SELECT dato_id FROM nba.dato_vigente")}
    ahora = {r[0] for r in db.execute("SELECT dato_id FROM nba.dato_a_las(now())")}
    assert vigentes == ahora and len(vigentes) == 2


def test_conflicto_lista_solo_marcadas(mundo):
    db, p, j = mundo
    db.execute("INSERT INTO nba.dato (partido_id, entidad_id, metrica_id, valor, fase, fuente, recibido_en, conflicto) "
               "SELECT %s, %s, metrica_id, 9, 'final', 'sofascore', now(), true FROM nba.metrica WHERE nombre='puntos'",
               (p, j))
    nuevo_dato(db, p, j, fuente="nba_oficial", valor=10.0)
    assert [r[0] for r in db.execute("SELECT fuente FROM nba.conflicto")] == ["sofascore"]


def test_cuota_cierre_toma_la_ultima_del_cierre_e_ignora_pre(mundo):
    db, p, _ = mundo
    nueva_cuota(db, p, Decimal("1.80"), "local", fase="cierre", recibido="2026-11-01T20:00:00Z")
    ultima = nueva_cuota(db, p, Decimal("1.85"), "local", fase="cierre", recibido="2026-11-01T21:00:00Z")
    nueva_cuota(db, p, Decimal("1.70"), "local", fase="pre", recibido="2026-11-01T22:00:00Z")
    assert [r[0] for r in db.execute("SELECT cuota_id FROM nba.cuota_cierre")] == [ultima]


def test_cuota_margen_dos_lados(mundo):
    db, p, _ = mundo
    nueva_cuota(db, p, Decimal("1.91"), "over", mercado="total", linea=Decimal("221.5"), contrato="t1")
    nueva_cuota(db, p, Decimal("1.91"), "under", mercado="total", linea=Decimal("221.5"), contrato="t1")
    fila = db.execute("SELECT n_lados, margen FROM nba.cuota_margen WHERE mercado = 'total'").fetchone()
    assert fila[0] == 2 and abs(fila[1] - (2 / Decimal("1.91") - 1)) < Decimal("1e-9")


def test_cuota_margen_empareja_los_lados_de_un_handicap_con_lineas_opuestas(mundo):
    db, p, _ = mundo
    nueva_cuota(db, p, Decimal("1.91"), "local", mercado="spreads", linea=Decimal("-4.5"), contrato="s1")
    nueva_cuota(db, p, Decimal("1.91"), "visit", mercado="spreads", linea=Decimal("4.5"), contrato="s1")
    fila = db.execute("SELECT n_lados, margen, linea_abs FROM nba.cuota_margen WHERE mercado = 'spreads'").fetchone()
    assert fila[0] == 2 and abs(fila[1] - (2 / Decimal("1.91") - 1)) < Decimal("1e-9") and fila[2] == Decimal("4.5")


def con_rol(db, rol):
    db.execute(psycopg.sql.SQL("SET ROLE {}").format(psycopg.sql.Identifier(rol)))


def test_escritor_inserta_pero_no_actualiza_ni_borra(mundo):
    db, p, j = mundo
    con_rol(db, "nba_escritor")
    nuevo_dato(db, p, j)
    for sentencia in ("UPDATE nba.dato SET fase = fase", "DELETE FROM nba.dato", "TRUNCATE nba.dato"):
        db.execute("SAVEPOINT s")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            db.execute(sentencia)
        db.execute("ROLLBACK TO SAVEPOINT s")


def test_lector_solo_lee(mundo):
    db, p, j = mundo
    nuevo_dato(db, p, j)
    con_rol(db, "nba_lector")
    assert db.execute("SELECT count(*) FROM nba.dato_vigente").fetchone()[0] == 1
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        nuevo_dato(db, p, j, valor=99.0)
