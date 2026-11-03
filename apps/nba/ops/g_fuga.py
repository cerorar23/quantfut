"""G-fuga: reproducibilidad puntual del motor v2.0 de equipo sobre `nba_datos` (solo lectura).

    NBA_DB_DSN=postgresql://... python -m ... apps/nba/ops/g_fuga.py [temporada=2025-26] [n=200]

Para n partidos pasados reparte el corte a las 12:00 UTC de su fecha y comprueba:
  1. Repetibilidad: dos instantáneas del mismo (partido, corte) dan la misma huella `version_datos` y el motor, la misma distribución.
  2. Sin fuga: ninguna fila de la historia es de la fecha del partido o posterior; las filas propias no incluyen la fase `final`.
  3. Correctitud contra una implementación independiente: ratings reproducidos desde una consulta distinta (sin DISTINCT ON ni
     función punto-en-el-tiempo) jugando los partidos por fecha, con las predicciones de cada fecha antes de actualizar con ella.
  4. Alarma de fuga: Brier del ganador por debajo de 0,18 en estos partidos obliga a revisar antes de celebrar.
Escribe una línea JSON con el resumen; no escribe nada en la base (transacción de solo lectura).
"""
from collections import defaultdict
from datetime import datetime, UTC
import json
import os
from pathlib import Path
import sys

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from nba.contratos.validar import ContratoIncumplido, validar_equipo, validar_jugador  # noqa: E402
from nba.v2 import equipo_jugadores, identidad, motor_equipo, motor_jugadores, nucleo, parametros, pit, props  # noqa: E402
from nba.v2.plantilla_pit import plantilla  # noqa: E402
import numpy as np  # noqa: E402
from nba.v2.nucleo import Ratings  # noqa: E402

CAJA = """
WITH f AS (
  SELECT d.partido_id, d.entidad_id, m.nombre, d.valor,
         row_number() OVER (PARTITION BY d.partido_id, d.entidad_id, d.metrica_id
                            ORDER BY CASE d.fuente WHEN 'nba_oficial' THEN 0 WHEN 'sofascore' THEN 1 ELSE 2 END, d.recibido_en DESC, d.dato_id DESC) AS rk
  FROM nba.dato d JOIN nba.metrica m ON m.metrica_id = d.metrica_id
  WHERE d.fuente IN ('nba_oficial', 'sofascore', 'espn') AND d.fase = 'final' AND d.periodo = 0
    AND m.nombre IN ('minutos', 'puntos', 'rebotes', 'asistencias', 'triples_anotados', 'equipo_del_jugador'))
SELECT e.fecha_juego_et, f.partido_id, f.entidad_id,
  max(CASE WHEN f.nombre = 'minutos' THEN f.valor END), max(CASE WHEN f.nombre = 'puntos' THEN f.valor END),
  max(CASE WHEN f.nombre = 'rebotes' THEN f.valor END), max(CASE WHEN f.nombre = 'asistencias' THEN f.valor END),
  max(CASE WHEN f.nombre = 'triples_anotados' THEN f.valor END), max(CASE WHEN f.nombre = 'equipo_del_jugador' THEN f.valor END)
FROM f JOIN nba.entidad e ON e.entidad_id = f.partido_id AND e.canonica_id = e.entidad_id
WHERE f.rk = 1
GROUP BY 1, 2, 3 HAVING max(CASE WHEN f.nombre = 'minutos' THEN f.valor END) > 0
   AND max(CASE WHEN f.nombre = 'equipo_del_jugador' THEN f.valor END) IS NOT NULL      -- solo jugadores: los equipos también tienen minutos
ORDER BY 1, 2, 3
"""

