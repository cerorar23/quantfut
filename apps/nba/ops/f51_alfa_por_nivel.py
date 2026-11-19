"""F5.1 — Sobredispersión de los props: una alfa por estadística frente a una por nivel de rol (medición hacia adelante).

    python apps/nba/ops/f51_alfa_por_nivel.py CARPETA [temporadas_prueba=2024-25,2025-26,2026-27]

Misma carpeta que `evaluar_s4.py` (las cuotas no hacen falta). Para cada temporada de prueba todo se ajusta con las anteriores y con los
(k, decaimiento) de producción (`entrenar_props.py`). Se compara, por estadística y tramo de minutos esperados: la frecuencia del PIT en las
colas (< 0,10, < 0,25, > 0,75, > 0,90; calibrado = 0,10/0,25/0,25/0,10), la cobertura del 80 % y la log-verosimilitud media por fila, con
IC 95 % de la diferencia por bootstrap de días (las filas de un mismo día no son independientes). Salida: informe_f51.json en CARPETA.
"""
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import entrenar_props as ep  # noqa: E402
import evaluar_s3 as e3  # noqa: E402
import evaluar_s4 as e4  # noqa: E402
from nba.v2 import minutos, props  # noqa: E402

TRAMOS = ((0.0, 20.0), (20.0, 28.0), (28.0, 34.0), (34.0, 99.0))


def pmf_filas(tasa, muestras, alfa_fila, techo):
    """pmf por fila con una alfa por fila (agrupa las filas con la misma alfa)."""
    salida = [None] * len(tasa)
    for a in np.unique(alfa_fila):
        idx = np.flatnonzero(alfa_fila == a)
        for i in range(0, len(idx), 4000):
            b = idx[i:i + 4000]
            p = props.pmf_mezcla_adaptativa(tasa[b], muestras[b], float(a), techo)
            for j, fila in zip(b, p):
                salida[j] = fila
    ancho = max(len(x) for x in salida)
    return np.vstack([np.pad(x, (0, ancho - len(x))) for x in salida])


def colas(pit, m):
    return {"<0.10": round(float((pit[m] < 0.1).mean()), 4), "<0.25": round(float((pit[m] < 0.25).mean()), 4),
            ">0.75": round(float((pit[m] > 0.75).mean()), 4), ">0.90": round(float((pit[m] > 0.9).mean()), 4),
            "cob80": round(float(((pit[m] > 0.1) & (pit[m] < 0.9)).mean()), 4), "n": int(m.sum())}


def main(carpeta: Path, pruebas):
    sys.stdout.reconfigure(encoding="utf8")
    rng = np.random.default_rng(51)
    juegos, _ = e3.leer(carpeta)
    fecha = {g["pid"]: g["fecha"] for g in juegos}
    filas, _, _ = e4.construir_filas(carpeta, juegos)
    temp, mp = filas["temp"], filas["mp"].astype(float)
    informe = {"k": ep.K, "decaimiento": ep.DECAIMIENTO, "temporadas": {}}
    for prueba in pruebas:
        entren, pm = temp < prueba, temp == prueba
        res = minutos.ajustar_residuos(zip(mp[entren], filas["m"][entren]))
        prior = props.prior_por_nivel(mp[entren], filas["m"][entren], filas["y"][entren])
        tasa_e = props.tasa_por_minuto(filas["mh"][entren], filas["sh"][entren], prior[props.nivel(mp[entren])], ep.K, ep.DECAIMIENTO)
        tasa_t = props.tasa_por_minuto(filas["mh"][pm], filas["sh"][pm], prior[props.nivel(mp[pm])], ep.K, ep.DECAIMIENTO)
        muestras = minutos.muestras_condicionadas(mp[pm], res, e4.N_MIN)
        y, mpt = filas["y"][pm], mp[pm]
        dias = np.array([fecha[int(p)] for p in filas["pid"][pm]])
        _, g = np.unique(dias, return_inverse=True)
        inf = {}
        print(f"\n=== {prueba}: {pm.sum()} filas ===")
        for s, nombre in enumerate(props.ESTADISTICAS):
            mu_e = tasa_e[:, s] * filas["m"][entren]
            a_glob = props.estimar_alfa(mu_e, filas["y"][entren][:, s])
            a_niv = props.estimar_alfa_por_nivel(mp[entren], mu_e, filas["y"][entren][:, s])
            r = {"alfa_global": round(a_glob, 5), "alfa_por_nivel": np.round(a_niv, 5).tolist()}
            ll = {}
            for variante, alfa_fila in (("global", np.full(len(y), a_glob)), ("por_nivel", a_niv[props.nivel(mpt)])):
                pmf = pmf_filas(tasa_t[:, s], muestras, alfa_fila, props.TECHO[nombre])
                pit = props.pit_aleatorio(pmf, y[:, s], semilla=s)
                ll[variante] = np.log(np.maximum(pmf[np.arange(len(y)), np.clip(y[:, s].astype(int), 0, pmf.shape[1] - 1)], 1e-300))
                r[variante] = {"todos": colas(pit, np.ones(len(y), bool)), "ge20": colas(pit, mpt >= 20)}
                r[variante].update({f"tramo_{lo:.0f}_{hi:.0f}": colas(pit, (mpt >= lo) & (mpt < hi)) for lo, hi in TRAMOS})
                r[variante]["logver_media"] = round(float(ll[variante].mean()), 5)
            d = ll["por_nivel"] - ll["global"]
            sims = []
            suma, cuenta = np.bincount(g, d), np.bincount(g)
            for _ in range(1000):
                w = rng.poisson(1.0, len(cuenta))
                sims.append((w * suma).sum() / (w * cuenta).sum())
            r["dif_logver"] = {"media": round(float(d.mean()), 5), "ic95": np.round(np.percentile(sims, [2.5, 97.5]), 5).tolist()}
            inf[nombre] = r
            print(f"{nombre:12s} alfa {a_glob:.3f} → {np.round(a_niv, 3).tolist()} | Δlogver {d.mean():+.4f} {r['dif_logver']['ic95']}")
            for variante in ("global", "por_nivel"):
                print(f"   {variante:9s} ≥20 min {r[variante]['ge20']} | ≥34 {r[variante]['tramo_34_99']} | <20 {r[variante]['tramo_0_20']}")
        informe["temporadas"][prueba] = inf
    (carpeta / "informe_f51.json").write_text(json.dumps(informe, indent=1, ensure_ascii=False), encoding="utf8")


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2].split(",") if len(sys.argv) > 2 else ["2024-25", "2025-26", "2026-27"])
