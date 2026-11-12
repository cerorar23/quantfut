"""Reglas de acceso versionadas por fecha de lote (db/111).

Las pruebas 1, 2, 5 y 6 corren sin base (sustituyen `_cargar`); la 3 y la 4 usan Postgres
real y se omiten sin `QF_TEST_PG_DSN` (corren en CI). Nunca apuntarlo a producción.
"""
import os
from datetime import date, datetime, timedelta, timezone

import pytest

from qf.api import mobile
from qf.comercial import acceso_reglas as ar

D, D1 = date(2026, 11, 10), date(2026, 11, 11)


def regla(rid, desde, lo=.73, hi=.95, fr=.10):
    return ar.Regla(rid, desde, lo, hi, fr, 'test', None, 'n')


def fijar(monkeypatch, *reglas):
    monkeypatch.setattr(ar, '_cargar', lambda: sorted(reglas, key=lambda r: (r.vigente_desde, r.regla_id)))
    ar.invalidar_cache()


def fila(i, batch, prob=.80, price=1.45, kick=None):
    return {'match_id': f'{batch}-{i}', 'market': 'totals', 'selection': 'over', 'line': 1.5,
            'prob': prob, 'ref_price': price, 'local': 'A', 'visitante': 'B', 'batch_date': batch.isoformat(),
            'kickoff_utc': kick or datetime.now(timezone.utc) + timedelta(days=1)}


def lote(batch, n):
    return [fila(i, batch, prob=.75 + i / 200) for i in range(1, n + 1)]


SEMILLA = regla(1, date(2000, 1, 1))


def test_regla_que_sube_la_fraccion_no_toca_el_lote_anterior(monkeypatch):
    fijar(monkeypatch, SEMILLA, regla(2, D1, fr=.50))
    antes, despues = lote(D, 10), lote(D1, 10)
    assert len(mobile.choose_free(antes, 'alta_probabilidad')) == 1       # 10 %
    assert len(mobile.choose_free(despues, 'alta_probabilidad')) == 5     # 50 %
    # top_up y cap_free también usan la regla DEL LOTE: el D no gana gratis por haber subido la fracción.
    now = datetime.now(timezone.utc)
    assert mobile.top_up(antes, {mobile.pick_key(antes[-1])}, now) == []
    libres = {mobile.pick_key(r) for r in antes}
    assert len(mobile.cap_free(antes, libres, now)) == 1
    assert len(mobile.cap_free(despues, {mobile.pick_key(r) for r in despues}, now)) == 5


def test_regla_que_baja_la_fraccion_no_pone_candado_a_los_abiertos_del_lote_anterior(monkeypatch):
    fijar(monkeypatch, regla(1, date(2000, 1, 1), fr=.50), regla(2, D1, fr=.10))
    now = datetime.now(timezone.utc)
    antes = lote(D, 10)
    libres = {mobile.pick_key(r) for r in mobile.choose_free(antes, 'alta_probabilidad')}
    assert len(libres) == 5
    assert mobile.cap_free(antes, libres, now) == libres                   # siguen gratis
    assert len(mobile.choose_free(lote(D1, 10), 'alta_probabilidad')) == 1


def test_el_rango_nuevo_filtra_el_lote_nuevo_pero_no_el_anterior(monkeypatch):
    fijar(monkeypatch, SEMILLA, regla(2, D1, lo=.85, hi=.90, fr=1.0))
    assert len(mobile.choose_free([fila(1, D, prob=.74)], 'alta_probabilidad')) == 1
    assert mobile.choose_free([fila(1, D1, prob=.74)], 'alta_probabilidad') == []


def test_misma_fecha_gana_la_ultima(monkeypatch):
    fijar(monkeypatch, SEMILLA, regla(2, D1, fr=.20), regla(3, D1, fr=.30), regla(4, date(2026, 12, 1), fr=.9))
    assert ar.vigente(D1).regla_id == 3
    assert ar.vigente('2026-11-20').regla_id == 3
    assert ar.vigente(D).regla_id == 1
    assert ar.vigente(datetime(2026, 12, 1, 5, tzinfo=timezone.utc)).regla_id == 4


def test_config_informa_la_regla_de_hoy(monkeypatch):
    hoy = ar.hoy_utc()
    fijar(monkeypatch, SEMILLA, regla(2, hoy, lo=.80, hi=.90, fr=.25),
          regla(3, hoy + timedelta(days=1), lo=.70, hi=.95, fr=.40))
    monkeypatch.setattr(mobile.mobile_updates, 'configuration', lambda: dict(mobile.mobile_updates.DEFAULTS))
    monkeypatch.setattr(mobile, 'features', lambda: {})
    cfg = mobile.config()
    assert (cfg['probability_min'], cfg['probability_max'], cfg['high_probability_free_fraction']) == (.80, .90, .25)
    assert cfg['ladder_free_count'] == 1


