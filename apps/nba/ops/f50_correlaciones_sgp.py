"""F5.0 — Parley de un solo partido (same-game), fase 0: dependencia entre patas medida sobre los errores del motor v2.

    python apps/nba/ops/f50_correlaciones_sgp.py CARPETA [temporadas_prueba=2024-25,2025-26,2026-27]

CARPETA: la de `preparar_datos_entrenamiento.py` (s3_juegos.csv, players.jsonl.gz, s3b_*.csv; s3_cierres.csv puede ir vacío).
Solo lectura y hacia adelante: para cada temporada de prueba, los props se predicen como en `evaluar_s4.py` (tasa, prior, alfa,
residuos de minutos y (k, decaimiento) ajustados SOLO con temporadas anteriores) y el marcador con el núcleo de equipo (`e3.recorrer`,
ratings previos a cada partido). Cada pata se pasa a su puntuación normal z = Φ⁻¹(PIT aleatorio): la correlación de esas z es el
parámetro de una cópula gaussiana. Además se compara la frecuencia conjunta observada de «patas de 75 %» con el producto (independencia)
y con lo que predice la cópula, que es lo que decide si la cópula basta o hace falta la parte jerárquica (minutos en palizas).

Intervalos: bootstrap de Poisson por partido (los pares de un mismo partido no son independientes). Salida: informe_f50.json en CARPETA.
"""
from collections import defaultdict
import gzip
import itertools
import json
from pathlib import Path
import sys

import numpy as np
from scipy.stats import multivariate_normal, norm

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import evaluar_s3 as e3  # noqa: E402
import evaluar_s4 as e4  # noqa: E402
from nba.v2 import minutos, props  # noqa: E402
from nba.v2.equipos import NBA_IDS  # noqa: E402
from nba.v2.nucleo import Parametros  # noqa: E402

E = len(props.ESTADISTICAS)
CORTE = norm.ppf(0.25)                 # «pata de 75 %»: la variable queda por encima de su cuantil 25 % pronosticado
MIN_PROP = 20.0                        # solo jugadores con ≥ 20 minutos esperados: los que tienen línea de prop en las casas
N_BOOT = 400
P_NUCLEO = Parametros(eta=0.045, arrastre=0.65, eta_liga=0.01, efecto_b2b=2.78)


def equipos_de_jugadores(carpeta):
    """(partido, jugador) → team_id, con los mismos ids canónicos que usa `e4.construir_filas`."""
    par, jug = {}, {}
    import csv
    for r in csv.DictReader(open(carpeta / "s3b_partidos.csv", encoding="utf8")):
        if r["fuente"] == "nba_oficial" and r["id_en_fuente"].isdigit():
            par[r["id_en_fuente"]] = int(r["canonica_id"])
    for r in csv.DictReader(open(carpeta / "s3b_jugadores.csv", encoding="utf8")):
        if r["fuente"] == "nba_oficial" and r["id_en_fuente"].isdigit():
            jug[int(r["id_en_fuente"])] = int(r["canonica_id"])
    salida = {}
    with gzip.open(carpeta / "players.jsonl.gz", "rt", encoding="utf8") as f:
        for linea in f:
            r = json.loads(linea)
            pid, jid = par.get(r["game_id"]), jug.get(r["player_id"])
            if pid is not None and jid is not None:
                salida[(pid, jid)] = r["team_id"]
    return salida


