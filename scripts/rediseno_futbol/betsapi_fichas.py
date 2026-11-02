"""
Fichas prematch de bet365 (BetsAPI, partidos del 23-25 oct-2026): ¿qué mercados de las listas traen cuota y cumple el
porcentaje de la casa? Mercados con resultado calculable: ambos marcan 1.ª parte, resultado al descanso, doble
oportunidad al descanso, gol / córner / tarjeta en los primeros 10 minutos, tarjetas del partido, ambos equipos
reciben tarjeta y equipo marca en cada mitad.

    PYTHONPATH=src python scripts/rediseno_futbol/betsapi_fichas.py --raiz .local/betsapi_futbol \
        --datos .local/rediseno_20261101b --pred .local/rediseno_20261101 --sufijo _eu

Las fichas se descargaron DESPUÉS de los partidos (`fetched_at`), pero los precios son de antes del saque (p. ej. 1X2
1,91/2,60/6,00 en un partido que acabó 5-0); la hora exacta de captura no se conoce. Solo lectura de archivos locales.
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from qf.eval import rediseno as R
from qf.eval import rediseno_betsapi as B
from qf.eval.rediseno_acierto import wilson
from qf.eval.rediseno_mercados import matrices_mitades, pmf_diferencia
from qf.model.calibration import score_matrices
from qf.model.devig import devig


def leer_fichas(raiz: Path, ligas: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    evs, filas = [], []
    for liga in ligas:
        for f in sorted((raiz / liga / "prematch").glob("*.json.gz")):
            try:
                j = json.load(gzip.open(f))
            except (OSError, ValueError):
                continue
            p = j.get("prematch") or {}
            p = p.get("results", p)
            p = p[0] if isinstance(p, list) and p else p
            ev = j.get("event") or {}
            if not isinstance(p, dict) or not ev.get("time"):
                continue
            ss = str(ev.get("ss") or "").split("-")
            evs.append({"bid": int(ev["id"]), "liga": liga, "kickoff": int(ev["time"]), "home": (ev.get("home") or {}).get("name"),
                        "away": (ev.get("away") or {}).get("name"), "gl_h": B.numero(ss[0]) if len(ss) == 2 else np.nan,
                        "gl_a": B.numero(ss[1]) if len(ss) == 2 else np.nan, "fetched_at": int(j.get("fetched_at") or 0)})
            for sec, v in p.items():
                if not (isinstance(v, dict) and "sp" in v):
                    continue
                for k, m in v["sp"].items():
                    if isinstance(m, dict) and m.get("odds"):
                        for o in m["odds"]:
                            filas.append({"bid": int(ev["id"]), "mercado": f"{sec}/{k}", "nombre": o.get("name"),
                                          "header": o.get("header"), "linea": o.get("handicap"), "equipo": o.get("team"),
                                          "cuota": B.numero(o.get("odds"))})
    return pd.DataFrame(evs), pd.DataFrame(filas)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", default=".local/betsapi_futbol")
    ap.add_argument("--datos", default=".local/rediseno_20261101b")
    ap.add_argument("--pred", default=".local/rediseno_20261101")
    ap.add_argument("--ligas", default=",".join(B.LIGAS))
    ap.add_argument("--sufijo", default="")
    a = ap.parse_args()
    raiz, d, dp = Path(a.raiz), Path(a.datos), Path(a.pred)
    partidos = pd.read_csv(d / "partidos.csv.gz", parse_dates=["kickoff_utc"])
    ev, fi = leer_fichas(raiz, a.ligas.split(","))
    puente = B.emparejar(ev[ev["gl_h"].notna()], partidos)
    ev = ev.merge(puente[["bid", "match_id"]], on="bid")
    print(f"fichas {len(ev)}: con partido emparejado {ev['match_id'].notna().sum()}; "
          f"horas entre el saque y la captura: mediana {np.median((ev['fetched_at'] - ev['kickoff']) / 3600):.0f}")
    cnt = fi.groupby("mercado")["bid"].nunique().sort_values(ascending=False)
    print("\nMercados con cuota en las fichas (partidos):")
    print(cnt.head(60).to_string())

    datos = R.cargar(d)
    inc = datos.incidencias
    con_inc = set(inc["match_id"])
    g10 = set(inc[inc["subtipo"].eq("goal") & ~inc["anulada"].fillna(False).astype(bool) & (inc["minuto"] <= 10)]["match_id"])
    t10 = set(inc[inc["subtipo"].eq("card") & (inc["minuto"] <= 10)]["match_id"])
    # córners en los primeros 10 minutos desde la serie en vivo de las cuotas
    tkp = raiz / f"ticks{a.sufijo}.csv.gz"
    c10 = {}
    if tkp.exists():
        tk = pd.read_csv(tkp, low_memory=False)
        v = tk[tk["corners_vivo"].notna() & tk["minuto"].between(8, 10)].sort_values(["bid", "t"]).groupby("bid").tail(1)
        cc = v["corners_vivo"].astype(str).str.split("-", expand=True)
        c10 = dict(zip(v["bid"], pd.to_numeric(cc[0], errors="coerce") + pd.to_numeric(cc[1], errors="coerce")))
    pr = partidos.set_index("match_id")
    pred = pd.read_csv(dp / "pred_f3.csv.gz").query("modelo == 'a0_xg'").set_index("match_id")

    filas = []
    for e in ev.itertuples(index=False):
        if e.match_id not in pr.index:
            continue
        m = pr.loc[e.match_id]
        hg, ag, h1, a1 = m["home_goals"], m["away_goals"], m["home_goals_ht"], m["away_goals_ht"]
        sub = fi[fi["bid"] == e.bid]
        motor = {}
        if e.match_id in pred.index:
            f = pred.loc[e.match_id]
            m1 = matrices_mitades(np.array([f["lam"]]), np.array([f["mu"]]), 0.44)[0]
            dif, sop = pmf_diferencia(m1)
            motor = {"btts1t": float(m1[0, 1:, 1:].sum()), "ht": {"1": dif[0, sop > 0].sum(), "Draw": dif[0, sop == 0].sum(), "2": dif[0, sop < 0].sum()},
                     "g10": 1 - np.exp(-(f["lam"] + f["mu"]) * 0.0818)}

        def grupo(clave, nombres, resultados, etiquetas, mp=None):
            g = sub[sub["mercado"] == clave]
            if g.empty or pd.isna(h1) and "1t" in etiquetas:
                return
            cu = [g[g["nombre"] == n]["cuota"].mean() for n in nombres]
            if any(pd.isna(c) or c <= 1 for c in cu):
                return
            q = devig(np.array(cu), "shin") if len(cu) == 3 else (1 / np.array(cu)) / (1 / np.array(cu)).sum()
            for i, (n, c) in enumerate(zip(nombres, cu)):
                filas.append({"match_id": e.match_id, "mercado": etiquetas, "seleccion": n, "cuota": c, "casa": q[i],
                              "motor": (mp or {}).get(n, np.nan), "acierto": float(resultados == n)})

        if pd.notna(h1):
            res_ht = "1" if h1 > a1 else "Draw" if h1 == a1 else "2"
            grupo("half/half_time_result", ["1", "Draw", "2"], res_ht, "descanso 1X2", motor.get("ht"))
            grupo("goals/both_teams_to_score_in_1st_half", ["Yes", "No"], "Yes" if (h1 > 0 and a1 > 0) else "No", "ambos marcan 1T",
                  {"Yes": motor["btts1t"], "No": 1 - motor["btts1t"]} if motor else None)
            # equipo marca en cada mitad (equipo 1 = local)
            tm = sub[sub["mercado"] == "half/to_score_in_half"]
            for equipo, gh1, gh2 in (("1", h1, hg - h1), ("2", a1, ag - a1)):
                for mitad, gm in (("1st Half", gh1), ("2nd Half", gh2)):
                    g = tm[(tm["equipo"] == equipo) & (tm["nombre"] == mitad)]
                    y, n_ = g[g["header"] == "Yes"]["cuota"], g[g["header"] == "No"]["cuota"]
                    if len(y) and len(n_) and y.iloc[0] > 1 and n_.iloc[0] > 1:
                        q = (1 / np.array([y.iloc[0], n_.iloc[0]])) / (1 / np.array([y.iloc[0], n_.iloc[0]])).sum()
                        for i, (s, c) in enumerate((("Yes", y.iloc[0]), ("No", n_.iloc[0]))):
                            filas.append({"match_id": e.match_id, "grupo": equipo, "mercado": f"equipo marca en la {mitad[:1]}.ª parte", "seleccion": s,
                                          "cuota": c, "casa": q[i], "motor": np.nan, "acierto": float((gm > 0) == (s == "Yes"))})
        if e.match_id in con_inc:
            g = sub[(sub["mercado"] == "goals/first_10_minutes_(00:00_09:59)") & (sub["linea"].astype(str) == "0.5")]
            for nombre, hecho, etq in (("Goals", e.match_id in g10, "gol en los primeros 10 min"),
                                       ("Cards", e.match_id in t10, "tarjeta en los primeros 10 min"),
                                       ("Corners", (c10.get(e.bid, np.nan) >= 1) if e.bid in c10 else None, "córner en los primeros 10 min")):
                if hecho is None or (isinstance(hecho, float) and np.isnan(hecho)):
                    continue
                o_, u_ = g[(g["nombre"] == nombre) & (g["header"] == "Over")]["cuota"], g[(g["nombre"] == nombre) & (g["header"] == "Under")]["cuota"]
                if len(o_) and len(u_) and o_.iloc[0] > 1 and u_.iloc[0] > 1:
                    q = (1 / np.array([o_.iloc[0], u_.iloc[0]])) / (1 / np.array([o_.iloc[0], u_.iloc[0]])).sum()
                    for i, (s, c) in enumerate((("Over", o_.iloc[0]), ("Under", u_.iloc[0]))):
                        filas.append({"match_id": e.match_id, "mercado": etq, "seleccion": s, "cuota": c, "casa": q[i],
                                      "motor": (motor["g10"] if s == "Over" else 1 - motor["g10"]) if (motor and nombre == "Goals") else np.nan,
                                      "acierto": float(bool(hecho) == (s == "Over"))})
            tarj = m["home_yellow"] + m["away_yellow"] + m["home_red"] + m["away_red"]
            g = sub[sub["mercado"] == "cards_fouls/number_of_cards_in_match"]
            for ln, gg in g.groupby("nombre"):
                o_, u_ = gg[gg["header"] == "Over"]["cuota"], gg[gg["header"] == "Under"]["cuota"]
                if len(o_) and len(u_) and pd.notna(tarj):
                    q = (1 / np.array([o_.iloc[0], u_.iloc[0]])) / (1 / np.array([o_.iloc[0], u_.iloc[0]])).sum()
                    for i, (s, c) in enumerate((("Over", o_.iloc[0]), ("Under", u_.iloc[0]))):
                        filas.append({"match_id": e.match_id, "mercado": "tarjetas del partido (cualquier línea)", "seleccion": s, "cuota": c,
                                      "casa": q[i], "motor": np.nan, "acierto": float((tarj > float(ln)) == (s == "Over"))})
            g = sub[sub["mercado"] == "cards_fouls/both_teams_to_receive_cards"]
            y, n_ = g[(g["nombre"] == "a Card") & (g["header"] == "Yes")]["cuota"], g[(g["nombre"] == "a Card") & (g["header"] == "No")]["cuota"]
            if len(y) and len(n_):
                ambos = (m["home_yellow"] + m["home_red"] > 0) and (m["away_yellow"] + m["away_red"] > 0)
                q = (1 / np.array([y.iloc[0], n_.iloc[0]])) / (1 / np.array([y.iloc[0], n_.iloc[0]])).sum()
                for i, (s, c) in enumerate((("Yes", y.iloc[0]), ("No", n_.iloc[0]))):
                    filas.append({"match_id": e.match_id, "mercado": "ambos equipos reciben tarjeta", "seleccion": s, "cuota": c, "casa": q[i],
                                  "motor": np.nan, "acierto": float(ambos == (s == "Yes"))})
    o = pd.DataFrame(filas)
    o.to_csv(raiz / f"fichas_opciones{a.sufijo}.csv.gz", index=False)
    print("\nMercado | partidos | margen medio | casa anuncia / ocurre (todas las opciones) | opción más probable: acierto, anuncia, cuota"
          " | ≥1,28: n, acierto, anuncia")
    for mk, g in o.groupby("mercado"):
        n_p = g["match_id"].nunique()
        marg = (g.assign(i=1 / g["cuota"]).groupby(["match_id", g["grupo"].fillna("")])["i"].sum() - 1).mean()
        mejor = g.sort_values("casa", ascending=False).drop_duplicates("match_id")
        x = mejor[mejor["cuota"] >= 1.28]
        lo, hi = wilson(mejor["acierto"].sum(), len(mejor))
        print(f"{mk:44s} {n_p:4d} partidos | margen {marg:.3f} | todas: {g['casa'].mean():.3f}/{g['acierto'].mean():.3f} | más probable: "
              f"{mejor['acierto'].mean():.3f} [{lo:.2f};{hi:.2f}] anuncia {mejor['casa'].mean():.3f} cuota {mejor['cuota'].mean():.2f} | "
              f"≥1,28: n {len(x)} {x['acierto'].mean() if len(x) else np.nan:.3f} anuncia {x['casa'].mean() if len(x) else np.nan:.3f}")


if __name__ == "__main__":
    main()
