"""Comprobación cruzada con datos REALES (TML, copia local): muestra reproducible de 1.000 partidos ATP/WTA.

El cargador de aquí es MÍNIMO y solo sirve para esta prueba (el de producción es del Sprint 2). Los recuentos y
sumas esperados se calculan con pandas por otro camino (sobre la columna `score` y las columnas originales).
"""
import hashlib
import re
from datetime import date, timedelta
from pathlib import Path

import pytest

psycopg = pytest.importorskip("psycopg")
pd = pytest.importorskip("pandas")
from psycopg.types.json import Jsonb  # noqa: E402

from db_util import insertar, ts  # noqa: E402

PARQUET = Path("C:/Users/huye/Documents/apuesta proyec/data/tennis/full_20261016/canonical/matches.parquet")
N = 1000
SEMILLA = 20261104
RECIBIDO = ts("2026-11-04")
CORTE_PRUEBA = ts("2026-11-05")
COLUMNAS = ["tourney_id", "tourney_date", "round", "winner_id", "loser_id", "winner_name", "loser_name",
            "surface", "score", "best_of", "circuit", "minutes", "w_svpt", "w_1stIn", "w_1stWon", "w_2ndWon",
            "l_svpt", "l_1stIn", "l_1stWon", "l_2ndWon", "completed_standard", "valid_serve_counts",
            "eligible_model", "match_id"]
SUPERFICIE = {"Hard": "hard", "Clay": "clay", "Grass": "grass", "Carpet": "carpet"}
PATRON_SET = re.compile(r"(\d+)-(\d+)(?:\((\d+)\))?")


def parsear_sets(score: str):
    """Marcador TML desde la perspectiva del ganador: [(games_ganador, games_perdedor, tb_perdedor|None)]."""
    sets = []
    for tok in score.split():
        mm = PATRON_SET.fullmatch(tok)
        sets.append((int(mm[1]), int(mm[2]), int(mm[3]) if mm[3] else None))
    return sets


def muestra():
    """Registros (dict) de una muestra reproducible: ATP/WTA, completados, marcador limpio, sin duplicados."""
    if not PARQUET.exists():
        pytest.skip("copia local de matches.parquet ausente")
    df = pd.read_parquet(PARQUET, columns=COLUMNAS)
    ok = df.eligible_model & df.completed_standard & df.circuit.isin(["ATP", "WTA"])
    ok &= ~df.score.astype(str).str.contains(r"RET|W/O|DEF|ABN|Walkover", regex=True)
    ok &= df.score.astype(str).apply(lambda s: len(s.split()) >= 2 and all(PATRON_SET.fullmatch(t) for t in s.split()))
    m = df[ok].drop_duplicates(subset=["tourney_id", "round", "winner_id", "loser_id"])
    m = m.sample(n=N, random_state=SEMILLA).reset_index(drop=True)
    return m.to_dict("records")


def valido_saque(r, lado):
    p = "w_" if lado == "ganador" else "l_"
    svpt, dentro, ganados, seg = r[p + "svpt"], r[p + "1stIn"], r[p + "1stWon"], r[p + "2ndWon"]
    return bool(r["valid_serve_counts"]) and all(pd.notna(x) for x in (svpt, dentro, ganados, seg)) \
        and dentro <= svpt and ganados <= dentro


