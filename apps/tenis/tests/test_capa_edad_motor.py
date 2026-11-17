"""Gancho de la capa de edad en el motor: lectura de edades al corte (PIT) y aplicación sobre π."""
from datetime import datetime, timedelta, timezone

import pytest

from tenis import motor
from tenis.modelo import capa_edad as ce

UTC = timezone.utc
CAPA = ce.CapaEdad(0.96, -0.15, 5.0, 12000, 2013, 2024)
PARAMS = {"capa_edad": CAPA.como_dict()}


def test_sin_capa_pi_intacta_y_sin_trazas():
    pi, traza = motor.aplicar_capa_edad(0.585, 22.0, 30.0, {})
    assert pi == 0.585 and traza == {}


def test_con_capa_el_mas_joven_sube():
    base, _ = motor.aplicar_capa_edad(0.5, None, None, PARAMS)
    joven, traza = motor.aplicar_capa_edad(0.5, 21.0, 31.0, PARAMS)     # lado 1 diez años más joven
    viejo, _ = motor.aplicar_capa_edad(0.5, 31.0, 21.0, PARAMS)
    assert base == pytest.approx(0.5) and joven > 0.5 > viejo
    assert joven + viejo == pytest.approx(1.0)                           # simetría de lados
    assert traza == {"capa_edad": True, "pi_base": 0.5, "edad_dif": -10.0}


def test_edad_desconocida_solo_pendiente():
    pi, traza = motor.aplicar_capa_edad(0.7, None, 25.0, PARAMS)
    esperado = float(ce.aplicar(0.7, float("nan"), CAPA))
    assert pi == pytest.approx(esperado) and traza["edad_dif"] is None


psycopg = pytest.importorskip("psycopg")
from db_util import cargar_minimo, ts  # noqa: E402
from inferencia_util import params_prueba, partido_futuro, ranking  # noqa: E402


def test_edades_al_corte_pit(esquema):
    with esquema.conectar() as db:
        m = cargar_minimo(db)
        a, b, c, _ = m["jugadores"]
        r = m["recibo"]
        for j, valor, cuando in ((a, "1996-04-10", "2026-01-05"), (b, "2002-09-01", "2026-01-05"),
                                 (b, "2000-01-01", "2026-03-01")):          # esta última llega DESPUÉS del corte
            db.execute("INSERT INTO jugador_asercion (jugador_id, campo, valor, fuente, recibo_id, recibido_en) "
                       "VALUES (%s, 'fecha_nacimiento', %s, 'sofascore', %s, %s)", (j, valor, r, ts(cuando)))
        corte = datetime(2026, 2, 1, tzinfo=UTC)
        e1, e2 = motor.edades_al_corte(db, a, b, corte)
        assert e1 == pytest.approx((corte - datetime(1996, 4, 10, tzinfo=UTC)).days / 365.25)
        assert e2 == pytest.approx((corte - datetime(2002, 9, 1, tzinfo=UTC)).days / 365.25)   # ignora la aserción futura
        assert motor.edades_al_corte(db, c, a, corte)[0] is None                              # sin fecha → None


def test_motor_con_capa_cambia_la_probabilidad_y_deja_traza(esquema):
    with esquema.conectar() as db:
        m = cargar_minimo(db)
        a, b, _, _ = m["jugadores"]
        r = m["recibo"]
        for j, valor in ((a, "1996-04-10"), (b, "2003-02-01")):
            db.execute("INSERT INTO jugador_asercion (jugador_id, campo, valor, fuente, recibo_id, recibido_en) "
                       "VALUES (%s, 'fecha_nacimiento', %s, 'sofascore', %s, %s)", (j, valor, r, ts("2026-01-05")))
        ranking(db, b, 80)
        partido = partido_futuro(db, m, a, b, "SF")
        partido = next(x for x in motor.buscar_partidos_pendientes(db, "vx") if x["partido_id"] == partido)
        corte = datetime.now(UTC) - timedelta(hours=2)
        kw = dict(db=db, partido=partido, version_modelo="vx", version_datos="d", forzar_corte=corte, dry_run=True)
        sin = motor.simular_y_sellar_partido(parametros=params_prueba(), **kw)
        con = motor.simular_y_sellar_partido(parametros=params_prueba(capa_edad=CAPA.como_dict()), **kw)
        assert sin["estado"] == con["estado"] == "dry_run_ok"
        # lado 2 (b) es ~7 años más joven: la capa le quita probabilidad al lado 1
        assert con["distribucion"]["mercados"]["gana_a"] < sin["distribucion"]["mercados"]["gana_a"]
