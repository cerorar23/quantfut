from datetime import datetime, timedelta, UTC

import numpy as np
import pytest

from nba.v2 import identidad, motor_jugadores, parametros, pit
from nba.v2.carga import DatoNuevo, guardar_datos
from nba.v2.plantilla_pit import plantilla
from test_sellado_pit import EQUIPOS, liga

ADQUIRIDO = datetime(2026, 11, 2, tzinfo=UTC)


def con_jugadores(db, n=30, traspaso=None):
    """Liga de 6 equipos con 9 jugadores cada uno: minutos y estadísticas deterministas, equipo del jugador y caja final.
    `traspaso` = (jugador_idx, partido_desde): ese jugador de BOS pasa a NYK desde esa posición."""
    ids, partidos = liga(db, n)
    jugadores = {t: [identidad.jugador(db, "nba_oficial", f"{1000 + 10 * k + i}", f"{t} jugador {i}") for i in range(9)]
                 for k, t in enumerate(EQUIPOS)}
    minutos = [34, 32, 30, 28, 24, 20, 16, 10, 3]
    filas = []
    for pos, (pid, fecha, a, b) in enumerate(partidos):
        for t in (a, b):
            equipo = t
            plantel = list(enumerate(jugadores[t]))
            if traspaso is not None and pos > traspaso:
                if t == "BOS":
                    plantel = [(i, j) for i, j in plantel if i != 1]                  # el viajero ya no juega con BOS
                elif t == "NYK":
                    plantel.append((1, jugadores["BOS"][1]))                         # …y juega con NYK
            for i, jug in plantel:
                m = minutos[i] + (pos % 3) - 1
                base = dict(partido_id=pid, entidad_id=jug, fase="final", fuente="nba_oficial", recibido_en=ADQUIRIDO, pit="reconstruido")
                filas += [DatoNuevo(metrica="minutos", valor=float(m), **base), DatoNuevo(metrica="jugo", valor=1.0, **base),
                          DatoNuevo(metrica="puntos", valor=float(round(0.5 * m + (i + pos) % 4)), **base),
                          DatoNuevo(metrica="rebotes", valor=float(round(0.2 * m + (pos % 3))), **base),
                          DatoNuevo(metrica="asistencias", valor=float(round(0.12 * m + (i % 2))), **base),
                          DatoNuevo(metrica="triples_anotados", valor=float((i + pos) % 3), **base),
                          DatoNuevo(metrica="equipo_del_jugador", valor=float(ids[equipo]), **base)]
    guardar_datos(db, filas)
    db.commit()
    return ids, partidos, jugadores


def parte(db, pid, jug, estado, recibido):
    guardar_datos(db, [DatoNuevo(partido_id=pid, entidad_id=jug, metrica="estado_disponibilidad", etiqueta=estado, fase="pre",
                                 fuente="nba_oficial", recibido_en=recibido)])
    db.commit()


def test_la_plantilla_solo_ve_el_pasado_y_el_parte_visible_en_el_corte(base_migrada):
    db = base_migrada
    ids, partidos, jugadores = con_jugadores(db)
    pid, fecha, a, b = partidos[25]
    corte = datetime(fecha.year, fecha.month, fecha.day, 12, tzinfo=UTC)
    inst = pit.instantanea(db, pid, corte)
    p0 = plantilla(db, inst)
    lado_a = p0.lados["local"] if inst.local == a else p0.lados["visitante"]
    assert len(lado_a) == 9 and all(len(j.minutos) >= 5 and len(j.minutos) == len(j.stats) <= 30 for j in lado_a)
    assert all(j.estado is None for j in lado_a)
    # un parte llegado antes del corte se ve; uno llegado después, no
    jug = jugadores[a][0]
    parte(db, pid, jug, "Out", corte - timedelta(hours=2))
    p1 = plantilla(db, inst)
    assert {j.id: j.estado for l in p1.lados.values() for j in l}[jug] == "Out" and p1.version_datos != p0.version_datos
    parte(db, pid, jug, "Available", corte + timedelta(hours=1))
    assert plantilla(db, inst).version_datos == p1.version_datos
    # el resultado de un partido POSTERIOR no mueve la huella
    futuro = partidos[28][0]
    guardar_datos(db, [DatoNuevo(partido_id=futuro, entidad_id=jugadores[partidos[28][2]][0], metrica="minutos", valor=48.0, fase="final",
                                 fuente="nba_oficial", recibido_en=ADQUIRIDO, pit="reconstruido")])
    db.commit()
    assert plantilla(db, pit.instantanea(db, pid, corte)).version_datos == p1.version_datos


