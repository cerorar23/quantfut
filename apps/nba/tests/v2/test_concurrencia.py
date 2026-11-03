"""Concurrencia del sellado: varios procesos sellando a la vez no pueden romper la cadena ni duplicar sellos."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, UTC

import psycopg

from nba.v2 import sellado
from nba.v2.sellado import PronosticoNuevo
from test_sellado_pit import liga

AYER = datetime.now(UTC) - timedelta(days=1)


def test_ocho_procesos_sellando_a_la_vez_dejan_una_cadena_integra_sin_duplicados(base_migrada_dsn):
    with psycopg.connect(base_migrada_dsn) as db:
        _, partidos = liga(db, 30)
        db.commit()
    pids = [p[0] for p in partidos]

    def trabajador(k: int):
        hashes = []
        with psycopg.connect(base_migrada_dsn) as db:
            for i in range(25):
                pid = pids[(k + i) % len(pids)]                       # los hilos se pisan a propósito: la misma clave la intentan varios
                hashes.append(sellado.sellar(db, PronosticoNuevo(pid, "equipo", "v-conc", "d" * 64, AYER, {"i": i}, {"p": 0.5})))
        return hashes

    with ThreadPoolExecutor(max_workers=8) as pool:
        resultados = list(pool.map(trabajador, range(8)))
    with psycopg.connect(base_migrada_dsn) as db:
        n = db.execute("SELECT count(*) FROM nba.pronostico").fetchone()[0]
        assert n == len(set(pids[(k + i) % len(pids)] for k in range(8) for i in range(25)))        # una sola fila por clave única
        assert sellado.verificar_cadena(db) == n
        assert db.execute("SELECT count(DISTINCT hash_previo) FROM nba.pronostico").fetchone()[0] == n   # cada eslabón apunta a uno distinto
    # quien repitió una clave recibió el mismo hash que quien la selló
    por_clave = {}
    for k, hashes in enumerate(resultados):
        for i, h in enumerate(hashes):
            assert por_clave.setdefault(pids[(k + i) % len(pids)], h) == h
