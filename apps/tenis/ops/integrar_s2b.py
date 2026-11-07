# apps/tenis/ops/integrar_s2b.py
"""Integración del S2b sobre DATOS REALES, en un esquema aislado (se borra al terminar):

  1. carga TML (snapshot) con el cargador del S2a;
  2. carga SofaScore con el resolutor MULTIFUENTE (une los jugadores con los de TML por nombre, país y edad);
  3. mide la unión de jugadores (tasa, métodos, homónimos, contradicciones);
  4. VALIDA el calendario retro de TML contra las horas reales de SofaScore: en los partidos que están en las dos
     fuentes, ¿el `visible_desde` del resultado de TML cae ANTES del fin real? (eso sería una fuga) y ¿la pareja de TML
     se hace visible DESPUÉS del inicio real? (eso sería cobertura perdida);
  5. repite la carga de SofaScore: 0 filas nuevas.

Uso: python integrar_s2b.py <tml/originals> [--salida informe.json]
"""
import argparse
import json
import os
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
from tenis.carga import sofascore_cli, tml_cli  # noqa: E402
from tenis.identidad import enlazar  # noqa: E402
from tenis.identidad.resolver import ResolutorMultifuente, cargar_equivalencias  # noqa: E402

INDICE = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\rediseno_20261104\tablas\sofascore_local_tenis_eventos.csv")
RAIZ_SOFA = Path(r"C:\Users\huye\Documents\SOFASCORE\data\v3")

