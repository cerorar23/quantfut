"""Presupuesto de peticiones (tenis_op.presupuesto): topes diario y semanal, tope desconocido, concurrencia."""
import threading
from datetime import datetime, timezone

import pytest

psycopg = pytest.importorskip("psycopg")

from tenis.captura import presupuesto as pr  # noqa: E402

LUNES = datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc)  # lunes de la semana ISO 45 de 2026


def conexion(e):
    db = psycopg.connect(e.dsn, autocommit=True)
    db.execute(f"SET search_path TO {e.nombre}, {e.nombre_op}, public")
    return db


def usadas(db, dia):
    fila = db.execute("SELECT usadas FROM presupuesto WHERE fuente = 'sportsapipro' AND dia = %s",
                      (dia,)).fetchone()
    return fila[0] if fila else None


def test_sin_fila_no_hay_permiso_de_gasto(esquema):
    with conexion(esquema) as db:
        with pytest.raises(pr.SinTopeConocido):
            pr.reservar(db, "sportsapipro", 1, LUNES)


def test_tope_null_no_es_cero_ni_infinito(esquema):
    with conexion(esquema) as db:
        pr.fijar_tope(db, "sportsapipro", LUNES, None)
        with pytest.raises(pr.SinTopeConocido):
            pr.reservar(db, "sportsapipro", 1, LUNES)
        assert usadas(db, LUNES.date()) == 0


def test_tope_cero_rechaza_cualquier_reserva(esquema):
    with conexion(esquema) as db:
        pr.fijar_tope(db, "sportsapipro", LUNES, 0)
        with pytest.raises(pr.TopeDiarioAgotado):
            pr.reservar(db, "sportsapipro", 1, LUNES)


def test_reserva_por_encima_del_tope_diario_no_cambia_nada(esquema):
    with conexion(esquema) as db:
        pr.fijar_tope(db, "sportsapipro", LUNES, 1)
        pr.reservar(db, "sportsapipro", 1, LUNES)
        with pytest.raises(pr.TopeDiarioAgotado):
            pr.reservar(db, "sportsapipro", 1, LUNES)
        assert usadas(db, LUNES.date()) == 1


def test_tope_semanal_de_dos_peticiones_aunque_el_diario_sobre(esquema):
    with conexion(esquema) as db:
        for dia in (2, 3, 4):
            pr.fijar_tope(db, "sportsapipro", LUNES.replace(day=dia), 100)
        pr.reservar(db, "sportsapipro", 1, LUNES.replace(day=2))
        pr.reservar(db, "sportsapipro", 1, LUNES.replace(day=3))
        with pytest.raises(pr.TopeSemanalAgotado):
            pr.reservar(db, "sportsapipro", 1, LUNES.replace(day=4))
        # La semana siguiente empieza con cupo nuevo.
        pr.fijar_tope(db, "sportsapipro", LUNES.replace(day=9), 100)
        pr.reservar(db, "sportsapipro", 1, LUNES.replace(day=9))


def test_devolver_restituye_la_cuota_y_no_baja_de_cero(esquema):
    with conexion(esquema) as db:
        pr.fijar_tope(db, "sportsapipro", LUNES, 5)
        pr.reservar(db, "sportsapipro", 1, LUNES)
        pr.devolver(db, "sportsapipro", 1, LUNES)
        assert usadas(db, LUNES.date()) == 0
        pr.devolver(db, "sportsapipro", 1, LUNES)
        assert usadas(db, LUNES.date()) == 0


def test_confirmar_sin_reserva_es_error(esquema):
    with conexion(esquema) as db:
        pr.fijar_tope(db, "sportsapipro", LUNES, 5)
        with pytest.raises(ValueError):
            pr.confirmar(db, "sportsapipro", 1, LUNES)


def test_fuente_sin_tope_semanal_solo_aplica_el_diario(esquema):
    with conexion(esquema) as db:
        pr.fijar_tope(db, "propline", LUNES, 3)
        for _ in range(3):
            pr.reservar(db, "propline", 1, LUNES)
        with pytest.raises(pr.TopeDiarioAgotado):
            pr.reservar(db, "propline", 1, LUNES)


def test_dos_reservas_simultaneas_no_pasan_del_tope(esquema):
    with conexion(esquema) as preparacion:
        pr.fijar_tope(preparacion, "sportsapipro", LUNES, 1)
    barrera = threading.Barrier(2)
    resultados = []

    def intentar():
        with conexion(esquema) as db:
            barrera.wait()
            try:
                pr.reservar(db, "sportsapipro", 1, LUNES)
                resultados.append("ok")
            except pr.PresupuestoError as exc:
                resultados.append(type(exc).__name__)

    hilos = [threading.Thread(target=intentar) for _ in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=60)
    assert sorted(resultados) == ["TopeDiarioAgotado", "ok"]
    with conexion(esquema) as db:
        assert usadas(db, LUNES.date()) == 1