REFERENCIA = """
WITH f AS (
  SELECT d.partido_id, d.entidad_id, d.valor,
         row_number() OVER (PARTITION BY d.partido_id, d.entidad_id
                            ORDER BY CASE d.fuente WHEN 'nba_oficial' THEN 0 WHEN 'sofascore' THEN 1 ELSE 2 END, d.recibido_en DESC, d.dato_id DESC) AS rk
  FROM nba.dato d JOIN nba.metrica m ON m.metrica_id = d.metrica_id
  WHERE m.nombre = 'puntos' AND d.periodo = 0 AND d.fase = 'final' AND d.fuente IN ('nba_oficial', 'sofascore', 'espn'))
SELECT e.fecha_juego_et, e.entidad_id, tl.id_en_fuente, tv.id_en_fuente,
       max(CASE WHEN f.entidad_id = tl.entidad_id THEN f.valor END), max(CASE WHEN f.entidad_id = tv.entidad_id THEN f.valor END)
FROM nba.entidad e
JOIN nba.entidad tl ON tl.entidad_id = (e.atributos->>'local')::bigint
JOIN nba.entidad tv ON tv.entidad_id = (e.atributos->>'visitante')::bigint
JOIN f ON f.partido_id = e.entidad_id AND f.rk = 1 AND f.entidad_id IN (tl.entidad_id, tv.entidad_id)
WHERE e.tipo = 'partido' AND e.canonica_id = e.entidad_id
GROUP BY 1, 2, 3, 4 HAVING count(DISTINCT f.entidad_id) = 2
ORDER BY 1, 2
"""


def referencia_por_fecha(filas, objetivos):
    """mu (local, visitante) de cada partido objetivo: ratings con todos los partidos de fechas ESTRICTAMENTE anteriores."""
    p = motor_equipo.PARAMETROS
    r, ultimo, temporada, salida = Ratings(), {}, None, {}
    por_fecha = defaultdict(list)
    for f in filas:
        por_fecha[f[0]].append(f)
    for fecha in sorted(por_fecha):
        t = identidad.temporada(fecha)
        if t != temporada:
            if temporada is not None:
                nucleo.nueva_temporada(r, p)
            temporada = t
        dias = {}
        for _, pid, lo, vi, _, _ in por_fecha[fecha]:
            dl = (fecha - ultimo[lo]).days if lo in ultimo else 7
            dv = (fecha - ultimo[vi]).days if vi in ultimo else 7
            dias[pid] = nucleo.ajuste_descanso(dl, dv, p)
            if pid in objetivos:
                salida[pid] = r.esperado(lo, vi, dias[pid])
        for _, pid, lo, vi, pl, pv in por_fecha[fecha]:
            nucleo.actualizar(r, lo, vi, pl, pv, p, dias[pid])
        for _, pid, lo, vi, _, _ in por_fecha[fecha]:
            ultimo[lo] = ultimo[vi] = fecha
    return salida


def referencia_plantilla(caja, juegos, equipos_ids, objetivo, en_parte):
    """Plantilla de (partido objetivo, lado) calculada desde cero: jugadores con ≥ 5 partidos, historial de 30 y último equipo, usando
    solo partidos de fecha estrictamente anterior. Camino distinto de `plantilla_pit` (sin DISTINCT ON ni punto en el tiempo)."""
    fecha, pid, tri_l, tri_v = objetivo
    antes = [r for r in caja if r[0] < fecha]
    por_jugador = defaultdict(list)
    for r in antes:
        por_jugador[r[2]].append(r)
    salida = {}
    for lado, tri in (("local", tri_l), ("visitante", tri_v)):
        eq = equipos_ids[tri]
        pids = [g[1] for g in juegos if g[0] < fecha and tri in (g[2], g[3])][-10:]
        plantel = {r[2] for r in antes if r[1] in pids and int(r[8]) == eq}
        for jug, filas in por_jugador.items():
            if int(filas[-1][8]) == eq and (jug in plantel or jug in en_parte) and len(filas) >= 5:
                ult = filas[-30:]
                salida[jug] = (lado, tuple(float(r[3]) for r in ult), tuple(tuple(float(x or 0.0) for x in r[4:8]) for r in ult))
    return salida


