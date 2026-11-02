from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from nba.v2.fuentes import rotowire

FIX = Path(__file__).parent / "fixtures"
HTML = (FIX / "rotowire_lineups.html").read_text(encoding="utf-8")
MINUTOS_OKC = (FIX / "rotowire_minutos_OKC.json").read_text(encoding="utf-8")
AHORA = datetime(2026, 11, 2, 16, 0, tzinfo=UTC)


def test_parsear_lineups_partidos_titulares_y_ausentes():
    pagina = rotowire.parsear_lineups(HTML)
    assert pagina.fecha == date(2026, 11, 2)
    assert [(p.visitante, p.local) for p in pagina.partidos] == [("OKC", "CLE"), ("CHI", "PHI")]
    okc = pagina.partidos[0].equipos["OKC"]
    assert [j.id_rw for j in okc.titulares] == ["4387", "6266", "6289", "4462", "4147"]
    assert okc.estado == "expected" and okc.titulares[0].nombre == "Shai Gilgeous-Alexander"
    assert all(j.prob_jugar == 1.0 and j.estado is None for j in okc.titulares)
    assert {j.nombre for j in okc.ausentes} == {"Alex Caruso", "Chet Holmgren", "Thomas Sorber", "Nikola Topic",
                                                "Cason Wallace", "Jalen Williams"}
    assert all(j.estado == "Out" and j.prob_jugar == 0.0 for j in okc.ausentes)


def test_parsear_lineups_probabilidades_por_nivel():
    pagina = rotowire.parsear_lineups(HTML)
    todos = [j for p in pagina.partidos for e in p.equipos.values() for j in e.titulares + e.ausentes]
    pares = {(j.estado, j.prob_jugar) for j in todos if j.estado}
    assert ("Out", 0.0) in pares and any(e == "Ques" and p == 0.5 for e, p in pares)
    assert any(e == "Prob" and p == 0.75 for e, p in pares) and any(e == "Doubt" and p == 0.25 for e, p in pares)


def test_parsear_lineups_arbitros_y_hora():
    p = rotowire.parsear_lineups(HTML).partidos[0]
    assert p.hora_et == "7:00 PM ET"
    assert p.arbitros == [("3566", "Marc Davis"), ("3563", "Sean Corbin"), ("795085", "Dedric Taylor")]


def test_parsear_minutos():
    m = {x.id_rw: x for x in rotowire.parsear_minutos(MINUTOS_OKC)}
    sga = m["4387"]
    assert (sga.proy, sga.promedio, sga.minimo, sga.maximo, sga.desviacion, sga.lineup) == (33, 33, 28, 37, 4.5, "PG")
    assert m["3952"].proy == 0 and m["3952"].lineup == "BE" and m["3952"].estado == "Out"


@pytest.fixture
def cargado(base_migrada, tmp_path):
    cuerpos = {rotowire.URL_LINEUPS: (200, HTML.encode()), rotowire.URL_MINUTOS + "OKC": (200, MINUTOS_OKC.encode())}

    def obtener(url):
        if url in cuerpos:
            return cuerpos[url]
        return 404, b"no existe"

    return base_migrada, obtener, tmp_path


def filas(db, sql, *args):
    return db.execute(sql, args).fetchall()


def test_capturar_carga_disponibilidad_titulares_minutos_y_arbitros(cargado):
    db, obtener, raiz = cargado
    r = rotowire.capturar(db, obtener, raiz, AHORA)
    assert r["ok"] and r["partidos"] == 2
    por_metrica = dict(filas(db, "SELECT m.nombre, count(*) FROM nba.dato d JOIN nba.metrica m USING (metrica_id) "
                                 "WHERE d.fuente = 'rotowire' AND d.fase = 'pre' GROUP BY 1"))
    assert por_metrica["titular_esperado"] == 20          # 2 partidos x 2 equipos x 5
    assert por_metrica["arbitro_asignado"] == 6
    assert por_metrica["minutos_proyectados"] == 17       # solo OKC tenía minutos en el fixture
    assert por_metrica["estado_disponibilidad"] > 20
    q = filas(db, "SELECT d.etiqueta, d.valor FROM nba.dato d JOIN nba.metrica m USING (metrica_id) JOIN nba.entidad e "
                  "ON e.entidad_id = d.entidad_id WHERE m.nombre = 'estado_disponibilidad' AND e.nombre = 'Alex Caruso'")
    assert q == [("Out", 0.0)]
    assert db.execute("SELECT recibido_en FROM nba.dato WHERE fuente = 'rotowire' LIMIT 1").fetchone()[0] == AHORA


