"""Tabla única de candidatos (fútbol, tenis, NBA y props): cuota, p sin margen y resultado.

Parte del análisis de topes de cuota del parley (2026-11-06). Informe y tablas:
docs/parley_topes_medicion_20261106.md. Investigación: no publica ni cambia
ningún motor. Las salidas van a QF_PARLEY_OUT (por defecto ./salida).
"""
import os
from pathlib import Path
import glob, gzip, json, math
import numpy as np, pandas as pd

P = str(Path(__file__).resolve().parents[2]) + "/"
OUT = os.environ.get("QF_PARLEY_OUT", str(Path(__file__).parent / "salida")) + "/"
os.makedirs(OUT, exist_ok=True)
cols = ["sport", "market", "mid", "date", "sel", "price_best", "price_ref", "p", "win"]
parts = []

def devig2(a, b):
    ia, ib = 1 / a, 1 / b
    s = ia + ib
    return ia / s, ib / s

def devig3(a, b, c):
    ia, ib, ic = 1 / a, 1 / b, 1 / c
    s = ia + ib + ic
    return ia / s, ib / s, ic / s

def frame(sport, market, mid, date, sel, pb, pr, p, win):
    return pd.DataFrame({"sport": sport, "market": market, "mid": mid, "date": pd.to_datetime(date),
                         "sel": sel, "price_best": pb, "price_ref": pr, "p": p, "win": win.astype(int)})

# ---------------- FUTBOL ----------------
fs = sorted(glob.glob(P + ".local/fd_cache/*_*.csv"))
def _leer(f):
    x = pd.read_csv(f, encoding="latin-1", on_bad_lines="skip")
    x.columns = [c.replace("ï»¿", "").replace("﻿", "") for c in x.columns]
    return x
d = pd.concat([_leer(f) for f in fs], ignore_index=True)
d["date"] = pd.to_datetime(d["Date"], dayfirst=True, errors="coerce")
d = d.dropna(subset=["date", "FTR", "FTHG", "FTAG"]).drop_duplicates(["Div", "date", "HomeTeam", "AwayTeam"])
d["mid"] = "fb|" + d.Div + "|" + d.HomeTeam + "|" + d.AwayTeam + "|" + d.date.dt.strftime("%Y%m%d")
d["tot"] = d.FTHG + d.FTAG
d["gd"] = d.FTHG - d.FTAG

x = d[d[["PSH", "PSD", "PSA", "B365H", "B365D", "B365A", "MaxH", "MaxD", "MaxA"]].notna().all(axis=1)]
x = x[(x[["PSH", "PSD", "PSA", "B365H", "B365D", "B365A", "MaxH", "MaxD", "MaxA"]] > 1).all(axis=1)]
ph, pdw, pa = devig3(x.PSH.values, x.PSD.values, x.PSA.values)
for sel, p, c in [("1", ph, "H"), ("X", pdw, "D"), ("2", pa, "A")]:
    parts.append(frame("futbol", "1X2", x.mid, x.date, sel, x["Max" + c].values, x["B365" + c].values, p,
                       (x.FTR.values == c)))
cc = ["P>2.5", "P<2.5", "B365>2.5", "B365<2.5", "Max>2.5", "Max<2.5"]
y = d[d[cc].notna().all(axis=1)]
y = y[(y[cc] > 1).all(axis=1)]
po, pu = devig2(y["P>2.5"].values, y["P<2.5"].values)
parts.append(frame("futbol", "Goles O/U 2.5", y.mid, y.date, "Over", y["Max>2.5"].values, y["B365>2.5"].values, po, y.tot.values > 2.5))
parts.append(frame("futbol", "Goles O/U 2.5", y.mid, y.date, "Under", y["Max<2.5"].values, y["B365<2.5"].values, pu, y.tot.values < 2.5))
cc = ["AHh", "PAHH", "PAHA", "B365AHH", "B365AHA", "MaxAHH", "MaxAHA"]
z = d[d[cc].notna().all(axis=1)]
z = z[(z[cc[1:]] > 1).all(axis=1)]
z = z[np.isclose((z.AHh.abs() % 1), 0.5)]  # solo lineas .5: sin push ni cuartos
ph_, pa_ = devig2(z.PAHH.values, z.PAHA.values)
cover_h = (z.gd.values + z.AHh.values) > 0
parts.append(frame("futbol", "Handicap asiatico .5", z.mid, z.date, "Local", z.MaxAHH.values, z.B365AHH.values, ph_, cover_h))
parts.append(frame("futbol", "Handicap asiatico .5", z.mid, z.date, "Visitante", z.MaxAHA.values, z.B365AHA.values, pa_, ~cover_h))

# ---------------- TENIS ----------------
t = pd.read_parquet(P + "data/tennis/tennis_data_manual_processed/odds_matched.parquet")
t = t[t["Comment"].astype(str).str.contains("Completed", na=False)]
cc = ["PSW", "PSL", "B365W", "B365L", "MaxW", "MaxL"]
for c_ in cc:
    t[c_] = pd.to_numeric(t[c_], errors="coerce")
