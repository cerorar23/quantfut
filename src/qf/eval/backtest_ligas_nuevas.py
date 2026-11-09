"""
Backtest walk-forward de las ligas nuevas (8-nov-2026).

    ejecutar.sh .local/entreno_AAAAMMDD qf.eval.backtest_ligas_nuevas correr --variante pit
    ejecutar.sh .local/entreno_AAAAMMDD qf.eval.backtest_ligas_nuevas informe

Qué mide: la probabilidad 1X2 del Dixon-Coles de producción (semivida 270, mezcla de xG 0,65), reentrenado cada
30 días SOLO con partidos anteriores al corte (`walk_forward_oos` -> `fit(as_of=corte)`), sobre el tramo limpio
desde 2025-07-01. Ese tramo se eligió ANTES de ver nada: los parámetros del modelo se fijaron con datos hasta
2025-06, así que medir antes sería premiar un ajuste sobre los mismos partidos.

Variantes (misma tabla, distinta información de xG):
  pit             lo que el motor realmente sabía: el xG con procedencia solo cuenta desde su recepción real.
                  ES LA ÚNICA QUE DECIDE. Es lo que hará el motor en vivo.
  reconstruccion  xG disponible siempre (valores recibidos después del partido). Optimista: informativa.
  goles           sin xG (`xg_blend = 0`): mide cuánto aporta el xG, sobre todo en Serie B y LaLiga 2 (xG parcial).
  sin_nuevas      el modelo con solo las 13 competiciones actuales: sirve de control para comprobar que añadir
                  las 8 ligas no empeora lo ya publicado.
  nivel           como `pit` pero con la recalibración del nivel de goles por liga (`DixonColes._nivel_reciente`). Se activa con
                  `DC_NIVEL_HALFLIFE_DAYS=90` en el entorno al ejecutar (ver docs/correccion_nivel_goles_20261109.md).

CRITERIOS DE APROBACIÓN (fijados el 8-nov-2026 antes de medir; no se cambian después de ver los resultados):
  C1  n >= 150 partidos fuera de muestra con los dos equipos conocidos.
  C2  Log-loss 1X2 mejor que la frecuencia de resultados de la liga ANTES de 2025-07 (base fuera de muestra, no la
      del propio periodo) y con el intervalo al 95 % (errores por semana) entero a favor del modelo.
  C3  Calibración: ECE (10 bins sobre las 3 probabilidades) <= 0,05 y sesgo medio por resultado
      (local / empate / visitante) <= 0,05 en valor absoluto.
  C4  No empeora las 13 competiciones actuales: en ninguna el log-loss sube mas de 0,005 con el intervalo al 95 %
      entero por encima de 0 (comparando `pit` contra `sin_nuevas`).
Una liga solo pasa a `model_enabled` si cumple C1-C3 en `pit` y C4 se cumple en el conjunto. Si solo cumple en
`reconstruccion`, queda marcada «depende de xG recibido tarde» y no se enciende.
No es objetivo ganar a Pinnacle: la comparación con el mercado se informa, pero no decide (decisión del titular,
1-nov-2026: probabilidad calibrada y honesta, no batir al cierre).
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .metrics import brier, diebold_mariano, ece, log_loss, rps

log = logging.getLogger("backtest_ligas_nuevas")

LIGAS_NUEVAS = ("gb.championship", "de.bundesliga2", "tr.super_lig", "no.eliteserien",
                "es.laliga2", "it.serie_b", "se.allsvenskan", "ch.super_league")
INICIO = "2025-07-01"
PASO_DIAS = 30
SEMIVIDA = 270.0   # igual que el worker (entorno.sh)
MEZCLA_XG = 0.65
VARIANTES = ("pit", "reconstruccion", "goles", "sin_nuevas", "nivel", "nivel45", "nivel180")
CRITERIOS = {"n_min": 150, "ece_max": 0.05, "sesgo_max": 0.05, "regresion_max": 0.005}
EPS = 1e-12


def cargar_datos(variante: str) -> pd.DataFrame:
    from ..model.train import load_training_data
    df = load_training_data(incluir=list(LIGAS_NUEVAS))
    if variante == "sin_nuevas":
        df = df[~df["league_id"].isin(LIGAS_NUEVAS)].copy()
    if variante == "reconstruccion":
        df = df.assign(xg_source=None)  # sin procedencia: el xG vale para cualquier corte
    return df


def correr(variante: str, salida: Path, inicio: str = INICIO, paso: int = PASO_DIAS) -> Path:
    from ..eval.backtest import check_leakage, walk_forward_oos
    df = cargar_datos(variante)
    problemas = check_leakage(df)
    for p in problemas:
        log.warning("check_leakage: %s", p)
    xg_mezcla = 0.0 if variante == "goles" else MEZCLA_XG
    log.info("variante=%s partidos=%d ligas=%d xg_blend=%s", variante, len(df), df["league_id"].nunique(), xg_mezcla)
    oos = walk_forward_oos(df, inicio, step_days=paso, halflife=SEMIVIDA, xg_blend=xg_mezcla)
    oos["variante"] = variante
    salida.mkdir(parents=True, exist_ok=True)
    destino = salida / f"{variante}_oos.csv"
    oos.to_csv(destino, index=False)
    (salida / f"{variante}_leakage.json").write_text(json.dumps(problemas, ensure_ascii=False), encoding="utf-8")
    log.info("guardado %s (%d predicciones)", destino, len(oos))
    return destino


# ----------------------------------------------------------------------------------------------- informe

def _probs(oos: pd.DataFrame) -> np.ndarray:
    return oos[["p_home", "p_draw", "p_away"]].to_numpy(float)


def _perdida(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    return -np.log(np.clip(p[np.arange(len(y)), y], EPS, 1.0))


def _semana(oos: pd.DataFrame) -> np.ndarray:
    k = pd.to_datetime(oos["kickoff_utc"], utc=True)
    return (k.dt.isocalendar().year.astype(str) + "-" + k.dt.isocalendar().week.astype(str)).to_numpy()


def frecuencia_previa(historico: pd.DataFrame, liga: str, antes) -> np.ndarray:
    """Frecuencia de local/empate/visitante de la liga ANTES del tramo medido (base fuera de muestra)."""
    h = historico[(historico["league_id"] == liga) & (historico["kickoff_utc"] < antes)]
    h = h.dropna(subset=["home_goals", "away_goals"])
    if len(h) < 100:
        return np.array([np.nan] * 3)
    y = np.where(h["home_goals"] > h["away_goals"], 0, np.where(h["home_goals"] == h["away_goals"], 1, 2))
    return np.bincount(y, minlength=3) / len(y)


def evaluar_liga(oos: pd.DataFrame, base: np.ndarray) -> dict:
    """Métricas 1X2 de una liga y su veredicto C1-C3 (ver el docstring del módulo)."""
    o = oos[oos["both_known"].astype(bool)] if "both_known" in oos else oos
    n = len(o)
    if n == 0:
        return {"n": 0, "c1": False}
    p, y = _probs(o), o["outcome"].to_numpy(int)
    onehot = np.zeros_like(p)
    onehot[np.arange(n), y] = 1.0
    res = {"n": n, "rps": rps(p, y), "log_loss": log_loss(p, y), "brier": brier(p, y),
           "ece": ece(p.ravel(), onehot.ravel()),
           "sesgo": [float(x) for x in (p.mean(axis=0) - onehot.mean(axis=0))]}
    res["c1"] = n >= CRITERIOS["n_min"]
    if np.isfinite(base).all():
        pb = np.tile(base, (n, 1))
        dm = diebold_mariano(_perdida(p, y), _perdida(pb, y), _semana(o))
        res.update(ll_base=log_loss(pb, y), dm_vs_base=dm,
                   skill_ll=1.0 - res["log_loss"] / log_loss(pb, y))
        res["c2"] = bool(dm["ic95"][1] < 0)
    else:
        res["c2"] = False
    res["c3"] = bool(res["ece"] <= CRITERIOS["ece_max"] and max(abs(x) for x in res["sesgo"]) <= CRITERIOS["sesgo_max"])
    mk = o.dropna(subset=["mk_home", "mk_draw", "mk_away"])
    if len(mk) >= 30:
        pm = mk[["mk_home", "mk_draw", "mk_away"]].to_numpy(float)
        ym = mk["outcome"].to_numpy(int)
        res["mercado"] = {"n": len(mk), "rps_mercado": rps(pm, ym), "rps_modelo": rps(_probs(mk), ym),
                          "ll_mercado": log_loss(pm, ym), "ll_modelo": log_loss(_probs(mk), ym)}
    return res


def regresion(pit: pd.DataFrame, control: pd.DataFrame, ligas: list[str]) -> dict:
    """C4: log-loss de `pit` menos el de `sin_nuevas` en las competiciones actuales (positivo = peor)."""
    out = {}
    llave = ["match_id"]
    for liga in ligas:
        a = pit[pit["league_id"] == liga].merge(control[control["league_id"] == liga][llave + ["p_home", "p_draw", "p_away"]],
                                                on=llave, suffixes=("", "_c"))
        if a.empty:
            continue
        y = a["outcome"].to_numpy(int)
        pa = _probs(a)
        pc = a[["p_home_c", "p_draw_c", "p_away_c"]].to_numpy(float)
        dm = diebold_mariano(_perdida(pa, y), _perdida(pc, y), _semana(a))
        out[liga] = {**dm, "peor": bool(dm["delta"] > CRITERIOS["regresion_max"] and dm["ic95"][0] > 0)}
    return out


MERCADOS_GOLES = ("over_1.5", "over_2.5", "over_3.5", "btts", "doble_oportunidad")


def mercados_goles(oos: pd.DataFrame, ligas=LIGAS_NUEVAS) -> list[dict]:
    """Calibración de los mercados que dependen solo del marcador, por liga (variante `pit`). Informa, no decide."""
    from .evaluacion_goles import tabla_goles
    from .evaluador import ModelEvaluator
    filas = []
    for liga in ligas:
        o = oos[oos["league_id"] == liga]
        if o.empty:
            continue
        partidos = o.rename(columns={"match_id": "evento", "home_goals": "goles_local", "away_goals": "goles_visitante"})[
            ["evento", "lam", "mu", "rho", "goles_local", "goles_visitante"]]
        t = tabla_goles(partidos)
        t = t[t["mercado"].isin(MERCADOS_GOLES)]
        ev = ModelEvaluator(t).evaluar()
        for mercado, r in ev.iterrows():
            filas.append({"liga": liga, "mercado": mercado, "n": int(r["n"]), "prob_media": float(r["prob_media"]),
                          "tasa_real": float(r["tasa_real"]), "brier_skill": float(r["brier_skill"]),
                          "log_loss_skill": float(r["log_loss_skill"])})
    return filas


def informe(directorio: Path, historico: pd.DataFrame | None = None) -> dict:
    oos = {v: pd.read_csv(directorio / f"{v}_oos.csv", parse_dates=["kickoff_utc"])
           for v in VARIANTES if (directorio / f"{v}_oos.csv").exists()}
    if "pit" not in oos:
        raise SystemExit("falta pit_oos.csv: corre primero `correr --variante pit`")
    if historico is None:
        from ..model.train import load_training_data
        historico = load_training_data(incluir=list(LIGAS_NUEVAS))
    antes = pd.Timestamp(INICIO, tz="UTC")
    ligas = sorted(oos["pit"]["league_id"].unique())
    res: dict = {"inicio": INICIO, "criterios": CRITERIOS, "ligas": {}}
    for liga in ligas:
        base = frecuencia_previa(historico, liga, antes)
        fila = {"base_previa": [float(x) for x in base], "variantes": {}}
        for v, tabla in oos.items():
            if v == "sin_nuevas":
                continue
            fila["variantes"][v] = evaluar_liga(tabla[tabla["league_id"] == liga], base)
        res["ligas"][liga] = fila
    actuales = [l for l in ligas if l not in LIGAS_NUEVAS]
    if "sin_nuevas" in oos:
        res["regresion"] = regresion(oos["pit"], oos["sin_nuevas"], actuales)
    regresiona = [l for l, r in (res.get("regresion") or {}).items() if r["peor"]]
    res["c4"] = {"evaluado": "sin_nuevas" in oos, "ligas_peores": regresiona, "ok": "sin_nuevas" in oos and not regresiona}
    veredicto = {}
    for liga in LIGAS_NUEVAS:
        v = res["ligas"].get(liga, {}).get("variantes", {})
        pit, rec = v.get("pit", {}), v.get("reconstruccion", {})
        ok = lambda e: bool(e) and e.get("c1") and e.get("c2") and e.get("c3")
        if ok(pit) and res["c4"]["ok"]:
            veredicto[liga] = "APRUEBA"
        elif ok(pit):
            veredicto[liga] = "APRUEBA_C1_C3_FALTA_C4"
        elif ok(rec):
            veredicto[liga] = "DEPENDE_DE_XG_RECIBIDO_TARDE"
        else:
            veredicto[liga] = "NO_APRUEBA"
    res["veredicto"] = veredicto
    res["mercados_goles"] = mercados_goles(oos["pit"])
    (directorio / "informe.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    return res


def _f(x, d=4):
    return "-" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{d}f}"


def markdown(res: dict) -> str:
    """Tabla por liga de la variante `pit` (la que decide) y las otras como contexto."""
    L = ["# Backtest de las ligas nuevas", "",
         f"Walk-forward desde {res['inicio']}, reentrenado cada {PASO_DIAS} dias solo con partidos anteriores al corte.",
         "Criterios fijados antes de medir: " + ", ".join(f"{k} = {v}" for k, v in res["criterios"].items()) + ".", ""]
    L += ["## Veredicto (variante `pit`)", "",
          "| Liga | n | log-loss | base previa | skill | IC95 dif. vs base | ECE | sesgo max | C1 | C2 | C3 | Veredicto |",
          "|---|---:|---:|---:|---:|---|---:|---:|:-:|:-:|:-:|---|"]
    for liga in LIGAS_NUEVAS:
        e = res["ligas"].get(liga, {}).get("variantes", {}).get("pit", {})
        if not e.get("n"):
            L.append(f"| {liga} | 0 | | | | | | | | | | SIN DATOS |")
            continue
        dm = e.get("dm_vs_base") or {}
        ic = dm.get("ic95")
        L.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | **{}** |".format(
            liga, e["n"], _f(e["log_loss"]), _f(e.get("ll_base")), _f(e.get("skill_ll")),
            f"[{_f(ic[0])}, {_f(ic[1])}]" if ic else "-", _f(e["ece"]), _f(max(abs(x) for x in e["sesgo"])),
            "si" if e["c1"] else "no", "si" if e.get("c2") else "no", "si" if e["c3"] else "no",
            res["veredicto"][liga]))
    L += ["", "## Cuanto aporta el xG y que pasa si se reconstruye", "",
          "| Liga | log-loss `pit` | `reconstruccion` | sin xG (`goles`) | RPS `pit` | RPS sin xG |", "|---|---:|---:|---:|---:|---:|"]
    for liga in LIGAS_NUEVAS:
        v = res["ligas"].get(liga, {}).get("variantes", {})
        g = lambda k, m: _f((v.get(k) or {}).get(m))
        L.append(f"| {liga} | {g('pit','log_loss')} | {g('reconstruccion','log_loss')} | {g('goles','log_loss')} | {g('pit','rps')} | {g('goles','rps')} |")
    L += ["", "## Frente al mercado (informativo, no decide)", "",
          "| Liga | n con cuota | RPS modelo | RPS mercado | log-loss modelo | log-loss mercado |", "|---|---:|---:|---:|---:|---:|"]
    for liga in LIGAS_NUEVAS:
        m = (res["ligas"].get(liga, {}).get("variantes", {}).get("pit") or {}).get("mercado")
        if m:
            L.append(f"| {liga} | {m['n']} | {_f(m['rps_modelo'])} | {_f(m['rps_mercado'])} | {_f(m['ll_modelo'])} | {_f(m['ll_mercado'])} |")
        else:
            L.append(f"| {liga} | <30 | | | | |")
    if res.get("mercados_goles"):
        L += ["", "## Mercados de goles (variante `pit`; informa, no decide)", "",
              "Probabilidad media predicha frente a la frecuencia real, y mejora (skill) sobre predecir siempre la frecuencia del periodo.", "",
              "| Liga | Mercado | n | predicha | real | dif. | skill Brier |", "|---|---|---:|---:|---:|---:|---:|"]
        for r in res["mercados_goles"]:
            L.append(f"| {r['liga']} | {r['mercado']} | {r['n']} | {_f(r['prob_media'], 3)} | {_f(r['tasa_real'], 3)} | "
                     f"{r['prob_media'] - r['tasa_real']:+.3f} | {_f(r['brier_skill'], 4)} |")
    L += ["", "## C4: las 13 competiciones actuales no empeoran", ""]
    c4 = res["c4"]
    L.append("Evaluado: " + ("si" if c4["evaluado"] else "NO (falta la variante `sin_nuevas`)") +
             f". Competiciones peores: {', '.join(c4['ligas_peores']) or 'ninguna'}.")
    if res.get("regresion"):
        L += ["", "| Liga | dif. log-loss (con nuevas - sin nuevas) | IC95 |", "|---|---:|---|"]
        for liga, r in sorted(res["regresion"].items()):
            L.append(f"| {liga} | {_f(r['delta'], 5)} | [{_f(r['ic95'][0], 5)}, {_f(r['ic95'][1], 5)}] |")
    return "\n".join(L) + "\n"


def main(argv=None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("correr")
    c.add_argument("--variante", choices=VARIANTES, required=True)
    c.add_argument("--salida", default=".local/backtest_ligas_nuevas")
    c.add_argument("--inicio", default=INICIO)
    c.add_argument("--paso", type=int, default=PASO_DIAS)
    i = sub.add_parser("informe")
    i.add_argument("--salida", default=".local/backtest_ligas_nuevas")
    i.add_argument("--markdown", help="ruta del .md que se escribe")
    a = ap.parse_args(argv)
    if a.cmd == "correr":
        correr(a.variante, Path(a.salida), a.inicio, a.paso)
    else:
        res = informe(Path(a.salida))
        if a.markdown:
            Path(a.markdown).write_text(markdown(res), encoding="utf-8")
        print(json.dumps(res["veredicto"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
