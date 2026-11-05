# apps/tenis/ops/verificar_tml.py
"""Verificación INDEPENDIENTE de la carga TML: carga el snapshot en un esquema aislado y lo compara con los CSV originales
con código propio (no reutiliza el parseo del cargador): orientación del ganador, sets por lado, nulos frente a ceros,
invariantes de `visible_desde` e idempotencia (segunda carga = 0 filas nuevas).

Uso: python verificar_tml.py <carpeta tml/originals> [--max-muestra 40000]
"""
import argparse
import csv
import json
import os
import random
import re
import sys
import time
import uuid
from pathlib import Path

import psycopg
from psycopg import sql

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "tests"))
from db_util import MIGRACIONES, sql_de  # noqa: E402
from tenis.carga.tml_cli import ejecutar  # noqa: E402  (solo para ORQUESTAR la carga; las comprobaciones no lo usan)

SET = re.compile(r"(\d+)-(\d+)(?:\((\d+)\))?")
FICHERO = re.compile(r"^(\d{4})(_wta|_challenger)?\.csv$")


def leer_csv(carpeta: Path):
    """Filas crudas de los ficheros cargables (mismo alcance que el cargador: anuales, wta, challenger, quali)."""
    for p in sorted(carpeta.rglob("*.csv")):
        rel = p.relative_to(carpeta).as_posix()
        if not (FICHERO.match(rel) or re.match(r"^atp_quali/\d{4}_atp_quali\.csv$", rel)):
            continue
        with open(p, encoding="utf-8", newline="") as f:
            for fila in csv.DictReader(f):
                fila["_fichero"] = rel
                yield fila


