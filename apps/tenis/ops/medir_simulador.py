"""Mediciones del simulador (S3-A): cifras publicadas, tiempos, cuadratura, Monte Carlo y sensibilidad.

Uso: correr_script_tenis.ps1 apps/tenis/ops/medir_simulador.py [rapido|tiempos|mc|sens|todo]
"""
import sys
import time

import numpy as np

from tenis.simulador import Formato, Incertidumbre, SIN_INCERTIDUMBRE, distribucion_mezclada, distribucion_partido, prob_ganar
from tenis.simulador.inversion import invertir
from tenis.simulador.juego import ganar_juego
from tenis.simulador.montecarlo import simular
from tenis.simulador.sensibilidad import sensibilidad
from tenis.simulador.set_ import tabla_set

B3 = Formato(3, "tiebreak_7")
B5_10 = Formato(5, "tiebreak_10")
B5_7 = Formato(5, "tiebreak_7")
FD = Incertidumbre(0.22, -0.45)


def rapido():
    print("g(0.65) =", ganar_juego(0.65))
    for s in "AB":
        t = tabla_set(0.60, 0.55, s, "tiebreak_7")
        d = dict(zip(t.marcadores, t.prob))
        print(s, "set", round(t.gana_a, 5), "6-1", round(d[(6, 1, False)], 4), "6-3", round(d[(6, 3, False)], 4),
              "6-6", round(d[(7, 6, True)] + d[(6, 7, True)], 4))
    for f in (B5_7, B5_10):
        d = distribucion_partido(0.60, 0.55, f)
        r = {k: 0.0 for k in ((3, 0), (3, 1), (3, 2))}
        for sa, sb, p in zip(d.sets_a, d.sets_b, d.prob):
            if (sa, sb) in r:
                r[(sa, sb)] += p
        print(f, round(d.gana_a, 5), {k: round(v, 4) for k, v in r.items()}, "masa", d.masa_total)
    print("A31 0.6/0.5:", distribucion_partido(0.6, 0.5, B5_7).gana_a, distribucion_partido(0.6, 0.5, B3).gana_a)
    print("0.66/0.60 sin efecto:", prob_ganar(0.66, 0.60, B3, SIN_INCERTIDUMBRE),
          "con efecto:", prob_ganar(0.66, 0.60, B3, FD))
    for q in (5, 7, 9, 15, 21):
        print("Q", q, prob_ganar(0.66, 0.60, B3, FD, q))
    inv = invertir(1.25, 0.70, B3, FD)
    print("D.4:", inv)


def _mejor(f, veces):
    """Mínimo de `veces` mediciones (robusto a otros procesos en la máquina), en ms."""
    out = []
    for _ in range(veces):
        t0 = time.perf_counter(); f(); out.append(time.perf_counter() - t0)
    return 1e3 * min(out), 1e3 * float(np.median(out))


def tiempos():
    """81 nodos (Q = 9), primer sacador 50/50, Σ de A26 (H)."""
    for f in (B3, Formato(3, "tiebreak_10"), Formato(3, "ventaja"), Formato(3, "super_tiebreak_10"), B5_10,
              Formato(5, "ventaja")):
        g = _mejor(lambda: prob_ganar(0.64, 0.62, f, FD), 30)
        c = _mejor(lambda: distribucion_mezclada(0.64, 0.62, f, FD), 10)
        d = distribucion_mezclada(0.64, 0.62, f, FD)
        e = _mejor(d.marcadores, 2)
        i = _mejor(lambda: invertir(1.26, 0.7, f, FD), 3)
        print(f"{f.mejor_de} {f.decisivo:18s} ganar {g[0]:6.2f} ms (mediana {g[1]:6.2f})  conjunta {c[0]:6.1f} ms "
              f"(mediana {c[1]:6.1f})  filas {len(d.prob):7d}  dict de marcadores {e[0]:7.1f} ms  inversión {i[0]:6.1f} ms")


