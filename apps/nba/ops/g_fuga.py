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
from nba.v2 import identidad, motor_equipo, nucleo, pit  # noqa: E402
from nba.v2.nucleo import Ratings  # noqa: E402

REFERENCIA = """
SELECT e.fecha_juego_et, e.entidad_id, tl.id_en_fuente, tv.id_en_fuente,
       max(CASE WHEN d.entidad_id = tl.entidad_id THEN d.valor END), max(CASE WHEN d.entidad_id = tv.entidad_id THEN d.valor END)
FROM nba.entidad e
JOIN nba.entidad tl ON tl.entidad_id = (e.atributos->>'local')::bigint
JOIN nba.entidad tv ON tv.entidad_id = (e.atributos->>'visitante')::bigint
JOIN nba.dato d ON d.partido_id = e.entidad_id AND d.periodo = 0 AND d.fase = 'final' AND d.fuente = 'nba_oficial'
JOIN nba.metrica m ON m.metrica_id = d.metrica_id AND m.nombre = 'puntos'
WHERE e.tipo = 'partido' AND e.canonica_id = e.entidad_id AND d.entidad_id IN (tl.entidad_id, tv.entidad_id)
GROUP BY 1, 2, 3, 4 HAVING count(DISTINCT d.entidad_id) = 2
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
        res["brier_ganador"] = sum((p - o) ** 2 for p, o in zip(p_local, y)) / len(y)
        res["alarma_fuga_brier_menor_0_18"] = res["brier_ganador"] < 0.18
        res["aprobado"] = (res["difs_repetibilidad"] == 0 and res["fugas_historia"] == 0 and res["fugas_propias"] == 0
                           and res["max_dif_mu_vs_referencia"] < 1e-3 and not res["alarma_fuga_brier_menor_0_18"])
    print(json.dumps(res))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "2025-26", int(sys.argv[2]) if len(sys.argv) > 2 else 200)
