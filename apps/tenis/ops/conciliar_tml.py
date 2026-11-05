"""Conciliación de la carga TML (snapshot A, 16-oct) con la auditoría del 5-nov.

Crea un esquema aislado (y lo borra al terminar), carga el snapshot completo con el cargador real y compara sus
recuentos con las cifras de la auditoría. Escribe el informe Markdown en la carpeta de trabajo (TRABAJO) y lo imprime.

  python apps/tenis/ops/conciliar_tml.py
Requiere PG_DSN (o QF_TEST_PG_DSN) en el entorno: el usuario de la base puede crear esquemas, no bases ni roles.
"""
import os
import sys
import time
import uuid
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]           # apps/tenis
sys.path.insert(0, str(RAIZ / "tests"))
sys.path.insert(0, str(RAIZ / "src"))

import psycopg  # noqa: E402
from psycopg import sql  # noqa: E402

from db_util import MIGRACIONES, sql_de  # noqa: E402
from tenis.carga.tml_cli import ejecutar  # noqa: E402

SNAPSHOT = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\full_20261016\tml\originals")
TRABAJO = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\rediseno_20261104\tmp\conciliacion_tml")

# Cifras de la auditoría del 5-nov para este mismo snapshot (canónico de la auditoría).
AUDITORIA = {
    "partidos": 492_251, "atp": 394_592, "wta": 97_659, "elegibles_modelo": 249_938, "completados": 469_527,
    "mejor_de_3": 449_335, "mejor_de_5": 42_916, "Hard": 222_518, "Clay": 194_048, "Grass": 41_812,
    "Carpet": 33_873, "filas_invalidas": 3_923, "conflictos": 15,
}


def _consultas(cur) -> dict:
    def uno(q):
        cur.execute(q)
        return cur.fetchone()[0]
    datos = {
        "partidos": uno("SELECT count(*) FROM partido"),
        "atp": uno("SELECT count(*) FROM partido p JOIN edicion e ON e.edicion_id = p.edicion_id "
                   "JOIN torneo t ON t.torneo_id = e.torneo_id WHERE t.circuito = 'atp'"),
        "wta": uno("SELECT count(*) FROM partido p JOIN edicion e ON e.edicion_id = p.edicion_id "
                   "JOIN torneo t ON t.torneo_id = e.torneo_id WHERE t.circuito = 'wta'"),
        "completados": uno("SELECT count(*) FROM resultado WHERE estado = 'completado'"),
        "mejor_de_3": uno("SELECT count(*) FROM partido WHERE mejor_de = 3"),
        "mejor_de_5": uno("SELECT count(*) FROM partido WHERE mejor_de = 5"),
        "ranking": uno("SELECT count(*) FROM ranking"),
        "estadisticas": uno("SELECT count(*) FROM estadistica"),
        "jugadores": uno("SELECT count(*) FROM jugador"),
        "torneos": uno("SELECT count(*) FROM torneo"),
        "ediciones": uno("SELECT count(*) FROM edicion"),
    }
    cur.execute("SELECT e.superficie, count(*) FROM partido p JOIN edicion e ON e.edicion_id = p.edicion_id "
                "GROUP BY 1")
    for superficie, n in cur.fetchall():
        datos[f"superficie:{superficie}"] = n
    cur.execute("SELECT estado, count(*) FROM resultado GROUP BY 1")
    for estado, n in cur.fetchall():
        datos[f"estado:{estado}"] = n
    return datos


