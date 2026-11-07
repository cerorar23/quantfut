"""Captura del ranking oficial (SportsAPIPro): análisis puro, captura contra base con transporte falso y PIT.

NO PROBADO CONTRA RESPUESTA REAL: no hay muestra guardada en el repositorio y en este sprint no hay red.
Los datos de `SINTETICO` son inventados y solo verifican la forma conocida (ver docstring de captura/ranking.py).
"""
import json
from datetime import date, datetime, timedelta, timezone

import pytest

psycopg = pytest.importorskip("psycopg")

from tenis.captura import presupuesto as pr  # noqa: E402
from tenis.captura import ranking as rk  # noqa: E402
from tenis.captura.cursor import leer  # noqa: E402

from db_util import cargar_minimo  # noqa: E402

RECIBIDO = datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc)  # lunes
MARTES = datetime(2026, 11, 3, 9, 0, tzinfo=timezone.utc)

# SINTETICO: inventado, con la forma documentada. No es una respuesta real de SportsAPIPro.
SINTETICO = {"data": {"rankings": [
    {"ranking": 1, "points": 9550, "previousRanking": 2, "team": {"id": 1001, "name": "Jugador Uno"},
     "rowName": "J. Uno", "country": {"name": "Esp"}},
    {"ranking": 2, "points": 9000, "previousRanking": 1, "team": {"id": 1002, "name": "Jugador Dos"},
     "rowName": "J. Dos"},
    {"ranking": 3, "points": None, "team": {"id": 1003, "name": "Jugador Tres"}},
    {"ranking": 4, "points": 4100, "team": {"id": 1004, "name": "Jugador Cuatro"}},
]}}


def _cuerpo(doc) -> bytes:
    return json.dumps(doc).encode("utf-8")


def _con(cambios_fila=None, extra=None, quitar=None):
    doc = json.loads(json.dumps(SINTETICO))
    filas = doc["data"]["rankings"]
    if cambios_fila is not None:
        indice, campos = cambios_fila
        filas[indice].update(campos)
    if quitar:
        for k in quitar:
            doc["data"].pop(k, None)
    if extra:
        doc["data"].update(extra)
    return _cuerpo(doc)


# ---------- análisis puro ----------

def test_respuesta_valida_produce_observaciones_y_fecha_lunes():
    a = rk.analizar(_cuerpo(SINTETICO), "atp", RECIBIDO)
    assert a.aceptado and a.motivo is None
    assert [f.posicion for f in a.filas] == [1, 2, 3, 4]
    assert a.filas[2].puntos is None  # faltante, nunca 0
    assert a.fecha_publicacion == date(2026, 11, 2) and a.regla_fecha == "lunes_captura"


def test_recuento_independiente_coincide_con_el_analisis():
    """Segundo cálculo, aparte del módulo, sobre el mismo texto: recuentos y suma de puntos deben coincidir."""
    filas = json.loads(_cuerpo(SINTETICO))["data"]["rankings"]
    aceptadas = [f for f in filas if isinstance(f.get("ranking"), int) and f["ranking"] >= 1]
    suma = sum(f["points"] for f in aceptadas if f.get("points") is not None)
    a = rk.analizar(_cuerpo(SINTETICO), "atp", RECIBIDO)
    assert len(a.filas) == len(aceptadas) == 4
    assert sum(f.puntos for f in a.filas if f.puntos is not None) == suma == 22650


@pytest.mark.parametrize("cambio, motivo", [
    ((0, {"ranking": 0}), "posicion_invalida"),
    ((0, {"ranking": -3}), "posicion_invalida"),
    ((0, {"ranking": "1"}), "posicion_invalida"),
    ((0, {"ranking": True}), "posicion_invalida"),
    ((1, {"ranking": 1}), "posicion_duplicada"),
    ((1, {"team": {"id": 1001, "name": "Jugador Uno"}}), "jugador_duplicado"),
    ((2, {"points": -5}), "puntos_invalidos"),
    ((2, {"points": "9000"}), "puntos_invalidos"),
    ((2, {"team": {"name": "Sin id"}}), "id_ausente"),
    ((2, {"team": {"id": 1003, "name": ""}, "rowName": ""}), "nombre_ausente"),
])
def test_filas_absurdas_rechazan_la_respuesta_entera(cambio, motivo):
    a = rk.analizar(_con(cambios_fila=cambio), "atp", RECIBIDO)
    assert not a.aceptado and a.motivo == motivo and a.filas == []


