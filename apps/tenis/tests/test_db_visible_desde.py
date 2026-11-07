"""`visible_desde` por dato retro (0004): la fatiga intratorneo ve las rondas anteriores y nunca la propia.

Torneo de 2025 que termina el domingo 2025-03-16 (regla por semana: datos retro visibles tras 2025-03-17).
R1 se conoce el 05-mar, R2 el 08-mar; el dato sin `visible_desde` sigue la regla por semana.
"""
import pytest
from psycopg.types.json import Jsonb

from db_util import cargar_minimo, insertar, nuevo_recibo, ts

SETS = Jsonb([[6, 3, None, None], [6, 4, None, None]])


def _partido(db, edicion, ronda, j1, j2, recibo, visible):
    return insertar(db, "INSERT INTO partido (edicion_id, ronda, jugador_1, jugador_2, mejor_de, fuente, recibo_id, "
                        "recibido_en, visible_desde) VALUES (%s, %s, %s, %s, 3, 'tml', %s, %s, %s) RETURNING partido_id",
                    (edicion, ronda, j1, j2, recibo, ts("2026-10-17"), visible))


def _resultado(db, partido, recibo, visible):
    return insertar(db, "INSERT INTO resultado (partido_id, estado, ganador, sets, sets_completos, fuente, recibo_id, "
                        "recibido_en, visible_desde) VALUES (%s, 'completado', 1, %s, 2, 'tml', %s, %s, %s) "
                        "RETURNING resultado_id", (partido, SETS, recibo, ts("2026-10-17"), visible))


@pytest.fixture
def torneo_retro(esquema):
    with esquema.conectar() as db:
        d = cargar_minimo(db)
        rr = nuevo_recibo(db, "tml", "2026-10-17", retro=True)
        a, b, c, e = d["jugadores"]
        ed = insertar(db, "INSERT INTO edicion (torneo_id, temporada, lunes_semana, fecha_fin, superficie, indoor, "
                          "fuente, recibo_id, recibido_en, visible_desde) VALUES (%s, 2025, '2025-03-10', '2025-03-16', "
                          "'hard', false, 'tml', %s, %s, %s) RETURNING edicion_id",
                      (d["torneo"], rr, ts("2026-10-17"), ts("2025-03-03")))
        p1 = _partido(db, ed, "R1", a, b, rr, ts("2025-03-04"))
        p2 = _partido(db, ed, "R2", a, c, rr, ts("2025-03-07"))
        p3 = _partido(db, ed, "R3", a, e, rr, None)  # sin visible_desde: regla por semana
        r1 = _resultado(db, p1, rr, ts("2025-03-05T18:00:00Z"))
        r2 = _resultado(db, p2, rr, ts("2025-03-08T18:00:00Z"))
        r3 = _resultado(db, p3, rr, None)
        yield db, dict(ed=ed, p1=p1, p2=p2, p3=p3, r1=r1, r2=r2, r3=r3)


def _ids(db, funcion, columna, corte):
    return {x[0] for x in db.execute(f"SELECT {columna} FROM {funcion}(%s)", (ts(corte),))}


def test_la_ronda_anterior_se_ve_y_la_propia_no(torneo_retro):
    db, t = torneo_retro
    corte = "2025-03-07T09:00:00Z"  # un día antes de que termine R2
    resultados = _ids(db, "resultado_a_las", "resultado_id", corte)
    assert t["r1"] in resultados          # R1 ya conocido: la fatiga puede usarlo
    assert t["r2"] not in resultados      # el propio partido de ese día aún no
    assert t["r3"] not in resultados      # sin visible_desde: regla por semana, oculto hasta 2025-03-17


def test_la_edicion_y_los_partidos_son_visibles_antes_de_acabar_la_semana(torneo_retro):
    db, t = torneo_retro
    assert t["ed"] in _ids(db, "edicion_a_las", "edicion_id", "2025-03-03T12:00:00Z")   # superficie y formato conocidos
    partidos = _ids(db, "partido_a_las", "partido_id", "2025-03-07T09:00:00Z")
    assert {t["p1"], t["p2"]} <= partidos and t["p3"] not in partidos


def test_el_limite_es_estricto_y_sin_visible_desde_manda_la_semana(torneo_retro):
    db, t = torneo_retro
    assert t["r1"] not in _ids(db, "resultado_a_las", "resultado_id", "2025-03-05T18:00:00Z")   # corte == visible_desde
    assert t["r1"] in _ids(db, "resultado_a_las", "resultado_id", "2025-03-05T18:00:01Z")
    assert t["r3"] not in _ids(db, "resultado_a_las", "resultado_id", "2025-03-17T00:00:00Z")   # corte == lunes + 7
    assert t["r3"] in _ids(db, "resultado_a_las", "resultado_id", "2025-03-17T00:00:01Z")
    todos = _ids(db, "resultado_a_las", "resultado_id", "2026-11-05T00:00:00Z")
    assert {t["r1"], t["r2"], t["r3"]} <= todos


def test_un_dato_no_retro_ignora_visible_desde(esquema):
    with esquema.conectar() as db:
        d = cargar_minimo(db)
        r = nuevo_recibo(db, "tml", "2026-01-05", retro=False)
        a, _, c, _ = d["jugadores"]
        p = _partido(db, d["edicion"], "R16", a, c, r, None)     # partido nuevo: sin otra fuente que lo tape
        res = _resultado(db, p, r, ts("2030-01-01"))             # visible_desde en el futuro: no cuenta si no es retro
        # El ayudante recibe todo el 2026-10-17: un corte posterior lo ve aunque visible_desde sea 2030 (no es retro).
        assert res in _ids(db, "resultado_a_las", "resultado_id", "2026-11-01T00:00:00Z")
        assert res not in _ids(db, "resultado_a_las", "resultado_id", "2026-10-16T00:00:00Z")   # y antes de recibirlo, no


def test_un_dato_retro_es_visible_para_un_corte_anterior_a_su_descarga(esquema):
    """Defecto hallado el 5-nov: el filtro recibido_en <= corte ocultaba toda la historia retro (descargada en 2026)."""
    with esquema.conectar() as db:
        d = cargar_minimo(db)
        rr = nuevo_recibo(db, "tml", "2026-10-17", retro=True)
        a, _, c, _ = d["jugadores"]
        ed = insertar(db, "INSERT INTO edicion (torneo_id, temporada, lunes_semana, fecha_fin, superficie, indoor, fuente, "
                          "recibo_id, recibido_en) VALUES (%s, 2023, '2023-03-13', '2023-03-19', 'clay', false, 'tml', %s, %s) "
                          "RETURNING edicion_id", (d["torneo"], rr, ts("2026-10-17")))
        p = _partido(db, ed, "R32", a, c, rr, None)
        res = _resultado(db, p, rr, None)
        assert res not in _ids(db, "resultado_a_las", "resultado_id", "2023-03-15T00:00:00Z")   # semana aún en curso
        assert res in _ids(db, "resultado_a_las", "resultado_id", "2023-03-21T00:00:00Z")       # semana cerrada, descarga futura
