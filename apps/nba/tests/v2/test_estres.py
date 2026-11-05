"""Estrés del motor: un día de 15 partidos con fuentes caídas, datos faltantes y datos corruptos. Regla de oro: nunca se sella algo imputado como 0
ni con ratings viejos; lo que no se puede pronosticar se omite y se informa."""
from datetime import date, datetime, timedelta, UTC

import numpy as np
import pytest

from nba.contratos.validar import validar_equipo, validar_jugador
from nba.v2 import equipos, identidad, motor, sellado
from nba.v2.carga import DatoNuevo, guardar_datos_lote

ADQ = datetime(2026, 11, 2, tzinfo=UTC)
TRI = sorted(equipos.TRICODES)
MINUTOS = [34, 32, 30, 28, 24, 20, 16, 10, 3]


def liga_completa(db, dias=20, sin_hora=(), equipos_sin_datos=(), sin_puntos=None, minutos_corruptos=None):
    """30 equipos, 15 partidos por día durante `dias` días de historia y un día objetivo (el día `dias`) con 15 partidos."""
    ids = {t: identidad.equipo(db, t) for t in TRI}
    jug = {t: [identidad.jugador(db, "nba_oficial", f"{2000 + 20 * k + i}", f"{t} jugador {i}") for i in range(9)] for k, t in enumerate(TRI)}
    filas, objetivo, inicio = [], [], {}
    reloj = datetime.now(UTC)
    for d in range(dias + 1):
        rot = TRI[d % 29:] + TRI[:d % 29] if d else TRI
        for g in range(15):
            a, b = rot[g], rot[29 - g] if g else rot[29]
            if a == b:
                continue
            fecha = reloj.date() + timedelta(days=-dias+d)
            if d == dias:
                pid = identidad.partido(db, "nba_oficial", f"00225{d:03d}{g:02d}", fecha, ids[a], ids[b], identidad.temporada(fecha))
                objetivo.append((pid, a, b))
                if len(objetivo) - 1 not in sin_hora:
                    t = reloj + timedelta(minutes=30)
                    inicio[pid] = t
                    filas.append(DatoNuevo(partido_id=pid, entidad_id=ids[a], metrica="inicio_programado_utc", fase="pre", fuente="nba_oficial",
                                           recibido_en=datetime(2025, 12, 1, tzinfo=UTC), valor=t.timestamp()))
                continue
            if (a in equipos_sin_datos or b in equipos_sin_datos) and d > dias - 12:
                continue                                              # a esos equipos les faltan los resultados de los últimos 12 días
            pid = identidad.partido(db, "nba_oficial", f"00225{d:03d}{g:02d}", fecha, ids[a], ids[b], identidad.temporada(fecha))
            filas.append(DatoNuevo(partido_id=pid, entidad_id=pid, metrica="estado_partido", etiqueta="final", fase="final", fuente="nba_oficial",
                                   recibido_en=datetime(fecha.year, fecha.month, fecha.day, 6, tzinfo=UTC) + timedelta(days=1), pit="reconstruido"))           # el partido ya terminó (así lo registra la captura real)
            for t, eq in ((a, ids[a]), (b, ids[b])):
                recibido = datetime.combine(fecha + timedelta(days=1), datetime.min.time(), UTC) + timedelta(hours=6)
                base = dict(partido_id=pid, fase="final", fuente="nba_oficial", recibido_en=recibido, pit="reconstruido")
                filas.append(DatoNuevo(entidad_id=eq, metrica="puntos", valor=100.0 + (d * 7 + g) % 25, **base))
                for i, j in enumerate(jug[t]):
                    m = float(MINUTOS[i] + (d % 3) - 1)
                    if minutos_corruptos == j and d == dias - 1:
                        m = 150.0
                    b2 = dict(base, entidad_id=j)
                    filas += [DatoNuevo(metrica="minutos", valor=m, **b2), DatoNuevo(metrica="jugo", valor=1.0, **b2),
                              DatoNuevo(metrica="rebotes", valor=float(round(0.2 * m)), **b2), DatoNuevo(metrica="asistencias", valor=float(round(0.12 * m)), **b2),
                              DatoNuevo(metrica="triples_anotados", valor=float((i + d) % 3), **b2), DatoNuevo(metrica="equipo_del_jugador", valor=float(eq), **b2)]
                    if not (sin_puntos and j == sin_puntos and d >= dias - 3):          # el dato de puntos falta en sus 3 últimos partidos
                        filas.append(DatoNuevo(metrica="puntos", valor=float(round(0.5 * m + 1.5)), **b2))
    guardar_datos_lote(db, filas)
    db.commit()
    return ids, jug, objetivo, inicio


def ejecutar(db, inicio, objetivo):
    ahora = min(inicio.values()) - timedelta(minutes=30)
    return motor.ejecutar(db, ahora)


