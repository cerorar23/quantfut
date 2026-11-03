"""
Cuotas reales de bet365 (archivo de BetsAPI, ago-2023 → oct-2026, 9 ligas) frente a los modelos: acierto con cuota ≥ 1,28,
a T-60 y al cierre, por mercado.

    PYTHONPATH=src python scripts/rediseno_futbol/betsapi_cuotas.py --raiz .local/betsapi_futbol \
        --datos .local/rediseno_20261101b --pred .local/rediseno_20261101

Fases (cada una guarda su resultado en `--raiz` y se salta si ya existe):
  1. lectura de los 9 × ~1.100 archivos → eventos.csv.gz y ticks.csv.gz
  2. emparejamiento con `matches` (hora, marcador, nombres) → puente.csv.gz
  3. opciones a T-60 y al cierre con la liquidación real y las probabilidades de bet365 (sin margen) y del motor
Solo lectura de archivos locales. Muestra desde 2024-07-01 (el motor no tiene predicciones fuera de muestra antes).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from qf.eval import rediseno_betsapi as B
from qf.eval.rediseno_acierto import calibracion_alta, seleccion_diaria, wilson
from qf.eval.rediseno_mercados import adelgazar, matrices_mitades, pmf_diferencia, pmf_suma
from qf.model.calibration import score_matrices
from qf.model.devig import devig

EVAL = pd.Timestamp("2024-07-01", tz="UTC")
CUOTA_MIN = 1.40  # decisión del titular (2-nov-2026); --cuota-min la cambia


def fase1(raiz: Path, ligas: list[str], suf: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    ev_p, tk_p = raiz / f"eventos{suf}.csv.gz", raiz / f"ticks{suf}.csv.gz"
    if ev_p.exists() and tk_p.exists():
        return pd.read_csv(ev_p), pd.read_csv(tk_p, low_memory=False)
    eventos, ticks = [], []
    for liga in ligas:
        archivos = sorted((raiz / liga / "odds").glob("*.json.gz"))
        for f in archivos:
            r = B.leer_evento(f)
            if r is None:
                continue
            eventos.append({**r[0], "liga": liga}); ticks += r[1]
        print(f"{liga}: {len(archivos)} archivos", flush=True)
    ev, tk = pd.DataFrame(eventos), pd.DataFrame(ticks)
    ev.to_csv(ev_p, index=False); tk.to_csv(tk_p, index=False)
    return ev, tk


def fase2(raiz: Path, ev: pd.DataFrame, partidos: pd.DataFrame, suf: str) -> pd.DataFrame:
    ruta = raiz / f"puente{suf}.csv.gz"
    if ruta.exists():
        return pd.read_csv(ruta)
    ev = ev[ev["estado"].astype(str).eq("3") & ev["gl_h"].notna()]
    puente = B.emparejar(ev, partidos)
    puente.to_csv(ruta, index=False)
    return puente


def p_sin_margen(fila: pd.Series, mercado: str) -> dict[str, float]:
    if mercado in ("1x2", "descanso"):
        v = fila[["home_od", "draw_od", "away_od"]].to_numpy(float)
        if np.isnan(v).any() or (v <= 1).any():
            return {}
        q = devig(v, "shin")
        return {"home": q[0], "draw": q[1], "away": q[2]}
    if mercado in ("ah", "ah_1t"):
        v = fila[["home_od", "away_od"]].to_numpy(float); lados = ("home", "away")
    else:
        v = fila[["over_od", "under_od"]].to_numpy(float); lados = ("over", "under")
    if np.isnan(v).any() or (v <= 1).any():
        return {}
    q = (1 / v) / (1 / v).sum()
    return dict(zip(lados, q))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", default=".local/betsapi_futbol")
    ap.add_argument("--datos", default=".local/rediseno_20261101b")
    ap.add_argument("--pred", default=".local/rediseno_20261101")
    ap.add_argument("--cuota-min", type=float, default=1.40, help="cuota mínima de las opciones publicables")
    ap.add_argument("--ligas", default=",".join(B.LIGAS), help="subconjunto de ligas, separadas por coma")
    ap.add_argument("--sufijo", default="", help="sufijo de los archivos de caché si se usa un subconjunto")
    a = ap.parse_args()
    global CUOTA_MIN
    CUOTA_MIN = a.cuota_min
    raiz, d, dp = Path(a.raiz), Path(a.datos), Path(a.pred)
    partidos = pd.read_csv(d / "partidos.csv.gz", parse_dates=["kickoff_utc"])
    ev, tk = fase1(raiz, a.ligas.split(","), a.sufijo)
    print("eventos", len(ev), "ticks", len(tk))
    puente = fase2(raiz, ev, partidos, a.sufijo)
    fin = ev[ev["estado"].astype(str).eq("3") & ev["gl_h"].notna()]
    emp = fin.merge(puente, on="bid", how="left")
    print("\nEmparejamiento por liga (partidos terminados):")
    print(emp.groupby("liga").agg(eventos=("bid", "size"), emparejados=("match_id", lambda s: s.notna().mean())).round(3).to_string())
    print(f"similitud media {puente['similitud'].mean():.2f}; sin marcador igual {(~puente['con_marcador']).sum()}")
    rp = partidos.set_index("match_id")
    chk = emp.dropna(subset=["match_id"]).join(rp[["home_corners", "away_corners", "home_goals_ht", "away_goals_ht"]], on="match_id")
    ok_c = ((chk["cor_h"] == chk["home_corners"]) & (chk["cor_a"] == chk["away_corners"]))
    ok_ht = ((chk["ht_h"] == chk["home_goals_ht"]) & (chk["ht_a"] == chk["away_goals_ht"]))
    print(f"córners de BetsAPI = córners de nuestra tabla en {ok_c.mean():.1%} (de {chk['home_corners'].notna().sum()}); "
          f"goles al descanso en {ok_ht.mean():.1%}")
    print("córners de 1.ª parte: media BetsAPI", round((chk['cor1t_h'] + chk['cor1t_a']).mean(), 2),
          "frente a total", round((chk['cor_h'] + chk['cor_a']).mean(), 2))

    # --- probabilidades del motor (fuera de muestra, desde 2024-07)
    pred = pd.read_csv(dp / "pred_f3.csv.gz").query("modelo == 'a0_xg'").set_index("match_id")
    cl = pd.read_csv(d / "pred_corners_lado.csv.gz").query("variante == 'c2_yip'").set_index("match_id")
    rec = d / "pred_conteos_recientes.csv.gz"
    if rec.exists():
        cl = pd.concat([cl, pd.read_csv(rec).query("variante == 'c2_yip'").set_index("match_id")]).groupby(level=0).first()
    previo = partidos[partidos["kickoff_utc"] < EVAL].merge(emp[["match_id", "cor1t_h", "cor1t_a", "cor_h", "cor_a"]],
                                                              on="match_id")
    antes = partidos[partidos["kickoff_utc"] < EVAL].dropna(subset=["home_goals_ht"])
    f1_liga = (antes.assign(g1=antes["home_goals_ht"] + antes["away_goals_ht"], g=antes["home_goals"] + antes["away_goals"])
               .groupby("league_id")[["g1", "g"]].sum().pipe(lambda x: x["g1"] / x["g"]))
    s_corner_1t = float((previo["cor1t_h"] + previo["cor1t_a"]).sum() / (previo["cor_h"] + previo["cor_a"]).sum())
    print("f1 goles por liga", f1_liga.round(3).to_dict(), "| parte de córners en la 1.ª", round(s_corner_1t, 3))

    k0 = fin.set_index("bid")["kickoff"]
    objetos = {}
    for nombre, antes in (("T-60", 3600), ("cierre", 0)):
        s = B.instantaneas(tk, k0, antes)
        s = s.merge(puente[["bid", "match_id"]], on="bid").merge(partidos[["match_id", "league_id", "kickoff_utc", "home_goals",
                                                                          "away_goals", "home_goals_ht", "away_goals_ht"]], on="match_id")
        s = s.merge(fin[["bid", "cor_h", "cor_a", "cor1t_h", "cor1t_a"]], on="bid")
        s = s[s["kickoff_utc"] >= EVAL]
        filas = []
        cache = {}
        for r in s.itertuples(index=False):
            fila = pd.Series(r._asdict())
            mid, mk = fila["match_id"], fila["mercado"]
            q = p_sin_margen(fila, mk)
            if not q:
                continue
            ls = B.lineas(fila["linea"]) if mk not in ("1x2", "descanso") else []
            if mk not in ("1x2", "descanso") and (len(ls) != 1):
                continue  # líneas de cuarto aparte
            hg, ag, h1, a1 = fila["home_goals"], fila["away_goals"], fila["home_goals_ht"], fila["away_goals_ht"]
            c_tot, c_1t = fila["cor_h"] + fila["cor_a"], fila["cor1t_h"] + fila["cor1t_a"]
            # matrices del motor
            if mid not in cache:
                M = m1 = None
                if mid in pred.index:
                    f = pred.loc[mid]
                    M = score_matrices(np.array([f["lam"]]), np.array([f["mu"]]), float(f["rho"]))
                    m1 = matrices_mitades(np.array([f["lam"]]), np.array([f["mu"]]), f1_liga.get(fila["league_id"], 0.44))[0]
                Pc = cl.loc[mid].filter(regex=r"^p\d+$").to_numpy(float) if mid in cl.index else None
                cache[mid] = (M, m1, Pc)
            M, m1, Pc = cache[mid]
            sel = []
            if mk in ("1x2", "descanso"):
                cuotas = {"home": fila["home_od"], "draw": fila["draw_od"], "away": fila["away_od"]}
                gh, ga = (hg, ag) if mk == "1x2" else (h1, a1)
                real = "home" if gh > ga else "draw" if gh == ga else "away"
                mat = M if mk == "1x2" else m1
                pm = {}
                if mat is not None:
                    dif, sop = pmf_diferencia(mat)
                    pm = {"home": dif[0, sop > 0].sum(), "draw": dif[0, sop == 0].sum(), "away": dif[0, sop < 0].sum()}
                for lado, cu in cuotas.items():
                    sel.append((lado, 0.0, cu, "gana" if lado == real else "pierde", pm.get(lado, np.nan), q[lado], np.nan))
            elif mk in ("ah", "ah_1t"):
                gh, ga = (hg, ag) if mk == "ah" else (h1, a1)
                mat = M if mk == "ah" else m1
                for lado, cu in (("home", fila["home_od"]), ("away", fila["away_od"])):
                    res = B.liquidar_handicap(gh - ga, ls, lado)
                    pg = pp = np.nan
                    if mat is not None:
                        dif, sop = pmf_diferencia(mat)
                        pg = B.p_handicap(dif[0], sop, ls, lado)
                        pp = B.p_handicap(dif[0], sop, ls, "away" if lado == "home" else "home")  # pierde = gana el rival
                    sel.append((lado, ls[0], cu, res, pg / (pg + pp) if pg == pg and pg + pp > 0 else np.nan, q[lado], np.nan))
            else:
                valor, pmf = {"goles": (hg + ag, None if M is None else pmf_suma(M)[0]),
                              "goles_1t": (h1 + a1, None if m1 is None else pmf_suma(m1)[0]),
                              "corners": (c_tot, Pc),
                              "corners_1t": (c_1t, None if Pc is None else adelgazar(Pc[None], s_corner_1t)[0])}[mk]
                for lado, cu, dire in (("over", fila["over_od"], "mas"), ("under", fila["under_od"], "menos")):
                    res = B.liquidar_total(valor, ls, dire)
                    pm = np.nan
                    if pmf is not None and np.isfinite(pmf).all():
                        pg = B.p_total(pmf, ls, dire)
                        pp = B.p_total(pmf, ls, "menos" if dire == "mas" else "mas")
                        pm = pg / (pg + pp) if pg + pp > 0 else np.nan
                    sel.append((lado, ls[0], cu, res, pm, q[lado], np.nan))
            for lado, ln, cu, res, pmo, pme, _ in sel:
                if res in ("gana", "pierde") and cu > 1:
                    filas.append({"match_id": mid, "liga": fila["league_id"], "mercado": mk, "seleccion": lado, "linea": ln,
                                  "cuota": cu, "acierto": float(res == "gana"), "motor": pmo, "casa": pme,
                                  "kickoff_utc": fila["kickoff_utc"]})
        o = pd.DataFrame(filas)
        o["dia"] = o["kickoff_utc"].dt.strftime("%Y-%m-%d")
        o.to_csv(raiz / f"opciones_{nombre.replace('-', '')}{a.sufijo}.csv.gz", index=False)
        objetos[nombre] = o
        print(f"\n######## {nombre}: {o['match_id'].nunique()} partidos, {len(o)} opciones sin cuartos; "
              f"cuota ≥ {CUOTA_MIN}: {(o['cuota'] >= CUOTA_MIN).mean():.1%}")
        informe(o)


def informe(o: pd.DataFrame) -> None:
    x = o[o["cuota"] >= CUOTA_MIN]
    print(f"\n   Por mercado: la opción más probable de cada partido con cuota ≥ {CUOTA_MIN}")
    filas = []
    for mk, g in x.groupby("mercado"):
        for fuente in ("casa", "motor"):
            y = g[g[fuente].notna()]
            m = y.sort_values(fuente, ascending=False).drop_duplicates("match_id")
            lo, hi = wilson(m["acierto"].sum(), len(m))
            filas.append({"mercado": mk, "fuente": fuente, "n": len(m), "acierto": m["acierto"].mean(), "ic95": f"[{lo:.3f};{hi:.3f}]",
                          "anuncia": m[fuente].mean(), "cuota": m["cuota"].mean()})
    print(pd.DataFrame(filas).round(3).to_string(index=False))
    print("\n   Todos los mercados juntos, 10 % / 30 % / 100 % más probable de cada día:")
    for fuente in ("casa", "motor"):
        y = x[x[fuente].notna()]
        m = y.sort_values(fuente, ascending=False).drop_duplicates("match_id")
        s = seleccion_diaria(m.assign(prob=m[fuente]), coberturas=(0.1, 0.3, 1.0))
        print(f"   [{fuente}]"); print(s.round(3).to_string(index=False))
        print(calibracion_alta(y[fuente].to_numpy(), y["acierto"].to_numpy(), cortes=(0.5, 0.6, 0.7, 0.8, 1.0001)).round(3).to_string(index=False))
    z = x[x["casa"].notna() & x["motor"].notna()]
    print("\n   Desacuerdo motor − casa:")
    for lo, hi in [(-1, -0.05), (-0.05, 0.05), (0.05, 1)]:
        w = z[((z["motor"] - z["casa"]) > lo) & ((z["motor"] - z["casa"]) <= hi)]
        print(f"   ({lo},{hi}]: n {len(w)}, motor {w['motor'].mean():.3f}, casa {w['casa'].mean():.3f}, real {w['acierto'].mean():.3f}")


if __name__ == "__main__":
    main()
