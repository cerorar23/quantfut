"""Evaluación de «jugadores en el núcleo» (Sprint 3b): impacto por jugador × minutos esperados frente al rating de equipo.

    python apps/nba/ops/evaluar_s3b.py CARPETA [temporada_prueba=2025-26]

CARPETA debe tener los CSV de evaluar_s3.py más: s3b_jugadores.csv, s3b_partidos.csv (alias de ids exportados de `nba_datos`),
s2_estados.csv (partes oficiales) y players.jsonl.gz (caja por jugador con `team_id`, copia del archivo histórico cargado).
Todo hacia adelante: el impacto se reajusta cada 21 días solo con partidos anteriores; los minutos esperados de cada partido salen de
la plantilla reciente, el último parte y los minutos previos del jugador. Hiperparámetros y desviaciones, solo con temporadas < prueba.
"""
import csv
from collections import defaultdict, deque
from datetime import date
import gzip
import itertools
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import evaluar_s3 as e3  # noqa: E402
from nba.v2 import equipos, mercados, minutos, nucleo, plantilla  # noqa: E402
from nba.v2.nucleo import Parametros  # noqa: E402
from nba.v2.plantilla import PartidoFila  # noqa: E402

BLOQUE_DIAS = 21
VENTANA_EQUIPO = 10                       # partidos recientes del equipo que definen quién es candidato
TRAMOS = (15.0, 25.0)


def tramo(m):
    return int(sum(m >= c for c in TRAMOS))


def leer_cajas(carpeta, por_pid):
    par, jug, canon_j, canon_p = {}, {}, {}, {}
    with open(carpeta / "s3b_partidos.csv", encoding="utf8") as f:
        for r in csv.DictReader(f):
            canon_p[int(r["entidad_id"])] = int(r["canonica_id"])
            if r["fuente"] == "nba_oficial" and r["id_en_fuente"].isdigit():
                par[r["id_en_fuente"]] = int(r["canonica_id"])
    with open(carpeta / "s3b_jugadores.csv", encoding="utf8") as f:
        for r in csv.DictReader(f):
            canon_j[int(r["entidad_id"])] = int(r["canonica_id"])
            if r["fuente"] == "nba_oficial" and r["id_en_fuente"].isdigit():
                jug[int(r["id_en_fuente"])] = int(r["canonica_id"])
    cajas = defaultdict(lambda: {"local": defaultdict(float), "visit": defaultdict(float)})
    global HIST_PM
    HIST_PM = defaultdict(list)
    with gzip.open(carpeta / "players.jsonl.gz", "rt", encoding="utf8") as f:
        for linea in f:
            r = json.loads(linea)
            if not r.get("participated") or not r.get("minutes"):
                continue
            pid = par.get(r["game_id"])
            g = por_pid.get(pid)
            jid = jug.get(r["player_id"])
            tri = equipos.NBA_IDS.get(r["team_id"])
            if g is None or jid is None or tri is None:
                continue
            lado = "local" if tri == g["local"] else "visit" if tri == g["visit"] else None
            if lado:
                cajas[pid][lado][jid] += float(r["minutes"])
                if r.get("plus_minus") is not None:
                    HIST_PM[jid].append((g["dia"], float(r["minutes"]), float(r["plus_minus"])))
    estados = {}
    with open(carpeta / "s2_estados.csv", encoding="utf8") as f:
        for r in csv.DictReader(f):
            clave = (canon_p.get(int(r["partido_id"]), int(r["partido_id"])), canon_j.get(int(r["jugador_id"]), int(r["jugador_id"])))
            if clave not in estados or r["hora_parte"] > estados[clave][0]:
                estados[clave] = (r["hora_parte"], r["estado"])
    por_partido = defaultdict(dict)
    for (pid, j), (_, est) in estados.items():
        por_partido[pid][j] = est
    return cajas, por_partido


def registrar_candidatos(juegos, cajas, estados):
    """Una pasada cronológica: quién podía jugar cada partido, sus minutos previos y su último parte (solo información previa)."""
    hist, ultimo_eq = defaultdict(list), {}
    recientes = defaultdict(lambda: deque(maxlen=VENTANA_EQUIPO))
    registros = {}
    for g in juegos:
        caja = cajas.get(g["pid"])
        if caja is None:
            continue
        reg = {}
        for lado in ("local", "visit"):
            eq = g[lado]
            cand = {j for s in recientes[eq] for j in s if ultimo_eq.get(j) == eq}
            cand |= {j for j in estados.get(g["pid"], {}) if ultimo_eq.get(j) == eq and hist[j]}
            lista = []
            for j in sorted(cand):
                mh = minutos.punto(hist[j])
                if mh is None:
                    mh = float(np.mean(hist[j]))
                lista.append((j, mh, estados.get(g["pid"], {}).get(j), j in caja[lado]))
            reg[lado] = lista
        registros[g["pid"]] = reg
        for lado in ("local", "visit"):
            for j, m in caja[lado].items():
                hist[j].append(m)
                ultimo_eq[j] = g[lado]
            recientes[g[lado]].append(set(caja[lado]))
    return registros