VALIDACION = """
WITH tml AS (
  SELECT p.jugador_1, p.jugador_2, p.ronda, p.visible_desde AS vis_pareja, r.visible_desde AS vis_res,
         e.visible_desde AS ed_ini, ((e.fecha_fin + 1)::timestamp AT TIME ZONE 'UTC') AS ed_fin,
         (e.fecha_fin - e.lunes_semana) AS dummy, (e.fecha_fin - (e.visible_desde AT TIME ZONE 'UTC')::date + 1) AS dias
  FROM partido p JOIN resultado r ON r.partido_id = p.partido_id AND r.fuente = 'tml'
  JOIN edicion e ON e.edicion_id = p.edicion_id AND e.fuente = 'tml'
  WHERE p.fuente = 'tml' AND p.visible_desde IS NOT NULL AND r.visible_desde IS NOT NULL),
sf AS (
  SELECT p.jugador_1, p.jugador_2, p.ronda AS ronda_sf, g.inicio_programado_utc AS inicio,
         (r.visible_desde - interval '30 minutes') AS fin_real
  FROM partido p JOIN programa g ON g.partido_id = p.partido_id AND g.fuente = 'sofascore'
  JOIN resultado r ON r.partido_id = p.partido_id AND r.fuente = 'sofascore'
  WHERE p.fuente = 'sofascore' AND r.estado IN ('completado', 'retirada'))
SELECT tml.dias, tml.ronda, count(*) AS comparados,
       sum((tml.vis_res < sf.fin_real)::int) AS fuga_resultado_antes_del_fin_real,
       sum((tml.vis_pareja > sf.inicio)::int) AS pareja_despues_del_inicio_real
FROM tml JOIN sf ON sf.jugador_1 = tml.jugador_1 AND sf.jugador_2 = tml.jugador_2
 AND sf.ronda_sf = tml.ronda AND sf.inicio >= tml.ed_ini AND sf.inicio < tml.ed_fin
GROUP BY tml.dias, tml.ronda ORDER BY tml.dias, tml.ronda
"""
# Una fila por partido comparable, con los desfases en DÍAS desde el inicio L (00:00 UTC) de la edición de TML: fin real
# (SofaScore), inicio real y el instante en que TML hace visible el resultado. Sirve para recalibrar el calendario de
# TML con datos y validarlo FUERA DE MUESTRA (calibrar con 2022-2024, validar con 2025-2026) sin recargar la base.
OFFSETS = VALIDACION.split("SELECT tml.dias")[0] + """
SELECT tml.dias, tml.ronda, sf.inicio,
       EXTRACT(EPOCH FROM (sf.fin_real - tml.ed_ini)) / 86400.0 AS off_fin_real,
       EXTRACT(EPOCH FROM (sf.inicio - tml.ed_ini)) / 86400.0 AS off_inicio_real,
       EXTRACT(EPOCH FROM (tml.vis_res - tml.ed_ini)) / 86400.0 AS off_vis_tml
FROM tml JOIN sf ON sf.jugador_1 = tml.jugador_1 AND sf.jugador_2 = tml.jugador_2
 AND sf.ronda_sf = tml.ronda AND sf.inicio >= tml.ed_ini AND sf.inicio < tml.ed_fin
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("snapshot", type=Path)
    ap.add_argument("--salida", type=Path)
    a = ap.parse_args()
    dsn = os.environ.get("QF_TEST_PG_DSN") or os.environ.get("PG_DSN")
    snap = a.snapshot.resolve()
    raiz = snap.parents[1]
    esquema = f"tenis_s2b_{uuid.uuid4().hex[:8]}"
    trabajo = Path(os.environ.get("TEMP", ".")) / f"integ_{esquema}"
    trabajo.mkdir(parents=True, exist_ok=True)
    inf = {"esquema": esquema, "snapshot_tml": str(snap)}
    with psycopg.connect(dsn, autocommit=True) as admin:
        for m in MIGRACIONES:
            admin.execute(sql_de(m, esquema, esquema + "_op"))
    try:
        t = time.time()
        r = tml_cli.ejecutar(snap, dsn, esquema, raiz / "download_manifest.json", trabajo / "almacen_tml",
                             trabajo / "rechazos_tml.csv")
        inf["tml"] = {"seg": round(time.time() - t), "leidas": r["leidas"], "cuadra": r["cuadra"],
                      "cargado": r["contadores"]["cargado"], **{f"filas_{k}": v for k, v in r["despues"].items()}}
        nombres, _ = tml_cli.listar(snap)
        db = psycopg.connect(dsn, autocommit=True)
        db.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(esquema)))
        cur = db.cursor()
        edades = enlazar.edades_para_resolutor(cur, list(enlazar.filas_tml([snap / n for n in nombres])))
        equiv = cargar_equivalencias(RAIZ / "config" / "equivalencias.csv")

        def fabrica(conn):
            return ResolutorMultifuente(conn, equivalencias=equiv, edades=edades)

        t = time.time()
        s = sofascore_cli.ejecutar(INDICE, RAIZ_SOFA, dsn, esquema, trabajo / "almacen_sofa", trabajo / "rechazos_sofa.csv",
                                   fabrica_resolutor=fabrica)
        inf["sofascore"] = {"seg": round(time.time() - t), "leidas": s["leidas"], "cuadra": s["cuadra"],
                            "contadores": {k: v for k, v in sorted(s["contadores"].items()) if not k.startswith("aviso")}}
        inf["union_jugadores"] = enlazar.medir(cur, fuente="sofascore", referencia="tml")
        inf["union_jugadores"].pop("pares_detalle", None)
        inf["validacion_calendario_tml_vs_sofascore"] = [
            dict(zip(("dias", "ronda", "comparados", "fuga_resultado_antes_del_fin_real", "pareja_despues_del_inicio_real"), f))
            for f in cur.execute(VALIDACION).fetchall()]
        import csv
        filas_off = cur.execute(OFFSETS).fetchall()
        ruta_off = (a.salida.with_suffix(".offsets.csv") if a.salida else trabajo / "offsets.csv")
        with open(ruta_off, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["dias", "ronda", "inicio", "off_fin_real", "off_inicio_real", "off_vis_tml"])
            w.writerows(filas_off)
        inf["offsets_csv"] = str(ruta_off)
        # Segunda carga de SofaScore: 0 filas nuevas.
        antes = {t_: cur.execute(f"SELECT count(*) FROM {t_}").fetchone()[0]
                 for t_ in ("jugador", "jugador_alias", "partido", "resultado", "estadistica", "juego_pbp", "programa")}
        sofascore_cli.ejecutar(INDICE, RAIZ_SOFA, dsn, esquema, trabajo / "almacen_sofa", trabajo / "rechazos_sofa2.csv",
                               fabrica_resolutor=fabrica)
        despues = {t_: cur.execute(f"SELECT count(*) FROM {t_}").fetchone()[0] for t_ in antes}
        inf["segunda_carga_sofascore_filas_nuevas"] = {k: despues[k] - antes[k] for k in antes}
        inf["filas_finales"] = despues
        txt = json.dumps(inf, indent=1, ensure_ascii=False, default=str)
        print(txt)
        if a.salida:
            a.salida.write_text(txt, encoding="utf-8")
    finally:
        with psycopg.connect(dsn, autocommit=True) as admin:
            admin.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(esquema)))
            admin.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(esquema + "_op")))


if __name__ == "__main__":
    main()