def media_puntos(db, jugador):
    fila = db.execute("SELECT distribucion->>'media' FROM nba.pronostico WHERE entidad_id = %s AND mercado = 'jugador:puntos'", (jugador,)).fetchone()
    return float(fila[0]) if fila else None


def test_dia_normal_de_15_partidos_sella_todo_y_todo_cumple_los_contratos(base_migrada):
    db = base_migrada
    ids, jug, objetivo, inicio = liga_completa(db)
    r = ejecutar(db, inicio, objetivo)
    assert r["errores"] == [] and len(r["sellados"]) == 15 and len(r["props"]) == 15 and r["omitidos"] == [] and r["sin_hora"] == []
    for mercado, dist in db.execute("SELECT mercado, distribucion FROM nba.pronostico").fetchall():
        (validar_equipo if mercado == "equipo" else validar_jugador)(dist)
    assert sellado.verificar_cadena(db) == db.execute("SELECT count(*) FROM nba.pronostico").fetchone()[0]


def test_dia_con_fuentes_caidas_omite_lo_que_no_se_puede_pronosticar_y_no_imputa_ceros(base_migrada):
    db = base_migrada
    sin_hora = {0, 1, 2, 3, 4}                                      # la hora de 5 partidos no llegó
    stale = {TRI[7], TRI[22]}                                         # a dos equipos les faltan los últimos 12 días de resultados
    base_normal = None
    ids, jug, objetivo, inicio = liga_completa(db, sin_hora=sin_hora, equipos_sin_datos=stale, sin_puntos=None)
    r = ejecutar(db, inicio, objetivo)
    con_hora = {pid for i, (pid, _, _) in enumerate(objetivo) if i not in sin_hora}
    atrasados = {pid for pid, a, b in objetivo if pid in con_hora and (a in stale or b in stale)}
    assert set(r["sin_hora"]) == {objetivo[i][0] for i in sin_hora}
    assert {o["partido"] for o in r["omitidos"] if o["razon"] == "equipo_sin_resultados_recientes"} == atrasados and atrasados
    assert r["errores"] == [] and {s["partido"] for s in r["sellados"]} == con_hora - atrasados
    sellados_db = {p for (p,) in db.execute("SELECT DISTINCT partido_id FROM nba.pronostico").fetchall()}
    assert sellados_db == con_hora - atrasados                      # nada de los omitidos llegó a la base, ni siquiera props
    assert sellado.verificar_cadena(db) > 0


def test_una_estadistica_que_falta_no_cuenta_como_cero(base_migrada):
    db = base_migrada
    ids, _, _, _ = (None,) * 4
    from nba.v2 import equipos as _  # noqa: F401
    db_ids = {t: identidad.equipo(db, t) for t in TRI}
    afectado = identidad.jugador(db, "nba_oficial", f"{2000 + 20 * 3 + 2}", f"{TRI[3]} jugador 2")      # el jugador 2 del equipo 3
    db.commit()
    ids, jug, objetivo, inicio = liga_completa(db, sin_puntos=afectado)
    ejecutar(db, inicio, objetivo)
    otros = [media_puntos(db, jug[t][2]) for t in TRI if t != TRI[3]]
    mio, tipico = media_puntos(db, afectado), float(np.mean([x for x in otros if x]))
    assert mio is not None and abs(mio / tipico - 1) < 0.05            # si los 3 partidos sin puntos se contaran como 0 caería ≈ 8-10 %


def test_minutos_corruptos_no_inflan_la_prediccion(base_migrada):
    db = base_migrada
    afectado = identidad.jugador(db, "nba_oficial", f"{2000 + 20 * 5 + 1}", f"{TRI[5]} jugador 1")
    db.commit()
    ids, jug, objetivo, inicio = liga_completa(db, minutos_corruptos=afectado)
    ejecutar(db, inicio, objetivo)
    esperados = {j: float(m) for j, m in db.execute("SELECT entidad_id, distribucion->>'minutos_esperados' FROM nba.pronostico WHERE mercado = 'jugador:puntos'")}
    tipico = float(np.mean([esperados[jug[t][1]] for t in TRI if t != TRI[5] and jug[t][1] in esperados]))
    assert esperados[afectado] == pytest.approx(tipico, rel=0.06) and esperados[afectado] <= 60


def test_sin_ninguna_historia_no_se_sella_nada_y_no_hay_errores(base_migrada):
    db = base_migrada
    ids, jug, objetivo, inicio = liga_completa(db, dias=0)
    r = ejecutar(db, inicio, objetivo)
    assert r["sellados"] == [] and r["errores"] == [] and {o["razon"] for o in r["omitidos"]} == {"historia_atrasada"}
    assert db.execute("SELECT count(*) FROM nba.pronostico").fetchone()[0] == 0


def test_base_vacia_no_rompe_el_motor(base_migrada):
    r = motor.ejecutar(base_migrada, datetime(2026, 11, 3, 12, tzinfo=UTC))
    assert r["sellados"] == [] and r["errores"] == [] and r["omitidos"] == [] and r["sin_hora"] == []