def probar_jugadores(db, elegidos, n, ref_equipo=None):
    par = parametros.cargar_props()
    caja = db.execute(CAJA).fetchall()
    equipos_ids = {tri: eid for eid, tri in db.execute("SELECT entidad_id, id_en_fuente FROM nba.entidad WHERE tipo = 'equipo'").fetchall()}
    juegos = [(f, int(pid), lo, vi) for f, pid, lo, vi, _, _ in db.execute(REFERENCIA).fetchall()]
    real = {(r[1], r[2]): r for r in caja}
    imp = parametros.cargar_impacto()
    res = {"n": 0, "difs_repetibilidad": 0, "difs_plantilla_vs_referencia": 0, "pronosticos": 0, "pit": [], "difs_repetibilidad_mezcla": 0,
           "mezclas_2_1": 0, "mezclas_respaldo_2_0": 0, "max_dif_mezcla_vs_referencia": 0.0, "violaciones_contrato": 0, "validados": 0}
    paso = max(1, len(elegidos) // n)
    for fecha, pid, lo, vi, _, _ in elegidos[::paso][:n]:
        corte = datetime(fecha.year, fecha.month, fecha.day, 12, tzinfo=UTC)
        inst = pit.instantanea(db, pid, corte)
        a, b = plantilla(db, inst), plantilla(db, pit.instantanea(db, pid, corte))
        ra, rb = motor_jugadores.pronosticar(a, par), motor_jugadores.pronosticar(b, par)
        res["n"] += 1
        if a.version_datos != b.version_datos or ra != rb:
            res["difs_repetibilidad"] += 1
        en_parte = {r[0] for r in db.execute("SELECT DISTINCT d.entidad_id FROM nba.dato d JOIN nba.metrica m ON m.metrica_id = d.metrica_id "
                                             "WHERE d.partido_id = %s AND m.nombre = 'estado_disponibilidad' AND d.fuente = 'nba_oficial' AND d.recibido_en <= %s",
                                             (pid, corte)).fetchall()}
        ref = referencia_plantilla(caja, juegos, equipos_ids, (fecha, pid, lo, vi), en_parte)
        motor = {j.id: (lado, j.minutos, j.stats) for lado, js in a.lados.items() for j in js}
        if motor != ref:
            res["difs_plantilla_vs_referencia"] += 1
            ej = {"partido": pid, "solo_motor": len(motor.keys() - ref.keys()), "solo_referencia": len(ref.keys() - motor.keys())}
            for jug in motor.keys() & ref.keys():
                if motor[jug] != ref[jug]:
                    m, r_ = motor[jug], ref[jug]
                    ej["jugador"] = jug
                    ej["lado"] = (m[0], r_[0])
                    ej["n_minutos"] = (len(m[1]), len(r_[1]))
                    ej["minutos_distintos"] = [(i, a_, b_) for i, (a_, b_) in enumerate(zip(m[1], r_[1])) if a_ != b_][:3]
                    ej["stats_distintas"] = [(i, a_, b_) for i, (a_, b_) in enumerate(zip(m[2], r_[2])) if a_ != b_][:3]
                    break
            res.setdefault("ejemplos", []).append(ej)
        # mezcla equipo + jugadores (v2.1): repetible y con el margen igual a la media del margen de equipo INDEPENDIENTE y el de jugadores
        try:
            va, esc_a, dist_a = equipo_jugadores.pronosticar(inst, a, imp, par)
            vb, esc_b, dist_b = equipo_jugadores.pronosticar(inst, b, imp, par)
        except ValueError:                                   # sin historia visible: el motor se niega, igual que en producción
            res["pronosticos"] += len(ra)
            continue
        try:                                                 # frontera: todo lo que el motor produciría debe cumplir el contrato
            validar_equipo(dist_a)
            for x in ra:
                validar_jugador(x["distribucion"])
            res["validados"] += 1 + len(ra)
        except ContratoIncumplido as e:
            res["violaciones_contrato"] += 1
            res.setdefault("ejemplos_contrato", []).append({"partido": pid, "error": str(e)[:200]})
        if (va, esc_a, dist_a) != (vb, esc_b, dist_b):
            res["difs_repetibilidad_mezcla"] += 1
        if va.startswith("equipo-2.1") and ref_equipo is not None and pid in ref_equipo:
            res["mezclas_2_1"] += 1
            t_l, t_v = ref_equipo[pid]
            esperado = ((t_l - t_v) + esc_a["margen_jugadores"]) / 2
            res["max_dif_mezcla_vs_referencia"] = max(res["max_dif_mezcla_vs_referencia"], abs((dist_a["mu"][0] - dist_a["mu"][1]) - esperado),
                                                      abs((dist_a["mu"][0] + dist_a["mu"][1]) - (t_l + t_v)))
        else:
            res["mezclas_respaldo_2_0"] += 1
        res["pronosticos"] += len(ra)
        for x in ra:
            if x["mercado"] == "jugador:puntos" and (pid, x["jugador"]) in real:
                pmf = np.array([x["distribucion"]["pmf"]])
                res["pit"].append(float(props.pit_aleatorio(pmf, np.array([real[(pid, x["jugador"])][4]]), semilla=len(res["pit"]))[0]))
    pit_ = np.array(res.pop("pit"))
    res["cobertura80_puntos"] = float(np.mean((pit_ > 0.1) & (pit_ < 0.9))) if len(pit_) else None
    res["n_puntos_evaluados"] = int(len(pit_))
    res["ejemplos"] = res.get("ejemplos", [])[:5]
    res["aprobado"] = (res["difs_repetibilidad"] == 0 and res["difs_plantilla_vs_referencia"] == 0 and res["pronosticos"] > 0
                       and res["difs_repetibilidad_mezcla"] == 0 and res["violaciones_contrato"] == 0 and res["max_dif_mezcla_vs_referencia"] < 2e-3 and res["mezclas_2_1"] > 0
                       and res["cobertura80_puntos"] is not None and 0.74 <= res["cobertura80_puntos"] <= 0.86)
    return res


def main(temporada: str, n: int):
    with psycopg.connect(os.environ["NBA_DB_DSN"]) as db:
        db.execute("SET TRANSACTION READ ONLY")
        filas = [(f, int(pid), lo, vi, float(a), float(b)) for f, pid, lo, vi, a, b in db.execute(REFERENCIA).fetchall()]
        prueba = [f for f in filas if identidad.temporada(f[0]) == temporada]
        paso = max(1, len(prueba) // n)
        elegidos = prueba[::paso][:n]
        objetivos = {f[1] for f in elegidos}
        ref = referencia_por_fecha(filas, objetivos)
        res = {"temporada": temporada, "n": len(elegidos), "difs_repetibilidad": 0, "fugas_historia": 0, "fugas_propias": 0,
               "max_dif_mu_vs_referencia": 0.0, "sin_historia": 0}
        p_local, y = [], []
        for fecha, pid, lo, vi, pl, pv in elegidos:
            corte = datetime(fecha.year, fecha.month, fecha.day, 12, tzinfo=UTC)
            a, b = pit.instantanea(db, pid, corte), pit.instantanea(db, pid, corte)
            if a.version_datos != b.version_datos:
                res["difs_repetibilidad"] += 1
            res["fugas_historia"] += int(any(h[0] >= fecha for h in a.historia))
            res["fugas_propias"] += int(any(x[3] == "final" for x in a.propias))
            try:
                esc_a, dist_a = motor_equipo.pronosticar(a)
            except ValueError:
                res["sin_historia"] += 1
                continue
            if (esc_a, dist_a) != motor_equipo.pronosticar(b):
                res["difs_repetibilidad"] += 1
            mu = dist_a["mu"]
            dif = max(abs(mu[0] - ref[pid][0]), abs(mu[1] - ref[pid][1]))
            res["max_dif_mu_vs_referencia"] = max(res["max_dif_mu_vs_referencia"], dif)
            n_ref = sum(1 for f in filas if f[0] < fecha)
            if dif > 1e-3 or n_ref != len(a.historia):
                res.setdefault("discrepancias", []).append({"pid": pid, "fecha": fecha.isoformat(), "dif": round(dif, 3),
                                                            "n_historia_motor": len(a.historia), "n_historia_ref": n_ref})
            p_local.append(dist_a["p_local"])
            y.append(1.0 if pl > pv else 0.0)
        res["discrepancias"] = res.get("discrepancias", [])[:6]
        res["jugadores"] = probar_jugadores(db, elegidos, int(os.environ.get("NBA_G_FUGA_JUGADORES", "60")), ref)
        res["brier_ganador"] = sum((p - o) ** 2 for p, o in zip(p_local, y)) / len(y)
        res["alarma_fuga_brier_menor_0_18"] = res["brier_ganador"] < 0.18
        res["aprobado_equipo"] = (res["difs_repetibilidad"] == 0 and res["fugas_historia"] == 0 and res["fugas_propias"] == 0
                           and res["max_dif_mu_vs_referencia"] < 1e-3 and not res["alarma_fuga_brier_menor_0_18"])
        res["aprobado"] = res["aprobado_equipo"] and res["jugadores"]["aprobado"]
    print(json.dumps(res))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "2025-26", int(sys.argv[2]) if len(sys.argv) > 2 else 200)