def tablas_p_juega(juegos, registros, hasta):
    """P(jugó) por estado y, sin parte, por tramo de minutos esperados; medidas con temporadas < `hasta`."""
    por_estado, sin_parte = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    for g in juegos:
        if g["temporada"] >= hasta or g["pid"] not in registros:
            continue
        for lado in ("local", "visit"):
            for _, mh, est, jugo in registros[g["pid"]][lado]:
                c = por_estado[est] if est is not None else sin_parte[tramo(mh)]
                c[0] += 1
                c[1] += int(jugo)
    est = {k: v[1] / v[0] for k, v in por_estado.items() if v[0] >= 30}
    sp = {k: v[1] / v[0] for k, v in sin_parte.items() if v[0] >= 30}
    return est, sp


def minutos_del_partido(reg, tabla_estado, tabla_sin_parte):
    salida = {}
    for lado in ("local", "visit"):
        cand = {}
        for j, mh, est, _ in reg[lado]:
            p = tabla_estado.get(est, 0.84) if est is not None else tabla_sin_parte.get(tramo(mh), 0.84)
            cand[j] = (mh, p)
        salida[lado] = plantilla.minutos_esperados(cand)
    return salida


HIST_PM = {}
_CACHE_PRIOR = {}


def prior_en(corte, c, n0=1500.0, vida=730.0):
    """Impacto previo = c × (más/menos por 48 minutos con decaimiento) encogido por minutos acumulados; solo partidos < corte."""
    if corte not in _CACHE_PRIOR:
        crudo = {}
        for j, lst in HIST_PM.items():
            w = [(0.5 ** ((corte - d) / vida), m, pm) for d, m, pm in lst if d < corte]
            mins = sum(a * m for a, m, _ in w)
            if mins > 0:
                crudo[j] = (48.0 * sum(a * pm for a, _, pm in w) / mins, mins)
        _CACHE_PRIOR[corte] = crudo
    return {j: c * v * m / (m + n0) for j, (v, m) in _CACHE_PRIOR[corte].items()}