def a26():
    """A26 (Klaassen y Magnus 2003): ejemplos de inversión de TENNISPROB (Wimbledon, set final con ventaja)."""
    for nombre, f, pa, pb, impreso in (("Sampras-Becker 1995", Formato(5, "ventaja"), 0.6824, 0.6663, 0.598),
                                       ("Graf-Novotna 1993", Formato(3, "ventaja"), 0.6265, 0.5273, 0.906)):
        m = prob_ganar(pa, pb, f, SIN_INCERTIDUMBRE)
        inv = invertir(pa + pb, impreso, f, SIN_INCERTIDUMBRE)
        print(f"{nombre}: M({pa}, {pb}) = {m:.5f} (impreso {impreso}); inversión p = {inv.p_a:.4f}/{inv.p_b:.4f}")
    print("K = logit(m5)/logit(m3) (diagnóstico; m5 con TB7 en todos los sets, m3 gira regular):")
    ks = []
    for pa in (0.55, 0.60, 0.62, 0.65, 0.70):
        for pb in (0.55, 0.58, 0.60, 0.62, 0.65):
            if pa <= pb:
                continue
            m3, m5 = prob_ganar(pa, pb, B3, SIN_INCERTIDUMBRE), prob_ganar(pa, pb, B5_7, SIN_INCERTIDUMBRE)
            k = np.log(m5 / (1 - m5)) / np.log(m3 / (1 - m3))
            ks.append(k)
            print(f"  {pa:.2f}/{pb:.2f}: m3 {m3:.4f} m5 {m5:.4f} K {k:.4f}")
    print(f"  K media {np.mean(ks):.4f}, mín {np.min(ks):.4f}, máx {np.max(ks):.4f} (teórico √1,4 = {np.sqrt(1.4):.4f})")
    kf = []
    for pa, pb in ((0.60, 0.55), (0.65, 0.60), (0.70, 0.60), (0.62, 0.60)):
        m3, m5 = prob_ganar(pa, pb, B3, FD), prob_ganar(pa, pb, B5_7, FD)
        kf.append(np.log(m5 / (1 - m5)) / np.log(m3 / (1 - m3)))
    print(f"  con forma del día (0,22/−0,45): K = {', '.join(f'{k:.4f}' for k in kf)}")


def tb_media():
    sys.path.insert(0, "apps/tenis/tests")
    from test_simulador_referencia import ref_tiebreak
    from tenis.simulador.tiebreak import puntos_media_var
    for p in (0.5, 0.9):
        fin, err = ref_tiebreak(p, p, 7, "A")
        m = sum(v * (a + b) for (a, b), v in fin.items())
        v = sum(x * (a + b) ** 2 for (a, b), x in fin.items()) - m * m
        print(p, "ref", m, np.sqrt(v), "err", err, "cerrada", puntos_media_var(p, p, 7, "A"))


def cuadratura():
    from tenis.simulador.mezcla import verificar_cuadratura
    formatos = [B3, Formato(3, "tiebreak_10"), Formato(3, "ventaja"), Formato(3, "super_tiebreak_10"), B5_10,
                Formato(5, "ventaja")]
    pares = [(0.66, 0.60), (0.55, 0.50), (0.72, 0.70), (0.45, 0.62), (0.80, 0.78), (0.62, 0.62)]
    for nombre, inc in (("A26 H 0.22/-0.45", FD), ("A26 M 0.18/-0.64", Incertidumbre(0.18, -0.64)),
                        ("H + V 0.01", Incertidumbre(0.22, -0.45, ((0.01, 0.0), (0.0, 0.01)))),
                        ("0.30 + V 0.02-0.03", Incertidumbre(0.30, -0.45, ((0.02, 0.005), (0.005, 0.03)))),
                        ("0.40/0", Incertidumbre(0.40, 0.0))):
        for f in formatos:
            peor = max(verificar_cuadratura(pa, pb, f, inc, 9) for pa, pb in pares)
            q_ok = next((q for q in (9, 11, 13, 15, 17) if
                         max(verificar_cuadratura(pa, pb, f, inc, q) for pa, pb in pares) < 1e-4), None)
            print(f"{nombre:20s} {f.mejor_de} {f.decisivo:18s} máx|Q9−Q21| {peor:.2e}  Q mínimo < 1e-4: {q_ok}")


def mc(n: int = 80_000, replicas: int = 20):
    """Plan G.5: error de Monte Carlo punto a punto frente al exacto, R réplicas independientes por caso.
    Meta: percentil 99 de |error| < 0,5 pp en ganador, 1.er set y total de juegos (líneas 18,5…26,5 y 38,5)."""
    casos = [(B3, 0.64, 0.61, SIN_INCERTIDUMBRE), (B3, 0.66, 0.60, FD), (Formato(3, "tiebreak_10"), 0.58, 0.55, FD),
             (B5_10, 0.67, 0.63, SIN_INCERTIDUMBRE), (B5_10, 0.62, 0.62, FD)]
    errores, zs, t_total = [], [], 0.0
    for f, pa, pb, inc in casos:
        ex = distribucion_mezclada(pa, pb, f, inc)
        lineas = (18.5, 20.5, 22.5, 24.5, 26.5, 38.5) if f.mejor_de == 3 else (32.5, 36.5, 38.5, 40.5, 44.5)
        for r in range(replicas):
            t0 = time.perf_counter()
            sim = simular(pa, pb, f, n, 1000 * r + 7, inc=inc)
            t_total += time.perf_counter() - t0
            pares = [(sim.gana_a(), ex.gana_a), (sim.primer_set_a(), ex.primer_set_a_prob)]
            pares += [(sim.juegos_mas_de(x), ex.juegos_mas_de(x)) for x in lineas]
            for (est, ee), exacto in pares:
                errores.append(abs(est - exacto))
                zs.append((est - exacto) / max(np.sqrt(exacto * (1 - exacto) / n), 1e-12))
    e = np.array(errores)
    zs = np.array(zs)
    print(f"N = {n}, réplicas = {replicas}, comparaciones = {len(e)}; tiempo medio por simulación "
          f"{t_total / (replicas * len(casos)):.2f} s")
    print(f"|error| pp: mediana {100 * np.median(e):.3f}, p95 {100 * np.quantile(e, 0.95):.3f}, "
          f"p99 {100 * np.quantile(e, 0.99):.3f}, máx {100 * e.max():.3f}")
    print(f"z = error/EE: media {zs.mean():.3f}, DE {zs.std():.3f} (esperado 0 y 1), |z|>2,576: {np.mean(abs(zs) > 2.576):.4f}")
    print(f"N mínimo teórico peor caso (p=0,5): {int(np.ceil((2.576 * 0.5 / 0.005) ** 2))}")


