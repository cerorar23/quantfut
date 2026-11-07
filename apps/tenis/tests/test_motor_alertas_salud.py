"""Pruebas del motor programado, alertas y chequeos de salud de tenis v2 (Sprint 6)."""
from datetime import datetime, timedelta, timezone

import pytest

psycopg = pytest.importorskip("psycopg")

from db_util import cargar_minimo, insertar, ts
from tenis import alertas, salud
from tenis.motor import (
    buscar_partidos_pendientes,
    ejecutar_pasada_motor,
    simular_y_sellar_partido,
)
from tenis.sellado import verificar_cadena

UTC = timezone.utc


def test_alertas_deduplicacion():
    alertas.sembrar_alertas()  # limpiar estado
    fecha = "2026-11-10"

    r1 = alertas.enviar_alerta("sello_tardio", "Partido ya empezó", partido_id=101, fecha=fecha)
    assert r1["estado"] in ("registrada_local", "enviada")

    # Segunda emisión el mismo día y para el mismo partido -> debe ser omitida
    r2 = alertas.enviar_alerta("sello_tardio", "Partido ya empezó (segundo intento)", partido_id=101, fecha=fecha)
    assert r2["estado"] == "omitida_deduplicada"

    # Distinto tipo o distinto partido -> debe registrarse
    r3 = alertas.enviar_alerta("contrato_roto", "Error de contrato", partido_id=101, fecha=fecha)
    assert r3["estado"] in ("registrada_local", "enviada")

    r4 = alertas.enviar_alerta("sello_tardio", "Otro partido empezó", partido_id=102, fecha=fecha)
    assert r4["estado"] in ("registrada_local", "enviada")


def test_salud_informe_completo(esquema):
    with esquema.conectar() as db:
        cargar_minimo(db)

        # 1. Comprobar cadena
        c_cad = salud.comprobar_cadena(db)
        assert c_cad["estado"] == "ok"
        assert c_cad["total_sellos"] >= 1

        # 2. Comprobar frescura capturas
        c_fresc = salud.comprobar_frescura_capturas(db, max_horas=999999)
        assert c_fresc["estado"] == "ok"

        # 3. Comprobar sin_resolver
        c_sin = salud.comprobar_tasa_sin_resolver(db)
        assert c_sin["estado"] in ("ok", "alerta")

        # 4. Comprobar artefacto activo
        c_art = salud.comprobar_artefacto_activo(db)
        assert c_art["estado"] == "ok"
        assert len(c_art["sha256"]) == 64

        # 5. Informe completo
        inf = salud.informe_salud_completo(db)
        assert "fecha_utc" in inf
        assert inf["cadena"]["estado"] == "ok"


def test_motor_simulacion_y_sellado(esquema):
    with esquema.conectar() as db:
        m = cargar_minimo(db)
        r = db.execute("SELECT recibo_id FROM recibo LIMIT 1").fetchone()[0]

        # Crear partido futuro para el motor
        p = insertar(
            db,
            "INSERT INTO partido (edicion_id, ronda, jugador_1, jugador_2, mejor_de, fuente, recibo_id, recibido_en) "
            "VALUES (%s, 'SF', %s, %s, 3, 'sofascore', %s, %s) RETURNING partido_id",
            (m["edicion"], m["jugadores"][0], m["jugadores"][1], r, ts("2026-01-05")),
        )
        inicio_futuro = ts("2099-01-01T14:00:00Z")
        db.execute(
            "INSERT INTO programa (partido_id, inicio_programado_utc, tipo_hora, estado, fuente, recibo_id, recibido_en) "
            "VALUES (%s, %s, 'fija', 'programado', 'sofascore', %s, %s)",
            (p, inicio_futuro, r, ts("2026-01-05")),
        )

        pendientes = buscar_partidos_pendientes(db, "v1")
        assert any(x["partido_id"] == p for x in pendientes)

        partido_dict = next(x for x in pendientes if x["partido_id"] == p)

        # Prueba dry-run: debe generar DistribucionPartido sin escribir
        res_dry = simular_y_sellar_partido(
            db=db,
            partido=partido_dict,
            version_modelo="v1",
            version_datos="d_test",
            parametros={},
            forzar_corte=datetime.now(UTC) - timedelta(hours=1),
            dry_run=True,
        )
        assert res_dry["estado"] == "dry_run_ok"
        assert res_dry["distribucion"]["mercados"]["gana_a"] > 0

        # Prueba de sellado real con forzar_corte
        corte_fijo = datetime.now(UTC) - timedelta(hours=2)
        res_real = simular_y_sellar_partido(
            db=db,
            partido=partido_dict,
            version_modelo="v1",
            version_datos="d_test",
            parametros={},
            forzar_corte=corte_fijo,
            dry_run=False,
        )
        assert res_real["estado"] == "sellado"
        assert len(res_real["hash"]) == 64

        # Validar que la cadena se conserva íntegra tras el sello del motor
        cad = verificar_cadena(db)
        assert cad["integra"] is True


def test_motor_omite_partido_tardio(esquema):
    with esquema.conectar() as db:
        m = cargar_minimo(db)
        r = db.execute("SELECT recibo_id FROM recibo LIMIT 1").fetchone()[0]

        # Partido que empezó en el pasado
        p = insertar(
            db,
            "INSERT INTO partido (edicion_id, ronda, jugador_1, jugador_2, mejor_de, fuente, recibo_id, recibido_en) "
            "VALUES (%s, 'QF', %s, %s, 3, 'sofascore', %s, %s) RETURNING partido_id",
            (m["edicion"], m["jugadores"][0], m["jugadores"][1], r, ts("2026-01-05")),
        )
        inicio_pasado = ts("2020-01-01T10:00:00Z")
        db.execute(
            "INSERT INTO programa (partido_id, inicio_programado_utc, tipo_hora, estado, fuente, recibo_id, recibido_en) "
            "VALUES (%s, %s, 'fija', 'programado', 'sofascore', %s, %s)",
            (p, inicio_pasado, r, ts("2026-01-05")),
        )

        partido_dict = {
            "partido_id": p,
            "circuito": "atp",
            "superficie": "hard",
            "mejor_de": 3,
            "inicio_programado_utc": inicio_pasado,
        }

        alertas.sembrar_alertas()
        res = simular_y_sellar_partido(
            db=db,
            partido=partido_dict,
            version_modelo="v1",
            version_datos="d1",
            parametros={},
            forzar_corte=None,
        )
        assert res["estado"] == "omitido_tardio"
        # Debe haber registrado alerta de sello tardío
        assert alertas.esta_enviada("sello_tardio", partido_id=p)
