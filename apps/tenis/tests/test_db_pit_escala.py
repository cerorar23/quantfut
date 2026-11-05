"""Regresión de la lectura PIT por conjunto (0004): coincide con la fórmula original por fila y escala.

Contexto: `partido_a_las` y las demás llamaban por fila a `lunes_partido_a_las` (que recorre las ediciones): 2.000 partidos
tardaban 1,9 s y 8.000 tardaban 13,7 s. Ahora usan `lunes_por_partido_a_las` en una pasada. Esta prueba comprueba que el
resultado NO cambió (referencia = la definición antigua escrita aquí, por otro camino) y que el tiempo es razonable.
"""
import sys
import time
from pathlib import Path

import pytest

psycopg = pytest.importorskip("psycopg")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ops"))
from medir_pit import crear  # noqa: E402

# Definición ANTIGUA (por fila) como referencia independiente de la función nueva.
REFERENCIA_RESULTADO = """
    SELECT DISTINCT ON (x.partido_id) x.resultado_id
    FROM resultado x JOIN fuente f ON f.fuente = x.fuente JOIN recibo r ON r.recibo_id = x.recibo_id
    WHERE x.recibido_en <= %(c)s AND retro_visible(%(c)s, r.retro, lunes_partido_a_las(x.partido_id, %(c)s))
    ORDER BY x.partido_id, f.prioridad_resultado, x.recibido_en DESC, x.resultado_id DESC
"""
REFERENCIA_PARTIDO = """
    SELECT p.partido_id FROM partido p JOIN recibo r ON r.recibo_id = p.recibo_id
    WHERE p.recibido_en <= %(c)s AND retro_visible(%(c)s, r.retro, lunes_partido_a_las(p.partido_id, %(c)s))
"""
CORTES = ["2026-10-16T00:00:00Z", "2026-10-17T02:00:00Z", "2026-10-19T00:00:00Z", "2026-10-20T00:00:00Z",
          "2026-11-05T00:00:00Z", "2027-01-01T00:00:00Z"]


@pytest.fixture
def mundo(dsn):
    db, esquema = crear(dsn, 1500)
    try:
        # Un recibo posterior y no retro para una corrección de edición y datos nuevos.
        rid = db.execute(
            "INSERT INTO recibo (fuente, recurso, recibido_en, estado_http, sha256, ruta_objeto, bytes, lote, retro) "
            "VALUES ('tml', 'correccion', '2026-10-18T00:00:00Z', 200, repeat('b', 64), "
            "'objetos/bb/' || repeat('b', 64) || '.json.gz', 1, 'correccion', false) RETURNING recibo_id").fetchone()[0]
        # Edición con fin reciente: sus datos retro solo se ven tras 2026-10-19.
        db.execute("INSERT INTO edicion (torneo_id, temporada, lunes_semana, superficie, indoor, fuente, recibo_id, recibido_en) "
                   "SELECT min(torneo_id), 2026, DATE '2026-10-12', 'hard', false, 'tml', "
                   "(SELECT min(recibo_id) FROM recibo), '2026-10-17T01:00:00Z' FROM torneo")
        # Corrección de una edición antigua: cambia su lunes de fin y por tanto la visibilidad retro de sus partidos.
        db.execute("INSERT INTO edicion (torneo_id, temporada, lunes_semana, superficie, indoor, fuente, recibo_id, recibido_en) "
                   "SELECT torneo_id, temporada, DATE '2026-10-26', 'hard', false, 'tml', %s, '2026-10-18T00:00:00Z' "
                   "FROM edicion ORDER BY edicion_id LIMIT 1", (rid,))
        # Partidos de la edición reciente (retro) y un resultado nuevo no retro de un partido antiguo.
        db.execute("INSERT INTO partido (edicion_id, ronda, jugador_1, jugador_2, mejor_de, fuente, recibo_id, recibido_en) "
                   "SELECT (SELECT max(edicion_id) - 1 FROM edicion), 'R' || (i % 5 + 1), "
                   "(SELECT min(jugador_id) FROM jugador) + i, (SELECT min(jugador_id) FROM jugador) + 1500 + i, 3, 'tml', "
                   "(SELECT min(recibo_id) FROM recibo), '2026-10-17T01:00:00Z' FROM generate_series(1, 40) i")
        db.execute("INSERT INTO resultado (partido_id, estado, ganador, sets, sets_completos, fuente, recibo_id, recibido_en) "
                   "SELECT partido_id, 'completado', 2, '[[3,6,null,null],[4,6,null,null]]'::jsonb, 2, 'tml', "
                   "(SELECT min(recibo_id) FROM recibo), '2026-10-17T01:00:00Z' "
                   "FROM partido WHERE partido_id > (SELECT max(partido_id) - 40 FROM partido)")
        db.execute("INSERT INTO resultado (partido_id, estado, ganador, sets, sets_completos, fuente, recibo_id, recibido_en) "
                   "SELECT partido_id, 'completado', 2, '[[6,7,null,null],[6,3,null,null],[2,6,null,null]]'::jsonb, 3, 'tml', "
                   "%s, '2026-10-18T06:00:00Z' FROM partido ORDER BY partido_id LIMIT 200", (rid,))
        yield db
    finally:
        db.execute(f"DROP SCHEMA {esquema} CASCADE")
        db.execute(f"DROP SCHEMA {esquema}_op CASCADE")
        db.close()


@pytest.mark.parametrize("corte", CORTES)
def test_resultado_y_partido_coinciden_con_la_formula_por_fila(mundo, corte):
    nuevo = {r[0] for r in mundo.execute("SELECT resultado_id FROM resultado_a_las(%s)", (corte,))}
    ref = {r[0] for r in mundo.execute(REFERENCIA_RESULTADO, {"c": corte})}
    assert nuevo == ref
    nuevo_p = {r[0] for r in mundo.execute("SELECT partido_id FROM partido_a_las(%s)", (corte,))}
    ref_p = {r[0] for r in mundo.execute(REFERENCIA_PARTIDO, {"c": corte})}
    assert nuevo_p == ref_p


def test_los_cortes_distinguen_casos(mundo):
    """La prueba de equivalencia no sería informativa si todos los cortes dieran lo mismo."""
    tamanos = [mundo.execute("SELECT count(*) FROM resultado_a_las(%s)", (c,)).fetchone()[0] for c in CORTES]
    assert len(set(tamanos)) >= 4, tamanos
    assert tamanos[0] == 0


def test_escala_sin_crecer_mas_que_lineal(dsn):
    db, esquema = crear(dsn, 20000)
    try:
        t = time.perf_counter()
        filas = db.execute("SELECT count(*) FROM resultado_a_las('2026-11-05T00:00:00Z')").fetchone()[0]
        segundos = time.perf_counter() - t
        assert filas == 20000
        assert segundos < 5.0, f"resultado_a_las con 20.000 partidos tardó {segundos:.1f} s (medido 0,2 s; antes ~60 s)"
    finally:
        db.execute(f"DROP SCHEMA {esquema} CASCADE")
        db.execute(f"DROP SCHEMA {esquema}_op CASCADE")
        db.close()
