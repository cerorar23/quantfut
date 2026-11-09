"""
Backtest de TODOS los mercados de fútbol que se publican (9-nov-2026), por liga y por familia.

    ejecutar.sh .local/entreno_AAAAMMDD qf.eval.backtest_mercados correr \
        --oos .local/backtest_ligas_nuevas/pit_oos.csv --salida .local/backtest_mercados

Familias (las que muestra la API en `partido_mercados`):
  goles     1X2, doble oportunidad, ambos marcan, más/menos total y por equipo, hándicap asiático, marcador exacto,
            margen de victoria, goles esperados y «gana a cero» (local y visitante; es el mercado «Especiales» de la ficha). Salen de las lambdas del Dixon-Coles del backtest `pit`
            (`backtest_ligas_nuevas`), crudas como en producción (el calibrador rechazó su puerta).
  1t        gol en 1T, ambos anotan en 1T, más de 1,5 en 1T y ganador del 1T (`model/primer_tiempo`).
  corners   total, local y visitante por líneas (`model/estadisticas_mercado`).
  tarjetas  total (amarillas + rojas) con árbitro, como en producción.
Córners y tarjetas se reproducen como producción: UN acumulador por liga y estadística, partidos de la propia
competición en orden cronológico, y cada partido se predice ANTES de entrar al acumulador. No hay props de jugador de
fútbol publicados, así que no se miden.

Tramo medido: desde 2025-07-01 (los parámetros de córners, tarjetas y 1T salieron de datos de 2019-2022; los del
Dixon-Coles, de datos hasta 2025-06). Es el mismo tramo limpio del backtest 1X2.

CRITERIO DE PUBLICACIÓN EN ALTA PROBABILIDAD (fijado el 9-nov-2026 antes de ejecutar; no se mueve después):
  Se mira el lado de cada mercado cuya probabilidad es >= 0,75 (un «más de» con p <= 0,25 es un «menos de» con p >= 0,75).
  A1  Una familia solo se muestra como alta probabilidad en un grupo de ligas si tiene n_alta >= 100 y la promesa se
      cumple: probabilidad media predicha - frecuencia real <= 0,03.
  A2  Un mercado concreto con n_alta >= 30 y promesa incumplida en más de 0,05 queda FUERA de la alta probabilidad
      de esa familia aunque la familia pase.
  A3  La decisión es por grupo: «aprobadas» (Turquía, LaLiga 2, Serie B, Allsvenskan, las 4 con modelo) y por liga como
      contexto. Con n_alta < 30 en una liga no se concluye nada de esa liga.
Lo que no alcanza n_alta >= 100 se informa como «sin muestra suficiente», no como aprobado.
No es objetivo ganar al mercado; se mide la calibración y si la cifra prometida se cumple.

LECTURA ESTRICTA (POSTERIOR: se añadió después de ver que A1 aprobaba todo; NO estaba fijada de antemano y se informa aparte):
  A1 cuenta líneas, no partidos: un partido aporta decenas de líneas correlacionadas y el total lo dominan líneas
  triviales (p. ej. «menos de 5,5 goles»). La lectura estricta separa por franja de probabilidad (0,75-0,80, 0,80-0,85,
  0,85-0,90, >= 0,90; con cuota mínima 1,28 los picks reales caen en las dos primeras) y calcula el intervalo al 95 %
  de «promesa − realidad» remuestreando PARTIDOS completos. Una franja «cumple» si el límite superior de ese intervalo es
  <= 0,05; si el inferior es > 0,02 «sobrepromete».
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger("backtest_mercados")

INICIO = "2025-07-01"
HISTORIA_DESDE = "2021-07-01"   # 4 años antes del inicio, como la ventana de `escalera_datos.Modelos`
UMBRAL_ALTA = 0.75
CRITERIOS = {"n_alta_min": 100, "promesa_max": 0.03, "mercado_n_min": 30, "mercado_promesa_max": 0.05}
APROBADAS = ("tr.super_lig", "es.laliga2", "it.serie_b", "se.allsvenskan")
NUEVAS = APROBADAS + ("ch.super_league", "no.eliteserien", "gb.championship", "de.bundesliga2")
FAMILIAS = ("goles", "1t", "corners", "tarjetas")


# ------------------------------------------------------------------------------------------- utilidades

def wilson_inferior(aciertos: int, n: int, z: float = 1.96) -> float:
    """Límite inferior del intervalo de Wilson al 95 % de una proporción."""
    if n == 0:
        return float("nan")
    p = aciertos / n
    d = 1 + z * z / n
    centro = p + z * z / (2 * n)
    mar = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return float((centro - mar) / d)


def lados(tabla: pd.DataFrame, excluyentes: set[str]) -> pd.DataFrame:
    """Cada fila con probabilidad es un lado; en los mercados binarios se añade además su complemento."""
    t = tabla.dropna(subset=["prob", "resultado"])
    base = t[["liga", "evento", "mercado", "prob", "resultado"]].assign(lado="directo")
    binarios = base[~base["mercado"].isin(excluyentes)]
    compl = binarios.assign(prob=1.0 - binarios["prob"], resultado=1.0 - binarios["resultado"], lado="complemento")
    return pd.concat([base, compl], ignore_index=True)


def alta_probabilidad(tabla: pd.DataFrame, excluyentes: set[str], umbral: float = UMBRAL_ALTA) -> dict:
    """Promesa frente a realidad de los lados con probabilidad >= umbral, total y por mercado."""
    s = lados(tabla, excluyentes)
    a = s[s["prob"] >= umbral]
    out = {"n_alta": int(len(a))}
    if a.empty:
        return {**out, "predicha": None, "real": None, "promesa": None, "real_ic_inf": None, "mercados": []}
    n, hits = len(a), int(a["resultado"].sum())
    out.update(predicha=float(a["prob"].mean()), real=hits / n, promesa=float(a["prob"].mean() - hits / n),
               real_ic_inf=wilson_inferior(hits, n))
    por = []
    for (mercado, lado), g in a.groupby(["mercado", "lado"]):
        h = int(g["resultado"].sum())
        por.append({"mercado": mercado, "lado": lado, "n": len(g), "predicha": float(g["prob"].mean()),
                    "real": h / len(g), "promesa": float(g["prob"].mean() - h / len(g))})
    out["mercados"] = sorted(por, key=lambda r: -r["n"])
    return out


BANDAS = ((0.75, 0.80), (0.80, 0.85), (0.85, 0.90), (0.90, 1.0001))


def bandas(tabla: pd.DataFrame, excluyentes: set[str], n_boot: int = 1000, seed: int = 7) -> list[dict]:
    """Promesa frente a realidad por franja de probabilidad, con IC95 remuestreando partidos completos."""
    s = lados(tabla, excluyentes)
    s = s[s["prob"] >= UMBRAL_ALTA]
    rng = np.random.default_rng(seed)
    out = []
    for lo, hi in BANDAS:
        a = s[(s["prob"] >= lo) & (s["prob"] < hi)]
        fila = {"banda": f"{lo:.2f}-{min(hi, 1.0):.2f}", "lineas": int(len(a)), "partidos": 0, "predicha": None,
                "real": None, "promesa": None, "ic_inf": None, "ic_sup": None, "estado": "SIN_MUESTRA"}
        if len(a):
            ev = a.groupby("evento").agg(n=("prob", "size"), sp=("prob", "sum"), sr=("resultado", "sum"))
            n, sp, sr = ev["n"].to_numpy(float), ev["sp"].to_numpy(float), ev["sr"].to_numpy(float)
            gap = (sp.sum() - sr.sum()) / n.sum()
            idx = rng.integers(0, len(ev), size=(n_boot, len(ev)))
            g = (sp[idx].sum(axis=1) - sr[idx].sum(axis=1)) / n[idx].sum(axis=1)
            lo_ic, hi_ic = np.percentile(g, [2.5, 97.5])
            fila.update(partidos=int(len(ev)), predicha=float(sp.sum() / n.sum()), real=float(sr.sum() / n.sum()),
                        promesa=float(gap), ic_inf=float(lo_ic), ic_sup=float(hi_ic))
            if len(ev) >= CRITERIOS["n_alta_min"]:
                fila["estado"] = ("SOBREPROMETE" if lo_ic > 0.02 else "CUMPLE" if hi_ic <= 0.05 else "INCIERTO")
        out.append(fila)
    return out


def veredicto_familia(alta: dict) -> str:
    if alta["n_alta"] < CRITERIOS["n_alta_min"]:
        return "SIN_MUESTRA"
    return "APRUEBA" if alta["promesa"] <= CRITERIOS["promesa_max"] else "NO_APRUEBA"


def mercados_fuera(alta: dict) -> list[str]:
    """A2: mercados con muestra y promesa incumplida en más de 0,05."""
    return [f"{m['mercado']}|{m['lado']}" for m in alta.get("mercados", [])
            if m["n"] >= CRITERIOS["mercado_n_min"] and m["promesa"] > CRITERIOS["mercado_promesa_max"]]


# ------------------------------------------------------------------------------------------- tablas por familia

def _evaluar(tabla: pd.DataFrame, excluyentes: set[str]) -> pd.DataFrame:
    from .evaluador import ModelEvaluator
    return ModelEvaluator(tabla.drop(columns=["liga"], errors="ignore"), mercados_excluyentes=excluyentes).evaluar()


def gana_a_cero(oos: pd.DataFrame) -> pd.DataFrame:
    """«Gana a cero»: gana el equipo y el rival no marca. P sale de la matriz de marcadores del partido (lam, mu, rho)."""
    from ..model.calibration import score_matrices
    filas = []
    for rho, g in oos.groupby(oos["rho"].round(6)):
        m = score_matrices(g["lam"].to_numpy(), g["mu"].to_numpy(), float(rho), 10)
        p_loc, p_vis = m[:, 1:, 0].sum(axis=1), m[:, 0, 1:].sum(axis=1)
        hg, ag = g["home_goals"].to_numpy(int), g["away_goals"].to_numpy(int)
        for ev, pl, pv, h, a in zip(g["match_id"], p_loc, p_vis, hg, ag):
            filas.append({"evento": ev, "mercado": "gana_a_cero_local", "seleccion": "si", "prob": float(pl),
                          "resultado": float(h > 0 and a == 0), "esperado": np.nan, "real": np.nan})
            filas.append({"evento": ev, "mercado": "gana_a_cero_visitante", "seleccion": "si", "prob": float(pv),
                          "resultado": float(a > 0 and h == 0), "esperado": np.nan, "real": np.nan})
    return pd.DataFrame(filas, columns=["evento", "mercado", "seleccion", "prob", "resultado", "esperado", "real"])


def tablas_goles_y_1t(oos: pd.DataFrame, ht: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    from .evaluacion_goles import tabla_goles
    from .evaluacion_primer_tiempo import tabla_primer_tiempo
    g, t1 = [], []
    for liga, o in oos.groupby("league_id"):
        p = o.rename(columns={"match_id": "evento", "home_goals": "goles_local", "away_goals": "goles_visitante"})[
            ["evento", "lam", "mu", "rho", "goles_local", "goles_visitante"]]
        g.append(pd.concat([tabla_goles(p), gana_a_cero(o)], ignore_index=True).assign(liga=liga))
        q = p.merge(ht, left_on="evento", right_on="match_id", how="left").rename(
            columns={"home_goals_ht": "goles_1t_local", "away_goals_ht": "goles_1t_visitante"})
        t1.append(tabla_primer_tiempo(q[["evento", "lam", "mu", "goles_1t_local", "goles_1t_visitante"]]).assign(liga=liga))
    return pd.concat(g, ignore_index=True), pd.concat(t1, ignore_index=True)


def tablas_estadisticas(partidos: pd.DataFrame, desde: str = INICIO) -> dict[str, pd.DataFrame]:
    """Un acumulador por liga y estadística, como `escalera_datos.Modelos`."""
    from .evaluacion_estadisticas import tabla_estadistica
    out = {"corners": [], "cards": []}
    for liga, df in partidos.groupby("league_id"):
        for mercado, (vl, vv) in (("corners", ("home_corners", "away_corners")), ("cards", ("tarj_local", "tarj_visit"))):
            d = df.assign(valor_local=df[vl], valor_visit=df[vv]).dropna(subset=["valor_local", "valor_visit"])
            if len(d) < 50:
                continue
            p = d.rename(columns={"match_id": "evento", "kickoff_utc": "fecha", "home_team_id": "local",
                                  "away_team_id": "visitante", "referee": "arbitro"})
            t = tabla_estadistica(p[["evento", "fecha", "local", "visitante", "valor_local", "valor_visit", "arbitro"]],
                                  mercado, desde=pd.Timestamp(desde, tz="UTC"))
            out[mercado].append(t.assign(liga=liga))
    return {k: pd.concat(v, ignore_index=True) for k, v in out.items() if v}


def cargar_partidos_estadisticas() -> pd.DataFrame:
    from ..db import query
    rows = query("""SELECT match_id, league_id, kickoff_utc, home_team_id, away_team_id, referee,
                           home_corners, away_corners,
                           home_yellow + coalesce(home_red, 0) AS tarj_local,
                           away_yellow + coalesce(away_red, 0) AS tarj_visit
                    FROM matches WHERE status = 'finished' AND kickoff_utc >= %s ORDER BY kickoff_utc, match_id""",
                 (HISTORIA_DESDE,))
    df = pd.DataFrame(rows)
    df["kickoff_utc"] = pd.to_datetime(df["kickoff_utc"], utc=True)
    return df


def cargar_primer_tiempo(ids: list[str]) -> pd.DataFrame:
    from ..db import query
    return pd.DataFrame(query("SELECT match_id, home_goals_ht, away_goals_ht FROM matches WHERE match_id = ANY(%s)", (ids,)))


# ------------------------------------------------------------------------------------------- resumen

def _grupo(tabla: pd.DataFrame, ligas) -> pd.DataFrame:
    return tabla[tabla["liga"].isin(ligas)]


def resumir(tablas: dict[str, pd.DataFrame], excluyentes: dict[str, set[str]], ligas_todas: list[str]) -> dict:
    """Por familia: alta probabilidad en cada grupo (aprobadas, nuevas, actuales) y por liga nueva."""
    actuales = [l for l in ligas_todas if l not in NUEVAS]
    grupos = {"aprobadas": APROBADAS, "nuevas": NUEVAS, "actuales": tuple(actuales)}
    res: dict = {"inicio": INICIO, "umbral": UMBRAL_ALTA, "criterios": CRITERIOS, "familias": {}}
    for fam, tabla in tablas.items():
        ex = excluyentes.get(fam, set())
        r: dict = {"grupos": {}, "ligas": {}}
        for nombre, ligas in grupos.items():
            a = alta_probabilidad(_grupo(tabla, ligas), ex)
            r["grupos"][nombre] = {**a, "veredicto": veredicto_familia(a), "mercados_fuera": mercados_fuera(a),
                                   "bandas": bandas(_grupo(tabla, ligas), ex)}
        for liga in ligas_todas:
            a = alta_probabilidad(_grupo(tabla, [liga]), ex)
            r["ligas"][liga] = {k: a[k] for k in ("n_alta", "predicha", "real", "promesa")}
        res["familias"][fam] = r
    return res


def calibracion_por_mercado(tablas: dict[str, pd.DataFrame], excluyentes: dict[str, set[str]], ligas) -> dict:
    """ModelEvaluator por familia en el grupo de ligas: n, brier, skill, probabilidad media frente a frecuencia real."""
    out = {}
    for fam, tabla in tablas.items():
        t = _grupo(tabla, ligas)
        if t.empty:
            continue
        out[fam] = _evaluar(t, excluyentes.get(fam, set()))
    return out


# ------------------------------------------------------------------------------------------- informe

def _f(x, d=3):
    return "-" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{d}f}"


def markdown(res: dict) -> str:
    nombre = {"goles": "Goles (todas las líneas, hándicap, marcador, margen)", "1t": "Primera mitad",
              "corners": "Córners (total, local, visitante)", "tarjetas": "Tarjetas totales"}
    L = ["# Backtest de todos los mercados — ligas nuevas", "",
         f"Walk-forward desde {res['inicio']}. Alta probabilidad = lado con probabilidad >= {res['umbral']}.",
         "Criterios fijados antes de ejecutar: " + "; ".join(f"{k} = {v}" for k, v in res["criterios"].items()) + ".", "",
         "## Veredicto por familia (alta probabilidad)", "",
         "| Familia | Grupo | n alta | predicha | real | promesa − realidad | IC95 inf. real | Veredicto | Mercados fuera (A2) |",
         "|---|---|---:|---:|---:|---:|---:|---|---|"]
    for fam in FAMILIAS:
        r = res["familias"].get(fam)
        if not r:
            continue
        for g in ("aprobadas", "nuevas", "actuales"):
            a = r["grupos"][g]
            fuera = ", ".join(a["mercados_fuera"][:6]) + (" …" if len(a["mercados_fuera"]) > 6 else "")
            L.append(f"| {nombre[fam]} | {g} | {a['n_alta']} | {_f(a['predicha'])} | {_f(a['real'])} | {_f(a['promesa'])} | "
                     f"{_f(a['real_ic_inf'])} | **{a['veredicto']}** | {fuera or '-'} |")
    L += ["", "## Lectura estricta por franja de probabilidad (posterior a los criterios; IC95 remuestreando partidos)", "",
          "| Familia | Grupo | Franja | líneas | partidos | predicha | real | promesa − realidad | IC95 | Estado |",
          "|---|---|---|---:|---:|---:|---:|---:|---|---|"]
    for fam in FAMILIAS:
        r = res["familias"].get(fam)
        if not r:
            continue
        for g in ("aprobadas", "actuales"):
            for bd in r["grupos"][g]["bandas"]:
                ic = f"[{_f(bd['ic_inf'])}, {_f(bd['ic_sup'])}]" if bd["ic_inf"] is not None else "-"
                L.append(f"| {fam} | {g} | {bd['banda']} | {bd['lineas']} | {bd['partidos']} | {_f(bd['predicha'])} | "
                         f"{_f(bd['real'])} | {_f(bd['promesa'])} | {ic} | **{bd['estado']}** |")
    L += ["", "## Por liga, las 21 competiciones (contexto; con n alta < 30 no se concluye)", "",
          "| Familia | Liga | Grupo | n alta | predicha | real | promesa − realidad |", "|---|---|---|---:|---:|---:|---:|"]
    for fam in FAMILIAS:
        r = res["familias"].get(fam)
        if not r:
            continue
        for liga in sorted(r["ligas"], key=lambda l: (l not in NUEVAS, l)):
            a = r["ligas"][liga]
            grupo = "aprobada" if liga in APROBADAS else "nueva" if liga in NUEVAS else "actual"
            L.append(f"| {fam} | {liga} | {grupo} | {a['n_alta']} | {_f(a['predicha'])} | {_f(a['real'])} | {_f(a['promesa'])} |")
    L += ["", "## Mercados del grupo «aprobadas» con muestra en alta probabilidad", "",
          "| Familia | Mercado | Lado | n | predicha | real | promesa − realidad |", "|---|---|---|---:|---:|---:|---:|"]
    for fam in FAMILIAS:
        r = res["familias"].get(fam)
        if not r:
            continue
        for m in r["grupos"]["aprobadas"]["mercados"]:
            if m["n"] >= CRITERIOS["mercado_n_min"]:
                L.append(f"| {fam} | {m['mercado']} | {m['lado']} | {m['n']} | {_f(m['predicha'])} | {_f(m['real'])} | {_f(m['promesa'])} |")
    return "\n".join(L) + "\n"


def correr(oos_csv: Path, salida: Path) -> dict:
    oos = pd.read_csv(oos_csv, parse_dates=["kickoff_utc"])
    oos = oos[oos["both_known"].astype(bool)] if "both_known" in oos else oos
    ligas_todas = sorted(oos["league_id"].unique())
    ht = cargar_primer_tiempo([str(x) for x in oos["match_id"].unique()])
    goles, t1 = tablas_goles_y_1t(oos, ht)
    est = tablas_estadisticas(cargar_partidos_estadisticas())
    from .evaluacion_goles import MERCADOS_EXCLUYENTES
    tablas = {"goles": goles, "1t": t1}
    if "corners" in est:
        tablas["corners"] = est["corners"]
    if "cards" in est:
        tablas["tarjetas"] = est["cards"]
    ex = {"goles": set(MERCADOS_EXCLUYENTES), "1t": {"ganador_1t"}}
    salida.mkdir(parents=True, exist_ok=True)
    for fam, t in tablas.items():
        t.to_csv(salida / f"tabla_{fam}.csv.gz", index=False)
    res = resumir(tablas, ex, ligas_todas)
    for fam, t in tablas.items():
        cal = calibracion_por_mercado({fam: t}, ex, APROBADAS)
        if fam in cal:
            cal[fam].to_csv(salida / f"calibracion_{fam}_aprobadas.csv")
    (salida / "mercados.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    (salida / "mercados.md").write_text(markdown(res), encoding="utf-8")
    return res


def regenerar(salida: Path, oos_csv: Path) -> dict:
    """Rehace `mercados.json` y `mercados.md` desde las `tabla_*.csv.gz` ya guardadas (sin recalcular los modelos)."""
    from .evaluacion_goles import MERCADOS_EXCLUYENTES
    oos = pd.read_csv(oos_csv, parse_dates=["kickoff_utc"])
    ligas_todas = sorted(oos["league_id"].unique())
    nombres = {"goles": "goles", "1t": "1t", "corners": "corners", "tarjetas": "tarjetas"}
    tablas = {f: pd.read_csv(salida / f"tabla_{f}.csv.gz") for f in nombres if (salida / f"tabla_{f}.csv.gz").exists()}
    ex = {"goles": set(MERCADOS_EXCLUYENTES), "1t": {"ganador_1t"}}
    res = resumir(tablas, ex, ligas_todas)
    (salida / "mercados.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    (salida / "mercados.md").write_text(markdown(res), encoding="utf-8")
    return res


def main(argv=None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("correr")
    c.add_argument("--oos", default=".local/backtest_ligas_nuevas/pit_oos.csv")
    c.add_argument("--salida", default=".local/backtest_mercados")
    r = sub.add_parser("regenerar")
    r.add_argument("--oos", default=".local/backtest_ligas_nuevas/pit_oos.csv")
    r.add_argument("--salida", default=".local/backtest_mercados")
    a = ap.parse_args(argv)
    res = regenerar(Path(a.salida), Path(a.oos)) if a.cmd == "regenerar" else correr(Path(a.oos), Path(a.salida))
    print(json.dumps({f: {g: v["veredicto"] for g, v in r["grupos"].items()} for f, r in res["familias"].items()},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