def ajustar_props(filas, prueba):
    """Lo mismo que `evaluar_s4.main` pasos 1-2, sin cuotas: devuelve las z (PIT aleatorio → normal) de la temporada de prueba."""
    temp, mp = filas["temp"], filas["mp"].astype(float)
    anteriores = sorted(set(temp[temp < prueba].tolist()))
    primera_val = anteriores[-2] if len(anteriores) >= 3 else anteriores[-1]
    entren, valid = temp < primera_val, (temp >= primera_val) & (temp < prueba)
    res_v = minutos.ajustar_residuos(zip(mp[entren], filas["m"][entren]))
    prior_v = props.prior_por_nivel(mp[entren], filas["m"][entren], filas["y"][entren])
    mean_min_v = e4.muestras_minutos(mp[valid], res_v).mean(axis=1)
    mejor = None
    for k, dec in itertools.product((30.0, 100.0, 300.0), (0.85, 0.93, 0.97)):
        tasa = props.tasa_por_minuto(filas["mh"][valid], filas["sh"][valid], prior_v[props.nivel(mp[valid])], k, dec)
        err = np.abs(filas["y"][valid] - tasa * mean_min_v[:, None]).mean()
        if mejor is None or err < mejor[0]:
            mejor = (err, k, dec)
    _, k, dec = mejor
    entren, prueba_m = temp < prueba, temp == prueba
    res = minutos.ajustar_residuos(zip(mp[entren], filas["m"][entren]))
    prior = props.prior_por_nivel(mp[entren], filas["m"][entren], filas["y"][entren])
    tasa_e = props.tasa_por_minuto(filas["mh"][entren], filas["sh"][entren], prior[props.nivel(mp[entren])], k, dec)
    alfas = [props.estimar_alfa(tasa_e[:, s] * filas["m"][entren], filas["y"][entren][:, s]) for s in range(E)]
    tasa_t = props.tasa_por_minuto(filas["mh"][prueba_m], filas["sh"][prueba_m], prior[props.nivel(mp[prueba_m])], k, dec)
    muestras = e4.muestras_minutos(mp[prueba_m], res)
    y = filas["y"][prueba_m]
    z = np.empty_like(y, dtype=float)
    for s, nombre in enumerate(props.ESTADISTICAS):
        bloques = [props.pmf_mezcla_adaptativa(tasa_t[i:i + 4000, s], muestras[i:i + 4000], alfas[s], props.TECHO[nombre])
                   for i in range(0, len(y), 4000)]
        ancho = max(b.shape[1] for b in bloques)
        pmf = np.vstack([np.pad(b, ((0, 0), (0, ancho - b.shape[1]))) for b in bloques])
        pit = props.pit_aleatorio(pmf, y[:, s], semilla=1000 + s)
        z[:, s] = norm.ppf(np.clip(pit, 1e-6, 1 - 1e-6))
    return prueba_m, z, {"k": k, "decaimiento": dec}