def test_sin_tabla_rigen_los_valores_de_hoy(monkeypatch):
    from psycopg.errors import UndefinedTable
    monkeypatch.undo()   # quita el parche de conftest: la lectura real
    ar.invalidar_cache()

    def sin_tabla(*a, **k):
        raise UndefinedTable('no existe')
    monkeypatch.setattr(ar, 'query', sin_tabla)
    monkeypatch.setattr(ar, 'query_one', sin_tabla)
    ar.invalidar_cache()
    r = ar.vigente(D)
    assert (r.prob_min, r.prob_max, r.free_fraction) == (.73, .95, .10) and ar.dias_agenda() == 7
    ar.invalidar_cache()


def test_validar_rechaza_fechas_rangos_y_notas_invalidos():
    manana = ar.manana_utc()
    assert ar.validar('0.73', '0.95', '0.10', manana, 'ok')
    for args in [('0.73', '0.95', '0.10', ar.hoy_utc(), 'ok'),        # hoy
                 ('0.61', '0.95', '0.10', manana, 'ok'),              # por debajo de lo que se sella
                 ('0.73', '0.96', '0.10', manana, 'ok'),
                 ('0.90', '0.90', '0.10', manana, 'ok'),
                 ('0.73', '0.95', '1.10', manana, 'ok'),
                 ('0.73', '0.95', '0.10', manana, '  ')]:
        with pytest.raises(ValueError):
            ar.validar(*args)


# --- Postgres real (db/*.sql aplicados) ----------------------------------------------------------
DSN = os.getenv('QF_TEST_PG_DSN')
pg = pytest.mark.skipif(not DSN, reason='sin QF_TEST_PG_DSN')


@pytest.fixture
def base(monkeypatch):
    from psycopg_pool import ConnectionPool
    from qf import db
    pool = ConnectionPool(DSN, min_size=1, max_size=2, open=True)
    monkeypatch.setattr(db, '_pool', pool)
    yield db
    pool.close()


@pg
def test_el_trigger_rechaza_hoy_pasado_update_y_delete(base):
    import psycopg
    hoy = ar.hoy_utc()
    insertar = ("INSERT INTO acceso_reglas (stream, vigente_desde, prob_min, prob_max, free_fraction, "
                "creado_por, nota) VALUES ('alta_probabilidad', %s, 0.73, 0.95, 0.10, 't', 'n')")
    for dia in (hoy, hoy - timedelta(days=3)):
        with pytest.raises(psycopg.errors.RaiseException):
            with base.conn() as c:
                c.execute(insertar, (dia,))
    with pytest.raises(psycopg.errors.CheckViolation):    # fuera de 62-95 %
        with base.conn() as c:
            c.execute("INSERT INTO acceso_reglas (stream, vigente_desde, prob_min, prob_max, free_fraction, "
                      "creado_por, nota) VALUES ('alta_probabilidad', %s, 0.50, 0.95, 0.10, 't', 'n')",
                      (hoy + timedelta(days=1),))
    with pytest.raises(psycopg.errors.RaiseException):
        with base.conn() as c:
            c.execute("UPDATE acceso_reglas SET nota='x'")
    with pytest.raises(psycopg.errors.RaiseException):
        with base.conn() as c:
            c.execute("DELETE FROM acceso_reglas")


@pg
def test_el_historial_conserva_los_pronosticos_del_lote_viejo_fuera_del_rango_nuevo(base):
    """El mismo JOIN LATERAL de `high_rows()`/`markets_history()`, sobre lotes y pronósticos de juguete."""
    hoy = ar.hoy_utc()
    ayer, manana = hoy - timedelta(days=1), hoy + timedelta(days=1)
    # Las dos filas de juguete se evalúan con una regla nueva (rango estrecho) que NO alcanza al lote viejo.
    with base.conn() as c:
        c.execute("CREATE TEMP TABLE a (id int, prob numeric, batch_date date)")
        c.execute("INSERT INTO a VALUES (1, 0.74, %s), (2, 0.74, %s), (3, 0.88, %s)", (ayer, manana, manana))
        c.execute("CREATE TEMP TABLE b AS SELECT DISTINCT batch_date FROM a")
        c.execute("INSERT INTO acceso_reglas (stream, vigente_desde, prob_min, prob_max, free_fraction, "
                  "creado_por, nota) VALUES ('alta_probabilidad', %s, 0.85, 0.90, 0.10, 'test', 'prueba')",
                  (manana,))
        try:
            filas = c.execute(f"SELECT a.id FROM a JOIN b ON b.batch_date=a.batch_date {ar.RANGO_SQL} "
                              f"WHERE {ar.RANGO_WHERE} ORDER BY a.id", (.73, .95)).fetchall()
        finally:
            c.rollback()
    assert [f['id'] for f in filas] == [1, 3]    # el 74 % de ayer se conserva; el de mañana queda fuera