def juegos_ganador_perdedor(score: str):
    """(juegos del ganador, juegos del perdedor) desde el marcador de TML (el ganador va primero en cada set)."""
    sets = SET.findall(score or "")
    return (sum(int(a) for a, _, _ in sets), sum(int(b) for _, b, _ in sets)) if sets else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("snapshot", type=Path)
    ap.add_argument("--max-muestra", type=int, default=40000)
    a = ap.parse_args()
    dsn = os.environ.get("QF_TEST_PG_DSN") or os.environ.get("PG_DSN")
    snap = a.snapshot.resolve()
    raiz = snap.parents[1]
    esquema = f"tenis_verif_{uuid.uuid4().hex[:8]}"
    trabajo = Path(os.environ.get("TEMP", ".")) / f"verif_{esquema}"
    trabajo.mkdir(parents=True, exist_ok=True)
    informe = {}
    with psycopg.connect(dsn, autocommit=True) as admin:
        for m in MIGRACIONES:
            admin.execute(sql_de(m, esquema, esquema + "_op"))
    try:
        t = time.time()
        r1 = ejecutar(snap, dsn, esquema, raiz / "download_manifest.json", trabajo / "almacen", trabajo / "rechazos.csv")
        informe["carga1"] = {"seg": round(time.time() - t), "leidas": r1["leidas"], "cuadra": r1["cuadra"], **r1["despues"]}
        t = time.time()
        r2 = ejecutar(snap, dsn, esquema, raiz / "download_manifest.json", trabajo / "almacen", trabajo / "rechazos2.csv")
        nuevas = {k: r2["despues"][k] - r1["despues"][k] for k in r1["despues"]}
        informe["carga2_filas_nuevas"] = nuevas
        informe["carga2_seg"] = round(time.time() - t)
        informe["idempotente"] = all(v == 0 for v in nuevas.values())

        db = psycopg.connect(dsn, autocommit=True)
        db.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(esquema)))
        crudo = {}
        n_crudas = 0
        for f in leer_csv(snap):
            n_crudas += 1
            crudo[(f["tourney_id"], f["round"], frozenset((f["winner_id"], f["loser_id"])))] = f
        informe["filas_crudas"] = n_crudas
        filas = db.execute(
            "SELECT t.clave, e.temporada, p.ronda, a1.id_fuente, a2.id_fuente, r.estado, r.ganador, r.sets "
            "FROM partido p JOIN edicion e ON e.edicion_id = p.edicion_id JOIN torneo t ON t.torneo_id = e.torneo_id "
            "JOIN resultado r ON r.partido_id = p.partido_id "
            "JOIN jugador_alias a1 ON a1.jugador_id = p.jugador_1 AND a1.fuente = 'tml' "
            "JOIN jugador_alias a2 ON a2.jugador_id = p.jugador_2 AND a2.fuente = 'tml' "
            "WHERE r.estado IN ('completado', 'retirada')").fetchall()
        informe["resultados_comprobables"] = len(filas)
        random.Random(20261105).shuffle(filas)
        muestra = filas[: a.max_muestra]
        sin_clave = mal_ganador = mal_juegos = comparados_juegos = 0
        for clave, temporada, ronda, id1, id2, estado, ganador, sets in muestra:
            f = crudo.get((f"{temporada}-{clave}", ronda, frozenset((id1, id2))))
            if f is None:
                sin_clave += 1
                continue
            ganador_db = id1 if ganador == 1 else id2
            if ganador_db != f["winner_id"]:
                mal_ganador += 1
            jg = juegos_ganador_perdedor(f["score"]) if estado == "completado" else None
            if jg:
                lado_g = 0 if ganador == 1 else 1
                db_g = sum(s[lado_g] for s in sets)
                db_p = sum(s[1 - lado_g] for s in sets)
                comparados_juegos += 1
                mal_juegos += (db_g, db_p) != jg
        informe["muestra"] = {"n": len(muestra), "sin_clave_en_csv": sin_clave, "ganador_mal_orientado": mal_ganador,
                              "juegos_comparados": comparados_juegos, "juegos_mal_orientados": mal_juegos}
        # Nulos frente a ceros: la base no debe tener ceros que el CSV no tiene, ni rellenar los NaN con 0.
        cero_db = db.execute("SELECT count(*) FROM estadistica WHERE puntos_saque = 0").fetchone()[0]
        nulos_db = db.execute("SELECT count(*) FILTER (WHERE puntos_saque IS NULL), count(*) FROM estadistica").fetchone()
        cero_csv = sum(1 for f in crudo.values() if f["w_svpt"] == "0")
        informe["estadistica"] = {"filas": nulos_db[1], "puntos_saque_NULL": nulos_db[0], "puntos_saque_cero_db": cero_db,
                                  "w_svpt_cero_csv": cero_csv}
        # Invariantes de visible_desde.
        viol = db.execute(
            "SELECT count(*) FROM partido p JOIN edicion e ON e.edicion_id = p.edicion_id "
            "WHERE p.visible_desde IS NOT NULL AND p.visible_desde > (e.fecha_fin + 1)::timestamp AT TIME ZONE 'UTC'"
        ).fetchone()[0]
        previo = db.execute(
            "SELECT count(*) FROM (SELECT edicion_id, ronda, visible_desde FROM partido WHERE visible_desde IS NOT NULL) x "
            "JOIN edicion e ON e.edicion_id = x.edicion_id WHERE x.visible_desde < e.visible_desde").fetchone()[0]
        # Protocolo retro: la pareja debe ser visible ESTRICTAMENTE antes que su resultado (si no, no se puede pronosticar).
        sin_orden = db.execute(
            "SELECT count(*) FROM partido p JOIN resultado r ON r.partido_id = p.partido_id "
            "WHERE p.visible_desde IS NOT NULL AND r.visible_desde IS NOT NULL AND p.visible_desde >= r.visible_desde"
        ).fetchone()[0]
        informe["visible_desde"] = {"partidos_despues_del_fin": viol, "partidos_antes_que_su_edicion": previo,
                                    "pareja_no_anterior_a_su_resultado": sin_orden}
        informe["rechazos_por_motivo"] = r1["contadores"]
        print(json.dumps(informe, indent=1, ensure_ascii=False, default=str))
        (trabajo / "informe_verificacion.json").write_text(json.dumps(informe, indent=1, ensure_ascii=False, default=str),
                                                           encoding="utf-8")
    finally:
        with psycopg.connect(dsn, autocommit=True) as admin:
            admin.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(esquema)))
            admin.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(esquema + "_op")))


if __name__ == "__main__":
    main()
