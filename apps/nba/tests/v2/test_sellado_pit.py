from datetime import date, datetime, timedelta, UTC

import psycopg
import pytest

from nba.v2 import identidad, motor_equipo, nucleo, pit, sellado
from nba.v2.carga import DatoNuevo, guardar_datos
from nba.v2.sellado import PronosticoNuevo

AYER = datetime.now(UTC) - timedelta(days=1)
EQUIPOS = ["BOS", "NYK", "LAL", "GSW", "MIA", "CHI"]


def pronostico(partido, **kw):
    base = dict(partido_id=partido, mercado="ganador", version_modelo="t", version_datos="d" * 64, objetivo_en=AYER,
                escenarios={"a": 1}, distribucion={"p": 0.6})
    base.update(kw)
    return PronosticoNuevo(**base)


def liga(db, dias=30, fecha_base=date(2026, 1, 1)):
    """Seis equipos, un partido por día entre parejas rotativas, resultados reconstruidos conocidos."""
    ids = {t: identidad.equipo(db, t) for t in EQUIPOS}
    partidos = []
    for d in range(dias):
        a, b = EQUIPOS[d % 6], EQUIPOS[(d + 1 + d // 6) % 6]
        if a == b:
            b = EQUIPOS[(d + 2) % 6]
        fecha = fecha_base + timedelta(days=d)
        pid = identidad.partido(db, "nba_oficial", f"00225{d:05d}", fecha, ids[a], ids[b], identidad.temporada(fecha))
        recibido = datetime.combine(fecha + timedelta(days=1), datetime.min.time(), UTC) + timedelta(hours=6)
        guardar_datos(db, [DatoNuevo(partido_id=pid, entidad_id=ids[a], metrica="puntos", fase="final", fuente="nba_oficial",
                                     recibido_en=recibido, valor=100.0 + d, pit="reconstruido"),
                           DatoNuevo(partido_id=pid, entidad_id=ids[b], metrica="puntos", fase="final", fuente="nba_oficial",
                                     recibido_en=recibido, valor=98.0 + (d * 7) % 11, pit="reconstruido")])
        partidos.append((pid, fecha, a, b))
    return ids, partidos


def test_sellar_encadena_verifica_y_es_idempotente(base_migrada):
    db = base_migrada
    ids, partidos = liga(db, 5)
    h1 = sellado.sellar(db, pronostico(partidos[0][0]))
    h2 = sellado.sellar(db, pronostico(partidos[1][0]))
    assert h1 != h2 and sellado.sellar(db, pronostico(partidos[0][0])) == h1
    filas = db.execute("SELECT hash_previo, hash FROM nba.pronostico ORDER BY pronostico_id").fetchall()
    assert filas == [(sellado.GENESIS, h1), (h1, h2)] and sellado.verificar_cadena(db) == 2


def test_no_se_sella_un_pronostico_con_datos_del_futuro(base_migrada):
    db = base_migrada
    _, partidos = liga(db, 2)
    with pytest.raises(ValueError, match="posterior"):
        sellado.sellar(db, pronostico(partidos[0][0], objetivo_en=datetime.now(UTC) + timedelta(hours=1)))
    assert db.execute("SELECT count(*) FROM nba.pronostico").fetchone()[0] == 0


def test_la_cadena_detecta_una_alteracion_y_la_base_la_impide(base_migrada):
    db = base_migrada
    _, partidos = liga(db, 4)
    for p in partidos[:3]:
        sellado.sellar(db, pronostico(p[0]))
    with pytest.raises(psycopg.Error), db.transaction():
        db.execute("UPDATE nba.pronostico SET version_modelo = 'x'")
    db.execute("ALTER TABLE nba.pronostico DISABLE TRIGGER pronostico_inmutable")      # solo en la base de prueba
    db.execute("UPDATE nba.pronostico SET distribucion = '{\"p\": 0.99}' WHERE pronostico_id = (SELECT min(pronostico_id) FROM nba.pronostico)")
    with pytest.raises(ValueError, match="alterado"):
        sellado.verificar_cadena(db)


def test_la_instantanea_solo_ve_el_pasado_y_su_huella_es_estable(base_migrada):
    db = base_migrada
    ids, partidos = liga(db, 20)
    objetivo = partidos[12]
    corte = datetime(2026, 1, 13, 12, tzinfo=UTC)
    a = pit.instantanea(db, objetivo[0], corte)
    assert all(f[0] < objetivo[1] for f in a.historia) and len(a.historia) == 12            # 12 partidos anteriores
    assert pit.instantanea(db, objetivo[0], corte).version_datos == a.version_datos
    # una fila propia llegada DESPUÉS del corte no cambia nada; una llegada antes del corte, sí
    guardar_datos(db, [DatoNuevo(partido_id=objetivo[0], entidad_id=ids["BOS"], metrica="estado_partido", fase="pre",
                                 fuente="nba_oficial", recibido_en=corte + timedelta(hours=1), etiqueta="programado")])
    assert pit.instantanea(db, objetivo[0], corte).version_datos == a.version_datos
    guardar_datos(db, [DatoNuevo(partido_id=objetivo[0], entidad_id=ids["BOS"], metrica="estado_partido", fase="pre",
                                 fuente="nba_oficial", recibido_en=corte - timedelta(hours=1), etiqueta="programado")])
    b = pit.instantanea(db, objetivo[0], corte)
    assert b.version_datos != a.version_datos and len(b.propias) == 1
    # el resultado final del propio partido nunca entra, aunque ya esté en la base
    assert all(f[3] != "final" for f in b.propias)
    with pytest.raises(ValueError):
        pit.instantanea(db, objetivo[0], datetime(2026, 1, 13))                              # sin zona horaria


def test_el_primer_partido_de_una_temporada_aplica_el_arrastre(base_migrada):
    db = base_migrada
    ids = {t: identidad.equipo(db, t) for t in ("BOS", "NYK")}
    pids = []
    for d, (fecha, a, b, pa, pb) in enumerate([(date(2026, 5, 1), "BOS", "NYK", 130.0, 90.0), (date(2026, 5, 3), "NYK", "BOS", 95.0, 120.0),
                                                (date(2026, 10, 25), "BOS", "NYK", 110.0, 105.0)]):
        pid = identidad.partido(db, "nba_oficial", f"002250{d}", fecha, ids[a], ids[b], identidad.temporada(fecha))
        recibido = datetime.combine(fecha + timedelta(days=1), datetime.min.time(), UTC)
        guardar_datos(db, [DatoNuevo(partido_id=pid, entidad_id=ids[a], metrica="puntos", fase="final", fuente="nba_oficial",
                                     recibido_en=recibido, valor=pa, pit="reconstruido"),
                           DatoNuevo(partido_id=pid, entidad_id=ids[b], metrica="puntos", fase="final", fuente="nba_oficial",
                                     recibido_en=recibido, valor=pb, pit="reconstruido")])
        pids.append(pid)
    corte = datetime(2026, 10, 25, 12, tzinfo=UTC)
    _, d_nueva = motor_equipo.pronosticar(pit.instantanea(db, pids[2], corte))
    r_nueva, _ = motor_equipo._ratings(pit.instantanea(db, pids[2], corte))
    p = motor_equipo.PARAMETROS
    esperado = nucleo.Ratings()                         # repetición manual: dos partidos de mayo, arrastre, y recién el de octubre
    nucleo.actualizar(esperado, "BOS", "NYK", 130.0, 90.0, p, nucleo.ajuste_descanso(7, 7, p))
    nucleo.actualizar(esperado, "NYK", "BOS", 95.0, 120.0, p, nucleo.ajuste_descanso(2, 2, p))
    nucleo.nueva_temporada(esperado, p)
    assert r_nueva.ataque["BOS"] == pytest.approx(esperado.ataque["BOS"]) and r_nueva.defensa["NYK"] == pytest.approx(esperado.defensa["NYK"])
    assert d_nueva["mu"][0] > 0


def test_el_motor_es_determinista_no_ve_el_futuro_y_se_niega_sin_historia(base_migrada):
    db = base_migrada
    ids, partidos = liga(db, 25)
    objetivo = partidos[15]
    corte = datetime(2026, 1, 16, 12, tzinfo=UTC)
    inst = pit.instantanea(db, objetivo[0], corte)
    e1, d1 = motor_equipo.pronosticar(inst)
    e2, d2 = motor_equipo.pronosticar(pit.instantanea(db, objetivo[0], corte))
    assert (e1, d1) == (e2, d2) and 0.0 < d1["p_local"] < 1.0 and d1["margen"][99] == pytest.approx(d1["mu"][0] - d1["mu"][1], abs=1.0)
    # cambiar el resultado de un partido POSTERIOR (otra fecha) no mueve el pronóstico
    futuro = partidos[20][0]
    guardar_datos(db, [DatoNuevo(partido_id=futuro, entidad_id=ids[partidos[20][2]], metrica="puntos", fase="final", fuente="espn",
                                 recibido_en=datetime(2026, 11, 3, tzinfo=UTC), valor=150.0, pit="reconstruido")])
    assert motor_equipo.pronosticar(pit.instantanea(db, objetivo[0], corte)) == (e1, d1)
    with pytest.raises(ValueError, match="sin historia"):
        motor_equipo.pronosticar(pit.instantanea(db, partidos[0][0], datetime(2026, 1, 1, 6, tzinfo=UTC)))
    # el pronóstico se puede sellar con la huella de la instantánea y la cadena queda verificable
    h = sellado.sellar(db, PronosticoNuevo(objetivo[0], "equipo", motor_equipo.VERSION_MODELO, inst.version_datos, corte, e1, d1))
    assert len(h) == 64 and sellado.verificar_cadena(db) == 1
