"""Compara la referencia independiente del filtro R (`referencia_rating.py`) con `predicciones_wf.parquet`.

Uso:
  python apps/tenis/ops/comparar_referencia.py --demo                     # sin ficheros del otro agente
  python apps/tenis/ops/comparar_referencia.py --hiper <hiperparametros.json> --pred <predicciones_wf.parquet>

Muestra: 3.000 partidos 2019-2024 estratificados por circuito × año del corte × superficie (semilla fija) más
los casos límite. Tolerancia: 1e-6 en probabilidad (la referencia integra M̄_f con q_pred = 60, convergida a
<1e-9; ver informe). Salida: data/tennis/rediseno_20261104/referencia_rating/.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import referencia_rating as rr  # noqa: E402

BASE = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\rediseno_20261104")
EXPORT = BASE / "export_pit"
SALIDA = BASE / "referencia_rating"
SEMILLA = 20261105
TOL = 1e-6


# ------------------------------------------------------------------------------------------------ muestra
def elegir_muestra(df: pd.DataFrame, n_total: int = 3000, por_caso: int = 25, semilla: int = SEMILLA) -> pd.DataFrame:
    rng = np.random.default_rng(semilla)
    d = df.copy()
    d["anio"] = d["corte_utc"].dt.year
    ok = (d["excluir_motivo"].isna() & d["superficie"].notna() & d["formato_decisivo"].isin(rr.DECISIVOS)
          & d["anio"].between(2019, 2024))
    cand = d[ok]
    estratos = cand.groupby(["circuito", "anio", "superficie"])
    n_est = math.ceil(n_total / estratos.ngroups)
    elegidos = []
    for _, g in estratos:
        idx = rng.choice(len(g), size=min(n_est, len(g)), replace=False)
        elegidos.append(g.iloc[np.sort(idx)][["partido_key"]].assign(caso="aleatorio"))
    muestra = pd.concat(elegidos)

    # casos límite
    largo = pd.concat([d[["partido_key", "corte_utc", "visible_resultado_utc", "estado", "minutos_1"]]
                       .assign(jugador=d[f"jugador_{k}"]) for k in (1, 2)]).sort_values(["jugador", "corte_utc"])
    largo["vis_previo"] = largo.groupby("jugador")["visible_resultado_utc"].shift(1)
    gap = (largo["corte_utc"] - largo["vis_previo"]).dt.total_seconds() / 86400
    inactivos = set(largo.loc[gap >= 3 * 365, "partido_key"])
    sin_min = largo[largo["minutos_1"].isna() & largo["estado"].isin(["completado", "retirada", "descalificado"])]
    fat_desc = set()
    vis_sin_min = {j: np.sort(g["visible_resultado_utc"].to_numpy(dtype="datetime64[ns]"))
                   for j, g in sin_min.groupby("jugador")}
    for j, g in largo[largo["jugador"].isin(vis_sin_min.keys())].groupby("jugador"):
        s = vis_sin_min[j]
        c = g["corte_utc"].to_numpy(dtype="datetime64[ns]")
        i = np.searchsorted(s, c, side="left")                       # s[i-1] < c
        prev = np.where(i > 0, s[np.maximum(i - 1, 0)], np.datetime64("NaT"))
        cerca = (i > 0) & ((c - prev) <= np.timedelta64(96, "h"))
        fat_desc.update(g.loc[cerca, "partido_key"])
    casos = {
        "sin_historia_con_ranking": ((d["n_prev_1"] == 0) & d["puntos_1"].notna()) | ((d["n_prev_2"] == 0) & d["puntos_2"].notna()),
        "sin_historia_sin_ranking": ((d["n_prev_1"] == 0) & d["puntos_1"].isna()) | ((d["n_prev_2"] == 0) & d["puntos_2"].isna()),
        "inactividad_3_anios": d["partido_key"].isin(inactivos),
        "fatiga_desconocida": d["partido_key"].isin(fat_desc),
        "mejor_de_5": d["mejor_de"] == 5,
        "decisivo_tb10": d["formato_decisivo"] == "tiebreak_10",
        "supertiebreak_10": d["formato_decisivo"] == "supertiebreak_10",
        "ventaja": d["formato_decisivo"] == "ventaja",
        "tierra_bajo_techo": (d["superficie"] == "Clay") & (d["indoor"] == True),  # noqa: E712
        "jjoo": d["jjoo"] == True,  # noqa: E712
        "por_equipos": d["por_equipos"] == True,  # noqa: E712
        "semana_previa_gs": d["semana_previa_gs"] == True,  # noqa: E712
        "walkover_o_retirada": d["estado"].isin(["walkover", "retirada"]),
    }
    for nombre, m in casos.items():
        g = d[m & d["excluir_motivo"].isna() & d["anio"].between(2019, 2024)]
        if nombre != "sin_historia_sin_ranking":
            g = g[g["superficie"].notna() & g["formato_decisivo"].isin(rr.DECISIVOS)]
        for circ, gc in g.groupby("circuito"):
            idx = rng.choice(len(gc), size=min(por_caso, len(gc)), replace=False)
            muestra = pd.concat([muestra, gc.iloc[np.sort(idx)][["partido_key"]].assign(caso=nombre)])
    return muestra.groupby("partido_key", as_index=False)["caso"].agg(lambda s: ";".join(sorted(set(s))))


# ------------------------------------------------------------------------------------------------ hiperparámetros
ALIAS = {   # clave canónica de rr.Hiper → nombres aceptados en el JSON del otro agente
    "ell": ["ell", "ell_bar", "l_bar", "ellbar", "mu_saque"], "kappa": ["kappa", "kappa_R", "kappa_r"],
    "tau_theta": ["tau_theta"], "tau_d": ["tau_d"], "inact_umbral_dias": ["inact_umbral_dias", "umbral_inactividad"],
    "inact_var": ["inact_var", "aumento_inactividad", "var_inactividad"], "sigma_d": ["sigma_d"],
    "omega": ["omega", "Omega", "omega_d", "corr_d"], "zeta": ["zeta"], "var_d_iota": ["var_d_iota", "sigma_iota"],
    "phi": ["phi"], "lam": ["lam", "lambda", "lambda_fatiga"], "F90": ["F90", "f90"], "ventana_h": ["ventana_h"],
    "gamma": ["gamma"], "s_eps": ["s_eps", "sigma_eps"], "r_eps": ["r_eps", "rho_eps"],
    "prior_a": ["prior_a"], "prior_b": ["prior_b"], "prior_var": ["prior_var"],
    "theta_sin_ranking": ["theta_sin_ranking"], "omega_juegos": ["omega_juegos", "omega_margen"],
}


def hiper_desde_json(h: dict) -> tuple[rr.Hiper | None, list]:
    """Traduce los hiperparámetros congelados de UN circuito al formato canónico de la referencia. Devuelve
    (Hiper o None, claves que faltan). Lo que falte se informa como hallazgo de especificación: no se rellena."""
    vals, faltan = {}, []
    for k, alias in ALIAS.items():
        for a in alias:
            if a in h:
                vals[k] = h[a]; break
        else:
            faltan.append(k)
    if faltan:
        return None, faltan
    vals["phi"] = tuple(vals["phi"])
    return rr.Hiper(**vals).validar(), []


# ------------------------------------------------------------------------------------------------ comparación
def clasificar(fila) -> str:
    causas = []
    if fila.get("prior_1") or fila.get("prior_2"):
        causas.append("prior")
    elif fila.get("historia_corta"):
        causas.append("historia_corta")
    if fila.get("fatiga_desconocida"):
        causas.append("fatiga_desconocida")
    elif (fila.get("F_1") or 0) > 0 or (fila.get("F_2") or 0) > 0:
        causas.append("fatiga")
    if fila.get("mejor_de") == 5 or fila.get("decisivo") not in ("tiebreak_7", None):
        causas.append("formato")
    return "+".join(causas) or "ninguna_marca"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="hiperparámetros de demostración (prueba de humo)")
    ap.add_argument("--hiper"); ap.add_argument("--pred"); ap.add_argument("--col-pi")
    ap.add_argument("--ref-existente", help="reutiliza un pred_referencia.parquet y solo compara")
    ap.add_argument("--circuitos", default="atp,wta")
    ap.add_argument("--n", type=int, default=1500)
    args = ap.parse_args(argv)
    SALIDA.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    df = rr.cargar_entrada(str(EXPORT))
    muestra = elegir_muestra(df, n_total=args.n)
    muestra.to_parquet(SALIDA / "muestra.parquet")
    print(f"muestra: {len(muestra)} partidos ({muestra['caso'].value_counts().to_dict()}) en {time.time()-t0:.0f}s",
          flush=True)
    circuitos = args.circuitos.split(",")
    if args.demo:
        hps = {c: rr.hiper_demo(c) for c in circuitos}
    else:
        crudo = json.loads(Path(args.hiper).read_text(encoding="utf-8"))
        hps = {}
        for c in circuitos:
            h, faltan = hiper_desde_json(crudo.get(c, crudo))
            if faltan:
                raise SystemExit(f"{c}: el JSON no trae {faltan} → hallazgo de especificación; no se rellena")
            hps[c] = h
    if args.ref_existente:
        comparar(pd.read_parquet(args.ref_existente), pd.read_parquet(args.pred), args.col_pi)
        return
    hasta = pd.Timestamp("2025-01-01", tz="UTC")
    ref = rr.ejecutar(df, hps, set(muestra["partido_key"]), hasta=hasta, progreso=20000)
    ref = anadir_pi_simulador(ref.merge(muestra, on="partido_key", how="left"), hps, q=11)
    nombre = "pred_referencia_demo.parquet" if args.demo else "pred_referencia.parquet"
    ref.to_parquet(SALIDA / nombre)
    print(f"referencia: {ref['pi_ref'].notna().sum()} pronósticos en {time.time()-t0:.0f}s", flush=True)
    if args.demo:
        v = ref[ref["pi_ref"].notna() & ref["ganador_real"].notna()]
        y = (v["ganador_real"] == 1).astype(float)
        ll = -np.mean(y * np.log(v["pi_ref"]) + (1 - y) * np.log(1 - v["pi_ref"]))
        print(f"humo: log-loss {ll:.4f} (0,5 → {math.log(2):.4f}); acierto {np.mean((v['pi_ref'] > .5) == (y == 1)):.3f}; "
              f"|π q11 − π q60| máx {np.nanmax(np.abs(ref['pi_ref_q11'] - ref['pi_ref'])):.2e}")
        return
    otro = pd.read_parquet(args.pred)
    comparar(ref, otro, args.col_pi)


def anadir_pi_simulador(ref: pd.DataFrame, hps: dict, q: int = 11) -> pd.DataFrame:
    """π con la MISMA ρ y var(ρ) de la referencia pero integrada por `tenis.simulador.prob_ganar` (API pública)
    con orden q: separa la diferencia de cuadratura de la del filtro (q = 11 del simulador: hasta ~5e-4)."""
    from tenis.simulador import Formato, Incertidumbre, prob_ganar
    out = []
    for x in ref.itertuples():
        if not isinstance(x.decisivo, str) or pd.isna(x.pi_ref):
            out.append(np.nan); continue
        hp = hps[x.circuito]
        v = float(x.var_rho)
        pa, pb = rr.expit(x.ell + x.rho), rr.expit(x.ell - x.rho)
        out.append(prob_ganar(float(pa), float(pb), Formato(int(x.mejor_de), x.decisivo.replace("supertiebreak", "super_tiebreak")),
                              Incertidumbre(hp.s_eps, hp.r_eps, ((v, -v), (-v, v))), q=q))
    return ref.assign(**{f"pi_ref_sim_q{q}": out})


def _col_pi(otro: pd.DataFrame, col: str | None) -> str:
    if col:
        return col
    for c in ("pi", "pi_1", "pi_lado_1", "pi_r", "p_1", "prob_1", "prob_lado_1", "pi_ganador_1"):
        if c in otro.columns:
            return c
    raise KeyError(f"no encuentro la columna de π en {list(otro.columns)}; usa --col-pi")


def comparar(ref: pd.DataFrame, otro: pd.DataFrame, col_pi: str | None = None, sufijo: str = "") -> dict:
    c = _col_pi(otro, col_pi)
    o = otro.rename(columns={c: "pi_otro"})
    m = ref.merge(o.drop(columns=[x for x in ("circuito", "corte_utc") if x in o.columns]), on="partido_key",
                  how="inner")
    m["dif"] = m["pi_ref"] - m["pi_otro"]
    m["dif_q11"] = m["pi_ref_q11"] - m["pi_otro"]
    if "pi_ref_sim_q11" not in m:
        m["pi_ref_sim_q11"] = np.nan
    m["dif_sim_q11"] = m["pi_ref_sim_q11"] - m["pi_otro"]
    m["abs"] = m["dif"].abs()
    ambos = m[m["pi_ref"].notna() & m["pi_otro"].notna()].copy()
    ambos["causa_marcas"] = ambos.apply(lambda r: clasificar(r.to_dict()), axis=1)
    solo_ref = m[m["pi_ref"].notna() & m["pi_otro"].isna()]
    solo_otro = m[m["pi_ref"].isna() & m["pi_otro"].notna()]
    res = {
        "columna_pi_otro": c,
        "en_muestra": int(len(ref)), "emparejados": int(len(m)), "ambos_con_pi": int(len(ambos)),
        "solo_referencia_pronostica": int(len(solo_ref)), "solo_otro_pronostica": int(len(solo_otro)),
        "motivos_solo_otro": solo_otro["motivo"].value_counts().to_dict(),
        "tolerancia": TOL,
        "dif_abs_max": float(ambos["abs"].max()) if len(ambos) else None,
        "dif_abs_media": float(ambos["abs"].mean()) if len(ambos) else None,
        "dif_abs_mediana": float(ambos["abs"].median()) if len(ambos) else None,
        "dif_media_con_signo": float(ambos["dif"].mean()) if len(ambos) else None,
        "frac_dentro_tol": float((ambos["abs"] <= TOL).mean()) if len(ambos) else None,
        "frac_dentro_tol_q11_propia": float((ambos["dif_q11"].abs() <= TOL).mean()) if len(ambos) else None,
        "frac_dentro_tol_simulador_q11": float((ambos["dif_sim_q11"].abs() <= TOL).mean()) if len(ambos) else None,
        "dif_abs_max_simulador_q11": float(ambos["dif_sim_q11"].abs().max()) if len(ambos) else None,
        "frac_dentro_1e-3": float((ambos["abs"] <= 1e-3).mean()) if len(ambos) else None,
        "corr": float(np.corrcoef(ambos["pi_ref"], ambos["pi_otro"])[0, 1]) if len(ambos) > 2 else None,
        "por_causa": ambos.groupby("causa_marcas")["abs"].agg(["count", "mean", "max"])
                          .reset_index().to_dict("records"),
        "por_circuito": ambos.groupby("circuito")["abs"].agg(["count", "mean", "max"])
                             .reset_index().to_dict("records"),
    }
    if "caso" in ambos:
        res["por_caso"] = (ambos.assign(caso=ambos["caso"].str.split(";")).explode("caso").groupby("caso")["abs"]
                           .agg(["count", "mean", "max"]).reset_index().to_dict("records"))
    y = ambos["ganador_real"]
    v = ambos[y.notna()]
    if len(v):
        yy = (v["ganador_real"] == 1).astype(float)
        for k in ("pi_ref", "pi_otro"):
            p = v[k].clip(1e-12, 1 - 1e-12)
            res[f"logloss_{k}"] = float(-np.mean(yy * np.log(p) + (1 - yy) * np.log(1 - p)))
    cols = [x for x in ("partido_key", "circuito", "corte_utc", "caso", "pi_ref", "pi_ref_sim_q11", "pi_otro", "dif",
                        "rho", "var_rho", "prior_1", "prior_2", "historia_corta", "F_1", "F_2",
                        "fatiga_desconocida", "mejor_de", "decisivo", "n_prev_1", "n_prev_2", "causa_marcas")
            if x in ambos.columns]
    top = ambos.sort_values("abs", ascending=False)[cols].head(40)
    top.to_csv(SALIDA / f"comparacion_top{sufijo}.csv", index=False)
    m.to_parquet(SALIDA / f"comparacion{sufijo}.parquet")
    (SALIDA / f"comparacion{sufijo}.json").write_text(json.dumps(res, indent=1, default=str, ensure_ascii=False),
                                                      encoding="utf-8")
    print(json.dumps(res, indent=1, default=str, ensure_ascii=False))
    print(top.head(15).to_string())
    return res


if __name__ == "__main__":
    main()
