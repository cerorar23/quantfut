"""Evaluación del Sprint 2 con datos exportados de `nba_datos` (CSV): calibración del estado oficial y modelo de minutos.

    python apps/nba/ops/evaluar_s2.py CARPETA_CON_CSV [temporada_prueba=2025-26]

Entradas: s2_jugadores.csv (fecha, temporada, partido_id, jugador_id, jugo, minutos) y s2_estados.csv
(fecha, partido_id, jugador_id, estado, hora_parte). Validación hacia adelante: el modelo de cada partido solo usa los
partidos anteriores del jugador; las colas de la línea base se ajustan con temporadas anteriores a la de prueba.
"""
import csv
from collections import defaultdict
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from nba.v2 import disponibilidad as disp, minutos as mi  # noqa: E402

TAUS = (0.1, 0.5, 0.9)


def leer(carpeta: Path):
    jugadores = defaultdict(list)
    with open(carpeta / "s2_jugadores.csv", encoding="utf8") as f:
        for r in csv.DictReader(f):
            jugadores[int(r["jugador_id"])].append((r["fecha"], int(r["partido_id"]), r["temporada"],
                                                    r["jugo"] == "1" or r["jugo"] == "1.0",
                                                    float(r["minutos"]) if r["minutos"] else None))
    for lista in jugadores.values():
        lista.sort()
    ultimo = {}
    with open(carpeta / "s2_estados.csv", encoding="utf8") as f:
        for r in csv.DictReader(f):
            clave = (int(r["partido_id"]), int(r["jugador_id"]))
            if clave not in ultimo or r["hora_parte"] > ultimo[clave][0]:
                ultimo[clave] = (r["hora_parte"], r["estado"], r["fecha"])
    return jugadores, {k: (v[1], v[2]) for k, v in ultimo.items()}


def temporada_de(fecha: str) -> str:
    anio, mes = int(fecha[:4]), int(fecha[5:7])
    inicio = anio if mes >= 9 else anio - 1
    return f"{inicio}-{(inicio + 1) % 100:02d}"


def calibracion(jugadores, estados):
    """P(jugó | estado en el último parte), por temporada; quien no figura en la caja cuenta como que no jugó."""
    jugo = {(p, j): ok for j, lista in jugadores.items() for (_, p, _, ok, _) in lista}
    por_temporada = defaultdict(list)
    for (p, j), (estado, fecha) in estados.items():
        por_temporada[temporada_de(fecha)].append((estado, jugo.get((p, j), False)))
    tablas = {t_: disp.tabla_estados(pares) for t_, pares in sorted(por_temporada.items())}
    sin_parte = [ok for (p, j), ok in jugo.items() if (p, j) not in estados]
    return tablas, {"n": len(sin_parte), "p": float(np.mean(sin_parte))}


