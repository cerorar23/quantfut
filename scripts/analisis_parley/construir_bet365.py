"""Candidatos de fútbol con cuotas bet365 de BetsAPI (t60) y tenis prematch.

Entrada: los CSV que exportan los scripts de `vps/` (solo lectura del VPS):
  fb_betsapi_t60.csv   (exportar_futbol_bet365_t60.sql)
  tn_prematch.csv      (exportar_tenis_bet365.py)
Salida en QF_PARLEY_OUT (por defecto ./salida): cands_b365.parquet y, por
pantalla, las tablas de calibración por tramo de cuota. Investigación.

Solo se usan líneas .5 (sin empate posible: saberlo exigiría el resultado) y
el cierre de la pareja de cuotas de la propia casa como probabilidad sin margen.
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(os.environ.get("QF_PARLEY_OUT", Path(__file__).parent / "salida"))
OUT.mkdir(parents=True, exist_ok=True)
BINS = [1.0, 1.2, 1.5, 1.8, 2.1, 2.5, 3.5, 20]


def tramos(df: pd.DataFrame, por: list[str], precio: str = "price_best", minimo: int = 40) -> pd.DataFrame:
    df = df.assign(tr=pd.cut(df[precio], BINS))
    df = df.dropna(subset=["tr"])
    df["roi"] = df.win * df[precio] - 1
    g = df.groupby(por + ["tr"], observed=True).agg(
        n=("win", "size"), p=("p", "mean"), acierto=("win", "mean"), roi=("roi", "mean")).reset_index()
    g["dif_pp"] = (g.acierto - g.p) * 100
    return g[g.n >= minimo]


def futbol() -> pd.DataFrame:
    d = pd.read_csv(OUT / "fb_betsapi_t60.csv")
    d = d[d.cuota > 1].copy()
    d["date"] = pd.to_datetime(d.kickoff_utc.str[:10])
    d["gd"] = d.home_goals - d.away_goals
    d["tg"] = d.home_goals + d.away_goals
    d["gd1"] = d.home_goals_ht - d.away_goals_ht
    d["tg1"] = d.home_goals_ht + d.away_goals_ht
    d["tc"] = d.home_corners + d.away_corners
    partes: list[pd.DataFrame] = []

    def out(df, market, sel, cuota, p, win):
        partes.append(pd.DataFrame({
            "sport": "futbol_b365", "market": market, "mid": "fb|" + df.match_id.values,
            "date": df.date.values, "sel": sel, "price_best": cuota, "price_ref": cuota,
            "p": p, "win": np.asarray(win).astype(int)}))

    for mk, col, name in [("h2h", "gd", "1X2 bet365"), ("h2h_1t", "gd1", "1T 1X2 bet365")]:
        x = d[d.mercado == mk]
        w = x.pivot_table(index="match_id", columns="seleccion", values="cuota", aggfunc="first").dropna()
        p = (1 / w).div((1 / w).sum(axis=1), axis=0)
        meta = x.drop_duplicates("match_id").set_index("match_id").loc[w.index]
        for sel, val in [("home", 1), ("draw", 0), ("away", -1)]:
            out(meta.reset_index(), name, sel, w[sel].values, p[sel].values, np.sign(meta[col]).values == val)

    def dos_lados(mk, cond, name, sels=("over", "under"), base=None):
        x = (base if base is not None else d)
        x = x[x.mercado == mk]
        a = x[x.seleccion == sels[0]].set_index("match_id")
        b = x[x.seleccion == sels[1]].set_index("match_id")
        idx = a.index.intersection(b.index)
        a, b = a.loc[idx], b.loc[idx]
        ok = np.isclose(a.linea.abs() % 1, 0.5)
        a, b = a[ok], b[ok]
        pa = (1 / a.cuota) / ((1 / a.cuota) + (1 / b.cuota))
        w = cond(a).values
        out(a.reset_index(), name, sels[0], a.cuota.values, pa.values, w)
        out(a.reset_index(), name, sels[1], b.cuota.values, 1 - pa.values, ~w)

    dos_lados("totals", lambda a: a.tg > a.linea, "Goles O/U (linea .5) bet365")
    dos_lados("totals_1t", lambda a: a.tg1 > a.linea, "1T goles O/U (linea .5) bet365")
    dos_lados("corners", lambda a: a.tc > a.linea, "Corners O/U (linea .5) bet365", base=d[d.tc.notna()])
    dos_lados("spreads", lambda a: (a.gd + a.linea) > 0, "Handicap asiatico .5 bet365", ("home", "away"))
    dos_lados("spreads_1t", lambda a: (a.gd1 + a.linea) > 0, "1T handicap .5 bet365", ("home", "away"))
    F = pd.concat(partes, ignore_index=True)
    return F[np.isfinite(F.p) & (F.p > 0) & (F.p < 1)]


def tenis() -> pd.DataFrame:
    """Solo eventos capturados antes del inicio (`upd` <= `time`): 45 % de los exportados."""
    t = pd.read_csv(OUT / "tn_prematch.csv")
    t = t[(t.upd <= t.time) & (t.odds > 1)]
    filas = []

    def dos(name, ev, a, b, gana_a):
        pa = (1 / a.odds) / ((1 / a.odds) + (1 / b.odds))
        filas.append((name, ev, a.odds, pa, gana_a))
        filas.append((name, ev, b.odds, 1 - pa, not gana_a))

    for ev, g in t.groupby("event"):
        r = g.iloc[0]
        m = g[g.market == "winner"]
        if len(m) == 2:
            dos("Ganador (bet365)", ev, m[m.sel == "1"].iloc[0], m[m.sel == "2"].iloc[0], r.hs > r.as_)
        for linea, gg in g[g.market == "total_games"].groupby("line"):
            o, u = gg[gg.sel == "Over"], gg[gg.sel == "Under"]
            if len(o) == 1 and len(u) == 1 and abs(float(linea) % 1 - 0.5) < 1e-9:
                dos("Juegos totales (bet365)", ev, o.iloc[0], u.iloc[0], (r.hg + r.ag) > float(linea))
        m = g[g.market == "hcp_games"]
        for _, h in m[m.sel == "1"].iterrows():
            ln = float(str(h["line"]).replace("+", ""))
            if abs(ln % 1 - 0.5) > 1e-9:
                continue
            c = m[(m.sel == "2") & (m["line"].astype(str).str.replace("+", "").astype(float) == -ln)]
            if len(c) == 1:
                dos("Handicap de juegos (bet365)", ev, h, c.iloc[0], (r.hg - r.ag + ln) > 0)
    d = pd.DataFrame(filas, columns=["market", "ev", "price_best", "p", "win"])
    d["win"] = d.win.astype(int)
    return d


if __name__ == "__main__":
    F = futbol()
    F.to_parquet(OUT / "cands_b365.parquet")
    print(tramos(F, ["market"], minimo=150).round(3).to_string(index=False))
    print(tramos(tenis(), ["market"]).round(3).to_string(index=False))