def test_un_jugador_traspasado_cuenta_solo_para_su_equipo_actual(base_migrada):
    db = base_migrada
    ids, partidos, jugadores = con_jugadores(db, traspaso=12)
    viajero = jugadores["BOS"][1]
    objetivo = next(p for p in partidos[22:] if "NYK" in (p[2], p[3]) and "BOS" in (p[2], p[3]))
    inst = pit.instantanea(db, objetivo[0], datetime(objetivo[1].year, objetivo[1].month, objetivo[1].day, 12, tzinfo=UTC))
    p = plantilla(db, inst)
    donde = {j.id: lado for lado, js in p.lados.items() for j in js}
    assert viajero in donde and donde[viajero] == ("local" if inst.local == "NYK" else "visitante")


def test_los_props_son_distribuciones_coherentes_y_deterministas(base_migrada):
    db = base_migrada
    ids, partidos, jugadores = con_jugadores(db)
    pid, fecha, a, b = partidos[25]
    corte = datetime(fecha.year, fecha.month, fecha.day, 12, tzinfo=UTC)
    parte(db, pid, jugadores[a][0], "Out", corte - timedelta(hours=1))
    par = parametros.cargar_props()
    pl = plantilla(db, pit.instantanea(db, pid, corte))
    r1, r2 = motor_jugadores.pronosticar(pl, par), motor_jugadores.pronosticar(pl, par)
    assert r1 == r2 and len(r1) > 0
    por_jugador = {}
    for x in r1:
        por_jugador.setdefault(x["jugador"], {})[x["mercado"]] = x
        assert sum(x["distribucion"]["pmf"]) == pytest.approx(1.0, abs=1e-4)
        assert x["distribucion"]["p10"] <= x["distribucion"]["p50"] <= x["distribucion"]["p90"]
    assert jugadores[a][0] not in por_jugador                        # el ausente seguro no se pronostica
    assert all(set(m) == set(motor_jugadores.NOMBRES_MERCADO.values()) for m in por_jugador.values())
    titular = por_jugador[jugadores[b][0]] if jugadores[b][0] in por_jugador else por_jugador[jugadores[a][1]]
    suplente_id = jugadores[a][7]
    assert titular["jugador:puntos"]["distribucion"]["media"] > 8                       # ≈ 0,5 pts/min × 30 min
    if suplente_id in por_jugador:
        assert por_jugador[suplente_id]["jugador:puntos"]["distribucion"]["media"] < titular["jugador:puntos"]["distribucion"]["media"]
    assert jugadores[a][8] not in por_jugador and jugadores[b][8] not in por_jugador       # 3 minutos esperados: fuera de rotación


def test_sin_historial_suficiente_no_hay_plantilla(base_migrada):
    db = base_migrada
    ids, partidos, _ = con_jugadores(db, n=8)
    pid, fecha, _, _ = partidos[3]
    pl = plantilla(db, pit.instantanea(db, pid, datetime(fecha.year, fecha.month, fecha.day, 12, tzinfo=UTC)))
    assert all(len(js) == 0 for js in pl.lados.values())          # nadie ha jugado 5 partidos todavía
    assert np.isfinite(len(motor_jugadores.pronosticar(pl, parametros.cargar_props())))