t = t[t[cc].notna().all(axis=1)]
t = t[(t[cc] > 1).all(axis=1)]
t["date"] = pd.to_datetime(t["Date"], errors="coerce")
t = t.dropna(subset=["date"])
t["mid"] = "tn|" + t.match_id.astype(str)
pw, pl_ = devig2(t.PSW.values, t.PSL.values)
for sel, p, pb, pr, win in [("Ganador", pw, t.MaxW.values, t.B365W.values, np.ones(len(t), bool)),
                            ("Perdedor", pl_, t.MaxL.values, t.B365L.values, np.zeros(len(t), bool))]:
    parts.append(frame("tenis", "Ganador del partido", t.mid, t.date, sel, pb, pr, p, win))
# Los dos lados de cada partido: el nombre de seleccion no revela el resultado (solo el flag win).

# ---------------- NBA: mercados de partido ----------------
rows = []
with gzip.open(P + "apps/nba/.local/normalized/nba_betsapi_odds_20261024/odds.jsonl.gz", "rt", encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)
        tip = pd.Timestamp(r["tip_utc"])
        # ultima foto con >= 60 min antes del salto (hora de decision de la regla NBA)
        snaps = [s for s in r["path"] if s[0] >= 3600 and s[2] and s[3]]
        if not snaps:
            continue
        s = min(snaps, key=lambda q: q[0])  # la mas cercana al salto con >=60 min
        sec, ln, a, b = s
        hp, ap = r.get("home_points"), r.get("away_points")
        if hp is None or ap is None:
            continue
        kind, mk, per = r["kind"], r["market"], r["period"]
        if kind == "moneyline":
            if hp == ap:
                continue
            w1 = hp > ap
            lab = ("Local", "Visitante")
        elif kind == "spread":
            if ln is None or abs(ln % 1) != 0.5:
                continue
            w1 = (hp - ap + ln) > 0
            lab = ("Local", "Visitante")
        elif kind == "total":
            if ln is None or abs(ln % 1) != 0.5:
                continue
            w1 = (hp + ap) > ln
            lab = ("Over", "Under")
        else:
            continue
        if not (a > 1 and b > 1):
            continue
        p1, p2 = devig2(a, b)
        fam = {"ml": "Ganador", "spread": "Handicap", "total": "Total puntos"}[mk.split("_")[0]] + {"game": " partido", "h1": " 1a mitad", "q1": " 1er cuarto"}[per]
        mid = "nba|" + r["game_id"]
        rows.append((fam, mid, tip.normalize().tz_localize(None), lab[0], a, a, p1, w1))
        rows.append((fam, mid, tip.normalize().tz_localize(None), lab[1], b, b, p2, not w1))
g = pd.DataFrame(rows, columns=["market", "mid", "date", "sel", "price_best", "price_ref", "p", "win"])
g.insert(0, "sport", "nba")
g["win"] = g.win.astype(int)
parts.append(g[cols])
tipdate = {}
for r in rows:
    tipdate[r[1][4:]] = r[2]

# ---------------- NBA: props de jugador ----------------
pr = pd.read_json(P + "apps/nba/.local/normalized/nba_props_odds_20261024/props_linked.jsonl.gz", lines=True, compression="gzip")
pr = pr[(pr.participated == True) & pr.actual.notna() & pr.player_id.notna() & pr.over.notna() & pr.under.notna()]
pr = pr[(pr.over > 1) & (pr.under > 1) & ((pr.line % 1).round(3) == 0.5)]
pr["po"], pr["pu"] = devig2(pr.over.values, pr.under.values)
pr["lo"] = np.log(pr.po / (1 - pr.po))
key = ["game_id", "market", "player_id", "line"]
agg = pr.groupby(key).agg(nb=("book", "nunique"), lo=("lo", "mean"), ob=("over", "max"), oref=("over", "median"),
                          ub=("under", "max"), uref=("under", "median"), actual=("actual", "first"),
                          snap=("snapshot_utc", "first")).reset_index()
agg = agg[agg.nb >= 2]
agg["pcon"] = 1 / (1 + np.exp(-agg.lo))
agg["mid"] = "nba|" + agg.game_id.astype(str)
agg["date"] = pd.to_datetime(agg.snap).dt.tz_convert("UTC").dt.normalize().dt.tz_localize(None)
agg["date"] = [tipdate.get(g_, d_) for g_, d_ in zip(agg.game_id.astype(str), agg.date)]
name = {"player_points": "Props puntos jugador", "player_rebounds": "Props rebotes jugador",
        "player_assists": "Props asistencias jugador", "player_threes": "Props triples jugador"}
agg["mk"] = agg.market.map(name)
over_win = agg.actual > agg.line
parts.append(frame("nba", "", agg.mid, agg.date, "Over", agg.ob.values, agg.oref.values, agg.pcon.values, over_win.values).assign(market=agg.mk.values))
parts.append(frame("nba", "", agg.mid, agg.date, "Under", agg.ub.values, agg.uref.values, 1 - agg.pcon.values, (~over_win).values).assign(market=agg.mk.values))

C = pd.concat(parts, ignore_index=True)[cols]
C = C[(C.price_best > 1) & np.isfinite(C.price_best)]
C.to_parquet(OUT + "cands.parquet")
print(C.groupby(["sport", "market"]).agg(n=("win", "size"), ev=("mid", "nunique"), d0=("date", "min"), d1=("date", "max")).to_string())