def sens():
    for f in (B3, B5_10):
        for nombre, inc in (("sin efecto", SIN_INCERTIDUMBRE), ("forma del día", FD)):
            for pa, pb in ((0.64, 0.64), (0.66, 0.60), (0.70, 0.60), (0.58, 0.55)):
                s = sensibilidad(pa, pb, f, inc)
                pp = s.por_punto_porcentual()
                print(f"{f.mejor_de} {f.decisivo:12s} {nombre:13s} {pa:.2f}/{pb:.2f}: P {s.gana_a:.4f} "
                      f"ΔP/1pp(pA) {100 * pp['d_gana_pa']:+.2f} pp  ΔP/1pp(pB) {100 * pp['d_gana_pb']:+.2f} pp  "
                      f"Δ1.er set {100 * pp['d_primer_set_pa']:+.2f} pp  E[T] {s.media_juegos:.2f}  "
                      f"ΔE[T]/1pp(pA) {pp['d_juegos_pa']:+.3f}  (pB) {pp['d_juegos_pb']:+.3f}")


def referencia():
    """Error máximo de cada pieza cerrada frente a la referencia independiente de puntos (tests/test_simulador_referencia)."""
    sys.path.insert(0, "apps/tenis/tests")
    import test_simulador_referencia as R
    from tenis.simulador.tiebreak import distribucion_tiebreak, ganar_tiebreak
    pares = R.PARES
    e = max(abs(ganar_juego(p) - sum(m for (a, b), m in R.ref_juego(p)[0].items() if a > b))
            for p in (0.02, 0.3, 0.5, 0.65, 0.9, 0.98))
    print(f"juego: máx |g − ref| = {e:.2e}")
    e_tb, e_dist = 0.0, 0.0
    for pa, pb in pares:
        for k in (7, 10):
            for s in "AB":
                fin, _ = R.ref_tiebreak(pa, pb, k, s)
                e_tb = max(e_tb, abs(ganar_tiebreak(pa, pb, k, s) - sum(m for (a, b), m in fin.items() if a > b)))
                d = distribucion_tiebreak(pa, pb, k, s, rondas=30)
                e_dist = max(e_dist, max(abs(m - fin.get(x, 0.0)) for x, m in d.puntos.items()))
    print(f"tiebreak: máx |P − ref| = {e_tb:.2e}; máx error de marcador = {e_dist:.2e}")
    e_set = 0.0
    for pa, pb in pares:
        for regla in ("tiebreak_7", "tiebreak_10", "super_tiebreak_10"):
            for s in "AB":
                ref, _ = R.ref_set(pa, pb, s, regla)
                t = tabla_set(pa, pb, s, regla)
                e_set = max(e_set, max(abs(m - ref.get((a, b, tb, sg), 0.0))
                                       for (a, b, tb), m, sg in zip(t.marcadores, t.prob, t.siguiente_saca)))
    print(f"set (con sacador del set siguiente): máx error de marcador = {e_set:.2e}")
    e_p = 0.0
    for f in (B3, Formato(3, "tiebreak_10"), Formato(3, "super_tiebreak_10")):
        for pa, pb in ((0.64, 0.62), (0.58, 0.66), (0.95, 0.95)):
            ref = R.ref_partido(pa, pb, f)
            d = distribucion_partido(pa, pb, f).marcadores()
            e_p = max(e_p, max(abs(d[k] - ref[k]) for k in ref))
    ref = R.ref_partido(0.66, 0.63, B5_10)
    d = distribucion_partido(0.66, 0.63, B5_10).marcadores()
    e_p = max(e_p, max(abs(d[k] - ref[k]) for k in ref))
    print(f"partido (marcador completo): máx error = {e_p:.2e}")


def perfil():
    import cProfile
    import pstats
    distribucion_mezclada(0.64, 0.62, B5_10, FD)
    pr = cProfile.Profile()
    pr.enable()
    for _ in range(3):
        distribucion_mezclada(0.64, 0.62, B5_10, FD)
    pr.disable()
    pstats.Stats(pr).sort_stats("tottime").print_stats(12)


if __name__ == "__main__":
    que = sys.argv[1] if len(sys.argv) > 1 else "rapido"
    {"rapido": rapido, "tiempos": tiempos, "perfil": perfil, "a26": a26, "tb_media": tb_media,
     "cuadratura": cuadratura, "mc": mc, "sens": sens, "referencia": referencia}[que]()
