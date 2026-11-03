"""
Mercados «en vivo» y de tiempos con el archivo de BetsAPI (bet365): córners asiáticos en el minuto 65-70 con el favorito
perdiendo, carrera a X córners y córners / tarjetas en los primeros 10 minutos.

    PYTHONPATH=src python scripts/rediseno_futbol/betsapi_vivo.py --raiz .local/betsapi_futbol \
        --datos .local/rediseno_20261101b --pred .local/rediseno_20261101

Necesita eventos.csv.gz, ticks.csv.gz y puente.csv.gz de `betsapi_cuotas.py`. Las lecturas en vivo llegan cuando cambia
la línea (≈ una por minuto), así que el minuto de un córner se conoce con esa resolución; los casos en que los dos
equipos cruzan entre dos lecturas se descartan y se informa cuántos son.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import gamma

from qf.eval import rediseno_betsapi as B
from qf.eval.rediseno_acierto import wilson

EVAL = pd.Timestamp("2024-07-01", tz="UTC")
DURACION = 95.0  # minutos con descuento


def par(serie: pd.Series) -> pd.DataFrame:
    c = serie.astype(str).str.split("-", expand=True)
    if c.shape[1] < 2:
        return pd.DataFrame({"a": np.nan, "b": np.nan}, index=serie.index)
    return pd.DataFrame({"a": pd.to_numeric(c[0], errors="coerce"), "b": pd.to_numeric(c[1], errors="coerce")}, index=serie.index)


def corners_en_vivo(raiz: Path, ev: pd.DataFrame, tk: pd.DataFrame, puente: pd.DataFrame, partidos: pd.DataFrame) -> None:
    fin = ev[ev["estado"].astype(str).eq("3") & ev["gl_h"].notna()].merge(puente[["bid", "match_id"]], on="bid")
    fin["final"] = fin["cor_h"] + fin["cor_a"]
    k0 = fin.set_index("bid")["kickoff"]
    # favorito del cierre prepartido (cuota más baja del 1X2) y línea de córners del cierre
    cierre = B.instantaneas(tk, k0, 0)
    fav = cierre[cierre["mercado"].eq("1x2")].set_index("bid")
    fav = (fav["home_od"] <= fav["away_od"]).map({True: "home", False: "away"}).rename("fav")
    lin0 = cierre[cierre["mercado"].eq("corners")].set_index("bid")["linea"].map(lambda x: (B.lineas(x) or [np.nan])[0]).rename("linea_previa")
    v = tk[tk["mercado"].eq("corners") & tk["minuto"].between(65, 70)].sort_values(["bid", "t"]).groupby("bid").tail(1)
    g, c = par(v["marcador"]), par(v["corners_vivo"])
    v = v.assign(gh=g["a"], ga=g["b"], ch=c["a"], ca=c["b"]).merge(fin[["bid", "final", "kickoff", "match_id"]], on="bid")
    v = v.join(fav, on="bid").join(lin0, on="bid").dropna(subset=["gh", "ga", "ch", "ca", "fav"])
    v["gf"] = np.where(v["fav"] == "home", v["gh"], v["ga"]); v["gd"] = np.where(v["fav"] == "home", v["ga"], v["gh"])
    v["estado"] = np.where(v["gf"] < v["gd"], "favorito pierde", np.where(v["gf"] == v["gd"], "empate", "favorito gana"))
    v["ahora"] = v["ch"] + v["ca"]; v["resto"] = v["final"] - v["ahora"]
    v = v[v["resto"] >= 0]
    v["ls"] = v["linea"].map(B.lineas)
    v["resto_previsto"] = v["linea_previa"] * (DURACION - v["minuto"]) / DURACION  # lo que daría el ritmo previo al partido
    print(f"\n=== Córners en vivo, minuto 65-70: {len(v)} partidos con lectura; minuto medio {v['minuto'].mean():.1f}")
    t = v.groupby("estado").agg(n=("bid", "size"), linea_previa=("linea_previa", "mean"), resto_obs=("resto", "mean"),
                                resto_ritmo_previo=("resto_previsto", "mean"))
    t["razon_obs_prev"] = t["resto_obs"] / t["resto_ritmo_previo"]
    print(t.round(2).to_string())
    # mercado: línea única, más de la línea con la cuota de ese instante
    u = v[v["ls"].map(len) == 1].copy()
    u["l"] = u["ls"].map(lambda x: x[0])
    u["q_over"] = (1 / u["over_od"]) / (1 / u["over_od"] + 1 / u["under_od"])
    u["over_gana"] = (u["final"] > u["l"]).astype(float); u["push"] = (u["final"] == u["l"])
    nu = u[~u["push"]]
    print("\n   Mercado (líneas enteras y medias; sin devoluciones): más de la línea")
    filas = []
    for est, g_ in nu.groupby("estado"):
        lo, hi = wilson(g_["over_gana"].sum(), len(g_))
        filas.append({"estado": est, "n": len(g_), "over_real": g_["over_gana"].mean(), "ic95": f"[{lo:.3f};{hi:.3f}]",
                      "over_implicito": g_["q_over"].mean(), "diferencia": g_["over_gana"].mean() - g_["q_over"].mean(),
                      "cuota_over": g_["over_od"].mean()})
    print(pd.DataFrame(filas).round(3).to_string(index=False))
    print("\n   Mejor lado con cuota ≥ 1,28 cuando el favorito pierde (acierto del lado más probable según la casa):")
    f = nu[nu["estado"] == "favorito pierde"].copy()
    f["lado"] = np.where(f["q_over"] >= 0.5, "over", "under")
    f["p_lado"] = np.where(f["lado"] == "over", f["q_over"], 1 - f["q_over"])
    f["cuota_lado"] = np.where(f["lado"] == "over", f["over_od"], f["under_od"])
    f["ok"] = np.where(f["lado"] == "over", f["over_gana"], 1 - f["over_gana"])
    for etiqueta, h in (("todas", f), ("cuota ≥ 1,28", f[f["cuota_lado"] >= 1.28])):
        lo, hi = wilson(h["ok"].sum(), len(h))
        print(f"   {etiqueta}: n {len(h)}, acierto {h['ok'].mean():.3f} [{lo:.3f};{hi:.3f}], anuncia {h['p_lado'].mean():.3f}, cuota {h['cuota_lado'].mean():.2f}")
    print("   Solo 'más' (over) cuando el favorito pierde:")
    h = nu[(nu["estado"] == "favorito pierde")]
    for etiqueta, hh in (("todas", h), ("cuota over ≥ 1,28", h[h["over_od"] >= 1.28])):
        lo, hi = wilson(hh["over_gana"].sum(), len(hh))
        print(f"   {etiqueta}: n {len(hh)}, acierto {hh['over_gana'].mean():.3f} [{lo:.3f};{hi:.3f}], implícito {hh['q_over'].mean():.3f}, cuota {hh['over_od'].mean():.2f}")
    v[["bid", "match_id", "estado", "minuto", "ahora", "final", "linea", "over_od", "under_od"]].to_csv(raiz / "corners_vivo_65_70.csv.gz", index=False)


def carrera(ev: pd.DataFrame, tk: pd.DataFrame, puente: pd.DataFrame, partidos: pd.DataFrame, d: Path) -> None:
    fin = ev[ev["estado"].astype(str).eq("3") & ev["gl_h"].notna()].merge(puente[["bid", "match_id"]], on="bid")
    vivo = tk[tk["corners_vivo"].notna() & tk["minuto"].notna()]
    cl = pd.read_csv(d / "pred_corners_lado.csv.gz").query("variante == 'c2_yip'").set_index("match_id")
    mh = (cl.filter(regex=r"^h\d+$") * np.arange(cl.filter(regex=r"^h\d+$").shape[1])).sum(1)
    ma = (cl.filter(regex=r"^a\d+$") * np.arange(cl.filter(regex=r"^a\d+$").shape[1])).sum(1)
    medias = pd.DataFrame({"mh": mh, "ma": ma})
    pk = partidos.set_index("match_id")["kickoff_utc"]
    grupos = {bid: g for bid, g in vivo.groupby("bid")}
    t = np.linspace(0.01, DURACION, 400)
    print("\n=== Carrera a X córners (primer equipo en llegar a X)")
    for x in (3, 4, 5, 6):
        filas = []
        for r in fin.itertuples(index=False):
            if r.match_id not in medias.index or pk.get(r.match_id, EVAL) < EVAL or r.bid not in grupos:
                continue
            gan = B.llegada_carrera(grupos[r.bid], x)
            lh, la = medias.loc[r.match_id, "mh"] / DURACION, medias.loc[r.match_id, "ma"] / DURACION
            fh, fa = gamma.pdf(t, x, scale=1 / lh), gamma.pdf(t, x, scale=1 / la)
            Fh, Fa = gamma.cdf(t, x, scale=1 / lh), gamma.cdf(t, x, scale=1 / la)
            dt = t[1] - t[0]
            ph = float(np.sum(fh * (1 - Fa)) * dt); pa = float(np.sum(fa * (1 - Fh)) * dt)
            filas.append({"bid": r.bid, "gan": gan, "ph": ph, "pa": pa, "algun": pa + ph})
        o = pd.DataFrame(filas)
        res = o.dropna(subset=["gan"])
        res = res.assign(p_home=res["ph"] / (res["ph"] + res["pa"]), real_home=(res["gan"] == "home").astype(float))
        res = res.assign(p_lado=np.where(res["p_home"] >= 0.5, res["p_home"], 1 - res["p_home"]),
                         ok=np.where(res["p_home"] >= 0.5, res["real_home"], 1 - res["real_home"]))
        lo, hi = wilson(res["ok"].sum(), len(res))
        print(f"   a {x}: {len(o)} partidos con serie en vivo; {len(res)} con ganador claro ({len(res) / len(o):.0%}); "
              f"alguien llegó {o['gan'].notna().mean():.0%} (modelo {o['algun'].mean():.0%}); "
              f"lado más probable acierta {res['ok'].mean():.3f} [{lo:.3f};{hi:.3f}], anuncia {res['p_lado'].mean():.3f}; "
              f"local gana {res['real_home'].mean():.3f}, modelo {res['p_home'].mean():.3f}")
        top = res.sort_values("p_lado", ascending=False).head(max(1, len(res) // 10))
        print(f"        10 % más seguro: n {len(top)}, acierto {top['ok'].mean():.3f}, anuncia {top['p_lado'].mean():.3f}")


def primeros_10(ev: pd.DataFrame, tk: pd.DataFrame, puente: pd.DataFrame, partidos: pd.DataFrame, d: Path, dp: Path) -> None:
    fin = ev[ev["estado"].astype(str).eq("3") & ev["gl_h"].notna()].merge(puente[["bid", "match_id"]], on="bid")
    v = tk[tk["corners_vivo"].notna() & tk["minuto"].between(8, 10)].sort_values(["bid", "t"]).groupby("bid").tail(1)
    c = par(v["corners_vivo"]); v = v.assign(c10=c["a"] + c["b"], min10=v["minuto"]).merge(fin[["bid", "match_id"]], on="bid")
    v = v.dropna(subset=["c10"])
    pk = partidos.set_index("match_id")["kickoff_utc"]
    cl = pd.read_csv(d / "pred_corners_lado.csv.gz").query("variante == 'c2_yip'").set_index("match_id")
    pc = cl.filter(regex=r"^p\d+$"); mt = (pc * np.arange(pc.shape[1])).sum(1).rename("mt")
    v = v.join(mt, on="match_id")
    v["kick"] = v["match_id"].map(pk)
    print("\n=== Córner en los primeros 10 minutos (lectura entre el minuto 8 y 10)")
    # la serie de córners en vivo solo existe desde 2024-07: se calibra con la primera temporada y se evalúa en la siguiente
    corte = pd.Timestamp("2025-07-01", tz="UTC")
    v = v.dropna(subset=["mt"])
    ent, pru = v[v["kick"] < corte], v[v["kick"] >= corte]
    print(f"   lecturas con predicción: calibración {len(ent)} (2024-07 a 2025-06), evaluación {len(pru)}")
    print(f"   base real: ≥ 1 córner en los 10 primeros minutos {(v['c10'] >= 1).mean():.3f}")
    s = float(ent["c10"].sum() / ent["mt"].sum()) if len(ent) else np.nan
    print(f"   parte de los córners que cae en los primeros 10 minutos (calibración): {s:.3f}")
    if len(pru):
        p = 1 - np.exp(-pru["mt"] * s)
        y = (pru["c10"] >= 1).astype(float)
        lo, hi = wilson(y.sum(), len(pru))
        base_ent = float((ent["c10"] >= 1).mean())
        print(f"   evaluación: anuncia {p.mean():.3f}, ocurre {y.mean():.3f} [{lo:.3f};{hi:.3f}]; Brier modelo {((p - y) ** 2).mean():.4f} "
              f"frente a tasa base de la calibración {((base_ent - y) ** 2).mean():.4f}")
        top = pd.DataFrame({"p": p, "y": y}).sort_values("p", ascending=False).head(max(1, len(pru) // 10))
        print(f"   10 % más seguro: n {len(top)}, anuncia {top['p'].mean():.3f}, ocurre {top['y'].mean():.3f}")
    # tarjetas en los primeros 10 minutos (incidencias)
    from qf.eval import rediseno as R
    datos = R.cargar(d)
    inc = datos.incidencias
    tarj = inc[inc["subtipo"].eq("card")].merge(partidos[["match_id", "kickoff_utc"]], on="match_id")
    previo = tarj[tarj["kickoff_utc"] < EVAL]
    s_card = float((previo["minuto"] <= 10).mean())
    n10 = tarj[tarj["minuto"] <= 10].groupby("match_id").size()
    con_inc = set(inc["match_id"])
    py = pd.read_csv(dp / "pred_f4_yellow.csv.gz").query("variante == 't3_dawson'").set_index("match_id")
    pyp = py.filter(regex=r"^p\d+$"); my = (pyp * np.arange(pyp.shape[1])).sum(1).rename("my")
    z = partidos[(partidos["kickoff_utc"] >= EVAL) & partidos["match_id"].isin(con_inc)].set_index("match_id").join(my, how="inner")
    z["y"] = z.index.map(lambda m: float(n10.get(m, 0) >= 1))
    p = 1 - np.exp(-z["my"] * 1.06 * s_card)  # +6 % por las rojas (≈ 0,15 por partido sobre ≈ 4 amarillas… solo ritmo)
    lo, hi = wilson(z["y"].sum(), len(z))
    print(f"\n   Tarjeta en los primeros 10 minutos: parte de las tarjetas (antes de 2024-07) {s_card:.3f}; evaluación n {len(z)}: "
          f"anuncia {p.mean():.3f}, ocurre {z['y'].mean():.3f} [{lo:.3f};{hi:.3f}]")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", default=".local/betsapi_futbol")
    ap.add_argument("--datos", default=".local/rediseno_20261101b")
    ap.add_argument("--pred", default=".local/rediseno_20261101")
    ap.add_argument("--sufijo", default="")
    a = ap.parse_args()
    raiz, d, dp = Path(a.raiz), Path(a.datos), Path(a.pred)
    ev, tk, puente = (pd.read_csv(raiz / f"eventos{a.sufijo}.csv.gz"), pd.read_csv(raiz / f"ticks{a.sufijo}.csv.gz", low_memory=False),
                      pd.read_csv(raiz / f"puente{a.sufijo}.csv.gz"))
    partidos = pd.read_csv(d / "partidos.csv.gz", parse_dates=["kickoff_utc"])
    corners_en_vivo(raiz, ev, tk, puente, partidos)
    carrera(ev, tk, puente, partidos, d)
    primeros_10(ev, tk, puente, partidos, d, dp)


if __name__ == "__main__":
    main()
