"""Lectura punto en el tiempo (0004): visibilidad por corte, regla RETRO, desempates, alias y ranking."""
import pytest

psycopg = pytest.importorskip("psycopg")
from psycopg.types.json import Jsonb  # noqa: E402

from db_util import cargar_minimo, insertar, nuevo_recibo, ts  # noqa: E402


def insertar_asercion(db, jugador, campo, valor, fuente, recibido):
    r = nuevo_recibo(db, fuente, recibido)
    db.execute("INSERT INTO jugador_asercion (jugador_id, campo, valor, fuente, recibo_id, recibido_en) "
               "VALUES (%s, %s, %s, %s, %s, %s)", (jugador, campo, valor, fuente, r, ts(recibido)))


def valor_vigente(db, jugador, campo, corte):
    return db.execute("SELECT valor FROM jugador_asercion_a_las(%s) WHERE jugador_id = %s AND campo = %s",
                      (ts(corte), jugador, campo)).fetchone()


def test_fila_recibida_despues_del_corte_es_invisible(esquema):
    with esquema.conectar() as db:
        m = cargar_minimo(db)
        p = m["partido"]
        r = nuevo_recibo(db, "sofascore", "2026-02-01")
        db.execute("INSERT INTO resultado (partido_id, estado, ganador, sets, sets_completos, fuente, recibo_id, "
                   "recibido_en) VALUES (%s, 'completado', 2, %s, 2, 'sofascore', %s, %s)",
                   (p, Jsonb([[3, 6, None, None], [4, 6, None, None]]), r, ts("2026-02-01")))
        antes = db.execute("SELECT ganador FROM resultado_a_las(%s) WHERE partido_id = %s",
                           (ts("2026-01-20"), p)).fetchone()
        despues = db.execute("SELECT ganador FROM resultado_a_las(%s) WHERE partido_id = %s",
                             (ts("2026-03-01"), p)).fetchone()
        assert antes == (1,) and despues == (2,)


def test_dato_retro_no_es_visible_en_la_semana_del_partido(esquema):
    with esquema.conectar() as db:
        m = cargar_minimo(db)
        # Partido de la misma edición (termina el lunes 2026-03-02) que solo llega como dato retro.
        r_retro = nuevo_recibo(db, "tml", "2026-01-10", retro=True)
        pr = insertar(db, "INSERT INTO partido (edicion_id, ronda, jugador_1, jugador_2, mejor_de, fuente, recibo_id, "
                          "recibido_en) VALUES (%s, 'R16', %s, %s, 3, 'tml', %s, %s) RETURNING partido_id",
                      (m["edicion"], m["jugadores"][2], m["jugadores"][3], r_retro, ts("2026-01-10")))
        db.execute("INSERT INTO resultado (partido_id, estado, ganador, sets, sets_completos, fuente, recibo_id, "
                   "recibido_en) VALUES (%s, 'completado', 1, %s, 2, 'tml', %s, %s)",
                   (pr, Jsonb([[6, 2, None, None], [6, 2, None, None]]), r_retro, ts("2026-01-10")))

        def visible_partido(corte):
            return {f[0] for f in db.execute("SELECT partido_id FROM partido_a_las(%s)", (ts(corte),)).fetchall()}

        def visible_resultado(corte):
            return {f[0] for f in db.execute("SELECT partido_id FROM resultado_a_las(%s)", (ts(corte),)).fetchall()}

        # Antes del final de la semana: el partido retro no existe para el motor.
        assert pr not in visible_partido("2026-03-08T23:59:59Z")
        assert pr not in visible_resultado("2026-03-08T23:59:59Z")
        # Exactamente en el límite (00:00 UTC del lunes 9): sigue oculto (la regla es estrictamente posterior).
        assert pr not in visible_partido("2026-03-09T00:00:00Z")
        # Después del límite: visible; el partido normal siempre lo estuvo.
        assert pr in visible_partido("2026-03-09T00:00:01Z")
        assert pr in visible_resultado("2026-03-09T00:00:01Z")
        assert m["partido"] in visible_partido("2026-01-06")


