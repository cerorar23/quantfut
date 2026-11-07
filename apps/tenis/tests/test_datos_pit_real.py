"""Exportación PIT sobre DATOS REALES en un esquema aislado: TML 2024 (ATP y WTA, cargador real) + SofaScore de
enero-febrero de 2024 (cargador real con el resolutor multifuente). Prueba de propiedad contra la puerta oficial en 300
partidos al azar (semilla fija), fuga y determinismo. Se omite sin los ficheros locales o sin QF_TEST_PG_DSN."""
import csv
import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd
import psycopg
import pytest
from psycopg import sql

from db_util import MIGRACIONES, sql_de
from tenis.carga import sofascore_cli, tml_cli
from tenis.carga.sofascore_carga import leer_indice
from tenis.datos import equivalencia, exportar_pit
from tenis.identidad import enlazar
from tenis.identidad.resolver import ResolutorMultifuente

DATOS = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\rediseno_20261104")
TML = DATOS / "tml_vps_20261102" / "tml" / "originals"
MANIFIESTO = DATOS / "tml_vps_20261102" / "download_manifest.json"
INDICE = DATOS / "tablas" / "sofascore_local_tenis_eventos.csv"
RAIZ_SOFA = Path(r"C:\Users\huye\Documents\SOFASCORE\data\v3")
FICHEROS = ["2024.csv", "2024_wta.csv"]
DESDE, HASTA = "2024-01-01", "2024-03-01"
N = 300
SEMILLA = 20261105


@pytest.fixture(scope="module")
def real(tmp_path_factory):
    dsn = os.environ.get("QF_TEST_PG_DSN")
    if not dsn:
        pytest.skip("QF_TEST_PG_DSN ausente")
    if not all((TML / f).exists() for f in FICHEROS) or not INDICE.exists() or not RAIZ_SOFA.exists():
        pytest.skip("datos reales locales no disponibles")
    base = tmp_path_factory.mktemp("pit_real")
    snap = base / "snap"
    snap.mkdir()
    for f in FICHEROS:
        shutil.copyfile(TML / f, snap / f)
    esquema = f"tenis_t_{uuid.uuid4().hex[:10]}"
    with psycopg.connect(dsn, autocommit=True) as admin:
        for m in MIGRACIONES:
            admin.execute(sql_de(m, esquema, esquema + "_op"))
    try:
        r = tml_cli.ejecutar(snap, dsn, esquema, MANIFIESTO, base / "alm_tml", base / "rech_tml.csv")
        assert r["cuadra"]
        with psycopg.connect(dsn, autocommit=True) as db:
            db.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(esquema)))
            edades = enlazar.edades_para_resolutor(db.cursor(), list(enlazar.filas_tml([snap / f for f in FICHEROS])))
        with open(INDICE, encoding="utf-8", newline="") as f:
            ids = {int(x["event_id"]) for x in csv.DictReader(f) if DESDE <= x["fecha_utc"][:10] < HASTA}
        entradas = [e for e in leer_indice(INDICE) if e.evento_id in ids]
        s = sofascore_cli.ejecutar(INDICE, RAIZ_SOFA, dsn, esquema, base / "alm_sofa", base / "rech_sofa.csv",
                                   entradas=entradas,
                                   fabrica_resolutor=lambda conn: ResolutorMultifuente(conn, edades=edades))
        assert s["cuadra"] and s["contadores"]["cargado"] > 500
        man = exportar_pit.exportar(dsn, esquema, base / "exp")
        yield {"dsn": dsn, "esquema": esquema, "dir": base / "exp", "man": man, "base": base}
    finally:
        with psycopg.connect(dsn, autocommit=True) as admin:
            admin.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(esquema)))
            admin.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(esquema + "_op")))


