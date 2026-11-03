"""Evaluación del Sprint 4 (props de jugador): puntos, rebotes, asistencias y triples contra el cierre de The Odds API.

    python apps/nba/ops/evaluar_s4.py CARPETA [temporada_prueba=2025-26]

CARPETA: s3_juegos.csv, s3b_jugadores.csv, s3b_partidos.csv, players.jsonl.gz, s4_props.csv.gz (ver evaluar_s3/evaluar_s3b).
Todo hacia adelante: la tasa de cada jugador usa solo sus partidos anteriores. Prior por rol, sobredispersión, residuos de minutos
y (k, decaimiento) se fijan con temporadas anteriores a la de prueba. Las casas anulan la apuesta si no juega: se evalúa condicionado a jugar.
"""
import csv
from collections import defaultdict
import gzip
import itertools
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import evaluar_s3 as e3  # noqa: E402
from nba.v2 import equipos, minutos, props  # noqa: E402

V = 30                                            # partidos de historia que se guardan por fila
E = len(props.ESTADISTICAS)
CLAVES = ("points", "rebounds", "assists", "threes")
MERCADO = {"player_points": 0, "player_rebounds": 1, "player_assists": 2, "player_threes": 3}
CASAS = ("fanduel", "draftkings", "betmgm", "betonlineag")
N_MIN = 25                                        # muestras de minutos por fila


def construir_filas(carpeta, juegos):
    par, jug, canon_j, canon_p = {}, {}, {}, {}
    for r in csv.DictReader(open(carpeta / "s3b_partidos.csv", encoding="utf8")):
        canon_p[int(r["entidad_id"])] = int(r["canonica_id"])
        if r["fuente"] == "nba_oficial" and r["id_en_fuente"].isdigit():
            par[r["id_en_fuente"]] = int(r["canonica_id"])
    for r in csv.DictReader(open(carpeta / "s3b_jugadores.csv", encoding="utf8")):
        canon_j[int(r["entidad_id"])] = int(r["canonica_id"])
        if r["fuente"] == "nba_oficial" and r["id_en_fuente"].isdigit():
            jug[int(r["id_en_fuente"])] = int(r["canonica_id"])
    por_pid = {g["pid"]: g for g in juegos}
    cajas = defaultdict(list)
    with gzip.open(carpeta / "players.jsonl.gz", "rt", encoding="utf8") as f:
        for linea in f:
            r = json.loads(linea)
            pid, jid = par.get(r["game_id"]), jug.get(r["player_id"])
            if pid in por_pid and jid is not None and r.get("participated") and r.get("minutes"):
                cajas[pid].append((jid, float(r["minutes"]), [float(r.get(c) or 0) for c in CLAVES]))
    hist_m, hist_s = defaultdict(list), defaultdict(list)
    filas = defaultdict(list)
    for g in juegos:
        for jid, m, s in cajas.get(g["pid"], ()):
            if len(hist_m[jid]) >= 5 and g["temporada"] >= "2022-23":
                n = min(V, len(hist_m[jid]))
                mh = np.full(V, np.nan)
                sh = np.full((E, V), np.nan)
                mh[-n:] = hist_m[jid][-n:]
                sh[:, -n:] = np.array(hist_s[jid][-n:]).T
                filas["pid"].append(g["pid"]); filas["jid"].append(jid); filas["temp"].append(g["temporada"])
                filas["m"].append(m); filas["y"].append(s); filas["mh"].append(mh); filas["sh"].append(sh)
                filas["mp"].append(minutos.punto(hist_m[jid]))
        for jid, m, s in cajas.get(g["pid"], ()):
            hist_m[jid].append(m)
            hist_s[jid].append(s)
    d = {k: np.array(v) for k, v in filas.items() if k not in ("temp",)}
    d["temp"] = np.array(filas["temp"])
    return d, canon_p, canon_j