def predecir_bloques(filas, esperados, juegos_eval, lam, vida, dias_bloque_ini, descansos, c_prior=0.0):
    """Predice margen y total de cada partido de `juegos_eval` con impacto reajustado cada BLOQUE_DIAS días."""
    pred = {}
    inicios = sorted({dias_bloque_ini + BLOQUE_DIAS * ((g["dia"] - dias_bloque_ini) // BLOQUE_DIAS) for g in juegos_eval})
    por_bloque = defaultdict(list)
    for g in juegos_eval:
        por_bloque[dias_bloque_ini + BLOQUE_DIAS * ((g["dia"] - dias_bloque_ini) // BLOQUE_DIAS)].append(g)
    for ini in inicios:
        imp = plantilla.ajustar(filas, lam, lam, vida, dia_corte=ini, prior_beta=prior_en(ini, c_prior) if c_prior else None)
        for g in por_bloque[ini]:
            e = esperados[g["pid"]]
            d = descansos[g["pid"]]
            pred[g["pid"]] = (imp.margen(e["local"], e["visit"], d), imp.total(e["local"], e["visit"], d))
    return pred


def mu_de(margen, total):
    return (total + margen) / 2, (total - margen) / 2


def variante(nombre, mus, pruebas, cierres, sig_m, sig_t, n_sim=10000):
    ys, cols = defaultdict(lambda: defaultdict(list)), None
    for g in pruebas:
        mu = mus.get(g["pid"])
        c = cierres.get(g["pid"])
        if mu is None or not c or "h2h" not in c:
            continue
        m = nucleo.simular(mu[0], mu[1], sig_m, sig_t, n=n_sim, semilla=g["pid"])
        margen = g["pl"] - g["pv"]
        ys["ganador"]["p"].append(mercados.ganador(m))
        ys["ganador"]["m"].append(e3.desvig(c["h2h"]["local"], c["h2h"]["visit"]))
        ys["ganador"]["y"].append(1.0 if margen > 0 else 0.0)
        if "spread_linea" in c and c["spread_linea"] % 1 != 0 and "spread" in c:
            ys["handicap"]["p"].append(mercados.handicap(m, c["spread_linea"]))
            ys["handicap"]["m"].append(e3.desvig(c["spread"]["local"], c["spread"]["visit"]))
            ys["handicap"]["y"].append(1.0 if margen + c["spread_linea"] > 0 else 0.0)
            ys["rmse"]["margen_mod"].append(mu[0] - mu[1])
            ys["rmse"]["margen_mer"].append(-c["spread_linea"])
            ys["rmse"]["margen_y"].append(margen)
        if "total_linea" in c and c["total_linea"] % 1 != 0 and "total" in c:
            ys["total"]["p"].append(mercados.total(m, c["total_linea"]))
            ys["total"]["m"].append(e3.desvig(c["total"]["over"], c["total"]["under"]))
            ys["total"]["y"].append(1.0 if g["pl"] + g["pv"] > c["total_linea"] else 0.0)
            ys["rmse"]["total_mod"].append(mu[0] + mu[1])
            ys["rmse"]["total_mer"].append(c["total_linea"])
            ys["rmse"]["total_y"].append(g["pl"] + g["pv"])
    r = ys["rmse"]
    salida = {"nombre": nombre,
              "rmse_margen": e3.rmse(r["margen_mod"], r["margen_y"]), "rmse_margen_mercado": e3.rmse(r["margen_mer"], r["margen_y"]),
              "rmse_total": e3.rmse(r["total_mod"], r["total_y"]), "rmse_total_mercado": e3.rmse(r["total_mer"], r["total_y"])}
    for k in ("ganador", "handicap", "total"):
        d = ys[k]
        pend, inter = e3.pendiente_calibracion(np.array(d["p"]), d["y"])
        dif, lo, hi = e3.ic_diferencia(d["p"], d["m"], d["y"])
        salida[k] = dict(n=len(d["y"]), brier=e3.brier(d["p"], d["y"]), brier_mercado=e3.brier(d["m"], d["y"]),
                         pendiente=pend, dif=dif, ic95=[lo, hi])
    return salida


def main(carpeta, prueba):
    juegos, cierres = e3.leer(carpeta)
    p_nucleo = Parametros(eta=0.045, arrastre=0.65, eta_liga=0.01, efecto_b2b=2.78)
    mus_nucleo = e3.recorrer(juegos, p_nucleo)                    # también deja j["dias"]
    por_pid = {g["pid"]: g for g in juegos}
    for g in juegos:
        g["dia"] = date.fromisoformat(g["fecha"]).toordinal()
    cajas, estados = leer_cajas(carpeta, por_pid)
    print(f"{len(cajas)} partidos con caja de {len(juegos)}; partes en {len(estados)} partidos")
    registros = registrar_candidatos(juegos, cajas, estados)
    tabla_estado, tabla_sp = tablas_p_juega(juegos, registros, "2023-24")
    print("P(juega) por estado:", {k: round(v, 3) for k, v in tabla_estado.items()})
    print("P(juega) sin parte por tramo de minutos:", {k: round(v, 3) for k, v in tabla_sp.items()})
    esperados = {pid: minutos_del_partido(reg, tabla_estado, tabla_sp) for pid, reg in registros.items()}
    reales = {pid: {lado: dict(cajas[pid][lado]) for lado in ("local", "visit")} for pid in registros}
    descansos = {}
    for g, mu in zip(juegos, mus_nucleo):
        descansos[g["pid"]] = (1.0 if g["dias"]["visit"] == 1 else 0.0) - (1.0 if g["dias"]["local"] == 1 else 0.0)
    filas = [PartidoFila(g["dia"], g["pl"] - g["pv"], g["pl"] + g["pv"], reales[g["pid"]]["local"], reales[g["pid"]]["visit"],
                         descansos[g["pid"]]) for g in juegos if g["pid"] in reales]

    temporadas = sorted({g["temporada"] for g in juegos})
    ajuste = [t for t in temporadas if t < prueba]
    validar = set(ajuste[-2:])
    primero_eval = min(g["dia"] for g in juegos if g["temporada"] == ajuste[1])
    evaluables = [g for g in juegos if g["pid"] in registros and g["temporada"] >= ajuste[1]]
    val = [g for g in evaluables if g["temporada"] in validar]

    mejor = None
    for lam, vida in itertools.product((3.0, 5.0, 10.0, 20.0), (365.0, 730.0, 1500.0)):
        pred = predecir_bloques(filas, esperados, val, lam, vida, primero_eval, descansos)
        em = e3.rmse([pred[g["pid"]][0] for g in val], [g["pl"] - g["pv"] for g in val])
        et = e3.rmse([pred[g["pid"]][1] for g in val], [g["pl"] + g["pv"] for g in val])
        print(f"lam={lam:5.0f} vida={vida:5.0f} -> RMSE margen {em:.3f} total {et:.3f}")
        if mejor is None or em < mejor[0]:                    # el total de jugadores se compara aparte con el del equipo
            mejor = (em, lam, vida, em, et)
    _, lam, vida, em_val, et_val = mejor
    c_prior = 0.0
    for c, lam2 in itertools.product((0.3, 0.6, 1.0), (10.0, 20.0, 40.0)):
        pr = predecir_bloques(filas, esperados, val, lam2, vida, primero_eval, descansos, c)
        em = e3.rmse([pr[g["pid"]][0] for g in val], [g["pl"] - g["pv"] for g in val])
        et = e3.rmse([pr[g["pid"]][1] for g in val], [g["pl"] + g["pv"] for g in val])
        print(f"prior c={c} lam={lam2:.0f} -> RMSE margen {em:.3f} total {et:.3f}")
        if em < em_val:
            em_val, et_val, lam, c_prior = em, et, lam2, c
    print(f"con prior: c={c_prior} lam={lam}; validación margen {em_val:.3f}")
    print(f"elegido: lam={lam} vida={vida}; validación RMSE margen {em_val:.3f}, total {et_val:.3f}")

    # predicciones de todo lo evaluable con los parámetros elegidos (honestas y con minutos reales como techo)
    pred = predecir_bloques(filas, esperados, evaluables, lam, vida, primero_eval, descansos, c_prior)
    techo = predecir_bloques(filas, reales, evaluables, lam, vida, primero_eval, descansos, c_prior)
    nuc = {g["pid"]: m for g, m in zip(juegos, mus_nucleo)}
    res = [g for g in evaluables if g["temporada"] in validar]
    sig_m = float(np.std([(g["pl"] - g["pv"]) - pred[g["pid"]][0] for g in res]))
    sig_t = float(np.std([(g["pl"] + g["pv"]) - pred[g["pid"]][1] for g in res]))
    sig_t_eq = float(np.std([(g["pl"] + g["pv"]) - (mus_nucleo[i][0] + mus_nucleo[i][1])
                             for i, g in enumerate(juegos) if g["pid"] in registros and g["temporada"] in validar]))
    print(f"sigma margen {sig_m:.3f}, sigma total {sig_t:.3f} (validación)")

    # peso de mezcla con la línea del mercado y con el rating de equipo, medidos en validación
    def lin(pid):
        c = cierres.get(pid, {})
        return -c["spread_linea"] if "spread_linea" in c else None

    vv = [g for g in res if lin(g["pid"]) is not None]
    X = np.array([[pred[g["pid"]][0], nuc[g["pid"]][0] - nuc[g["pid"]][1], lin(g["pid"])] for g in vv])
    w = np.linalg.lstsq(X, np.array([g["pl"] - g["pv"] for g in vv]), rcond=None)[0]
    print(f"pesos del margen (jugadores, equipo, mercado) en validación: {w.round(3)}")

    pruebas = [g for g in evaluables if g["temporada"] == prueba]
    mus = {
        "jugadores": {g["pid"]: mu_de(*pred[g["pid"]]) for g in pruebas},
        "jugadores_techo_minutos_reales": {g["pid"]: mu_de(*techo[g["pid"]]) for g in pruebas},
        "equipo": {g["pid"]: nuc[g["pid"]] for g in pruebas},
        "margen_jugadores_total_equipo": {g["pid"]: mu_de(pred[g["pid"]][0], nuc[g["pid"]][0] + nuc[g["pid"]][1]) for g in pruebas},
        "mitad_margen_total_equipo": {g["pid"]: mu_de((pred[g["pid"]][0] + nuc[g["pid"]][0] - nuc[g["pid"]][1]) / 2,
                                                      nuc[g["pid"]][0] + nuc[g["pid"]][1]) for g in pruebas},
        "mitad_equipo_mitad_jugadores": {g["pid"]: tuple((np.array(nuc[g["pid"]]) + np.array(mu_de(*pred[g["pid"]]))) / 2) for g in pruebas},
        "mezcla_con_equipo": {g["pid"]: mu_de(w[0] / (w[0] + w[1]) * pred[g["pid"]][0] + w[1] / (w[0] + w[1]) * (nuc[g["pid"]][0] - nuc[g["pid"]][1]),
                                              pred[g["pid"]][1]) for g in pruebas},
    }
    informe = {"lam": lam, "vida_media_dias": vida, "sigma_margen": sig_m, "sigma_total": sig_t, "pesos_margen": w.tolist(),
               "p_juega_estado": tabla_estado, "p_juega_sin_parte_por_tramo": tabla_sp, "variantes": []}
    for nombre, mu in mus.items():
        s = variante(nombre, mu, pruebas, cierres, sig_m, sig_t_eq if "total_equipo" in nombre else sig_t)
        informe["variantes"].append(s)
        print(json.dumps(s, indent=1, ensure_ascii=False))
    (carpeta / "informe_s3b.json").write_text(json.dumps(informe, indent=1, ensure_ascii=False), encoding="utf8")


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "2025-26")
