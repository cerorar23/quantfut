import hashlib
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from ayudas import nueva_entidad
from nba.v2 import carga
from nba.v2.carga import CuotaNueva, DatoNuevo

T0 = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def mundo(base_migrada):
    db = base_migrada
    return db, nueva_entidad(db, "partido", "g1"), nueva_entidad(db, "jugador", "p1")


def fila(p, j, metrica="puntos", valor=10.0, fuente="nba_oficial", fase="final", recibido=T0, **kw):
    return DatoNuevo(partido_id=p, entidad_id=j, metrica=metrica, fase=fase, fuente=fuente, recibido_en=recibido,
                     valor=valor, **kw)


def cuenta(db, tabla="nba.dato"):
    return db.execute(f"SELECT count(*) FROM {tabla}").fetchone()[0]


def test_guardar_datos_es_idempotente(mundo):
    db, p, j = mundo
    assert carga.guardar_datos(db, [fila(p, j), fila(p, j, "minutos", 30.0)]) == 2
    assert carga.guardar_datos(db, [fila(p, j), fila(p, j, "minutos", 30.0)]) == 0
    assert cuenta(db) == 2


def test_conflicto_se_marca_en_la_fila_nueva_solo_si_difiere(mundo):
    db, p, j = mundo
    carga.guardar_datos(db, [fila(p, j, valor=20.0)])
    carga.guardar_datos(db, [fila(p, j, valor=20.0, fuente="sofascore")])
    carga.guardar_datos(db, [fila(p, j, valor=22.0, fuente="espn")])
    marcas = dict(db.execute("SELECT fuente, conflicto FROM nba.dato").fetchall())
    assert marcas == {"nba_oficial": False, "sofascore": False, "espn": True}


def test_tolerancia_de_minutos(mundo):
    db, p, j = mundo
    carga.guardar_datos(db, [fila(p, j, "minutos", 30.0)])
    carga.guardar_datos(db, [fila(p, j, "minutos", 30.4, fuente="sofascore"), fila(p, j, "minutos", 31.0, fuente="espn")])
    marcas = dict(db.execute("SELECT fuente, conflicto FROM nba.dato WHERE fuente <> 'nba_oficial'").fetchall())
    assert marcas == {"sofascore": False, "espn": True}


def test_por_fuente_nunca_marca_conflicto(mundo):
    db, p, j = mundo
    base = dict(metrica="minutos_proyectados", fase="pre")
    carga.guardar_datos(db, [fila(p, j, valor=30.0, fuente="rotowire", **base)])
    carga.guardar_datos(db, [fila(p, j, valor=12.0, fuente="espn", **base)])
    assert db.execute("SELECT count(*) FROM nba.dato WHERE conflicto").fetchone()[0] == 0


def test_metrica_desconocida_falla_sin_insertar_nada(mundo):
    db, p, j = mundo
    with pytest.raises(KeyError, match="metrica_inexistente"):
        carga.guardar_datos(db, [fila(p, j), fila(p, j, "metrica_inexistente", 1.0)])
    assert cuenta(db) == 0


def test_guardar_original_es_idempotente_y_hash_coincide(tmp_path):
    cuerpo = b'{"x": 1}'
    ruta, huella = carga.guardar_original(tmp_path, "espn", cuerpo, T0)
    assert huella == hashlib.sha256(cuerpo).hexdigest()
    assert ruta == f"espn/2026-11-01/{huella}" and (tmp_path / ruta).read_bytes() == cuerpo
    assert carga.guardar_original(tmp_path, "espn", cuerpo, T0) == (ruta, huella)


def test_registrar_captura_devuelve_id_y_guarda_error(mundo):
    db, p, _ = mundo
    ok = carga.registrar_captura(db, fuente="rotowire", objetivo="https://x", fase="pre", solicitado_en=T0, ok=True,
                                 recibido_en=T0, http_status=200, sha256="ab", bytes_=10, ruta="r", partido_id=p)
    mal = carga.registrar_captura(db, fuente="rotowire", objetivo="https://x", fase="pre", solicitado_en=T0, ok=False,
                                  http_status=403, error="bloqueado", creditos=1)
    assert mal > ok
    assert db.execute("SELECT ok, error, creditos FROM nba.captura WHERE captura_id = %s", (mal,)).fetchone() == (
        False, "bloqueado", Decimal("1.00"))


def test_guardar_cuotas_es_idempotente(mundo):
    db, p, _ = mundo
    c = CuotaNueva(partido_id=p, fuente="propline", casa="bet365", mercado="ganador", lado="local", cuota=Decimal("1.91"),
                   contrato_id="c1", fase="cierre", recibido_en=T0)
    assert carga.guardar_cuotas(db, [c]) == 1
    assert carga.guardar_cuotas(db, [c]) == 0
    assert cuenta(db, "nba.cuota") == 1


def test_solo_cambios_omite_repetidos_y_guarda_cambios(mundo):
    db, p, j = mundo
    kw = dict(metrica="estado_disponibilidad", fase="pre", fuente="rotowire", valor=0.5, etiqueta="Ques")
    t = lambda h: datetime(2026, 11, 1, h, 0, tzinfo=UTC)
    assert carga.guardar_datos(db, [fila(p, j, recibido=t(10), **kw)], solo_cambios=True) == 1
    assert carga.guardar_datos(db, [fila(p, j, recibido=t(11), **kw)], solo_cambios=True) == 0   # igual que el último
    cambio = dict(kw, valor=0.0, etiqueta="Out")
    assert carga.guardar_datos(db, [fila(p, j, recibido=t(12), **cambio)], solo_cambios=True) == 1
    assert carga.guardar_datos(db, [fila(p, j, recibido=t(13), **kw)], solo_cambios=True) == 1    # vuelve a Ques: es cambio
    assert cuenta(db) == 3


def test_guardar_eventos_es_idempotente_y_conserva_la_primera_version(mundo):
    from nba.v2.carga import EventoNuevo
    db, p, _ = mundo
    e = EventoNuevo(partido_id=p, fuente="nba_oficial", secuencia=15, periodo=1, reloj_s=669.0, tipo="2pt", subtipo="Layup",
                    recibido_en=T0, x=94.9, y=44.4, acierto=True, puntos=2, marcador_local=2, marcador_visit=0)
    assert carga.guardar_eventos(db, [e]) == 1
    editado = EventoNuevo(partido_id=p, fuente="nba_oficial", secuencia=15, periodo=1, reloj_s=669.0, tipo="3pt",
                          recibido_en=T0)
    assert carga.guardar_eventos(db, [e, editado]) == 0
    assert db.execute("SELECT tipo, puntos FROM nba.evento").fetchall() == [("2pt", 2)]