def test_fecha_de_martes_se_rechaza():
    a = rk.analizar(_con(extra={"rankingDate": "2026-11-03"}), "atp", RECIBIDO)
    assert not a.aceptado and a.motivo == "fecha_no_lunes"


def test_fecha_de_lunes_explicita_se_usa_tal_cual():
    a = rk.analizar(_con(extra={"rankingDate": "2026-10-26T00:00:00Z"}), "wta", RECIBIDO)
    assert a.aceptado and a.fecha_publicacion == date(2026, 10, 26) and a.regla_fecha == "campo"


def test_fecha_mal_formada_se_rechaza():
    a = rk.analizar(_con(extra={"date": "no es fecha"}), "atp", RECIBIDO)
    assert not a.aceptado and a.motivo == "fecha_invalida"


@pytest.mark.parametrize("cuerpo, motivo", [
    (b"", "json_invalido"),
    (b"{no json", "json_invalido"),
    (b"[]", "estructura"),
    (b'{"data": null}', "estructura"),
    (b'{"data": {"rankings": []}}', "vacia"),
    (b'{"data": {"rankings": "x"}}', "vacia"),
])
def test_respuesta_vacia_o_mal_formada(cuerpo, motivo):
    a = rk.analizar(cuerpo, "atp", RECIBIDO)
    assert not a.aceptado and a.motivo == motivo


def test_circuito_desconocido_es_error_de_programacion():
    with pytest.raises(ValueError):
        rk.analizar(_cuerpo(SINTETICO), "itf", RECIBIDO)


def test_rutas_del_motor_viejo():
    assert rk.RUTAS == {"atp": "/rankings/type/5", "wta": "/rankings/wta"}


# ---------- captura contra la base ----------

def _conexion(e):
    db = psycopg.connect(e.dsn, autocommit=True)
    db.execute(f"SET search_path TO {e.nombre}, {e.nombre_op}, public")
    return db


def _transporte(estado, cuerpo, llamadas):
    def obtener(ruta):
        llamadas.append(ruta)
        return estado, cuerpo
    return obtener


def _resolver_de(mapa):
    return lambda id_f, nombre, circuito: mapa.get(id_f)


def _mundo(db, m):
    """Tres de los cuatro jugadores del mundo mínimo resueltos; el id 1004 queda sin resolver."""
    j = m["jugadores"]
    return {"1001": j[1], "1002": j[2], "1003": j[3]}


def _reloj(instante):
    return lambda: instante


def _objetos(raiz):
    return sorted(p for p in (raiz / "objetos").rglob("*.json.gz"))