def cargar(db, registros):
    """Carga mínima: recibo, jugadores, torneos, ediciones, partidos, resultados y estadísticas."""
    with open(PARQUET, "rb") as f:
        sha = hashlib.file_digest(f, "sha256").hexdigest()
    rid = insertar(db, "INSERT INTO recibo (fuente, recurso, recibido_en, estado_http, sha256, ruta_objeto, bytes, lote, "
                       "retro) VALUES ('tml', 'matches.parquet', %s, 200, %s, %s, %s, 'prueba_cruzada', true) "
                       "RETURNING recibo_id",
                   (RECIBIDO, sha, f"objetos/{sha[:2]}/{sha}.csv.gz", PARQUET.stat().st_size))
    jugadores, torneos, ediciones = {}, {}, {}
    ganador_db, lunes_de, partidos = {}, {}, []

    def jugador(tml_id, circuito, nombre):
        if tml_id not in jugadores:
            jid = insertar(db, "INSERT INTO jugador (circuito, recibo_id, recibido_en) VALUES (%s, %s, %s) "
                               "RETURNING jugador_id", (circuito, rid, RECIBIDO))
            db.execute("INSERT INTO jugador_asercion (jugador_id, campo, valor, fuente, recibo_id, recibido_en) "
                       "VALUES (%s, 'nombre', %s, 'tml', %s, %s)", (jid, nombre, rid, RECIBIDO))
            jugadores[tml_id] = jid
        return jugadores[tml_id]

    for r in registros:
        circuito = r["circuit"].lower()
        slug = re.sub(r"[^a-z0-9-]+", "-", str(r["tourney_id"]).split("-", 1)[-1].lower()).strip("-") or "sin-nombre"
        if (circuito, slug) not in torneos:
            torneos[(circuito, slug)] = insertar(
                db, "INSERT INTO torneo (circuito, clave, nombre, fuente, recibo_id, recibido_en) "
                    "VALUES (%s, %s, %s, 'tml', %s, %s) RETURNING torneo_id", (circuito, slug, slug, rid, RECIBIDO))
        torneo = torneos[(circuito, slug)]
        s = str(r["tourney_date"])[:8]
        inicio = date(int(s[:4]), int(s[4:6]), int(s[6:8]))
        fin = inicio + timedelta(days=13)                      # cargador de prueba: fin aproximado de la edición
        lunes = fin - timedelta(days=fin.weekday())
        temporada = inicio.year
        if (torneo, temporada) not in ediciones:
            ediciones[(torneo, temporada)] = insertar(
                db, "INSERT INTO edicion (torneo_id, temporada, lunes_semana, superficie, fuente, recibo_id, recibido_en) "
                    "VALUES (%s, %s, %s, %s, 'tml', %s, %s) RETURNING edicion_id",
                (torneo, temporada, lunes, SUPERFICIE.get(r["surface"]), rid, RECIBIDO))
        edicion = ediciones[(torneo, temporada)]

        g = jugador(r["winner_id"], circuito, r["winner_name"])
        p = jugador(r["loser_id"], circuito, r["loser_name"])
        j1, j2 = sorted([g, p])
        pid = insertar(db, "INSERT INTO partido (edicion_id, ronda, jugador_1, jugador_2, mejor_de, fuente, recibo_id, "
                           "recibido_en) VALUES (%s, %s, %s, %s, %s, 'tml', %s, %s) RETURNING partido_id",
                       (edicion, str(r["round"]).upper(), j1, j2, int(r["best_of"]), rid, RECIBIDO))
        ganador_es_1 = g == j1
        ganador = 1 if ganador_es_1 else 2
        sets = parsear_sets(r["score"])
        if ganador_es_1:
            sets_j1 = [[gw, gl, None, tb] for gw, gl, tb in sets]      # el tiebreak parentizado es del perdedor (j2)
        else:
            sets_j1 = [[gl, gw, tb, None] for gw, gl, tb in sets]      # aquí el perdedor es j1
        minutos = int(r["minutes"]) if pd.notna(r["minutes"]) and 1 <= r["minutes"] <= 600 else None
        db.execute("INSERT INTO resultado (partido_id, estado, ganador, sets, sets_completos, duracion_min, fuente, "
                   "recibo_id, recibido_en) VALUES (%s, 'completado', %s, %s, %s, %s, 'tml', %s, %s)",
                   (pid, ganador, Jsonb(sets_j1), len(sets), minutos, rid, RECIBIDO))
        for lado_db, nombre in ((ganador, "ganador"), (3 - ganador, "perdedor")):
            if valido_saque(r, nombre):
                pre = "w_" if nombre == "ganador" else "l_"
                db.execute("INSERT INTO estadistica (partido_id, lado, puntos_saque, primeros_dentro, primeros_ganados, "
                           "segundos_ganados, fuente, recibo_id, recibido_en) "
                           "VALUES (%s, %s, %s, %s, %s, %s, 'tml', %s, %s)",
                           (pid, lado_db, int(r[pre + "svpt"]), int(r[pre + "1stIn"]), int(r[pre + "1stWon"]),
                            int(r[pre + "2ndWon"]), rid, RECIBIDO))
        ganador_db[pid] = g
        lunes_de[pid] = lunes
        partidos.append(pid)
    return {"partidos": partidos, "ganador_db": ganador_db, "lunes_de": lunes_de}


