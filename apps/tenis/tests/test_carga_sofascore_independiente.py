"""Carga SofaScore sobre datos reales (muestra reproducible) frente a un cálculo aparte.

El cálculo aparte lee los JSON originales con código propio (sin funciones del parseo ni del cargador): estado por
status.code, formato por defaultPeriodCount, circuito por category.slug, y ganador y juegos de cada lado. Se compara con
lo que quedó en la base: recuentos por estado, formato y circuito, y ganador y juegos de 100 partidos al azar.
Se omite si falta el archivo de SofaScore o QF_TEST_PG_DSN.
"""
import gzip
import json
import os
import random
from collections import Counter
from pathlib import Path

import psycopg
import pytest

from tenis.carga.sofascore_carga import leer_indice
from tenis.carga.sofascore_cli import ejecutar

RAIZ = Path(r"C:\Users\huye\Documents\SOFASCORE\data\v3")
INDICE = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\rediseno_20261104\tablas"
              r"\sofascore_local_tenis_eventos.csv")
SEMILLA = 20261105
N_EVENTOS = 300
N_PARTIDOS = 100


@pytest.fixture(scope="module")
def muestra():
    if not INDICE.exists() or not RAIZ.exists():
        pytest.skip("archivo SofaScore no disponible")
    if not os.environ.get("QF_TEST_PG_DSN"):
        pytest.skip("QF_TEST_PG_DSN ausente")
    entradas = [e for e in leer_indice(INDICE) if e.motivo_sin_datos is None]
    return random.Random(SEMILLA).sample(entradas, N_EVENTOS)


def _crudo(recurso: str) -> dict:
    """JSON original del evento, leído aquí (independiente del cargador)."""
    return json.loads(gzip.decompress((RAIZ / recurso).read_bytes()))


def _esperado(ev: dict) -> dict:
    """Lo que debe quedar en la base para este evento, calculado sin las reglas del cargador."""
    codigo = ev["status"]["code"]
    estado = {100: "completado", 92: "retirada", 91: "walkover"}.get(codigo)
    marcador = []
    for n in range(1, 6):
        if f"period{n}" in ev["homeScore"] and f"period{n}" in ev["awayScore"]:
            marcador.append((ev["homeScore"][f"period{n}"], ev["awayScore"][f"period{n}"]))
    return {
        "circuito": ev["tournament"]["category"]["slug"],
        "mejor_de": ev["defaultPeriodCount"],
        "estado": estado,
        "ganador_local": ev.get("winnerCode"),
        "juegos_local": [g[0] for g in marcador],
        "juegos_visitante": [g[1] for g in marcador],
        "id_local": str(ev["homeTeam"]["id"]),
        "id_visitante": str(ev["awayTeam"]["id"]),
    }


def test_recuentos_y_ganador_y_juegos_frente_al_original(esquema, muestra, tmp_path):
    cont = ejecutar(INDICE, RAIZ, esquema.dsn, esquema.nombre, tmp_path / "almacen", tmp_path / "rech.csv",
                    entradas=muestra)["contadores"]
    assert cont["cargado"] > 0
    # Repetir la carga sobre datos reales: 0 partidos nuevos y ninguna fila añadida a la evidencia.
    with psycopg.connect(esquema.dsn, autocommit=True) as db:
        antes = db.execute(f"SELECT (SELECT count(*) FROM {esquema.nombre}.partido), "
                           f"(SELECT count(*) FROM {esquema.nombre}.resultado), "
                           f"(SELECT count(*) FROM {esquema.nombre}.juego_pbp), "
                           f"(SELECT count(*) FROM {esquema.nombre}.estadistica)").fetchone()
    otra = ejecutar(INDICE, RAIZ, esquema.dsn, esquema.nombre, tmp_path / "almacen", tmp_path / "rech2.csv",
                    entradas=muestra)["contadores"]
    with psycopg.connect(esquema.dsn, autocommit=True) as db:
        despues = db.execute(f"SELECT (SELECT count(*) FROM {esquema.nombre}.partido), "
                             f"(SELECT count(*) FROM {esquema.nombre}.resultado), "
                             f"(SELECT count(*) FROM {esquema.nombre}.juego_pbp), "
                             f"(SELECT count(*) FROM {esquema.nombre}.estadistica)").fetchone()
    assert antes == despues and otra.get("cargado", 0) == 0 and otra["ya_cargado"] == cont["cargado"]
    with psycopg.connect(esquema.dsn, autocommit=True) as db:
        db.execute(f"SET search_path TO {esquema.nombre}")
        recursos = db.execute("SELECT recurso FROM recibo WHERE fuente = 'sofascore' "
                              "AND recurso LIKE 'events/%/event.json.gz'").fetchall()
        bd_partidos = db.execute(
            "SELECT p.partido_id, p.jugador_1, p.jugador_2, p.mejor_de, t.circuito, r.estado, r.ganador, r.sets, "
            "rc.recurso FROM partido p JOIN resultado r ON r.partido_id = p.partido_id "
            "JOIN edicion e ON e.edicion_id = p.edicion_id JOIN torneo t ON t.torneo_id = e.torneo_id "
            "JOIN recibo rc ON rc.recibo_id = p.recibo_id").fetchall()
        alias = dict(db.execute("SELECT jugador_id, id_fuente FROM jugador_alias WHERE fuente = 'sofascore'"
                                ).fetchall())

    # Recuentos por estado, formato y circuito: base frente a cálculo aparte sobre los mismos eventos.
    esperados = [_esperado(_crudo(r[0])) for r in recursos]
    cuenta_bd = Counter((estado, mejor, circ) for (_, _, _, mejor, circ, estado, _, _, _) in bd_partidos)
    cuenta_crudo = Counter((e["estado"], e["mejor_de"], e["circuito"]) for e in esperados if e["estado"])
    assert cuenta_bd == cuenta_crudo
    assert len(bd_partidos) == len(recursos) - sum(1 for e in esperados if e["estado"] is None)

    # Ganador y juegos de cada lado: 100 partidos al azar, en orientación canónica (jugador_1 es el de id menor).
    por_recurso = {r[0]: _esperado(_crudo(r[0])) for r in recursos}
    elegidos = random.Random(SEMILLA + 1).sample(bd_partidos, min(N_PARTIDOS, len(bd_partidos)))
    for (pid, j1, j2, mejor, circ, estado, ganador, sets, recurso) in elegidos:
        e = por_recurso[recurso]
        local_es_j1 = alias[j1] == e["id_local"]
        assert alias[j1] in (e["id_local"], e["id_visitante"]) and alias[j2] in (e["id_local"], e["id_visitante"])
        assert (alias[j1] == e["id_local"]) != (alias[j2] == e["id_local"])
        assert j1 < j2
        if e["ganador_local"] in (1, 2) and estado in ("completado", "retirada"):
            esperado_ganador = e["ganador_local"] if local_es_j1 else 3 - e["ganador_local"]
            assert ganador == esperado_ganador, pid
        if estado == "completado":
            j1_juegos = e["juegos_local"] if local_es_j1 else e["juegos_visitante"]
            j2_juegos = e["juegos_visitante"] if local_es_j1 else e["juegos_local"]
            assert [s[0] for s in sets] == j1_juegos, pid
            assert [s[1] for s in sets] == j2_juegos, pid
