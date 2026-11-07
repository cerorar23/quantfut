"""Pruebas unitarias exhaustivas del módulo de sellado y contratos de tenis (Sprint 6)."""
from datetime import datetime, timedelta, timezone

import pytest

psycopg = pytest.importorskip("psycopg")

from db_util import cargar_minimo, insertar, ts
from tenis.contratos.marcador import SetMarcador
from tenis.contratos.salida import DistribucionPartido
from tenis.sellado import (
    CadenaRotaError,
    ContratoInvalidoError,
    CorteFuturoError,
    InicioDesconocidoError,
    SelloTardioError,
    cargar_pronostico_sellado,
    redondear_distribucion,
    sellar_pronostico,
    verificar_cadena,
)

UTC = timezone.utc


def S(a, b, tb=False):
    return SetMarcador(juegos_a=a, juegos_b=b, tiebreak=tb)


def distribucion_ejemplo():
    s1 = [S(6, 4), S(6, 4)]
    s2 = [S(4, 6), S(6, 4), S(4, 6)]
    # Probabilidades con muchos decimales para probar el redondeo estricto
    p1 = 0.6123456789
    p2 = 0.3876543211
    return {
        "mejor_de": 3,
        "regla_decisivo": "tiebreak_7",
        "entradas": [
            {"sets": [x.model_dump() for x in s1], "probabilidad": p1},
            {"sets": [x.model_dump() for x in s2], "probabilidad": p2},
        ],
        "mercados": {
            "gana_a": p1,
            "primer_set_a": p1,
            "sets_mas_de": {"2": p2},
            "juegos_mas_de": {"20.5": p2},
            "handicap_sets": {"-1.5": p1},
        },
    }


def partido_para_sellar(db, m, inicio="2099-06-01T10:00:00Z", ronda="QF"):
    r = db.execute("SELECT recibo_id FROM recibo LIMIT 1").fetchone()[0]
    a, b = m["jugadores"][0], m["jugadores"][1]
    p = insertar(
        db,
        "INSERT INTO partido (edicion_id, ronda, jugador_1, jugador_2, mejor_de, fuente, recibo_id, recibido_en) "
        "VALUES (%s, %s, %s, %s, 3, 'sofascore', %s, %s) RETURNING partido_id",
        (m["edicion"], ronda, a, b, r, ts("2026-01-05")),
    )
    db.execute(
        "INSERT INTO programa (partido_id, inicio_programado_utc, tipo_hora, estado, fuente, recibo_id, recibido_en) "
        "VALUES (%s, %s, 'fija', 'programado', 'sofascore', %s, %s)",
        (p, ts(inicio), r, ts("2026-01-05")),
    )
    return p


def test_redondear_distribucion_conserva_suma_exacta_y_coherencia():
    raw = distribucion_ejemplo()
    dist = redondear_distribucion(raw)
    assert isinstance(dist, DistribucionPartido)

    # Cada probabilidad de entrada debe tener a lo sumo 6 decimales
    for e in dist.entradas:
        p = e.probabilidad
        assert round(p, 6) == p

    # La masa total debe ser 1.0 exacto
    assert sum(e.probabilidad for e in dist.entradas) == 1.0

    # Los mercados deben coincidir a 6 decimales y cumplir tolerancia
    assert round(dist.mercados.gana_a, 6) == dist.mercados.gana_a
    assert round(dist.mercados.primer_set_a, 6) == dist.mercados.primer_set_a


def test_sellado_normal_y_verificacion_cadena(esquema):
    with esquema.conectar() as db:
        m = cargar_minimo(db)
        p = partido_para_sellar(db, m, inicio="2099-01-01T15:00:00Z")

        corte = datetime.now(UTC) - timedelta(hours=1)
        dist = distribucion_ejemplo()

        h = sellar_pronostico(
            db=db,
            partido_id=p,
            version_modelo="tenis-v2.0",
            version_datos="d_test",
            corte=corte,
            entradas={"ratings": {"theta1": 0.5}},
            distribucion=dist,
            referencia_mercado={"pinnacle": {"ganador": 1.75}},
        )
        assert len(h) == 64

        # Verificar cadena criptográfica completa
        res = verificar_cadena(db)
        assert res["integra"] is True
        assert res["total_sellos"] >= 2
        assert res["ultimo_hash"] == h

        # Recuperar pronóstico sellado y comprobar contrato Pydantic
        pron = cargar_pronostico_sellado(db, p)
        assert pron.partido_id == p
        assert pron.hash == h
        assert pron.version_modelo == "tenis-v2.0"
        assert pron.distribucion.mercados.gana_a > 0


def test_sellado_corte_futuro_se_rechaza(esquema):
    with esquema.conectar() as db:
        m = cargar_minimo(db)
        p = partido_para_sellar(db, m, inicio="2099-01-01T15:00:00Z")
        corte_futuro = datetime.now(UTC) + timedelta(hours=2)

        with pytest.raises(CorteFuturoError):
            sellar_pronostico(
                db=db,
                partido_id=p,
                version_modelo="v1",
                version_datos="d1",
                corte=corte_futuro,
                entradas={},
                distribucion=distribucion_ejemplo(),
            )


def test_sellado_tardio_se_rechaza(esquema):
    with esquema.conectar() as db:
        m = cargar_minimo(db)
        # Partido programado en el pasado
        p = partido_para_sellar(db, m, inicio="2020-01-01T10:00:00Z")
        corte = datetime(2019, 12, 31, 10, 0, tzinfo=UTC)

        with pytest.raises(SelloTardioError):
            sellar_pronostico(
                db=db,
                partido_id=p,
                version_modelo="v1",
                version_datos="d1",
                corte=corte,
                entradas={},
                distribucion=distribucion_ejemplo(),
            )


def test_sellado_sin_inicio_conocido_se_rechaza(esquema):
    with esquema.conectar() as db:
        m = cargar_minimo(db)
        r = db.execute("SELECT recibo_id FROM recibo LIMIT 1").fetchone()[0]
        # Partido sin fila en programa
        p = insertar(
            db,
            "INSERT INTO partido (edicion_id, ronda, jugador_1, jugador_2, mejor_de, fuente, recibo_id, recibido_en) "
            "VALUES (%s, 'R128', %s, %s, 3, 'sofascore', %s, %s) RETURNING partido_id",
            (m["edicion"], m["jugadores"][0], m["jugadores"][1], r, ts("2026-01-05")),
        )

        with pytest.raises(InicioDesconocidoError):
            sellar_pronostico(
                db=db,
                partido_id=p,
                version_modelo="v1",
                version_datos="d1",
                corte=datetime.now(UTC) - timedelta(hours=1),
                entradas={},
                distribucion=distribucion_ejemplo(),
            )


def test_cadena_detecta_corrupcion_de_hash(esquema):
    with esquema.conectar() as db:
        m = cargar_minimo(db)
        p = partido_para_sellar(db, m, inicio="2099-01-01T15:00:00Z")
        sellar_pronostico(
            db=db,
            partido_id=p,
            version_modelo="v1",
            version_datos="d1",
            corte=datetime.now(UTC) - timedelta(hours=1),
            entradas={},
            distribucion=distribucion_ejemplo(),
        )

        # Alterar una fila en la base (violando integridad) deshabilitando trigger momentáneamente
        db.execute("DROP TRIGGER IF EXISTS pronostico_inmutable ON pronostico")
        db.execute("UPDATE pronostico SET hash = %s WHERE partido_id = %s", ("f" * 64, p))

        with pytest.raises(CadenaRotaError):
            verificar_cadena(db)