def _tabla(datos: dict, contadores: dict) -> str:
    """Tabla Markdown: nuestro recuento frente a la auditoría. Sin equivalente exacto, la celda dice «sin dato»."""
    mios = [
        ("Partidos cargados", datos["partidos"], AUDITORIA["partidos"]),
        ("ATP (gira, challenger y previas)", datos["atp"], AUDITORIA["atp"]),
        ("WTA", datos["wta"], AUDITORIA["wta"]),
        ("Completados", datos["completados"], AUDITORIA["completados"]),
        ("Mejor de 3", datos["mejor_de_3"], AUDITORIA["mejor_de_3"]),
        ("Mejor de 5", datos["mejor_de_5"], AUDITORIA["mejor_de_5"]),
        ("Superficie Hard", datos.get("superficie:hard", 0), AUDITORIA["Hard"]),
        ("Superficie Clay", datos.get("superficie:clay", 0), AUDITORIA["Clay"]),
        ("Superficie Grass", datos.get("superficie:grass", 0), AUDITORIA["Grass"]),
        ("Superficie Carpet", datos.get("superficie:carpet", 0), AUDITORIA["Carpet"]),
        ("Elegibles para el modelo", None, AUDITORIA["elegibles_modelo"]),
        ("Filas rechazadas (cuarentena)", contadores["rechazadas"], AUDITORIA["filas_invalidas"]),
        ("Duplicados de partido (conservada la primera)", contadores["duplicados"], AUDITORIA["conflictos"]),
        ("Conflictos de ranking (valor distinto el mismo lunes)", contadores["conflictos_ranking"], None),
    ]
    filas = ["| Concepto | Carga | Auditoría 5-nov | Diferencia |", "|---|---:|---:|---:|"]
    for nombre, mio, aud in mios:
        m = "sin dato" if mio is None else f"{mio:,}".replace(",", " ")
        a = "sin dato" if aud is None else f"{aud:,}".replace(",", " ")
        d = "" if (mio is None or aud is None) else f"{mio - aud:+,}".replace(",", " ")
        filas.append(f"| {nombre} | {m} | {a} | {d} |")
    return "\n".join(filas)


def main() -> int:
    dsn = os.environ.get("QF_TEST_PG_DSN") or os.environ.get("PG_DSN")
    if not dsn:
        raise SystemExit("falta PG_DSN")
    TRABAJO.mkdir(parents=True, exist_ok=True)
    esquema = f"tenis_conc_{uuid.uuid4().hex[:10]}"
    t0 = time.time()
    with psycopg.connect(dsn, autocommit=True) as admin:
        for nombre in MIGRACIONES:
            admin.execute(sql_de(nombre, esquema, esquema + "_op"))
    try:
        rechazos = TRABAJO / "rechazos_tml_full_20261016.csv"
        res = ejecutar(SNAPSHOT, dsn, esquema, SNAPSHOT.parents[1] / "download_manifest.json",
                       TRABAJO / "almacen", rechazos, equivalencias=RAIZ / "config" / "equivalencias.csv")
        with psycopg.connect(dsn, autocommit=True) as db:
            db.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(esquema)))
            datos = _consultas(db.cursor())
        c = res["contadores"]
        rechazadas = sum(v for k, v in c.items() if k.startswith("rechazo:"))
        contadores = {"rechazadas": rechazadas, "duplicados": c.get("duplicado", 0),
                      "conflictos_ranking": c.get("conflicto_ranking", 0)}
        tabla = _tabla(datos, contadores)
        resumen = "\n".join(f"- {k}: {v}" for k, v in sorted(c.items()))
        informe = (
            "# Conciliación de la carga TML (snapshot 16-oct) con la auditoría del 5-nov\n\n"
            f"Generado por `apps/tenis/ops/conciliar_tml.py`. Esquema aislado `{esquema}` (borrado al terminar).\n\n"
            f"Leídas: {res['leidas']:,}. Cuadra leídas = cargadas + rechazadas + duplicadas + dobles: **{res['cuadra']}**.\n"
            f"Tiempo de la carga completa: {res['segundos']} s.\n\n"
            f"## Recuentos\n\n{tabla}\n\n## Contadores de la carga\n\n{resumen}\n\n"
            "## Datos de la base\n\n" + "\n".join(f"- {k}: {v}" for k, v in sorted(datos.items())) + "\n\n"
            "## Ficheros no cargados\n\n"
            + "\n".join(f"- {n} ({m}): {f:,} filas" for n, m, f in res["no_cargados"]) + "\n")
        (TRABAJO / "conciliacion_tml.md").write_text(informe, encoding="utf-8")
        print(informe)
        return 0 if res["cuadra"] else 1
    finally:
        with psycopg.connect(dsn, autocommit=True) as admin:
            admin.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(esquema)))
            admin.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(esquema + "_op")))


if __name__ == "__main__":
    raise SystemExit(main())
