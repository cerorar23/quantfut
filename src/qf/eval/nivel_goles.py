"""
Evalúa la corrección del nivel de goles (`DixonColes._nivel_reciente`) contra los criterios N1-N5 fijados el 9-nov-2026
en docs/correccion_nivel_goles_20261109.md, ANTES de ejecutar. Compara dos CSV de `backtest_ligas_nuevas` sobre las mismas filas.

    ejecutar.sh .local/entreno_AAAAMMDD qf.eval.nivel_goles --base pit_oos.csv --con nivel_oos.csv

N4 (alta probabilidad) se evalúa aparte con `backtest_mercados` sobre `nivel_oos.csv`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .metrics import diebold_mariano

CRITERIOS = {"n1_total": 0.05, "n1_reciente": 0.10, "n1_liga": 0.15, "n1_frac_ligas": 0.75,
             "n2_agrupado": 0.001, "n2_liga": 0.005, "n3_mercado": 0.002, "n5_estable": 0.03}
RECIENTE_DESDE = "2026-08-01"
ESTABLE_HASTA = "2026-05-01"


def _cargar(ruta: Path) -> pd.DataFrame:
    d = pd.read_csv(ruta, parse_dates=["kickoff_utc"])
    return d[d["both_known"].astype(bool)] if "both_known" in d else d


def _semana(d: pd.DataFrame) -> np.ndarray:
    k = pd.to_datetime(d["kickoff_utc"], utc=True)
    return (k.dt.isocalendar().year.astype(str) + "-" + k.dt.isocalendar().week.astype(str)).to_numpy()


def sesgo(d: pd.DataFrame) -> float:
    """Goles totales esperados − reales (negativo = el modelo se queda corto)."""
    return float((d["lam"] + d["mu"] - d["home_goals"] - d["away_goals"]).mean())


def _ll(d: pd.DataFrame) -> np.ndarray:
    p = d[["p_home", "p_draw", "p_away"]].to_numpy(float)
    return -np.log(np.clip(p[np.arange(len(d)), d["outcome"].to_numpy(int)], 1e-12, 1.0))


def _brier_mercados(d: pd.DataFrame) -> dict[str, np.ndarray]:
    """Brier por partido de los mercados de goles de N3, desde lam, mu y rho de cada fila."""
    from ..model.calibration import score_matrices
    out: dict[str, list] = {k: [] for k in ("over_1.5", "over_2.5", "over_3.5", "btts", "local_over_1.5", "visitante_over_1.5")}
    for rho, g in d.groupby(d["rho"].round(6)):
        m = score_matrices(g["lam"].to_numpy(), g["mu"].to_numpy(), float(rho), 10)   # (n, 11, 11)
        gl = np.arange(m.shape[1])
        tot = gl[:, None] + gl[None, :]
        hg, ag = g["home_goals"].to_numpy(int), g["away_goals"].to_numpy(int)
        marg_l, marg_v = m.sum(axis=2), m.sum(axis=1)
        for k, p, y in (
            ("over_1.5", m[:, tot > 1.5].sum(axis=1), hg + ag > 1.5),
            ("over_2.5", m[:, tot > 2.5].sum(axis=1), hg + ag > 2.5),
            ("over_3.5", m[:, tot > 3.5].sum(axis=1), hg + ag > 3.5),
            ("btts", m[:, 1:, 1:].sum(axis=(1, 2)), (hg > 0) & (ag > 0)),
            ("local_over_1.5", marg_l[:, 2:].sum(axis=1), hg > 1.5),
            ("visitante_over_1.5", marg_v[:, 2:].sum(axis=1), ag > 1.5),
        ):
            out[k].append(pd.Series((p - y.astype(float)) ** 2, index=g.index))
    return {k: pd.concat(v).reindex(d.index).to_numpy() for k, v in out.items()}


def comparar(base: pd.DataFrame, con: pd.DataFrame) -> dict:
    llave = ["match_id"]
    cols = llave + ["p_home", "p_draw", "p_away", "lam", "mu", "rho"]
    j = base.merge(con[cols], on=llave, suffixes=("", "_c"))
    b = j[["match_id", "kickoff_utc", "league_id", "outcome", "home_goals", "away_goals",
           "p_home", "p_draw", "p_away", "lam", "mu", "rho"]]
    c = j[["match_id", "kickoff_utc", "league_id", "outcome", "home_goals", "away_goals",
           "p_home_c", "p_draw_c", "p_away_c", "lam_c", "mu_c", "rho_c"]].rename(
        columns={"p_home_c": "p_home", "p_draw_c": "p_draw", "p_away_c": "p_away", "lam_c": "lam", "mu_c": "mu", "rho_c": "rho"})
    res: dict = {"n": int(len(j)), "criterios": CRITERIOS}

    # N1 nivel
    rec = pd.to_datetime(b["kickoff_utc"], utc=True) >= pd.Timestamp(RECIENTE_DESDE, tz="UTC")
    est = pd.to_datetime(b["kickoff_utc"], utc=True) < pd.Timestamp(ESTABLE_HASTA, tz="UTC")
    ligas = sorted(b["league_id"].unique())
    por_liga = {l: {"antes": sesgo(b[b["league_id"] == l]), "despues": sesgo(c[c["league_id"] == l])} for l in ligas}
    n1 = {"total_antes": sesgo(b), "total_despues": sesgo(c),
          "reciente_antes": sesgo(b[rec]), "reciente_despues": sesgo(c[rec]),
          "estable_antes": sesgo(b[est]), "estable_despues": sesgo(c[est]),
          "ligas_ok_despues": sum(abs(v["despues"]) <= CRITERIOS["n1_liga"] for v in por_liga.values()),
          "ligas_ok_antes": sum(abs(v["antes"]) <= CRITERIOS["n1_liga"] for v in por_liga.values()), "ligas": len(ligas)}
    n1["ok"] = bool(abs(n1["total_despues"]) <= CRITERIOS["n1_total"] and abs(n1["reciente_despues"]) <= CRITERIOS["n1_reciente"]
                    and n1["ligas_ok_despues"] / len(ligas) >= CRITERIOS["n1_frac_ligas"])
    res["n1"], res["por_liga_sesgo"] = n1, por_liga

    # N2 1X2
    dl = _ll(c) - _ll(b)                       # negativo = mejora
    agr = diebold_mariano(_ll(c), _ll(b), _semana(b))
    peores = {}
    for l in ligas:
        m = (b["league_id"] == l).to_numpy()
        r = diebold_mariano(_ll(c)[m], _ll(b)[m], _semana(b)[m])
        if r["delta"] > CRITERIOS["n2_liga"] and r["ic95"][0] > 0:
            peores[l] = {"delta": r["delta"], "ic95": list(r["ic95"])}
    res["n2"] = {"delta_agrupado": float(dl.mean()), "ic95": list(agr["ic95"]), "ligas_peores": peores,
                 "ok": bool(dl.mean() <= CRITERIOS["n2_agrupado"] and not peores)}

    # N3 mercados de goles
    bb, bc = _brier_mercados(b.reset_index(drop=True)), _brier_mercados(c.reset_index(drop=True))
    mk = {k: float(np.mean(bc[k] - bb[k])) for k in bb}
    media = float(np.mean([np.mean(bc[k] - bb[k]) for k in bb]))
    dm = diebold_mariano(np.mean([bc[k] for k in bb], axis=0), np.mean([bb[k] for k in bb], axis=0), _semana(b))
    res["n3"] = {"delta_por_mercado": mk, "delta_medio": media, "ic95": list(dm["ic95"]),
                 "ok": bool(media <= 0 and max(mk.values()) <= CRITERIOS["n3_mercado"])}

    # N5 periodo estable
    res["n5"] = {"estable_antes": n1["estable_antes"], "estable_despues": n1["estable_despues"],
                 "ok": bool(abs(n1["estable_despues"]) - abs(n1["estable_antes"]) <= CRITERIOS["n5_estable"])}
    res["veredicto_n1_n2_n3_n5"] = bool(n1["ok"] and res["n2"]["ok"] and res["n3"]["ok"] and res["n5"]["ok"])
    return res


def corregir_oos(oos: pd.DataFrame, desde: str = "2025-07-01", paso_dias: int = 30, semivida: float = 60.0,
                 prior: float = 60.0, r_min: float = 0.85, r_max: float = 1.20) -> pd.DataFrame:
    """
    Candidato B: nivel de goles por competición medido con predicciones FUERA de muestra.

    En cada corte mensual `c`, por competición:  r = (Σ w·goles + K) / (Σ w·(λ+μ) + K)  sobre las filas del walk-forward con
    kickoff anterior a `c` (w con semivida `semivida` días), y se multiplica λ y μ de los partidos de [c, c + paso). Después se
    recalcula el 1X2. Solo usa filas anteriores al corte: es lo que haría el reentreno mensual con las predicciones OOS ya registradas.
    """
    from ..model.calibration import probs_1x2
    o = oos[oos["both_known"].astype(bool)] if "both_known" in oos else oos.copy()
    o = o.sort_values("kickoff_utc").reset_index(drop=True)
    k = pd.to_datetime(o["kickoff_utc"], utc=True)
    fin = k.max()
    corte = pd.Timestamp(desde, tz="UTC")
    out = o[k >= corte].copy()
    out_k = pd.to_datetime(out["kickoff_utc"], utc=True)
    factor = pd.Series(1.0, index=out.index)
    while corte <= fin:
        hist = o[k < corte]
        dias = (corte - pd.to_datetime(hist["kickoff_utc"], utc=True)).dt.total_seconds() / 86400.0
        w = np.exp(-np.log(2.0) / semivida * dias)
        real = w * (hist["home_goals"] + hist["away_goals"])
        esp = w * (hist["lam"] + hist["mu"])
        ratio = {}
        for liga, g in hist.groupby("league_id"):
            r = (float(real.loc[g.index].sum()) + prior) / (float(esp.loc[g.index].sum()) + prior)
            ratio[liga] = min(max(r, r_min), r_max)
        ventana = (out_k >= corte) & (out_k < corte + pd.Timedelta(days=paso_dias))
        factor[ventana] = out.loc[ventana, "league_id"].map(ratio).fillna(1.0)
        corte += pd.Timedelta(days=paso_dias)
    out["lam"], out["mu"] = out["lam"] * factor, out["mu"] * factor
    for rho, g in out.groupby(out["rho"].round(6)):
        out.loc[g.index, ["p_home", "p_draw", "p_away"]] = probs_1x2(g["lam"].to_numpy(), g["mu"].to_numpy(), float(rho))
    return out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True)
    ap.add_argument("--con", help="CSV ya corregido (candidato A)")
    ap.add_argument("--corregir-oos", action="store_true", help="candidato B: corrige --base con su propio sesgo fuera de muestra")
    ap.add_argument("--desde", default="2025-07-01")
    ap.add_argument("--semivida", type=float, default=60.0)
    ap.add_argument("--prior", type=float, default=60.0)
    ap.add_argument("--salida", help="ruta del .json")
    a = ap.parse_args(argv)
    base = _cargar(Path(a.base))
    if a.corregir_oos:
        con = corregir_oos(base, a.desde, semivida=a.semivida, prior=a.prior)
        base = base[pd.to_datetime(base["kickoff_utc"], utc=True) >= pd.Timestamp(a.desde, tz="UTC")]
    else:
        con = _cargar(Path(a.con))
    res = comparar(base, con)
    if a.salida:
        Path(a.salida).write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("n1", "n2", "n3", "n5", "veredicto_n1_n2_n3_n5")}, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main(sys.argv[1:])
