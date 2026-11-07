"""Carga, normaliza y enlaza cuotas de mercado (Tennis-Data y PropLine) con partidos del motor (Sprint 5, B.4, S5).

Lee:
  - data/tennis/tennis_data_manual_processed/odds_raw.parquet
  - data/tennis/rediseno_20261104/export_pit/partidos.parquet
  - data/tennis/rediseno_20261104/modelo_s3/predicciones_wf.parquet
  - .local/propline_shared_pilot_20261023 (si est disponible)

Genera:
  - data/tennis/rediseno_20261104/modelo_s5/precios_enlazados.parquet
  - data/tennis/rediseno_20261104/modelo_s5/cobertura_cruce.json
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from tenis.mercado.tennis_data_hist import cargar_tennis_data_raw, procesar_cuotas_partidos
from tenis.mercado.propline import cargar_ganadores_piloto
from tenis.mercado.enlace import construir_indice_cuotas, enlazar_partido_con_cuotas

DIR_DATOS_DEFECTO = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\rediseno_20261104")
DIR_MODELO_S3 = DIR_DATOS_DEFECTO / "modelo_s3"
DIR_MODELO_S5 = DIR_DATOS_DEFECTO / "modelo_s5"
DIR_EXPORT_PIT = DIR_DATOS_DEFECTO / "export_pit"
RUTA_ODDS_RAW = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\tennis_data_manual_processed\odds_raw.parquet")
RUTA_PROPLINE_PILOTO = Path(r"C:\Users\huye\Documents\apuesta proyec\.local\propline_shared_pilot_20261023")


def log(msg: str):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def obtener_mapa_jugadores(dir_datos: Path) -> dict[int, str]:
    """Carga el mapa jugador_id -> nombre desde cache o Postgres."""
    p_cache = dir_datos / "jugadores.parquet"
    if p_cache.exists():
        df = pd.read_parquet(p_cache)
        return dict(zip(df["jugador_id"], df["nombre"]))

    try:
        import psycopg
        dsn = os.environ.get("PG_DSN")
        if not dsn:
            return {}
        conn = psycopg.connect(dsn)
        cur = conn.cursor()
        cur.execute("SELECT jugador_id, valor FROM tenis_dev.jugador_asercion WHERE campo='nombre'")
        rows = cur.fetchall()
        conn.close()
        df = pd.DataFrame(rows, columns=["jugador_id", "nombre"]).drop_duplicates("jugador_id")
        df.to_parquet(p_cache, index=False)
        return dict(zip(df["jugador_id"], df["nombre"]))
    except Exception as e:
        log(f"Aviso: no se pudo consultar tenis_dev.jugador_asercion: {e}")
        return {}


def main():
    parser = argparse.ArgumentParser(description="Carga y enlaza precios de mercado con predicciones del motor")
    parser.add_argument("--datos_dir", type=Path, default=DIR_DATOS_DEFECTO)
    parser.add_argument("--odds_raw", type=Path, default=RUTA_ODDS_RAW)
    parser.add_argument("--salida_dir", type=Path, default=DIR_MODELO_S5)
    parser.add_argument("--desde", type=int, default=2019)
    parser.add_argument("--hasta", type=int, default=2026)
    args = parser.parse_args()

    args.salida_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    log("1. Cargando y procesando cuotas histricas de Tennis-Data...")
    raw_odds = cargar_tennis_data_raw(args.odds_raw, desde_anio=args.desde)
    cuotas_td = procesar_cuotas_partidos(raw_odds)
    log(f"   {len(cuotas_td)} partidos con cuotas procesadas desde {args.desde}")

    log("2. Construyendo ndice de cruce por parejas de jugadores...")
    idx_td = construir_indice_cuotas(cuotas_td)
    log(f"   {len(idx_td)} claves nicas indexadas")

    log("3. Cargando predicciones walk-forward y metadatos de partidos...")
    wf = pd.read_parquet(args.datos_dir / "modelo_s3/predicciones_wf.parquet")
    cols_part = [
        "partido_key", "circuito", "temporada", "categoria", "ronda",
        "jugador_1", "jugador_2", "fecha_partido", "fuente_tiempo",
        "y_estado", "y_ganador", "y_sets", "y_sets_completos", "y_juegos_1", "y_juegos_2"
    ]
    partidos = pd.read_parquet(args.datos_dir / "export_pit/partidos.parquet", columns=cols_part)
    mapa_jugadores = obtener_mapa_jugadores(args.datos_dir)
    log(f"   Mapa de jugadores con {len(mapa_jugadores)} entradas")

    # Unir WF con metadatos de partidos
    df = wf[["partido_key", "pi_lado1", "var_rho", "S_hat", "prior_ranking", "historia_corta", "fatiga_desconocida"]].merge(
        partidos, on="partido_key", how="inner"
    )
    df = df[(df.temporada >= args.desde) & (df.temporada <= args.hasta)].copy()
    log(f"   {len(df)} partidos pronosticados en el rango {args.desde}-{args.hasta}")

    log("4. Enlazando cuotas de mercado punto en el tiempo...")
    filas_enlace = []
    cruzados_conteo = 0

    for r in df.itertuples():
        n1 = mapa_jugadores.get(r.jugador_1)
        n2 = mapa_jugadores.get(r.jugador_2)
        fuente_t = getattr(r, "fuente_tiempo", "tml")

        cruce = enlazar_partido_con_cuotas(
            circuito=r.circuito,
            fecha_partido=r.fecha_partido,
            jugador_1_nombre=n1,
            jugador_2_nombre=n2,
            indice_cuotas=idx_td,
            fuente_tiempo=fuente_t,
        )

        if cruce is not None:
            cruzados_conteo += 1
            filas_enlace.append({
                "partido_key": r.partido_key,
                "cruzado_mercado": True,
                "ref_casa": cruce["ref_casa"],
                "clase_cierre": cruce["clase_cierre"],
                "p_cierre_lado1": cruce["p_cierre_lado1"],
                "p_cierre_lado2": cruce["p_cierre_lado2"],
                "margen_cierre": cruce["margen_cierre"],
                "dif_dias_mercado": cruce["dif_dias"],
                "mercado_fecha": cruce["mercado_fecha"],
                "torneo_mercado": cruce["torneo_mercado"],
            })
        else:
            filas_enlace.append({
                "partido_key": r.partido_key,
                "cruzado_mercado": False,
                "ref_casa": None,
                "clase_cierre": None,
                "p_cierre_lado1": None,
                "p_cierre_lado2": None,
                "margen_cierre": None,
                "dif_dias_mercado": None,
                "mercado_fecha": None,
                "torneo_mercado": None,
            })

    df_enlace = pd.DataFrame(filas_enlace)
    df_resultado = df.merge(df_enlace, on="partido_key", how="left")
    log(f"   Cruce completado: {cruzados_conteo} partidos enlazados de {len(df)} ({cruzados_conteo/len(df):.1%})")

    # Guardar precios enlazados
    ruta_salida = args.salida_dir / "precios_enlazados.parquet"
    df_resultado.to_parquet(ruta_salida, index=False)
    log(f"   Guardado: {ruta_salida} ({len(df_resultado)} filas)")

    # 5. Medicin de cobertura por circuito y temporada para ATP/WTA principal
    log("5. Midiendo cobertura de cruce (G-identidad) en ATP/WTA principal...")
    filtro_main = (
        df_resultado.categoria.isin([
            "GS", "M1000", "WTA1000", "500", "WTA500", "250", "WTA250", "Finales", "Premier", "International"
        ]) &
        (~df_resultado.ronda.isin(["Q1", "Q2", "Q3", "QL"])) &
        df_resultado.y_estado.isin(["completado", "retirada"])
    )
    df_main = df_resultado[filtro_main].copy()

    resumen_cobertura = {}
    for circ in ["atp", "wta"]:
        resumen_cobertura[circ] = {}
        for anio in range(args.desde, args.hasta + 1):
            sub = df_main[(df_main.circuito == circ) & (df_main.temporada == anio)]
            total = len(sub)
            cruz = int(sub.cruzado_mercado.sum())
            tasa = cruz / total if total > 0 else 0.0
            resumen_cobertura[circ][str(anio)] = {
                "partidos_cuadro_principal": total,
                "partidos_cruzados": cruz,
                "sin_cruce": total - cruz,
                "tasa_cruce": round(tasa, 4),
                "tasa_pct": round(tasa * 100, 2),
            }
            log(f"   {circ.upper()} {anio}: {cruz}/{total} ({tasa*100:.1f}%)")

    # Global
    for circ in ["atp", "wta"]:
        sub_tot = df_main[df_main.circuito == circ]
        tot = len(sub_tot)
        cr = int(sub_tot.cruzado_mercado.sum())
        resumen_cobertura[circ]["total"] = {
            "partidos_cuadro_principal": tot,
            "partidos_cruzados": cr,
            "sin_cruce": tot - cr,
            "tasa_cruce": round(cr / tot, 4) if tot > 0 else 0,
            "tasa_pct": round((cr / tot) * 100, 2) if tot > 0 else 0,
        }

    ruta_cobertura = args.salida_dir / "cobertura_cruce.json"
    with open(ruta_cobertura, "w", encoding="utf-8") as f:
        json.dump(resumen_cobertura, f, indent=2)
    log(f"   Resumen de cobertura guardado: {ruta_cobertura}")
    log(f"Fin cargar_precios en {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main()
