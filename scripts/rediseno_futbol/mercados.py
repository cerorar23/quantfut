"""
Los 37 mercados de las listas del titular (1-nov-2026): probabilidad, calibración, acierto del 10 % más seguro del
día, tasa base real y margen de las casas (PropLine, desde el 23-oct).

    PYTHONPATH=src python scripts/rediseno_futbol/mercados.py --datos .local/rediseno_20261101b --pred .local/rediseno_20261101

Fuentes de goles: A0 con xG (fuera de muestra) y el mercado 1X2 invertido a intensidades (`market_anchor`).
Córners: Yip (con distribución por equipo para el hándicap). Amarillas: Dawson. Jugadores: `eval/rediseno_jugadores`.
Periodo: 24/25 → hoy, 8 ligas del núcleo.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from qf.eval import rediseno as R
from qf.eval import rediseno_conteos as C
from qf.eval import rediseno_jugadores as J
from qf.eval.metrics import murphy
from qf.eval.rediseno_acierto import seleccion_diaria
from qf.eval.rediseno_mercados import (adelgazar, descanso_final, liquidar, matrices_mitades, mitad_con_mas_goles,
                                       pmf_diferencia, pmf_suma, prob_linea)
from qf.model.calibration import score_matrices
from qf.model.market_anchor import market_lambdas

EVAL = "2024-07-01"
TOPE_128 = 1 / (1.28 * 1.05)  # cuota mínima 1,28 con un margen típico de PropLine (5 %)
CAL_DESDE = "2022-07-01"  # ventana de recalibración de los props de jugador
NO_MEDIBLE = {
    ("L1", 12): "Córners asiáticos EN VIVO min 65-70 si el favorito pierde: no hay córners con minuto en la data",
    ("L2", 14): "Carrera a X córners: no hay córners con minuto",
}


def clave_tiempo(df: pd.DataFrame) -> pd.Series:
    return df["minuto"].fillna(0) + df["anadido"].fillna(0) / 100


def realizados(df: pd.DataFrame, inc: pd.DataFrame) -> pd.DataFrame:
    g = inc[inc["subtipo"].eq("goal") & ~inc["anulada"].fillna(False).astype(bool)].copy()
    g["clave"] = clave_tiempo(g)
    g = g.sort_values(["match_id", "clave"])
    primero = g.groupby("match_id").head(1)
    primero = primero.assign(primer_equipo=np.where(primero["marcador_local"].fillna(0) > primero["marcador_visita"].fillna(0),
                                                    "home", "away"),
                             primer_goleador=np.where(primero["clase"].eq("ownGoal"), np.nan, primero["jugador_id"]))
    temprano = g[g["minuto"] <= 10].groupby("match_id").size().rename("goles_0_10")
    am = inc[inc["subtipo"].eq("card") & inc["clase"].eq("yellow")]
    am1 = am[am["minuto"] <= 45].groupby("match_id").size().rename("amarillas_1t")
    con_inc = pd.Series(1, index=inc["match_id"].unique(), name="con_incidencias")
    r = df.set_index("match_id")[["home_goals", "away_goals", "home_goals_ht", "away_goals_ht", "home_corners",
                                  "away_corners", "home_yellow", "away_yellow"]]
    r = r.join(con_inc).join(primero.set_index("match_id")[["primer_equipo", "primer_goleador"]]).join(temprano).join(am1)
    sin = r["con_incidencias"].isna()
    r.loc[~sin, ["goles_0_10", "amarillas_1t"]] = r.loc[~sin, ["goles_0_10", "amarillas_1t"]].fillna(0)
    r.loc[~sin & r["primer_equipo"].isna(), "primer_equipo"] = "nadie"
    return r


def resumen(nombre: str, p_g, p_d, res, dia) -> dict:
    p_g, p_d, res = np.asarray(p_g, float), np.asarray(p_d, float), np.asarray(res, object)
    ok = np.isfinite(p_g) & pd.notna(res)
    p_g, p_d, res, dia = p_g[ok], p_d[ok], res[ok], np.asarray(dia)[ok]
    if not len(p_g):
        return {"mercado": nombre, "n": 0}
    gana = (res == "gana").astype(float); dev = (res == "devuelve")
    sin_dev = ~dev
    m = murphy(p_g, gana)
    cand = pd.DataFrame({"dia": dia[sin_dev], "prob": (p_g / np.clip(1 - p_d, 1e-9, None))[sin_dev],
                         "acierto": gana[sin_dev]})
    top = seleccion_diaria(cand, coberturas=(0.1, 1.0)).set_index("cobertura")
    c128 = cand[cand["prob"] <= TOPE_128]
    t128 = seleccion_diaria(c128, coberturas=(0.1,)).set_index("cobertura") if len(c128) else None
    return {"mercado": nombre, "n": int(len(p_g)), "anuncia_gana": p_g.mean(), "gana_real": gana.mean(),
            "anuncia_devuelve": p_d.mean(), "devuelve_real": dev.mean(),
            "acierto_sin_dev_anunciado": cand["prob"].mean(), "acierto_sin_dev_real": cand["acierto"].mean(),
            "mcb": m["mcb"], "dsc": m["dsc"], "top10_acierto": top.loc[0.1, "acierto"], "top10_anunciado": top.loc[0.1, "anunciado"],
            "top10_n": int(top.loc[0.1, "n"]),
            "top10_128_anunciado": t128.loc[0.1, "anunciado"] if t128 is not None else np.nan,
            "top10_128_acierto": t128.loc[0.1, "acierto"] if t128 is not None else np.nan,
            "top10_128_n": int(t128.loc[0.1, "n"]) if t128 is not None else 0}


def margenes(cuotas: pd.DataFrame) -> pd.DataFrame:
    c = cuotas[cuotas["source"].eq("propline")].copy()
    c["line"] = c["line"].fillna(-999)
    g = c.groupby(["match_id", "bookmaker", "market", "line"])
    agg = g.agg(n=("price", "size"), inv=("price", lambda s: (1 / s).sum())).reset_index()
    esperado = agg["market"].map({"h2h": 1, "double_chance": 2}).fillna(1)
    tam = agg["market"].map({"h2h": 3, "double_chance": 3}).fillna(2)
    agg = agg[agg["n"] == tam]
    agg["margen"] = agg["inv"] - esperado
    agg["casa"] = np.where(agg["bookmaker"].eq("pinnacle"), "pinnacle", "resto")
    return agg.groupby(["market", "casa"])["margen"].agg(["mean", "size"]).round(4).reset_index()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", default=".local/rediseno_20261101b")
    ap.add_argument("--pred", default=".local/rediseno_20261101")
    a = ap.parse_args()
    d, dp = Path(a.datos), Path(a.pred)
    datos = R.cargar(d)
    df = R.tabla_partidos(datos)
    df["dia"] = df["kickoff_utc"].dt.strftime("%Y-%m-%d")
    inc = datos.incidencias.merge(df[["match_id", "kickoff_utc"]], on="match_id")
    previo = df[df["kickoff_utc"] < pd.Timestamp(EVAL, tz="UTC")]
    base = df[df["kickoff_utc"] >= pd.Timestamp(EVAL, tz="UTC")].reset_index(drop=True)
    real = realizados(df, datos.incidencias).loc[base["match_id"]]

    # parámetros estimados SOLO con la historia anterior a la evaluación
    ht = previo.dropna(subset=["home_goals_ht"])
    f1 = (ht.groupby("league_id")[["home_goals_ht", "away_goals_ht"]].sum().sum(1)
          / ht.groupby("league_id")[["home_goals", "away_goals"]].sum().sum(1))
    inc_prev = inc[inc["kickoff_utc"] < pd.Timestamp(EVAL, tz="UTC")]
    gp = inc_prev[inc_prev["subtipo"].eq("goal") & ~inc_prev["anulada"].fillna(False).astype(bool)]
    s10 = float((gp["minuto"] <= 10).mean())
    ap_ = inc_prev[inc_prev["subtipo"].eq("card") & inc_prev["clase"].eq("yellow")]
    s_am1 = float((ap_["minuto"] <= 45).mean())
    print("f1 por liga", f1.round(3).to_dict(), "s10", round(s10, 4), "s_amarillas_1t", round(s_am1, 4))

    pred = pd.read_csv(dp / "pred_f3.csv.gz")
    a0 = base[["match_id"]].merge(pred[pred["modelo"] == "a0_xg"], on="match_id", how="left")
    ruta = d / "anclado.csv.gz"
    if ruta.exists():
        anc = pd.read_csv(ruta)
    else:
        rho = float(pred.loc[pred["modelo"] == "dc_prod", "rho"].median())
        filas = []
        for mid, h, x, v in base[["match_id", "mk_home", "mk_draw", "mk_away"]].dropna().itertuples(index=False):
            fit = market_lambdas(h, x, v, rho=rho)
            filas.append((mid, fit.lam, fit.mu, rho))
        anc = pd.DataFrame(filas, columns=["match_id", "lam", "mu", "rho"]); anc.to_csv(ruta, index=False)
    anc = base[["match_id"]].merge(anc, on="match_id", how="left")

    filas = []
    hg, ag = real["home_goals"].to_numpy(float), real["away_goals"].to_numpy(float)
    h1, a1 = real["home_goals_ht"].to_numpy(float), real["away_goals_ht"].to_numpy(float)
    dia = base["dia"].to_numpy()
    for fuente, x in {"a0_xg": a0, "mercado": anc}.items():
        ok = x["lam"].notna().to_numpy()
        lam, mu = x["lam"].fillna(1.3).to_numpy(), x["mu"].fillna(1.1).to_numpy()
        rho = float(x["rho"].dropna().iloc[0])
        mft = score_matrices(lam, mu, rho)
        f1_m = base["league_id"].map(f1).fillna(f1.mean()).to_numpy()
        m1, m2 = matrices_mitades(lam, mu, f1_m)
        dif, sop = pmf_diferencia(mft); tot = pmf_suma(mft)
        p_loc, p_vis = dif[:, sop > 0].sum(1), dif[:, sop < 0].sum(1)
        fav_local = p_loc >= p_vis
        dif_fav = np.where(fav_local[:, None], dif, dif[:, ::-1])  # diferencia desde el favorito
        real_dif_fav = np.where(fav_local, hg - ag, ag - hg)
        sop_t = np.arange(tot.shape[1])

        def add(lista, num, nombre, pg, pd_, res):
            r = resumen(nombre, np.where(ok, pg, np.nan), pd_, res, dia)
            filas.append({"lista": lista, "num": num, "fuente": fuente, **r})

        # Lista 1
        for h in (1.0, 1.5):  # hándicap asiático al no favorito: gana si (−dif_fav) + h > 0
            g_, d_ = prob_linea(dif_fav, sop, h, "menos")
            add("L1", 1, f"AH no favorito +{h}", g_, d_, liquidar(real_dif_fav, h, "menos"))
        g_, d_ = prob_linea(dif_fav, sop, 0, "mas"); add("L1", 2, "Empate no válido (favorito)", g_, d_, liquidar(real_dif_fav, 0, "mas"))
        g_, d_ = prob_linea(dif_fav, sop, -0.5, "mas"); add("L1", 3, "Doble oportunidad favorito", g_, d_, liquidar(real_dif_fav, -0.5, "mas"))
        g_, d_ = prob_linea(tot, sop_t, 1.5, "mas"); add("L1", 4, "Más de 1,5 goles", g_, d_, liquidar(hg + ag, 1.5, "mas"))
        for l in (4.0, 4.5):
            g_, d_ = prob_linea(tot, sop_t, l, "menos"); add("L1", 5, f"Menos de {l} goles", g_, d_, liquidar(hg + ag, l, "menos"))
        t1 = pmf_suma(m1); s1 = np.arange(t1.shape[1])
        for l, num in ((1.5, 6), (2.5, 7)):
            g_, d_ = prob_linea(t1, s1, l, "menos"); add("L1", num, f"1T menos de {l}", g_, d_, liquidar(h1 + a1, l, "menos"))
        d1, sd1 = pmf_diferencia(m1); d1_fav = np.where(fav_local[:, None], d1, d1[:, ::-1])
        real_d1_fav = np.where(fav_local, h1 - a1, a1 - h1)
        for h in (0.5, 1.0):
            g_, d_ = prob_linea(d1_fav, sd1, h, "menos"); add("L1", 8, f"1T AH no favorito +{h}", g_, d_, liquidar(real_d1_fav, h, "menos"))
        t2 = pmf_suma(m2)
        g_, d_ = prob_linea(t2, np.arange(t2.shape[1]), 0.5, "mas")
        add("L1", 10, "2T más de 0,5", g_, d_, liquidar(hg + ag - h1 - a1, 0.5, "mas"))
        mm = mitad_con_mas_goles(m1, m2)
        add("L1", 11, "Mitad con más goles: 2.ª", mm[:, 2], np.zeros(len(mm)),
            np.where(np.isnan(h1), None, np.where((hg + ag - h1 - a1) > (h1 + a1), "gana", "pierde")))
        p_eq = mft[:, 1:, :].sum((1, 2)); p_ev = mft[:, :, 1:].sum((1, 2))
        p_fav_marca = np.where(fav_local, p_eq, p_ev)
        add("L1", 18, "Favorito marca (más de 0,5)", p_fav_marca, np.zeros(len(lam)),
            np.where(np.where(fav_local, hg, ag) > 0, "gana", "pierde"))
        p_ambos = mft[:, 1:, 1:].sum((1, 2))
        add("L1", 19, "Ambos marcan: NO", 1 - p_ambos, np.zeros(len(lam)), np.where((hg > 0) & (ag > 0), "pierde", "gana"))
        # Lista 2 (goles)
        k = np.where(fav_local, 0, 2); p1x2 = np.stack([p_loc, 1 - p_loc - p_vis, p_vis], 1)
        res1x2 = np.where(hg > ag, 0, np.where(hg == ag, 1, 2))
        add("L2", 1, "1X2 favorito", p1x2[np.arange(len(k)), k], np.zeros(len(k)), np.where(res1x2 == k, "gana", "pierde"))
        g_t = np.stack([(mft[:, i, j] * ((i > 0) & (j > 0) & (i + j > 2))) for i in range(mft.shape[1]) for j in range(mft.shape[2])], 1).sum(1)
        add("L2", 2, "Ambos marcan y más de 2,5", g_t, np.zeros(len(k)), np.where((hg > 0) & (ag > 0) & (hg + ag > 2), "gana", "pierde"))
        flat = mft.reshape(len(lam), -1); kk = flat.argmax(1); n_g = mft.shape[1]
        add("L2", 6, "Marcador exacto (el más probable)", flat.max(1), np.zeros(len(kk)),
            np.where((hg == kk // n_g) & (ag == kk % n_g), "gana", "pierde"))
        p10 = 1 - np.exp(-(lam + mu) * s10)
        add("L2", 7, "Gol en minutos 0-10: sí", p10, np.zeros(len(k)),
            np.where(real["goles_0_10"].isna(), None, np.where(real["goles_0_10"] > 0, "gana", "pierde")))
        hf = descanso_final(m1, m2).reshape(len(lam), 9); khf = hf.argmax(1)
        real_ht = np.where(h1 > a1, 0, np.where(h1 == a1, 1, 2))
        add("L2", 9, "Descanso/final (el más probable)", hf.max(1), np.zeros(len(khf)),
            np.where(np.isnan(h1), None, np.where((real_ht == khf // 3) & (res1x2 == khf % 3), "gana", "pierde")))
        p0 = mft[:, 0, 0]
        p_primero_fav = np.where(fav_local, lam, mu) / (lam + mu) * (1 - p0)
        add("L2", 10, "Primer equipo en marcar: favorito", p_primero_fav, np.zeros(len(k)),
            np.where(real["primer_equipo"].isna(), None,
                     np.where(real["primer_equipo"].to_numpy() == np.where(fav_local, "home", "away"), "gana", "pierde")))
        kt = tot.argmax(1)
        add("L2", 12, "Total exacto de goles (el más probable)", tot.max(1), np.zeros(len(kt)), np.where(hg + ag == kt, "gana", "pierde"))
        add("L2", 13, "Ambos marcan en la 1.ª parte: sí", m1[:, 1:, 1:].sum((1, 2)), np.zeros(len(k)),
            np.where(np.isnan(h1), None, np.where((h1 > 0) & (a1 > 0), "gana", "pierde")))
        p_ambas = (1 - pmf_suma(m1)[:, 0]) * (1 - pmf_suma(m2)[:, 0])
        add("L2", 17, "Gol en ambas mitades: sí", p_ambas, np.zeros(len(k)),
            np.where(np.isnan(h1), None, np.where(((h1 + a1) > 0) & ((hg + ag - h1 - a1) > 0), "gana", "pierde")))
        base[f"fav_local_{fuente}"] = fav_local

    # córners (Yip, con distribución por equipo) y amarillas (Dawson)
    ruta_c = d / "pred_corners_lado.csv.gz"
    if ruta_c.exists():
        pc = pd.read_csv(ruta_c)
    else:
        Lc = C.rasgos(df, datos.contexto, pd.read_csv(d / "derbis.csv.gz"), datos.equipo, "corners")
        pc = C.walk_forward(Lc, "corners", ["c2_yip"], EVAL, por_lado=True); pc.to_csv(ruta_c, index=False)
    pc = base[["match_id"]].merge(pc, on="match_id", how="left")
    py = base[["match_id"]].merge(pd.read_csv(dp / "pred_f4_yellow.csv.gz").query("variante == 't3_dawson'"), on="match_id", how="left")
    Pc = pc.filter(regex=r"^p\d+$").to_numpy(); Ph = pc.filter(regex=r"^h\d+$").to_numpy(); Pa = pc.filter(regex=r"^a\d+$").to_numpy()
    Py = py.filter(regex=r"^p\d+$").to_numpy()
    okc, oky = np.isfinite(Pc).all(1), np.isfinite(Py).all(1)
    Pc, Ph, Pa, Py = np.nan_to_num(Pc), np.nan_to_num(Ph), np.nan_to_num(Pa), np.nan_to_num(Py)
    tc = (real["home_corners"] + real["away_corners"]).to_numpy(float)
    ty = (real["home_yellow"] + real["away_yellow"]).to_numpy(float)
    fuente = "modelo"

    def add2(lista, num, nombre, pg, pd_, res, ok_):
        r = resumen(nombre, np.where(ok_, pg, np.nan), pd_, res, dia)
        filas.append({"lista": lista, "num": num, "fuente": fuente, **r})

    sc = np.arange(Pc.shape[1]); sy = np.arange(Py.shape[1])
    for l in (6.5, 7.5):
        g_, d_ = prob_linea(Pc, sc, l, "mas"); add2("L1", 16, f"Córners más de {l}", g_, d_, liquidar(tc, l, "mas"), okc)
    for l in (9.5, 10.5):
        g_, d_ = prob_linea(Pc, sc, l, "mas"); add2("L2", 5, f"Córners más de {l}", g_, d_, liquidar(tc, l, "mas"), okc)
    # hándicap de córners al favorito (favorito según el mercado; si no hay, según A0)
    fav = np.where(np.isfinite(base["mk_home"]), base["mk_home"] >= base["mk_away"], base["fav_local_a0_xg"])
    n_c = Ph.shape[1]
    dc_ = np.zeros((len(Ph), 2 * n_c - 1))
    for i in range(n_c):
        dc_[:, i:i + n_c] += Ph[:, [i]] * Pa[:, ::-1]
    sop_dc = np.arange(-(n_c - 1), n_c)
    dc_fav = np.where(fav[:, None], dc_, dc_[:, ::-1])
    real_dc = np.where(fav, real["home_corners"] - real["away_corners"], real["away_corners"] - real["home_corners"]).astype(float)
    for h in (1.0, 1.5):
        g_, d_ = prob_linea(dc_fav, sop_dc, h, "mas"); add2("L1", 17, f"AH córners favorito −{h}", g_, d_, liquidar(real_dc, h, "mas"), okc)
    y1 = adelgazar(Py, s_am1)
    g_, d_ = prob_linea(y1, sy, 2.0, "menos")
    add2("L1", 9, "1T amarillas menos de 2,0 (asiático)", g_, d_,
         np.where(real["amarillas_1t"].isna(), None, liquidar(real["amarillas_1t"].fillna(0), 2.0, "menos")), oky)
    for l in (5.5, 6.5):
        g_, d_ = prob_linea(Py, sy, l, "menos"); add2("L1", 20, f"Amarillas menos de {l}", g_, d_, liquidar(ty, l, "menos"), oky)
    g_, d_ = prob_linea(Py, sy, 4.5, "mas"); add2("L2", 4, "Amarillas más de 4,5", g_, d_, liquidar(ty, 4.5, "mas"), oky)

    # jugadores: titulares con al menos 5 partidos previos. Cada prop se recalibra (Platt) con 22/23–23/24, que el
    # modelo de jugador no ha visto como evaluación; la probabilidad cruda sobrepromete en los props de línea alta.
    jt = J.previos(J.tabla(pd.read_csv(d / "jugadores.csv.gz", low_memory=False), df, datos.incidencias), EVAL)
    ok_j = jt["titular"] & (jt["n_prev"] >= 5) & jt["min_esp"].notna()
    ev = jt[ok_j & (jt["kickoff_utc"] >= pd.Timestamp(EVAL, tz="UTC"))]
    cal = jt[ok_j & jt["kickoff_utc"].between(pd.Timestamp(CAL_DESDE, tz="UTC"), pd.Timestamp(EVAL, tz="UTC"),
                                               inclusive="left")]
    entreno = jt[(jt["kickoff_utc"] < pd.Timestamp(EVAL, tz="UTC")) & jt["titular"]]
    kap = J.kappa_nb(entreno["pases_acertados"].to_numpy(float), entreno["m_pases_acertados"].to_numpy(float))
    kap_f = J.kappa_nb(entreno["faltas_recibidas"].to_numpy(float), entreno["m_faltas_recibidas"].to_numpy(float))
    print("kappa pases", round(kap, 1), "kappa faltas recibidas", round(kap_f, 1))

    def pases(x, frac):
        linea = np.floor(x["m_pases_acertados"].to_numpy() * frac) + 0.5
        return (np.array([J.p_mas(np.array([m]), l, kap)[0] for m, l in zip(x["m_pases_acertados"], linea)]),
                (x["pases_acertados"].to_numpy() > linea).astype(float))

    def supera(col, linea, kappa=None):
        return lambda x: (J.p_mas(x[f"m_{col}"].to_numpy(), linea, kappa),
                          (x[col] > linea).astype(float).where(x[col].notna()).to_numpy())

    PROPS = [
        ("L1", 13, "Estrella: más de 0,5 tiros a puerta", lambda x: x[x["m_tiros_puerta"] >= 0.8], supera("tiros_puerta", 0.5)),
        ("L1", 14, "Finalizador: más de 1,5 tiros", lambda x: x[x["m_tiros_totales"] >= 2.0], supera("tiros_totales", 1.5)),
        ("L1", 15, "Pivote: más pases completados (línea 80 % de su media)",
         lambda x: x[(x["posicion"] == "M") & (x["m_pases_acertados"] >= 50)], lambda x: pases(x, 0.8)),
        ("L1", 15, "Pivote: más pases completados (línea en su media)",
         lambda x: x[(x["posicion"] == "M") & (x["m_pases_acertados"] >= 50)], lambda x: pases(x, 1.0)),
        ("L2", 3, "Delantero titular marca", lambda x: x[x["posicion"] == "F"],
         lambda x: (1 - np.exp(-x["m_gol"].to_numpy()), x["goles"].to_numpy(float))),
        ("L2", 8, "Faltas recibidas más de 2,5", lambda x: x, supera("faltas_recibidas", 2.5, kap_f)),
        ("L2", 15, "Más de 2,5 tiros a puerta", lambda x: x[x["m_tiros_puerta"] >= 0.8], supera("tiros_puerta", 2.5)),
        ("L2", 16, "Jugador recibe tarjeta", lambda x: x[x["tarjeta"].notna()],
         lambda x: (1 - np.exp(-x["m_tarjeta"].to_numpy()), x["tarjeta"].to_numpy(float))),
    ]

    def addj(lista, num, nombre, sub, p, y, fuente):
        res = np.where(np.isnan(y), None, np.where(y > 0, "gana", "pierde"))
        filas.append({"lista": lista, "num": num, "fuente": fuente,
                      **resumen(nombre, p, np.zeros(len(p)), res, sub["dia"].to_numpy())})

    for lista, num, nombre, filtro, calcular in PROPS:
        sub_c, sub_e = filtro(cal), filtro(ev)
        p_c, y_c = calcular(sub_c)
        p_e, y_e = calcular(sub_e)
        addj(lista, num, nombre, sub_e, p_e, y_e, "jugador")
        addj(lista, num, nombre, sub_e, J.platt(p_c, y_c)(p_e), y_e, "jugador_cal")
    # primer goleador: carrera exponencial con la intensidad total del partido (A0); sin recalibrar (A0 no cubre 22/23)
    fg = ev.merge(a0[["match_id", "lam", "mu"]], on="match_id").merge(real[["primer_goleador"]], left_on="match_id",
                                                                       right_index=True)
    fg = fg[fg["lam"].notna() & fg["match_id"].isin(real.index[real["con_incidencias"].notna()])]
    Lam = fg["lam"] + fg["mu"]
    addj("L2", 11, "Primer goleador (titular)", fg, (fg["m_gol"] / Lam * (1 - np.exp(-Lam))).to_numpy(),
         (fg["jugador_id"] == fg["primer_goleador"]).astype(float).to_numpy(), "jugador")

    out = pd.DataFrame(filas)
    for (l, n), motivo in NO_MEDIBLE.items():
        out = pd.concat([out, pd.DataFrame([{"lista": l, "num": n, "mercado": motivo, "n": 0}])], ignore_index=True)
    out = out.sort_values(["lista", "num", "mercado", "fuente"]).reset_index(drop=True)
    out.to_csv(d / "mercados.csv", index=False)
    mg = margenes(datos.cuotas)
    mg.to_csv(d / "margenes_propline.csv", index=False)
    bts = base.assign(no_ambos=~((base["home_goals"] > 0) & (base["away_goals"] > 0))).groupby("league_id")["no_ambos"].mean()
    pd.set_option("display.width", 250)
    cols = ["lista", "num", "mercado", "fuente", "n", "anuncia_gana", "gana_real", "devuelve_real", "acierto_sin_dev_real",
            "mcb", "dsc", "top10_anunciado", "top10_acierto", "top10_128_anunciado",
            "top10_128_acierto"]
    print(out[cols].round(3).to_string(index=False))
    print("\nMárgenes PropLine (desde el 23-oct)\n", mg.to_string(index=False))
    print("\nAmbos marcan NO por liga\n", bts.round(3).to_string())


if __name__ == "__main__":
    main()