def test_capturar_es_idempotente_y_guarda_originales(cargado):
    db, obtener, raiz = cargado
    rotowire.capturar(db, obtener, raiz, AHORA)
    datos = db.execute("SELECT count(*) FROM nba.dato").fetchone()[0]
    r2 = rotowire.capturar(db, obtener, raiz, AHORA)
    assert db.execute("SELECT count(*) FROM nba.dato").fetchone()[0] == datos and r2["datos"] == 0
    assert len(list((raiz / "rotowire").rglob("*"))) >= 2
    assert db.execute("SELECT count(*) FROM nba.captura WHERE ok").fetchone()[0] >= 3


def test_partido_de_rotowire_es_unico_por_fecha_y_equipos(cargado):
    db, obtener, raiz = cargado
    rotowire.capturar(db, obtener, raiz, AHORA)
    assert db.execute("SELECT count(*) FROM nba.entidad WHERE tipo = 'partido'").fetchone()[0] == 2


def test_pagina_sin_partidos_no_escribe_datos(base_migrada, tmp_path):
    vacia = '<main class="page" data-gamedate="2026-07-04"></main>'
    r = rotowire.capturar(base_migrada, lambda url: (200, vacia.encode()), tmp_path, AHORA)
    assert r["ok"] and r["partidos"] == 0 and r["datos"] == 0
    assert base_migrada.execute("SELECT count(*) FROM nba.dato").fetchone()[0] == 0
    assert base_migrada.execute("SELECT ok FROM nba.captura").fetchall() == [(True,)]


def test_error_http_registra_captura_fallida(base_migrada, tmp_path):
    r = rotowire.capturar(base_migrada, lambda url: (403, b"bloqueado"), tmp_path, AHORA)
    assert not r["ok"]
    assert base_migrada.execute("SELECT ok, http_status FROM nba.captura").fetchall() == [(False, 403)]
    assert base_migrada.execute("SELECT count(*) FROM nba.dato").fetchone()[0] == 0


def test_falla_la_red_registra_error_sin_datos(base_migrada, tmp_path):
    def obtener(url):
        raise TimeoutError("sin respuesta")

    r = rotowire.capturar(base_migrada, obtener, tmp_path, AHORA)
    assert not r["ok"]
    assert base_migrada.execute("SELECT ok, error FROM nba.captura").fetchone() == (False, "TimeoutError: sin respuesta")


def test_minutos_nulos_no_se_imputan(cargado):
    db, obtener, raiz = cargado
    rotowire.capturar(db, obtener, raiz, AHORA)
    filas = db.execute(
        "SELECT m.nombre FROM nba.dato d JOIN nba.metrica m USING (metrica_id) JOIN nba.entidad e "
        "ON e.entidad_id = d.entidad_id WHERE e.nombre = 'Thomas Sorber' AND m.nombre LIKE 'minutos%'").fetchall()
    nombres = {f[0] for f in filas}
    assert "minutos_proyectados" in nombres and "minutos_promedio_reciente" not in nombres


from datetime import timedelta


def espiado(cuerpos):
    visitas = []

    def obtener(url):
        visitas.append(url)
        return cuerpos.get(url, (404, b"no existe"))

    return obtener, visitas


CUERPOS = {rotowire.URL_LINEUPS: (200, HTML.encode())}
CUERPOS.update({rotowire.URL_MINUTOS + t: (200, MINUTOS_OKC.encode()) for t in ("OKC", "CLE", "CHI", "PHI")})


def minutos_pedidos(visitas):
    return sorted(u.rsplit("=", 1)[1] for u in visitas if u.startswith(rotowire.URL_MINUTOS))