def minutos_eval(jugadores, prueba):
    # 1) pronóstico puntual y real de cada partido jugado con historia suficiente (hacia adelante)
    filas = []                                   # (temporada, y, media5, punto)
    for lista in jugadores.values():
        jugados: list[float] = []
        for fecha, partido, temporada, ok, m in lista:
            if ok and m and m > 0:
                base5, punto = mi.media_ultimos(jugados), mi.punto(jugados)
                if base5 is not None and punto is not None:
                    filas.append((temporada, m, base5, punto))
                jugados.append(m)
    temporadas = np.array([f[0] for f in filas])
    y, b5, pt = (np.array([f[i] for f in filas]) for i in (1, 2, 3))
    train, test = temporadas < prueba, temporadas == prueba
    # 2) residuos de las temporadas anteriores: del modelo (por tramo) y de la línea base (globales)
    residuos = mi.ajustar_residuos(zip(pt[train], y[train]))
    rb = {t_: float(np.quantile((y - b5)[train], t_)) for t_ in TAUS}
    niveles = (np.arange(mi.N_CUANTILES) + 0.5) / mi.N_CUANTILES
    # 3) cuantiles del modelo en la prueba (pronóstico + residuo del tramo, recortado a [0, 60])
    tr = np.array([mi.tramo(v, residuos.cortes) for v in pt])
    def cuantil_modelo(tau):
        idx = np.clip(np.round(tau * mi.N_CUANTILES - 0.5).astype(int), 0, mi.N_CUANTILES - 1)
        return np.clip(pt + np.array([residuos.cuantiles[k][idx] for k in tr]), 0, mi.MAXIMO)
    q = {tau: cuantil_modelo(tau) for tau in TAUS}
    sal = {"n_prueba": int(test.sum()), "n_entrenamiento": int(train.sum()),
           "parametros": {"decaimiento": mi.DECAIMIENTO, "ventana": mi.VENTANA}}
    mae_b = float(np.mean(np.abs(y - b5)[test]))
    sal["mae_base_media5"] = mae_b
    sal["mae_modelo_punto"] = float(np.mean(np.abs(y - pt)[test]))
    sal["MASE_modelo"] = sal["mae_modelo_punto"] / mae_b
    sal["cobertura_80_modelo"] = float(np.mean(((y >= q[0.1]) & (y <= q[0.9]))[test]))
    sal["cobertura_80_base"] = float(np.mean(((y >= b5 + rb[0.1]) & (y <= b5 + rb[0.9]))[test]))
    for nombre, qs in {"modelo": q, "base": {tau: b5 + rb[tau] for tau in TAUS}}.items():
        perdida = 0.0
        for tau in TAUS:
            e = (y - qs[tau])[test]
            perdida += float(np.mean(np.maximum(tau * e, (tau - 1) * e)))
        sal[f"pinball_medio_{nombre}"] = perdida / 3
    tramos = {}
    for nombre, lo, hi in (("<15", 0, 15), ("15-25", 15, 25), (">=25", 25, 99)):
        m = test & (pt >= lo) & (pt < hi)
        if m.sum():
            tramos[nombre] = {"n": int(m.sum()), "mae_modelo": float(np.mean(np.abs(y - pt)[m])),
                              "mae_base": float(np.mean(np.abs(y - b5)[m])),
                              "cobertura_80_modelo": float(np.mean(((y >= q[0.1]) & (y <= q[0.9]))[m])),
                              "cobertura_80_base": float(np.mean(((y >= b5 + rb[0.1]) & (y <= b5 + rb[0.9]))[m]))}
    sal["por_tramo_de_minutos_esperados"] = tramos
    return sal


def brier_juega(jugadores, estados, prueba):
    """Brier de la probabilidad de jugar: tabla medida en la temporada anterior, en TODAS las anteriores, convención y tasa global."""
    jugo = {(p, j): ok for j, lista in jugadores.items() for (_, p, _, ok, _) in lista}
    pares = [(temporada_de(fecha), estado, jugo.get((p, j), False)) for (p, j), (estado, fecha) in estados.items()]
    anterior = f"{int(prueba[:4]) - 1}-{prueba[2:4]}"
    ent_ant = disp.tabla_estados([(e, ok) for t_, e, ok in pares if t_ == anterior])
    ent_todas = disp.tabla_estados([(e, ok) for t_, e, ok in pares if t_ < prueba])
    test = [(e, ok) for t_, e, ok in pares if t_ == prueba]
    y = np.array([ok for _, ok in test], dtype=float)
    tasa = float(np.mean([ok for t_, e, ok in pares if t_ < prueba]))

    def brier(tabla):
        return float(np.mean((np.array([tabla[e]["p"] if e in tabla else tasa for e, _ in test]) - y) ** 2))

    return {"n": len(test), "temporada_anterior": anterior,
            "brier_tabla_temporada_anterior": brier(ent_ant), "brier_tabla_todas_las_anteriores": brier(ent_todas),
            "brier_convencion_inicial": float(np.mean((np.array([disp.prob_juega(e) for e, _ in test]) - y) ** 2)),
            "brier_tasa_global": float(np.mean((tasa - y) ** 2)),
            "tabla_temporada_anterior": {e: {"p": round(v["p"], 4), "n": v["n"]} for e, v in ent_ant.items()}}


if __name__ == "__main__":
    carpeta = Path(sys.argv[1])
    prueba = sys.argv[2] if len(sys.argv) > 2 else "2025-26"
    jugadores, estados = leer(carpeta)
    tablas, sin_parte = calibracion(jugadores, estados)
    informe = {"prueba": prueba,
               "calibracion_estados_por_temporada": {t_: {str(e): {"n": d["n"], "p": round(d["p"], 3)} for e, d in tabla.items()}
                                                     for t_, tabla in tablas.items()},
               "sin_parte": sin_parte,
               "brier_juega": brier_juega(jugadores, estados, prueba),
               "minutos": minutos_eval(jugadores, prueba)}
    print(json.dumps(informe, ensure_ascii=False, indent=1))