def test_captura_escribe_observaciones_recibo_y_sin_resolver(esquema, tmp_path):
    with _conexion(esquema) as db:
        m = cargar_minimo(db)
        mapa = _mundo(db, m)
        pr.fijar_tope(db, "sportsapipro", RECIBIDO, 100)
        llamadas = []
        r = rk.capturar(db, "atp", _transporte(200, _cuerpo(SINTETICO), llamadas), _resolver_de(mapa), tmp_path,
                        _reloj(RECIBIDO))
        assert r.estado == "escrito" and r.escritas == 3 and r.sin_resolver == 1
        assert llamadas == ["/rankings/type/5"]
        filas = db.execute("SELECT posicion, puntos, origen, visible_desde, fecha_publicacion, recibido_en "
                           "FROM ranking WHERE origen = 'oficial_capturado' AND recibido_en = %s "
                           "ORDER BY posicion", (RECIBIDO,)).fetchall()
        assert [f[0] for f in filas] == [1, 2, 3]
        assert filas[2][1] is None                       # faltante se queda NULL
        assert all(f[3] is None for f in filas)          # sin visible_desde
        assert all(f[4] == date(2026, 11, 2) for f in filas)
        rec = db.execute("SELECT retro, sha256, ruta_objeto, recibido_en FROM recibo WHERE recibo_id = %s",
                         (r.recibo_id,)).fetchone()
        assert rec[0] is False and rec[3] == RECIBIDO
        assert (tmp_path / rec[2]).exists()
        sin = db.execute("SELECT id_fuente, motivo FROM sin_resolver WHERE motivo = 'sin_resolver_ranking'").fetchall()
        assert sin == [("1004", "sin_resolver_ranking")]
        assert leer(db, "sportsapipro", "ranking_atp") == "2026-11-02"
        assert db.execute("SELECT usadas FROM presupuesto WHERE fuente = 'sportsapipro'").fetchone()[0] == 1


def test_mismo_contenido_dos_veces_es_un_objeto_y_dos_recepciones(esquema, tmp_path):
    with _conexion(esquema) as db:
        m = cargar_minimo(db)
        mapa = _mundo(db, m)
        pr.fijar_tope(db, "sportsapipro", RECIBIDO, 100)
        cuerpo = _cuerpo(SINTETICO)
        otro = RECIBIDO + timedelta(hours=1)
        rk.capturar(db, "atp", _transporte(200, cuerpo, []), _resolver_de(mapa), tmp_path, _reloj(RECIBIDO))
        rk.capturar(db, "atp", _transporte(200, cuerpo, []), _resolver_de(mapa), tmp_path, _reloj(otro))
        assert len(_objetos(tmp_path)) == 1
        assert db.execute("SELECT count(*) FROM recibo WHERE recurso = '/rankings/type/5'").fetchone()[0] == 2
        assert db.execute("SELECT count(*) FROM ranking WHERE fuente = 'sportsapipro'").fetchone()[0] == 6


@pytest.mark.parametrize("estado, cuerpo", [(500, b'{"error": "interno"}'), (503, b""), (200, b"")])
def test_error_http_o_vacio_no_escribe_y_devuelve_la_cuota(esquema, tmp_path, estado, cuerpo):
    with _conexion(esquema) as db:
        m = cargar_minimo(db)
        pr.fijar_tope(db, "sportsapipro", RECIBIDO, 100)
        antes = db.execute("SELECT count(*) FROM ranking").fetchone()[0]
        r = rk.capturar(db, "atp", _transporte(estado, cuerpo, []), _resolver_de(_mundo(db, m)), tmp_path,
                        _reloj(RECIBIDO))
        assert r.estado == "sin_datos"
        assert db.execute("SELECT count(*) FROM ranking").fetchone()[0] == antes
        assert db.execute("SELECT count(*) FROM recibo WHERE recurso = '/rankings/type/5'").fetchone()[0] == 0
        assert db.execute("SELECT usadas FROM presupuesto WHERE fuente = 'sportsapipro'").fetchone()[0] == 0
        assert _objetos(tmp_path) == []


def test_tope_agotado_no_llama_al_transporte(esquema, tmp_path):
    with _conexion(esquema) as db:
        m = cargar_minimo(db)
        pr.fijar_tope(db, "sportsapipro", RECIBIDO, 0)
        llamadas = []
        r = rk.capturar(db, "atp", _transporte(200, _cuerpo(SINTETICO), llamadas), _resolver_de(_mundo(db, m)),
                        tmp_path, _reloj(RECIBIDO))
        assert r.estado == "presupuesto" and llamadas == []


