"""Inventario SOLO LECTURA de datos de tenis en el disco local (tarea 1.1 de la auditoria).

No escribe fuera de --out. No modifica ningun origen. Todas las cifras de los CSV
salen de los ficheros indicados en cada seccion.

Secciones (--seccion, por defecto todas):
  locales    censo de data/tennis (carpetas, ficheros, parquet, csv, sqlite)
  canonico   TML canonico (full_20261016/canonical/matches.parquet)
  identidad  ids de jugador: canonico crudo frente a identity_bridge_v3
  solapes    solape de partidos entre fuentes por (fecha +-1 dia, apellidos)

Uso (Python 3.12 del sistema; ver docs/tenis_auditoria_inventario_datos_20261104.md):
  python -I apps/tennis/ops/inventario_datos.py --data-root "C:/Users/huye/Documents/apuesta proyec/data/tennis" --out docs/tenis_auditoria_tablas
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq


def escribir(out: Path, nombre: str, filas: list[dict]):
    out.mkdir(parents=True, exist_ok=True)
    ruta = out / nombre
    if not filas:
        ruta.write_text("", encoding="utf-8")
        return ruta
    claves: list[str] = []
    for f in filas:
        for k in f:
            if k not in claves:
                claves.append(k)
    with ruta.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=claves)
        w.writeheader()
        w.writerows(filas)
    print(f"  escrito {nombre}: {len(filas)} filas")
    return ruta


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def norm(texto: str) -> str:
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z ]", " ", t.lower()).strip()


def apellido_tml(nombre: str) -> str:
    """Nombres TML/SofaScore/MCP: 'Novak Djokovic' -> 'djokovic' (ultimo token)."""
    partes = norm(nombre).split()
    return partes[-1] if partes else ""


def apellido_tennis_data(nombre: str) -> str:
    """Formato tennis-data.co.uk: 'Djokovic N.' -> 'djokovic' (primer token)."""
    partes = norm(nombre).split()
    return partes[0] if partes else ""


# ---------------------------------------------------------------- locales
def seccion_locales(data: Path, out: Path):
    print("[locales]")
    filas_carpetas = []
    for item in sorted(data.iterdir(), key=lambda p: p.name.lower()):
        if item.is_file():
            st = item.stat()
            filas_carpetas.append({"entrada": item.name, "tipo": "fichero", "ficheros": 1,
                                   "bytes": st.st_size, "mtime_min_utc": iso(st.st_mtime),
                                   "mtime_max_utc": iso(st.st_mtime), "extensiones_top": item.suffix})
            continue
        n = 0
        total = 0
        mmin, mmax = float("inf"), 0.0
        ext = Counter()
        for raiz, _dirs, nombres in os.walk(item):
            for nombre in nombres:
                p = Path(raiz) / nombre
                try:
                    st = p.stat()
                except OSError:
                    continue
                n += 1
                total += st.st_size
                mmin = min(mmin, st.st_mtime)
                mmax = max(mmax, st.st_mtime)
                ext[p.suffix.lower() or "(sin)"] += 1
        filas_carpetas.append({
            "entrada": item.name, "tipo": "carpeta", "ficheros": n, "bytes": total,
            "mtime_min_utc": iso(mmin) if n else "", "mtime_max_utc": iso(mmax) if n else "",
            "extensiones_top": ";".join(f"{k}={v}" for k, v in ext.most_common(6)),
        })
    escribir(out, "inventario_local_carpetas.csv", filas_carpetas)

    filas_parquet = []
    for p in sorted(data.rglob("*.parquet")):
        try:
            md = pq.ParquetFile(p).metadata
            filas_parquet.append({"ruta_relativa": str(p.relative_to(data)).replace("\\", "/"),
                                  "filas": md.num_rows, "columnas": md.num_columns,
                                  "bytes": p.stat().st_size})
        except Exception as exc:
            filas_parquet.append({"ruta_relativa": str(p.relative_to(data)).replace("\\", "/"),
                                  "filas": f"ERROR {type(exc).__name__}", "columnas": "", "bytes": p.stat().st_size})
    escribir(out, "inventario_local_parquet.csv", filas_parquet)

    filas_sqlite = []
    for p in sorted(data.rglob("*.sqlite")):
        try:
            c = sqlite3.connect(f"file:{p.as_posix()}?mode=ro", uri=True)
            for (tabla,) in c.execute("select name from sqlite_master where type='table' order by name").fetchall():
                n = c.execute(f'select count(*) from "{tabla}"').fetchone()[0]
                filas_sqlite.append({"ruta_relativa": str(p.relative_to(data)).replace("\\", "/"),
                                     "tabla": tabla, "filas": n})
            c.close()
        except Exception as exc:
            filas_sqlite.append({"ruta_relativa": str(p.relative_to(data)).replace("\\", "/"),
                                 "tabla": f"ERROR {type(exc).__name__}", "filas": ""})
    escribir(out, "inventario_local_sqlite.csv", filas_sqlite)

    filas_csv = []
    for p in sorted(data.rglob("*.csv")):
        n = 0
        with p.open("rb") as fh:
            for _ in fh:
                n += 1
        filas_csv.append({"ruta_relativa": str(p.relative_to(data)).replace("\\", "/"),
                          "lineas_incl_cabecera": n, "bytes": p.stat().st_size})
    escribir(out, "inventario_local_csv.csv", filas_csv)

    # Ficheros de originales (TML, MCP, tennis-data, API-Tennis) por fuente.
    filas_orig = []
    for nombre, patron in [
        ("TML originals csv", "full_20261016/tml/originals/*.csv"),
        ("TML originals atp_quali", "full_20261016/tml/originals/atp_quali/*.csv"),
        ("MCP originals csv", "full_20261016/mcp/originals/*.csv"),
        ("tennis-data xls/xlsx", "tennis_data_manual/*/*.xls*"),
        ("API-Tennis receipts/responses", "intake_v1/api_tennis/originals/*/response.json"),
        ("weekly tml originals csv", "weekly/*/tml/originals/*.csv"),
    ]:
        archivos = sorted(data.glob(patron))
        filas_orig.append({"fuente": nombre, "patron": patron, "ficheros": len(archivos),
                           "bytes": sum(a.stat().st_size for a in archivos)})
    escribir(out, "inventario_local_originales_por_fuente.csv", filas_orig)


# ---------------------------------------------------------------- canonico
def cargar_canonico(data: Path) -> pd.DataFrame:
    df = pd.read_parquet(data / "full_20261016" / "canonical" / "matches.parquet")
    df["ano"] = df["tourney_date"].astype(str).str[:4]
    return df


def seccion_canonico(data: Path, out: Path):
    print("[canonico]")
    df = cargar_canonico(data)
    base = {"fuente": "full_20261016/canonical/matches.parquet"}

    def tab(cols, nombre):
        g = df.groupby(cols, dropna=False).agg(
            partidos=("match_id", "size"),
            elegibles_modelo=("eligible_model", "sum"),
            completados=("completed_standard", "sum"),
            serve_counts_validos=("valid_serve_counts", "sum"),
        ).reset_index()
        filas = [{**base, **{k: ("" if pd.isna(v) else v) for k, v in r.items()}} for r in g.to_dict("records")]
        escribir(out, nombre, filas)

    tab(["circuit", "ano"], "canon_circuito_ano.csv")
    tab(["circuit", "tourney_level"], "canon_circuito_nivel.csv")
    tab(["circuit", "surface"], "canon_circuito_superficie.csv")
    tab(["circuit", "best_of"], "canon_circuito_mejor_de.csv")
    tab(["circuit", "source_group"], "canon_circuito_grupo_fuente.csv")
    tab(["circuit", "round"], "canon_circuito_ronda.csv")
    tab(["circuit", "ano", "source_group"], "canon_circuito_ano_grupo.csv")

    dobles = df["winner_name"].astype(str).str.contains("/") | df["loser_name"].astype(str).str.contains("/")
    print(f"  nombres con '/' (dobles probables): {int(dobles.sum())}")
    cal = [
        {"metrica": "filas_canonicas", "valor": len(df)},
        {"metrica": "match_id_duplicados", "valor": int(df["match_id"].duplicated().sum())},
        {"metrica": "partidos_con_fecha_hora_verificada", "valor": int((df["date_precision"].str.contains("match_time_verified")).sum())},
        {"metrica": "partidos_fecha_sin_hora (date_precision distinto de hora verificada)", "valor": int(len(df))},
        {"metrica": "received_at_min", "valor": df["received_at"].min()},
        {"metrica": "received_at_max", "valor": df["received_at"].max()},
        {"metrica": "received_at_distintos", "valor": int(df["received_at"].nunique())},
        {"metrica": "tourney_date_min", "valor": df["tourney_date"].min()},
        {"metrica": "tourney_date_max", "valor": df["tourney_date"].max()},
        {"metrica": "nombres_con_barra_(dobles_probables)", "valor": int(dobles.sum())},
        {"metrica": "minutes_nulos", "valor": int(df["minutes"].isna().sum())},
        {"metrica": "w_svpt_nulos", "valor": int(df["w_svpt"].isna().sum())},
        {"metrica": "eligible_model_true", "valor": int(df["eligible_model"].sum())},
        {"metrica": "completed_standard_false", "valor": int((~df["completed_standard"]).sum())},
    ]
    escribir(out, "canon_calidad.csv", cal)

    q = json.loads((data / "full_20261016" / "canonical" / "quarantine.json").read_text(encoding="utf-8"))
    cov = json.loads((data / "full_20261016" / "canonical" / "coverage.json").read_text(encoding="utf-8"))
    print("  quarantine keys:", list(q.keys())[:10] if isinstance(q, dict) else type(q))
    filas_q = []
    if isinstance(q, dict):
        for k, v in q.items():
            filas_q.append({"clave": k, "valor": v if not isinstance(v, (list, dict)) else f"{type(v).__name__}[{len(v)}]"})
    escribir(out, "canon_cuarentena_resumen.csv", filas_q)
    print("  coverage.json as_of:", cov.get("as_of"), "canonical_matches:", cov.get("canonical_matches"))


# ---------------------------------------------------------------- identidad
def seccion_identidad(data: Path, out: Path):
    print("[identidad]")
    raw = cargar_canonico(data)
    br = pd.read_parquet(data / "identity_bridge_v3_20261019" / "canonical" / "matches.parquet")
    br["ano"] = br["tourney_date"].astype(str).str[:4]

    def alt_mask(d, circuito):
        """Criterio de id alterno solo para WTA (ids wta:3xxxxx, auditoria 19-oct).
        ATP: sin criterio fiable por prefijo (ids TML normales tienen forma letra+digitos)."""
        if circuito != "WTA":
            return None
        return d.winner_id.astype(str).str.match(r"^wta:3\d+$") | d.loser_id.astype(str).str.match(r"^wta:3\d+$")

    filas = []
    for circuito in ["ATP", "WTA"]:
        for ano in sorted(raw["ano"].unique())[-5:]:
            r = raw[(raw.circuit == circuito) & (raw.ano == ano)]
            b = br[(br.circuit == circuito) & (br.ano == ano)]
            if len(r) == 0:
                continue
            mr = alt_mask(r, circuito)
            mb = alt_mask(b, circuito)
            filas.append({
                "circuito": circuito, "ano": ano,
                "partidos_crudo": len(r),
                "partidos_con_id_alterno_wta3xxxxx_crudo": int(mr.sum()) if mr is not None else "NO MEDIDO (sin criterio)",
                "partidos_puente_v3": len(b),
                "partidos_con_id_alterno_wta3xxxxx_puente_v3": int(mb.sum()) if mb is not None else "NO MEDIDO (sin criterio)",
                "partidos_elegibles_crudo": int(r.eligible_model.sum()),
                "partidos_elegibles_puente_v3": int(b.eligible_model.sum()),
            })
    escribir(out, "identidad_ids_alternos_por_ano.csv", filas)

    # Semana 2026-06-08 (Queen's / 's-Hertogenbosch) citada en la auditoria del 19-oct.
    semana = raw[(raw.circuit == "WTA") & (raw.tourney_date.astype(str) == "20260608")]
    sem_b = br[(br.circuit == "WTA") & (br.tourney_date.astype(str) == "20260608")]
    escribir(out, "identidad_semana_2026_06_08_wta.csv", [
        {"fuente": "crudo", "partidos": len(semana),
         "con_id_alterno": int(alt_mask(semana, "WTA").sum()),
         "torneos": ";".join(sorted(semana.tourney_id.astype(str).unique()))},
        {"fuente": "puente_v3", "partidos": len(sem_b),
         "con_id_alterno": int(alt_mask(sem_b, "WTA").sum()),
         "torneos": ";".join(sorted(sem_b.tourney_id.astype(str).unique()))},
    ])

    # Mismo nombre normalizado con varios ids (crudo) y mismo id con varios nombres.
    nombres = pd.concat([
        raw[["circuit", "winner_id", "winner_name"]].rename(columns={"winner_id": "id", "winner_name": "nombre"}),
        raw[["circuit", "loser_id", "loser_name"]].rename(columns={"loser_id": "id", "loser_name": "nombre"}),
    ]).dropna()
    nombres["nombre_norm"] = nombres["nombre"].map(norm)
    por_nombre = nombres.groupby(["circuit", "nombre_norm"])["id"].nunique()
    varios_ids = por_nombre[por_nombre > 1].reset_index()
    varios_ids.columns = ["circuito", "nombre_normalizado", "ids_distintos"]
    varios_ids = varios_ids.sort_values("ids_distintos", ascending=False)
    escribir(out, "identidad_nombre_con_varios_ids_crudo.csv", varios_ids.head(500).to_dict("records"))
    por_id = nombres.groupby(["circuit", "id"])["nombre_norm"].nunique()
    print(f"  nombres normalizados con >1 id (crudo): {len(varios_ids)} "
          f"| ids con >1 nombre normalizado: {int((por_id > 1).sum())}")

    rep = json.loads((data / "identity_bridge_v3_20261019" / "canonical" / "identity_report.json").read_text(encoding="utf-8")) \
        if (data / "identity_bridge_v3_20261019" / "canonical" / "identity_report.json").exists() else {}
    if not rep:
        rep = json.loads((data / "identity_bridge_v3_20261019" / "identity_report.json").read_text(encoding="utf-8"))
    ab = json.loads((data / "identity_bridge_20261019" / "alias_report.json").read_text(encoding="utf-8"))
    alias_map = ab.get("alias_map", {})
    alias_2026 = [v for v in alias_map.values() if str(v.get("alias_last", "")).startswith("2026")]
    resumen = [
        {"metrica": "puente_v2_aliases_fusionados", "valor": ab.get("aliases_merged")},
        {"metrica": "puente_v2_filas_reescritas", "valor": ab.get("rows_rewritten")},
        {"metrica": "puente_v2_todavia_ambiguos", "valor": ab.get("still_ambiguous")},
        {"metrica": "puente_v2_alias_entradas_en_mapa", "valor": len(alias_map)},
        {"metrica": "puente_v2_alias_con_ultima_fecha_2026", "valor": len(alias_2026)},
        {"metrica": "puente_v2_filas_alias_con_ultima_fecha_2026", "valor": sum(int(v.get("alias_rows", 0)) for v in alias_2026)},
        {"metrica": "puente_v3_fusionados_por_fecha_nacimiento", "valor": len(rep.get("merged", []))},
        {"metrica": "puente_v3_confirmados_distintos", "valor": len(rep.get("confirmed_distinct", []))},
    ]
    escribir(out, "identidad_puente_resumen.csv", resumen)

    # Partidos WTA 2026 con id alterno que siguen sin fusionar en el puente v3.
    wta26 = br[(br.circuit == "WTA") & (br.ano == "2026")]
    m = alt_mask(wta26, "WTA")
    sin_fusion = wta26[m][["tourney_id", "tourney_date", "winner_id", "winner_name", "loser_id", "loser_name"]]
    escribir(out, "identidad_wta2026_alterno_sin_fusionar.csv", sin_fusion.head(300).to_dict("records"))
    print(f"  WTA 2026 en puente v3: {len(wta26)} | con id alterno sin fusionar: {int(m.sum())}")


# ---------------------------------------------------------------- solapes
def cargar_api_tennis(states: Path) -> pd.DataFrame:
    """Observaciones API-Tennis (copia local de states.sqlite del VPS, solo lectura)."""
    c = sqlite3.connect(f"file:{states.as_posix()}?mode=ro", uri=True)
    filas = []
    for event_id, payload in c.execute("select event_id, payload from observations group by event_id"):
        p = json.loads(payload)
        tipo = str(p.get("event_type_type") or "").lower()
        circ = "atp" if tipo.startswith("atp") else "wta" if tipo.startswith("wta") else "otro:" + tipo
        filas.append({"fecha": pd.to_datetime(p.get("event_date"), errors="coerce"), "circuito": circ,
                      "a": apellido_tml(p.get("event_first_player")),
                      "b": apellido_tml(p.get("event_second_player")),
                      "estado": p.get("event_status")})
    c.close()
    return pd.DataFrame(filas)


def cargar_fuentes(data: Path, sofa_csv: Path, api_states: Path | None = None):
    fuentes = {}
    raw = cargar_canonico(data)
    fuentes["TML canonico"] = pd.DataFrame({
        "fecha": pd.to_datetime(raw["tourney_date"].astype(str), format="%Y%m%d", errors="coerce"),
        "circuito": raw["circuit"].str.lower(),
        "a": raw["winner_name"].map(apellido_tml), "b": raw["loser_name"].map(apellido_tml),
    })
    sof = pd.read_csv(sofa_csv, dtype=str)
    sof = sof[sof.estado == "finished"]
    fuentes["SofaScore local"] = pd.DataFrame({
        "fecha": pd.to_datetime(sof["fecha_utc"].str[:10], errors="coerce"),
        "circuito": sof["circuito_categoria"],
        "a": sof["jugador_local"].map(apellido_tml), "b": sof["jugador_visitante"].map(apellido_tml),
    })
    mcp = pd.read_csv(data / "full_20261016" / "mcp" / "originals" / "charting-m-matches.csv", dtype=str)
    mcp_w = pd.read_csv(data / "full_20261016" / "mcp" / "originals" / "charting-w-matches.csv", dtype=str)
    mm = pd.concat([mcp.assign(circuito="atp"), mcp_w.assign(circuito="wta")])
    fuentes["Match Charting Project"] = pd.DataFrame({
        "fecha": pd.to_datetime(mm["Date"], format="%Y%m%d", errors="coerce"),
        "circuito": mm["circuito"],
        "a": mm["Player 1"].map(apellido_tml), "b": mm["Player 2"].map(apellido_tml),
    })
    return fuentes


def seccion_solapes(data: Path, out: Path, sofa_csv: Path, api_states: Path | None):
    print("[solapes]")
    fuentes = cargar_fuentes(data, sofa_csv)
    if api_states and api_states.exists():
        fuentes["API-Tennis (states.sqlite VPS, copia local)"] = cargar_api_tennis(api_states)
    # tennis-data.co.uk (cuotas y resultados manuales): solo para el solape de partidos
    tdm = []
    for p in sorted((data / "tennis_data_manual").glob("*/*.xls*")):
        circ = p.parent.name.lower()
        try:
            d = pd.read_excel(p, usecols=["Date", "Winner", "Loser"])
        except Exception:
            continue
        tdm.append(pd.DataFrame({"fecha": pd.to_datetime(d["Date"], errors="coerce", dayfirst=True),
                                 "circuito": circ,
                                 "a": d["Winner"].map(apellido_tennis_data),
                                 "b": d["Loser"].map(apellido_tennis_data)}))
    if tdm:
        fuentes["tennis-data.co.uk (manual)"] = pd.concat(tdm, ignore_index=True)

    # Partidos reducidos a clave (circuito, fecha, par de apellidos).
    claves = {}
    filas_fuente = []
    for nombre, d in fuentes.items():
        d = d.dropna(subset=["fecha"]).copy()
        d["par"] = d.apply(lambda r: "|".join(sorted([str(r["a"]), str(r["b"])])), axis=1)
        d = d[d["par"].str.len() > 3]
        claves[nombre] = d
        filas_fuente.append({"fuente": nombre, "partidos_con_fecha": len(d),
                             "fecha_min": str(d["fecha"].min().date()), "fecha_max": str(d["fecha"].max().date()),
                             "circuitos": ";".join(sorted(d["circuito"].dropna().unique()))})
    escribir(out, "solapes_fuentes_resumen.csv", filas_fuente)

    # TML guarda tourney_date (inicio de semana del torneo), no la hora del partido:
    # para pares con TML se acepta el partido 0..14 dias despues de esa fecha.
    # Para el resto (fecha del partido) se acepta +-1 dia por husos horarios.
    filas = []
    nombres = list(claves)
    for i, a in enumerate(nombres):
        for b in nombres[i + 1:]:
            da = claves[a].reset_index(drop=True).assign(idx=lambda x: x.index)
            db = claves[b].reset_index(drop=True).assign(idx=lambda x: x.index)
            m = da.merge(db, on=["par", "circuito"], suffixes=("_a", "_b"))
            if m.empty:
                filas.append({"fuente_a": a, "fuente_b": b, "partidos_unicos_a_con_pareja": 0,
                              "partidos_unicos_b_con_pareja": 0, "pares_fila_a_fila_b": 0,
                              "regla_fecha": "", "nota": "sin coincidencias de apellidos"})
                continue
            m["dif"] = (m["fecha_b"] - m["fecha_a"]).dt.days
            if "TML canonico" in (a, b):
                regla = "TML: partido 0..14 dias tras tourney_date"
                ok = m[(m["dif"] >= 0) & (m["dif"] <= 14)] if a == "TML canonico" else m[(m["dif"] <= 0) & (m["dif"] >= -14)]
            else:
                regla = "fecha de partido +-1 dia"
                ok = m[m["dif"].abs() <= 1]
            filas.append({
                "fuente_a": a, "fuente_b": b,
                "partidos_unicos_a_con_pareja": int(ok["idx_a"].nunique()),
                "partidos_unicos_b_con_pareja": int(ok["idx_b"].nunique()),
                "pares_fila_a_fila_b": len(ok),
                "partidos_a_total": len(claves[a]), "partidos_b_total": len(claves[b]),
                "regla_fecha": regla,
                "nota": "aproximado: apellido final (TML/SofaScore/MCP) o primer token (tennis-data); "
                        "homonimos posibles; no es clave de identidad; pares de fila pueden repetirse",
            })
    escribir(out, "solapes_pares_fuentes.csv", filas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--sofascore-csv", type=Path, default=None)
    ap.add_argument("--api-tennis-states", type=Path, default=None)
    ap.add_argument("--seccion", action="append", choices=["locales", "canonico", "identidad", "solapes"])
    args = ap.parse_args()
    secciones = args.seccion or ["locales", "canonico", "identidad", "solapes"]
    sofa = args.sofascore_csv or (args.out / "sofascore_local_tenis_eventos.csv")
    if "locales" in secciones:
        seccion_locales(args.data_root, args.out)
    if "canonico" in secciones:
        seccion_canonico(args.data_root, args.out)
    if "identidad" in secciones:
        seccion_identidad(args.data_root, args.out)
    if "solapes" in secciones:
        seccion_solapes(args.data_root, args.out, sofa, args.api_tennis_states)


if __name__ == "__main__":
    main()