def test_desempate_prioridad_de_fuente_luego_recibido_luego_id(esquema):
    with esquema.conectar() as db:
        m = cargar_minimo(db)
        c, d = m["jugadores"][2], m["jugadores"][3]
        # Prioridad gana a la recencia: sofascore (prioridad 1) antiguo frente a tml (prioridad 3) más nuevo.
        insertar_asercion(db, d, "altura_cm", "180", "sofascore", "2026-01-05")
        insertar_asercion(db, d, "altura_cm", "190", "tml", "2026-02-05")
        assert valor_vigente(db, d, "altura_cm", "2026-03-01") == ("180",)
        # Misma fuente: el recibido más reciente gana.
        insertar_asercion(db, c, "nombre", "Alfa", "tml", "2026-01-05")
        insertar_asercion(db, c, "nombre", "Beta", "tml", "2026-02-05")
        assert valor_vigente(db, c, "nombre", "2026-03-01") == ("Beta",)
        assert valor_vigente(db, c, "nombre", "2026-01-20") == ("Alfa",)
        # Mismo fuente y mismo recibido: gana el id mayor (la fila insertada después).
        insertar_asercion(db, c, "nombre", "Gamma", "tml", "2026-02-05")
        assert valor_vigente(db, c, "nombre", "2026-03-01") == ("Gamma",)


def test_alias_anulado_deja_de_contar_en_el_corte_de_la_anulacion(esquema):
    with esquema.conectar() as db:
        m = cargar_minimo(db)
        c, d = m["jugadores"][2], m["jugadores"][3]
        r1 = nuevo_recibo(db, "sofascore", "2026-01-05")
        a = insertar(db, "INSERT INTO jugador_alias (fuente, id_fuente, jugador_id, metodo, recibo_id, recibido_en) "
                         "VALUES ('sofascore', 'sf-2', %s, 'id_exacto', %s, %s) RETURNING alias_id",
                     (c, r1, ts("2026-01-05")))
        r2 = nuevo_recibo(db, "sofascore", "2026-02-05")
        db.execute("INSERT INTO jugador_alias (fuente, id_fuente, jugador_id, metodo, anula_a, recibo_id, recibido_en) "
                   "VALUES ('sofascore', 'sf-2', %s, 'manual', %s, %s, %s)", (d, a, r2, ts("2026-02-05")))

        def jugador_de(corte):
            return db.execute("SELECT jugador_id FROM jugador_alias_a_las(%s) WHERE id_fuente = 'sf-2'",
                              (ts(corte),)).fetchone()

        assert jugador_de("2026-01-20") == (c,)
        assert jugador_de("2026-03-01") == (d,)


def test_ranking_solo_cuenta_lunes_anteriores_a_la_fecha_del_partido(esquema):
    with esquema.conectar() as db:
        m = cargar_minimo(db)
        a = m["jugadores"][0]
        r = nuevo_recibo(db, "sofascore", "2026-01-05")
        db.execute("INSERT INTO ranking (circuito, fecha_publicacion, jugador_id, posicion, origen, fuente, recibo_id, "
                   "recibido_en) VALUES ('atp', '2026-03-09', %s, 3, 'oficial_capturado', 'sofascore', %s, %s)",
                   (a, r, ts("2026-01-05")))

        def posicion(fecha):
            return db.execute("SELECT posicion FROM ranking_a_las(%s, %s) WHERE jugador_id = %s",
                              (ts("2026-04-01"), fecha, a)).fetchone()

        # El lunes 9 no es visible para un partido del domingo 8: vale el lunes 2 (posición 5).
        assert posicion("2026-03-08") == (5,)
        assert posicion("2026-03-10") == (3,)
        assert posicion(None) == (3,)


def test_edicion_corregida_se_lee_segun_el_corte(esquema):
    with esquema.conectar() as db:
        m = cargar_minimo(db)
        r = nuevo_recibo(db, "sofascore", "2026-02-01")
        db.execute("INSERT INTO edicion (torneo_id, temporada, lunes_semana, superficie, fuente, recibo_id, recibido_en) "
                   "VALUES (%s, 2026, '2026-03-02', 'hard', 'sofascore', %s, %s)", (m["torneo"], r, ts("2026-02-01")))

        def superficie(corte):
            return db.execute("SELECT superficie FROM edicion_a_las(%s) WHERE torneo_id = %s AND temporada = 2026",
                              (ts(corte), m["torneo"])).fetchone()

        assert superficie("2026-01-20") == ("clay",)
        assert superficie("2026-03-01") == ("hard",)