def leer_props(carpeta, canon_p, canon_j, pids):
    crudo = defaultdict(lambda: defaultdict(dict))
    with gzip.open(carpeta / "s4_props.csv.gz", "rt", encoding="utf8") as f:
        for r in csv.DictReader(f):
            pid = canon_p.get(int(r["partido_id"]))
            if pid not in pids or r["mercado"] not in MERCADO:
                continue
            clave = (pid, canon_j.get(int(r["entidad_id"]), int(r["entidad_id"])), MERCADO[r["mercado"]])
            crudo[clave][r["casa"]].setdefault(float(r["linea"]), {})[r["lado"]] = float(r["cuota"])
    salida = {}
    for clave, casas in crudo.items():
        for casa in CASAS:
            if casa not in casas:
                continue
            cand = [(abs(1 / v["over"] - 1 / v["under"]), l, v) for l, v in casas[casa].items() if "over" in v and "under" in v]
            if cand:
                _, l, v = min(cand, key=lambda x: x[0])
                q_o, q_u = 1 / v["over"], 1 / v["under"]
                salida[clave] = (l, q_o / (q_o + q_u), casa)
                break
    return salida


def muestras_minutos(mp, residuos):
    return minutos.muestras_condicionadas(mp, residuos, N_MIN)


def main(carpeta, prueba):
    juegos, _ = e3.leer(carpeta)
    filas, canon_p, canon_j = construir_filas(carpeta, juegos)
    temp = filas["temp"]
    mp = filas["mp"].astype(float)
    print(f"{len(mp)} filas jugador-partido desde 2022-23")

    def residuos_de(mask):
        return minutos.ajustar_residuos(zip(mp[mask], filas["m"][mask]))

    # 1) rejilla (k, decaimiento) por error absoluto relativo en 2023-24 y 2024-25, con todo lo demás ajustado antes
    entren = temp < "2023-24"
    valid = (temp >= "2023-24") & (temp < prueba)
    res_v = residuos_de(entren)
    prior_v = props.prior_por_nivel(mp[entren], filas["m"][entren], filas["y"][entren])
    mean_min_v = muestras_minutos(mp[valid], res_v).mean(axis=1)
    base5 = np.nanmean(filas["sh"][valid][:, :, -5:], axis=2)
    mae5 = np.abs(filas["y"][valid] - base5).mean(axis=0)
    mejor = None
    for k, dec in itertools.product((30.0, 100.0, 300.0), (0.85, 0.93, 0.97)):
        tasa = props.tasa_por_minuto(filas["mh"][valid], filas["sh"][valid], prior_v[props.nivel(mp[valid])], k, dec)
        rel = (np.abs(filas["y"][valid] - tasa * mean_min_v[:, None]).mean(axis=0) / mae5)
        print(f"k={k:5.0f} dec={dec}: MASE puntos {rel[0]:.3f} reb {rel[1]:.3f} ast {rel[2]:.3f} 3p {rel[3]:.3f}")
        if mejor is None or rel.mean() < mejor[0]:
            mejor = (rel.mean(), k, dec)
    _, k, dec = mejor
    print(f"elegido k={k} decaimiento={dec}")

    # 2) ajuste final con todo lo anterior a la prueba
    entren = temp < prueba
    prueba_m = temp == prueba
    res = residuos_de(entren)
    prior = props.prior_por_nivel(mp[entren], filas["m"][entren], filas["y"][entren])
    tasa_e = props.tasa_por_minuto(filas["mh"][entren], filas["sh"][entren], prior[props.nivel(mp[entren])], k, dec)
    alfas = [props.estimar_alfa(tasa_e[:, s] * filas["m"][entren], filas["y"][entren][:, s]) for s in range(E)]
    print("alfa (sobredispersión):", dict(zip(props.ESTADISTICAS, np.round(alfas, 3))))

    tasa_t = props.tasa_por_minuto(filas["mh"][prueba_m], filas["sh"][prueba_m], prior[props.nivel(mp[prueba_m])], k, dec)
    muestras = muestras_minutos(mp[prueba_m], res)
    y = filas["y"][prueba_m]
    base5 = np.nanmean(filas["sh"][prueba_m][:, :, -5:], axis=2)
    pids, jids, mps = filas["pid"][prueba_m], filas["jid"][prueba_m], mp[prueba_m]
    lineas = leer_props(carpeta, canon_p, canon_j, set(pids.tolist()))
    informe = {"k": k, "decaimiento": dec, "alfa": dict(zip(props.ESTADISTICAS, alfas)), "n_filas_prueba": int(prueba_m.sum()), "stats": {}}

    for s, nombre in enumerate(props.ESTADISTICAS):
        techo = props.TECHO[nombre]
        pmf = np.vstack([props.pmf_mezcla(tasa_t[i:i + 4000, s], muestras[i:i + 4000], alfas[s], techo)
                         for i in range(0, len(y), 4000)])
        mu = tasa_t[:, s] * muestras.mean(axis=1)
        pit = props.pit_aleatorio(pmf, y[:, s], semilla=s)
        tr = np.array([minutos.tramo(x) for x in mps])
        sesgo = {f"tramo{t}": float((y[tr == t, s] - mu[tr == t]).mean() / y[tr == t, s].mean()) for t in range(3)}
        r = {"n": len(y), "MASE": float(np.abs(y[:, s] - mu).mean() / np.abs(y[:, s] - base5[:, s]).mean()),
             "cobertura80": float(np.mean((pit > 0.1) & (pit < 0.9))), "sesgo_relativo_por_minutos": sesgo}
        # contra la línea de cierre de la casa de referencia
        idx = [i for i in range(len(y)) if (pids[i], jids[i], s) in lineas and lineas[(pids[i], jids[i], s)][0] % 1 != 0]
        if idx:
            idx = np.array(idx)
            linea = np.array([lineas[(pids[i], jids[i], s)][0] for i in idx])
            p_mer = np.array([lineas[(pids[i], jids[i], s)][1] for i in idx])
            p_mod = props.prob_mas_de(pmf[idx], linea)
            pmf5 = props.pmf_mezcla(np.maximum(base5[idx, s], 0.05), np.ones((len(idx), 1)), alfas[s], techo)
            p_b5 = props.prob_mas_de(pmf5, linea)
            res_y = (y[idx, s] > linea).astype(float)
            pend, inter = e3.pendiente_calibracion(p_mod, res_y)
            d_m, lo, hi = e3.ic_diferencia(p_mod, p_mer, res_y)
            r["linea"] = {"n": len(idx), "logloss_modelo": e3.logloss(p_mod, res_y), "logloss_mercado": e3.logloss(p_mer, res_y),
                          "logloss_media5": e3.logloss(p_b5, res_y), "brier_modelo": e3.brier(p_mod, res_y),
                          "brier_mercado": e3.brier(p_mer, res_y), "brier_media5": e3.brier(p_b5, res_y),
                          "dif_brier_vs_mercado": d_m, "ic95": [lo, hi], "pendiente": pend, "intercepto": inter}
        informe["stats"][nombre] = r
        ln = r.get("linea", {})
        print(f"{nombre:12s} MASE {r['MASE']:.3f} cob80 {r['cobertura80']:.3f} sesgo {list(sesgo.values())[0]:+.3f}/{list(sesgo.values())[1]:+.3f}/{list(sesgo.values())[2]:+.3f}"
              f" | n línea {ln.get('n')} LL mod {ln.get('logloss_modelo', 0):.4f} mer {ln.get('logloss_mercado', 0):.4f} b5 {ln.get('logloss_media5', 0):.4f}"
              f" | Brier dif {ln.get('dif_brier_vs_mercado', 0):+.4f} {np.round(ln.get('ic95', [0, 0]), 4)} pend {ln.get('pendiente', 0):.2f}")
    (carpeta / "informe_s4.json").write_text(json.dumps(informe, indent=1, ensure_ascii=False), encoding="utf8")


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "2025-26")