def test_cruce_con_datos_reales_recuentos_sumas_y_orden(esquema):
    registros = muestra()
    with esquema.conectar() as db:
        carga = cargar(db, registros)

        # Recuentos por formato (pandas, independiente de la base).
        esperado_formato = {}
        for r in registros:
            esperado_formato[int(r["best_of"])] = esperado_formato.get(int(r["best_of"]), 0) + 1
        obtenido_formato = dict(db.execute("SELECT mejor_de, count(*) FROM partido GROUP BY mejor_de").fetchall())
        assert obtenido_formato == esperado_formato
        assert db.execute("SELECT count(*) FROM partido").fetchone()[0] == N
        assert db.execute("SELECT count(*) FROM resultado").fetchone()[0] == N

        # Sets: total y sets ganados por el ganador, calculados sobre el texto `score` en pandas.
        esperado_total, esperado_ganados = 0, 0
        for r in registros:
            sets = parsear_sets(r["score"])
            esperado_total += len(sets)
            esperado_ganados += sum(1 for gw, gl, _ in sets if gw > gl)
        obtenido_total = db.execute("SELECT coalesce(sum(sets_completos), 0) FROM resultado").fetchone()[0]
        assert obtenido_total == esperado_total
        obtenido_ganados = 0
        for ganador, sets in db.execute("SELECT ganador, sets FROM resultado").fetchall():
            for gj1, gj2, _, _ in sets:
                gana_j1 = gj1 > gj2
                obtenido_ganados += int(gana_j1 if ganador == 1 else not gana_j1)
        assert obtenido_ganados == esperado_ganados

        # Orden canónico: jugador_1 < jugador_2 en todas las filas; el ganador reconstruido coincide con el real.
        assert db.execute("SELECT count(*) FROM partido WHERE jugador_1 >= jugador_2").fetchone()[0] == 0
        filas = db.execute("SELECT p.partido_id, p.jugador_1, p.jugador_2, r.ganador FROM partido p "
                           "JOIN resultado r USING (partido_id)").fetchall()
        assert len(filas) == N
        for pid, j1, j2, ganador in filas:
            reconstruido = j1 if ganador == 1 else j2
            assert reconstruido == carga["ganador_db"][pid]

        # Estadísticas: una fila por lado válido, con el mismo criterio de validez aplicado en pandas.
        esperado_est = sum(int(valido_saque(r, "ganador")) + int(valido_saque(r, "perdedor")) for r in registros)
        assert db.execute("SELECT count(*) FROM estadistica").fetchone()[0] == esperado_est

        # Lectura PIT sobre datos reales: un partido es visible si su edición terminó hace más de una semana.
        esperado_visibles = sum(1 for pid in carga["partidos"]
                                if carga["lunes_de"][pid] + timedelta(days=7) < CORTE_PRUEBA.date())
        visibles = db.execute("SELECT count(*) FROM partido_a_las(%s)", (CORTE_PRUEBA,)).fetchone()[0]
        assert visibles == esperado_visibles
