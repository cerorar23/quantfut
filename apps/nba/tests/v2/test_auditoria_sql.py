from datetime import datetime, date, timedelta, UTC
import time

import pytest

from nba.v2 import identidad, pit, sellado
from nba.v2.carga import DatoNuevo, guardar_datos
from nba.v2.plantilla_pit import Q_ULTIMO_EQUIPO
from nba.v2.plantilla_pit import Q_PARTE
from nba.v2.sellado import PronosticoNuevo


def partido(db, sufijo='1'):
    a, b = identidad.equipo(db, 'BOS'), identidad.equipo(db, 'NYK')
    p = identidad.partido(db, 'nba_oficial', f'0022699{sufijo}', date(2026, 11, 1), a, b, '2026-27')
    return p, a, b


def test_exists_de_minutos_no_usa_recepcion_futura(base_migrada):
    db = base_migrada
    p, a, _ = partido(db)
    j = identidad.jugador(db, 'nba_oficial', '991', 'Jugador Prueba')
    corte = datetime(2026, 11, 2, tzinfo=UTC)
    base = dict(partido_id=p, entidad_id=j, fuente='nba_oficial', fase='final')
    guardar_datos(db, [DatoNuevo(**base, metrica='equipo_del_jugador', valor=float(a), recibido_en=corte - timedelta(days=1)),
                       DatoNuevo(**base, metrica='minutos', valor=30., recibido_en=corte + timedelta(days=1))])
    args = {'jug': [j], 'fecha': date(2026, 11, 2), 'corte': corte}
    assert db.execute(Q_ULTIMO_EQUIPO, args).fetchall() == []
    guardar_datos(db, [DatoNuevo(**base, metrica='minutos', valor=30., recibido_en=corte - timedelta(hours=1))])
    assert db.execute(Q_ULTIMO_EQUIPO, args).fetchall() == [(j, a)]


def test_caja_reconstruida_llegada_despues_no_es_historia_visible(base_migrada):
    db = base_migrada
    p, a, b = partido(db)
    objetivo = identidad.partido(db, 'nba_oficial', '0022699999', date(2026, 11, 2), a, b, '2026-27')
    corte = datetime(2026, 11, 2, 20, tzinfo=UTC)
    for equipo in (a, b):
        guardar_datos(db, [DatoNuevo(p, equipo, 'puntos', 'final', 'nba_oficial', corte + timedelta(hours=1), valor=110., pit='reconstruido')])
    assert pit.instantanea(db, objetivo, corte).historia == ()


def test_sello_con_salto_pasado_se_rechaza_al_persistir(base_migrada):
    db = base_migrada
    p, _, _ = partido(db)
    ahora = db.execute('SELECT clock_timestamp()').fetchone()[0]
    nuevo = PronosticoNuevo(p, 'equipo', 'auditoria', 'a' * 64, ahora - timedelta(hours=1), {}, {}, inicio_utc=ahora - timedelta(seconds=1))
    with pytest.raises(ValueError, match='empez'):
        sellado.sellar(db, nuevo)
    assert db.execute('SELECT count(*) FROM nba.pronostico').fetchone()[0] == 0


def test_cruzar_el_salto_durante_hash_no_inserta(base_migrada, monkeypatch):
    db = base_migrada
    p, _, _ = partido(db)
    ahora = db.execute('SELECT clock_timestamp()').fetchone()[0]
    original = sellado.calcular_hash
    def lento(*args):
        time.sleep(.25)
        return original(*args)
    monkeypatch.setattr(sellado, 'calcular_hash', lento)
    nuevo = PronosticoNuevo(p, 'equipo', 'auditoria', 'a' * 64, ahora - timedelta(hours=1), {}, {}, inicio_utc=ahora + timedelta(seconds=.15))
    with pytest.raises(ValueError, match='empez'):
        sellado.sellar(db, nuevo)
    assert db.execute('SELECT count(*) FROM nba.pronostico').fetchone()[0] == 0


def test_publicacion_antigua_no_elude_recepcion_del_original(base_migrada):
    from nba.v2.carga import registrar_captura
    db = base_migrada
    p, _, _ = partido(db)
    j = identidad.jugador(db, 'nba_oficial', '992', 'Lesionado Prueba')
    corte = datetime(2026, 11, 2, 20, tzinfo=UTC)
    captura = registrar_captura(db, fuente='nba_oficial', objetivo='parte-reconstruido', fase='historico',
                               solicitado_en=corte + timedelta(days=1), recibido_en=corte + timedelta(days=1), ok=True)
    guardar_datos(db, [DatoNuevo(p, j, 'estado_disponibilidad', 'pre', 'nba_oficial', corte - timedelta(hours=1),
                                etiqueta='Out', pit='reconstruido', captura_id=captura)])
    assert db.execute(Q_PARTE, {'partido':p,'corte':corte}).fetchall() == []
    assert db.execute('SELECT * FROM nba.dato_a_las(%s)', (corte,)).fetchall() == []
    assert db.execute('SELECT count(*) FROM nba.dato').fetchone()[0] == 1