def test_respuesta_con_fecha_de_martes_no_escribe_ni_avanza_cursor(esquema, tmp_path):
    with _conexion(esquema) as db:
        m = cargar_minimo(db)
        pr.fijar_tope(db, "sportsapipro", RECIBIDO, 100)
        cuerpo = _con(extra={"rankingDate": "2026-11-03"})
        r = rk.capturar(db, "atp", _transporte(200, cuerpo, []), _resolver_de(_mundo(db, m)), tmp_path,
                        _reloj(RECIBIDO))
        assert r.estado == "rechazado" and r.motivo == "fecha_no_lunes"
        assert db.execute("SELECT count(*) FROM ranking WHERE fuente = 'sportsapipro'").fetchone()[0] == 0
        assert leer(db, "sportsapipro", "ranking_atp") is None


def test_jugador_sin_resolver_no_se_inventa(esquema, tmp_path):
    with _conexion(esquema) as db:
        cargar_minimo(db)
        pr.fijar_tope(db, "sportsapipro", RECIBIDO, 100)
        antes = db.execute("SELECT count(*) FROM jugador").fetchone()[0]
        r = rk.capturar(db, "atp", _transporte(200, _cuerpo(SINTETICO), []), _resolver_de({}), tmp_path,
                        _reloj(RECIBIDO))
        assert r.estado == "escrito" and r.escritas == 0 and r.sin_resolver == 4
        assert db.execute("SELECT count(*) FROM jugador").fetchone()[0] == antes


# ---------- punto en el tiempo ----------

def test_observacion_recibida_despues_del_corte_no_es_visible(esquema, tmp_path):
    with _conexion(esquema) as db:
        m = cargar_minimo(db)
        pr.fijar_tope(db, "sportsapipro", RECIBIDO, 100)
        mapa = _mundo(db, m)
        rk.capturar(db, "atp", _transporte(200, _cuerpo(SINTETICO), []), _resolver_de(mapa), tmp_path,
                    _reloj(RECIBIDO))
        ids = [mapa["1001"], mapa["1002"], mapa["1003"]]
        antes = db.execute("SELECT jugador_id FROM ranking_a_las(%s, NULL) WHERE jugador_id = ANY(%s) "
                           "AND origen = 'oficial_capturado'", (RECIBIDO - timedelta(minutes=1), ids)).fetchall()
        despues = db.execute("SELECT jugador_id FROM ranking_a_las(%s, NULL) WHERE jugador_id = ANY(%s) "
                             "AND origen = 'oficial_capturado'", (RECIBIDO + timedelta(minutes=1), ids)).fetchall()
        assert antes == []
        assert len(despues) == 3


def test_fecha_del_partido_anterior_al_lunes_de_publicacion_no_la_ve(esquema, tmp_path):
    with _conexion(esquema) as db:
        m = cargar_minimo(db)
        pr.fijar_tope(db, "sportsapipro", RECIBIDO, 100)
        mapa = _mundo(db, m)
        rk.capturar(db, "atp", _transporte(200, _cuerpo(SINTETICO), []), _resolver_de(mapa), tmp_path,
                    _reloj(RECIBIDO))
        ids = [mapa["1001"], mapa["1002"], mapa["1003"]]
        corte_tardio = RECIBIDO + timedelta(days=30)
        sin_fecha = db.execute("SELECT count(*) FROM ranking_a_las(%s, NULL) WHERE jugador_id = ANY(%s) "
                               "AND origen = 'oficial_capturado'", (corte_tardio, ids)).fetchone()[0]
        antes_lunes = db.execute("SELECT count(*) FROM ranking_a_las(%s, %s) WHERE jugador_id = ANY(%s) "
                                 "AND origen = 'oficial_capturado'",
                                 (corte_tardio, date(2026, 10, 26), ids)).fetchone()[0]
        desde_lunes = db.execute("SELECT count(*) FROM ranking_a_las(%s, %s) WHERE jugador_id = ANY(%s) "
                                 "AND origen = 'oficial_capturado'",
                                 (corte_tardio, date(2026, 11, 2), ids)).fetchone()[0]
        assert sin_fecha == 3 and antes_lunes == 0 and desde_lunes == 3