def test_inicio_utc_desde_la_hora_et():
    assert rotowire.inicio_utc(date(2026, 11, 2), "7:00 PM ET") == datetime(2026, 11, 3, 0, 0, tzinfo=UTC)
    assert rotowire.inicio_utc(date(2026, 11, 2), "12:30 PM ET") == datetime(2026, 11, 2, 17, 30, tzinfo=UTC)
    assert rotowire.inicio_utc(date(2026, 11, 2), "") is None


def test_minutos_solo_dentro_de_la_ventana_antes_del_salto(base_migrada, tmp_path):
    obtener, visitas = espiado(CUERPOS)
    rotowire.capturar(base_migrada, obtener, tmp_path, AHORA, ventana_h=4)          # faltan 8 h: fuera de ventana
    assert minutos_pedidos(visitas) == []
    obtener, visitas = espiado(CUERPOS)
    rotowire.capturar(base_migrada, obtener, tmp_path, AHORA + timedelta(hours=5))   # faltan 3 h
    assert minutos_pedidos(visitas) == ["CHI", "CLE", "OKC", "PHI"]


def test_minutos_no_se_piden_despues_del_salto(base_migrada, tmp_path):
    obtener, visitas = espiado(CUERPOS)
    rotowire.capturar(base_migrada, obtener, tmp_path, AHORA + timedelta(hours=9))   # ya empezaron
    assert minutos_pedidos(visitas) == []


def test_minutos_respetan_la_espera_entre_capturas(base_migrada, tmp_path):
    ahora = AHORA + timedelta(hours=6)
    obtener, visitas = espiado(CUERPOS)
    rotowire.capturar(base_migrada, obtener, tmp_path, ahora)
    assert len(minutos_pedidos(visitas)) == 4
    obtener, visitas = espiado(CUERPOS)
    rotowire.capturar(base_migrada, obtener, tmp_path, ahora + timedelta(minutes=30))
    assert minutos_pedidos(visitas) == [] and rotowire.URL_LINEUPS in visitas        # la página sí se repite
    obtener, visitas = espiado(CUERPOS)
    rotowire.capturar(base_migrada, obtener, tmp_path, ahora + timedelta(minutes=61))
    assert len(minutos_pedidos(visitas)) == 4


def test_creditos_de_pago_quedan_en_la_captura(base_migrada, tmp_path):
    obtener = lambda url: (200, HTML.encode(), 1.0) if url == rotowire.URL_LINEUPS else (404, b"")
    rotowire.capturar(base_migrada, obtener, tmp_path, AHORA)
    assert base_migrada.execute("SELECT creditos FROM nba.captura WHERE objetivo = %s",
                                (rotowire.URL_LINEUPS,)).fetchone()[0] == 1


def test_gastado_hoy_suma_los_creditos_del_dia(base_migrada, tmp_path):
    obtener = lambda url: (200, HTML.encode(), 1.0) if url == rotowire.URL_LINEUPS else (404, b"")
    rotowire.capturar(base_migrada, obtener, tmp_path, AHORA)
    rotowire.capturar(base_migrada, obtener, tmp_path, AHORA + timedelta(hours=1))
    rotowire.capturar(base_migrada, obtener, tmp_path, AHORA + timedelta(days=1))
    assert rotowire.gastado_hoy(base_migrada, AHORA + timedelta(hours=2)) == 2


def test_respaldo_de_pago_solo_ante_bloqueo_y_con_presupuesto():
    llamadas = []
    directo = lambda url: (403, b"bloqueado")
    pago = lambda url: llamadas.append(url) or (200, b"ok")
    assert rotowire.con_respaldo(directo, pago, True)("u") == (200, b"ok", 1.0)
    assert rotowire.con_respaldo(directo, pago, False)("u") == (403, b"bloqueado", 0)           # sin presupuesto
    assert rotowire.con_respaldo(directo, None, True)("u") == (403, b"bloqueado", 0)            # sin clave
    assert rotowire.con_respaldo(lambda u: (200, b"x"), pago, True)("u") == (200, b"x", 0)      # no hace falta
    assert rotowire.con_respaldo(lambda u: (404, b"x"), pago, True)("u") == (404, b"x", 0)      # 404 no es bloqueo
    assert len(llamadas) == 1