def corr_boot(a, b, grupo, rng):
    """Correlación de Pearson con IC 95 % por bootstrap de Poisson sobre partidos."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    r = float(np.corrcoef(a, b)[0, 1])
    _, g = np.unique(grupo, return_inverse=True)
    sims = []
    for _ in range(N_BOOT):
        w = rng.poisson(1.0, g.max() + 1)[g].astype(float)
        sw = w.sum()
        ma, mb = (w * a).sum() / sw, (w * b).sum() / sw
        cov = (w * (a - ma) * (b - mb)).sum()
        sims.append(cov / np.sqrt((w * (a - ma) ** 2).sum() * (w * (b - mb) ** 2).sum()))
    lo, hi = np.percentile(sims, [2.5, 97.5])
    return {"r": round(r, 4), "ic95": [round(float(lo), 4), round(float(hi), 4)], "n": int(len(a))}


def conjunta_75(a, b, r):
    """Patas de 75 %: frecuencia conjunta observada frente a independencia y a la cópula gaussiana con correlación r."""
    ea, eb = a > CORTE, b > CORTE
    pa, pb, pab = ea.mean(), eb.mean(), (ea & eb).mean()
    # P(Z1 > c, Z2 > c) = P(−Z1 < −c, −Z2 < −c) = Φ2(−c, −c; r)
    copula = multivariate_normal(mean=[0, 0], cov=[[1, r], [r, 1]]).cdf([-CORTE, -CORTE])
    return {"p_a": round(float(pa), 4), "p_b": round(float(pb), 4), "conjunta_obs": round(float(pab), 4),
            "independencia": round(float(pa * pb), 4), "copula": round(float(copula), 4),
            "lift_obs": round(float(pab / (pa * pb)), 4)}


def main(carpeta: Path, pruebas):
    sys.stdout.reconfigure(encoding="utf8")
    rng = np.random.default_rng(50)
    juegos, _ = e3.leer(carpeta)
    mus = e3.recorrer(juegos, P_NUCLEO)
    por_pid = {g["pid"]: (g, mu) for g, mu in zip(juegos, mus)}
    team_id = {tri: tid for tid, tri in NBA_IDS.items()}
    filas, _, _ = e4.construir_filas(carpeta, juegos)
    eq = equipos_de_jugadores(carpeta)
    informe = {"corte_pata": 0.75, "min_minutos_esperados": MIN_PROP, "temporadas": {}}

    # residuos del marcador (el núcleo usa ratings previos a cada partido): margen y total, y su z con la desviación de temporadas previas
    for prueba in pruebas:
        print(f"\n=== {prueba} ===")
        gs = [(g, mu) for g, mu in zip(juegos, mus) if g["temporada"] == prueba]
        prev = [(g, mu) for g, mu in zip(juegos, mus) if g["temporada"] < prueba and g["temporada"] >= "2022-23"]
        def resid(lista):
            m = np.array([(g["pl"] - g["pv"]) - (mu[0] - mu[1]) for g, mu in lista])
            t = np.array([(g["pl"] + g["pv"]) - (mu[0] + mu[1]) for g, mu in lista])
            return m, t
        mp_, tp_ = resid(prev)
        sm, st = mp_.std(), tp_.std()
        m_res, t_res = resid(gs)
        zm, zt = m_res / sm, t_res / st
        inf = {"n_partidos": len(gs), "sigma_margen_prev": round(float(sm), 3), "sigma_total_prev": round(float(st), 3)}
        inf["margen_vs_total"] = corr_boot(m_res, t_res, np.arange(len(gs)), rng)
        inf["margen_vs_total"]["conjunta_75"] = conjunta_75(zm, zt, inf["margen_vs_total"]["r"])
        # «gana el local / cubre» y «más del total» como patas: la dirección importa; también visitante y menos
        z_partido = {g["pid"]: (zm[i], zt[i], m_res[i], abs(g["pl"] - g["pv"])) for i, (g, _) in enumerate(gs)}

        mask, z, hp = ajustar_props(filas, prueba)
        pid, jid, mpe = filas["pid"][mask], filas["jid"][mask], filas["mp"][mask].astype(float)
        ok = np.array([int(p) in z_partido and (int(p), int(j)) in eq for p, j in zip(pid, jid)])
        pid, jid, mpe, z = pid[ok], jid[ok], mpe[ok], z[ok]
        g_of = {p: por_pid[p][0] for p in set(pid.tolist())}
        local = np.array([eq[(int(p), int(j))] == team_id.get(g_of[int(p)]["local"]) for p, j in zip(pid, jid)])
        tid = np.array([eq[(int(p), int(j))] for p, j in zip(pid, jid)])
        zm_r = np.array([z_partido[int(p)][0] for p in pid]) * np.where(local, 1, -1)   # margen a favor del equipo del jugador
        zt_r = np.array([z_partido[int(p)][1] for p in pid])
        absm = np.array([z_partido[int(p)][3] for p in pid])
        sel = mpe >= MIN_PROP
        tit = mpe >= 28
        inf.update({"hiperparametros_props": hp, "n_filas_jugador": int(len(pid)), "n_filas_con_prop": int(sel.sum())})
        print(f"{len(gs)} partidos; {len(pid)} filas jugador-partido ({sel.sum()} con ≥ {MIN_PROP:.0f} min esperados)")
        print(f"margen vs total: {inf['margen_vs_total']}")

        # cobertura de calibración de las z (si el PIT es uniforme, P(z > corte) ≈ 0,75 para cada estadística)
        inf["calibracion_pata_75"] = {n: round(float((z[sel, s] > CORTE).mean()), 4) for s, n in enumerate(props.ESTADISTICAS)}

        # prop frente al partido
        inf["prop_vs_partido"] = {}
        for s, n in enumerate(props.ESTADISTICAS):
            d = {}
            for etiqueta, m in (("todos", sel), ("titulares", tit)):
                d[f"total_{etiqueta}"] = corr_boot(z[m, s], zt_r[m], pid[m], rng)
                d[f"margen_propio_{etiqueta}"] = corr_boot(z[m, s], zm_r[m], pid[m], rng)
                d[f"abs_margen_{etiqueta}"] = corr_boot(z[m, s], absm[m], pid[m], rng)
            d["total_titulares"]["conjunta_75"] = conjunta_75(z[tit, s], zt_r[tit], d["total_titulares"]["r"])
            d["margen_propio_titulares"]["conjunta_75"] = conjunta_75(z[tit, s], zm_r[tit], d["margen_propio_titulares"]["r"])
            inf["prop_vs_partido"][n] = d
            print(f"{n:12s} total {d['total_todos']['r']:+.3f} margen propio {d['margen_propio_todos']['r']:+.3f} "
                  f"|margen| titulares {d['abs_margen_titulares']['r']:+.3f}")

        # mismo jugador, dos estadísticas
        inf["mismo_jugador"] = {}
        for a, b in itertools.combinations(range(E), 2):
            clave = f"{props.ESTADISTICAS[a]}-{props.ESTADISTICAS[b]}"
            c = corr_boot(z[sel, a], z[sel, b], pid[sel], rng)
            c["conjunta_75"] = conjunta_75(z[sel, a], z[sel, b], c["r"])
            inf["mismo_jugador"][clave] = c
            print(f"mismo jugador {clave:22s} r {c['r']:+.3f} {c['ic95']} lift75 {c['conjunta_75']['lift_obs']:.3f} "
                  f"cópula {c['conjunta_75']['copula']:.4f} obs {c['conjunta_75']['conjunta_obs']:.4f}")

        # compañeros y rivales (pares de jugadores con ≥ MIN_PROP minutos esperados en el mismo partido)
        idx_por_pid = defaultdict(list)
        for i in np.flatnonzero(sel):
            idx_por_pid[int(pid[i])].append(i)
        comp, riv = [], []
        for lista in idx_por_pid.values():
            for i, j in itertools.combinations(lista, 2):
                (comp if tid[i] == tid[j] else riv).append((i, j))
        inf["companeros"], inf["rivales"] = {}, {}
        for nombre, pares in (("companeros", comp), ("rivales", riv)):
            if not pares:
                continue
            I, J = np.array(pares).T
            for a, b in [(s, s) for s in range(E)] + [(0, 2), (0, 1)]:
                clave = f"{props.ESTADISTICAS[a]}-{props.ESTADISTICAS[b]}"
                # simétrico: cada par entra en los dos órdenes cuando las estadísticas difieren
                za = np.concatenate([z[I, a], z[J, a]]) if a != b else z[I, a]
                zb = np.concatenate([z[J, b], z[I, b]]) if a != b else z[J, b]
                gp = np.concatenate([pid[I], pid[J]]) if a != b else pid[I]
                c = corr_boot(za, zb, gp, rng)
                c["conjunta_75"] = conjunta_75(za, zb, c["r"])
                inf[nombre][clave] = c
                print(f"{nombre:10s} {clave:22s} r {c['r']:+.3f} {c['ic95']} n {c['n']}")
        informe["temporadas"][prueba] = inf
    (carpeta / "informe_f50.json").write_text(json.dumps(informe, indent=1, ensure_ascii=False), encoding="utf8")
    print("\ninforme:", carpeta / "informe_f50.json")


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2].split(",") if len(sys.argv) > 2 else ["2024-25", "2025-26", "2026-27"])