def test_fusion_y_recuentos_reales(real):
    cal = json.loads((real["dir"] / "calidad.json").read_text(encoding="utf-8"))
    p = pd.read_parquet(real["dir"] / "partidos.parquet")
    assert cal["fusion"]["fusionados"] > 300            # TML y SofaScore comparten enero-febrero de 2024
    assert p["partido_key"].is_unique
    # Cada fila de la base aparece en una sola fila del mundo real.
    assert p["partido_id_tml"].dropna().is_unique and p["partido_id_sofascore"].dropna().is_unique
    # El orden de lados no revela el resultado: con ids de la base el menor gana más (orden de carga); en la
    # exportación el lado 1 gana ~50 % (binomial: |p − 0,5| < 4σ).
    g = p["y_ganador"].dropna()
    assert abs((g == 1).mean() - 0.5) < 4 * (0.25 / len(g)) ** 0.5
    assert cal["contadores"]["orden_lados:p_gana_id_menor"] > 0.5
    ev = pd.read_parquet(real["dir"] / "eventos_resultado.parquet")
    v = ev.merge(p[["partido_key", "jugador_1", "y_ganador", "y_juegos_1"]], on="partido_key")
    assert (v["jugador_1_x"] == v["jugador_1_y"]).all()
    assert (v["ganador"].fillna(0) == v["y_ganador"].fillna(0)).all()
    assert (v["juegos_1"].fillna(-1) == v["y_juegos_1"].fillna(-1)).all()
    assert set(p["superficie"].dropna()) <= {"Clay", "Grass", "Hard", "Indoor"}
    # Un partido fusionado usa los tiempos de SofaScore, nunca el calendario de TML.
    fus = p[p["fusion_metodo"].notna()]
    assert (fus["fuente_tiempo"] == "sofascore").all()
    assert ((fus["inicio_utc"] - fus["corte_utc"]) == pd.Timedelta(minutes=60)).all()


def test_equivalencia_con_la_puerta_oficial_real(real):
    res = equivalencia.verificar(real["dsn"], real["esquema"], real["dir"], n=N, semilla=SEMILLA, hilos=4)
    (real["base"] / "equivalencia.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    assert res["partidos_muestra"] == N
    assert res["identico"], json.dumps(res, default=str)[:3000]
    assert res["filas_comparadas"]["resultado"] > 0 and res["filas_comparadas"]["eventos"] > 0


def test_sin_fuga_en_ningun_partido_real(real):
    p = pd.read_parquet(real["dir"] / "partidos.parquet")
    ev = pd.read_parquet(real["dir"] / "eventos_resultado.parquet")
    ok = p[p["corte_utc"].notna() & p["excluir_motivo"].isna()]
    v = ok.merge(ev[["partido_key", "visible_resultado_utc"]], on="partido_key", suffixes=("", "_ev"))
    assert (v["visible_resultado_utc_ev"] >= v["corte_utc"]).all()        # el propio resultado nunca es visible
    hora = p[p["fuente_tiempo"] == "sofascore"]
    assert (hora["visible_resultado_utc"] > hora["inicio_utc"] - pd.Timedelta(minutes=60)).all()
    rk = pd.read_parquet(real["dir"] / "ranking_asof.parquet").dropna(subset=["ranking_id"])
    assert (rk["visible_desde"] < rk["corte_utc"]).all()
    assert (rk["fecha_publicacion"] <= rk["fecha_partido"]).all()
    es = pd.read_parquet(real["dir"] / "estadisticas_saque.parquet")
    assert (es["puntos_saque"].dropna() > 0).all()
    e2 = es.merge(ev[["partido_key", "visible_resultado_utc", "estado"]], on="partido_key")
    assert (e2["visible_desde"] >= e2["visible_resultado_utc"]).all() and (e2["estado"] == "completado").all()


def test_determinismo_real(real):
    otro = exportar_pit.exportar(real["dsn"], real["esquema"], real["base"] / "exp2")
    assert otro["sha256_export"] == real["man"]["sha256_export"]
    for k, v in otro["ficheros"].items():
        assert v["sha256_contenido"] == real["man"]["ficheros"][k]["sha256_contenido"], k
