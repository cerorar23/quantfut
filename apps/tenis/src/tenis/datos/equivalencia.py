"""Prueba de propiedad: lo que la exportación considera visible en el corte de cada partido es IDÉNTICO a lo que
devuelve la puerta oficial de la base (`partido_a_las`, `programa_a_las`, `resultado_a_las`, `estadistica_a_las`,
`ranking_a_las(corte, fecha)`), y no hay fuga.

Para cada partido de una muestra aleatoria (semilla fija) con corte c y fecha f:
  1. partidos visibles: {partido_id con vis < c} (visibilidad_filas) == partido_a_las(c)
  2. programas, resultados y estadísticas vigentes (clave, id de fila) == programa/resultado/estadistica_a_las(c)
  3. ranking de cada lado (ranking_id o nada) == ranking_a_las(c, f) para ese jugador
  4. eventos visibles {partido_key con visible_resultado_utc < c} == eventos cuya fila de resultado está en
     resultado_a_las(c); estadísticas de saque visibles == las de la puerta cuyo evento ya es visible
  5. fuga: el propio partido no está entre sus eventos visibles ni su resultado en la puerta; ningún evento visible
     tiene visible_resultado_utc >= c.
Solo lectura (transacción READ ONLY). Las consultas a la base van en paralelo con varias conexiones.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from .lectura import conexion_lectura
from .visibilidad import vigente_en


def _cargar(directorio: Path) -> dict:
    return {n: pd.read_parquet(directorio / f"{n}.parquet")
            for n in ("partidos", "eventos_resultado", "ranking_asof", "estadisticas_saque", "visibilidad_filas")}


class _Export:
    """Vista de la exportación para consultar «qué es visible en c» deprisa."""

    def __init__(self, d: dict):
        vf = d["visibilidad_filas"]
        self.tablas = {}
        for tabla, claves in (("partido", ["partido_id"]), ("programa", ["partido_id"]), ("resultado", ["partido_id"]),
                              ("estadistica", ["partido_id", "lado"])):
            x = vf[vf["tabla"] == tabla].copy()
            unico = not x.duplicated(claves).any()
            self.tablas[tabla] = (x, claves, unico)
        ev = d["eventos_resultado"]
        self.ev_key = ev["partido_key"].to_numpy()
        self.ev_vis = ev["visible_resultado_utc"].dt.tz_convert(None).to_numpy()
        self.ev_rid = ev["resultado_id"].to_numpy(dtype="int64")
        self.rid_a_key = dict(zip(self.ev_rid, self.ev_key))
        es = d["estadisticas_saque"]
        self.es_key = list(zip(es["partido_key"], es["lado"].astype(int)))
        self.es_vis = es["visible_desde"].dt.tz_convert(None).to_numpy()
        self.es_id = es["estadistica_id"].to_numpy(dtype="int64")
        rk = d["ranking_asof"]
        self.rk = {(k, int(l)): (None if pd.isna(r) else int(r))
                   for k, l, r in zip(rk["partido_key"], rk["lado"], rk["ranking_id"])}

    def visibles(self, tabla: str, corte) -> set:
        x, claves, unico = self.tablas[tabla]
        if tabla == "partido":
            return set(x.loc[x["vis"] < corte, "partido_id"].astype(int))
        sel = x[x["vis"] < corte] if unico else vigente_en(x, corte, claves, "fila_id")
        cols = claves + ["fila_id"]
        return set(map(tuple, sel[cols].astype(int).to_numpy().tolist()))


def _puerta(conn, corte, fecha, jugadores) -> dict:
    q = lambda s, p=(corte,): conn.execute(s, p).fetchall()  # noqa: E731
    return {
        "partido": {r[0] for r in q("SELECT partido_id FROM partido_a_las(%s)")},
        "programa": set(q("SELECT partido_id, programa_id FROM programa_a_las(%s)")),
        "resultado": set(q("SELECT partido_id, resultado_id FROM resultado_a_las(%s)")),
        "estadistica": set(q("SELECT partido_id, lado::int, estadistica_id FROM estadistica_a_las(%s)")),
        "ranking": q("SELECT jugador_id, ranking_id FROM ranking_a_las(%s, %s) WHERE jugador_id = ANY(%s)",
                     (corte, fecha, list(jugadores))),
    }


def verificar(dsn: str, esquema: str, directorio: Path, n: int = 300, semilla: int = 20261105,
              hilos: int = 4) -> dict:
    """Ejecuta la prueba de propiedad sobre `n` partidos al azar con corte. Devuelve recuentos y discrepancias."""
    d = _cargar(Path(directorio))
    ex = _Export(d)
    p = d["partidos"]
    candidatos = p[p["corte_utc"].notna()].reset_index(drop=True)
    idx = np.random.RandomState(semilla).choice(len(candidatos), size=min(n, len(candidatos)), replace=False)
    muestra = candidatos.iloc[np.sort(idx)]
    trabajos = [(r.partido_key, r.corte_utc.to_pydatetime(), r.fecha_partido.date(), int(r.jugador_1),
                 int(r.jugador_2), r.y_resultado_id, r.partido_id_tml, r.partido_id_sofascore, r.fuente_tiempo,
                 r.excluir_motivo if isinstance(r.excluir_motivo, str) else None)
                for r in muestra.itertuples()]

    def uno(lote):
        salida = []
        with conexion_lectura(dsn, esquema) as conn:
            for t in lote:
                salida.append((t, _puerta(conn, t[1], t[2], (t[3], t[4]))))
        return salida

    lotes = [trabajos[i::hilos] for i in range(hilos)]
    with ThreadPoolExecutor(hilos) as pool:
        resultados = [x for parte in pool.map(uno, lotes) for x in parte]

    disc = {k: 0 for k in ("partido", "programa", "resultado", "estadistica", "ranking", "eventos",
                           "estadisticas_saque", "fuga_evento_propio", "fuga_resultado_propio_en_puerta",
                           "fuga_evento_posterior", "exclusion_injustificada")}
    ejemplos = []
    otra_fuente_visible = 0
    tam = {"partido": 0, "resultado": 0, "estadistica": 0, "eventos": 0}
    excluidos_detectados = 0
    for (key, corte, fecha, j1, j2, rid, pt, ps, ft, excl), g in resultados:
        c = pd.Timestamp(corte)
        for tabla in ("partido", "programa", "resultado", "estadistica"):
            mia = ex.visibles(tabla, c)
            if mia != g[tabla]:
                disc[tabla] += 1
                ejemplos.append({"partido_key": key, "tabla": tabla, "solo_export": len(mia - g[tabla]),
                                 "solo_puerta": len(g[tabla] - mia)})
            if tabla in tam:
                tam[tabla] += len(mia)
        gate_rk = {int(a): int(b) for a, b in g["ranking"]}
        for lado, j in ((1, j1), (2, j2)):
            if ex.rk.get((key, lado)) != gate_rk.get(j):
                disc["ranking"] += 1
                ejemplos.append({"partido_key": key, "tabla": "ranking", "lado": lado,
                                 "export": ex.rk.get((key, lado)), "puerta": gate_rk.get(j)})
        vis_ev = ex.ev_vis < np.datetime64(c.tz_convert(None))
        mios = set(ex.ev_key[vis_ev])
        rids_puerta = {r for _, r in g["resultado"]}
        de_puerta = {ex.rid_a_key[r] for r in rids_puerta if r in ex.rid_a_key}
        tam["eventos"] += len(mios)
        if mios != de_puerta:
            disc["eventos"] += 1
            ejemplos.append({"partido_key": key, "tabla": "eventos", "solo_export": len(mios - de_puerta),
                             "solo_puerta": len(de_puerta - mios)})
        propio = key in mios or (pd.notna(rid) and int(rid) in rids_puerta)
        if excl is not None:
            # La exportación ya lo marcó como no apto (p. ej. pareja y resultado visibles a la vez): debe ser cierto.
            excluidos_detectados += 1
            if excl == "resultado_visible_en_su_corte" and not propio:
                disc["exclusion_injustificada"] += 1
        else:
            if key in mios:
                disc["fuga_evento_propio"] += 1
            if pd.notna(rid) and int(rid) in rids_puerta:
                disc["fuga_resultado_propio_en_puerta"] += 1
        if (ex.ev_vis[vis_ev] >= np.datetime64(c.tz_convert(None))).any():
            disc["fuga_evento_posterior"] += 1
        # resultado de la OTRA fuente de un partido fusionado visible en la puerta antes del corte: es la fuga del
        # calendario de TML que la exportación evita al usar los tiempos de SofaScore (informativo, no discrepancia)
        otra = pt if ft == "sofascore" else ps
        if pd.notna(otra) and any(pid == int(otra) for pid, _ in g["resultado"]):
            otra_fuente_visible += 1
        es_vis = ex.es_vis < np.datetime64(c.tz_convert(None))
        mios_es = {k for k, v in zip(ex.es_key, es_vis) if v}
        ids_puerta = {e for _, _, e in g["estadistica"]}
        de_puerta_es = {k for k, e in zip(ex.es_key, ex.es_id) if e in ids_puerta and k[0] in mios}
        if mios_es != de_puerta_es:
            disc["estadisticas_saque"] += 1
            ejemplos.append({"partido_key": key, "tabla": "estadisticas_saque",
                             "solo_export": len(mios_es - de_puerta_es), "solo_puerta": len(de_puerta_es - mios_es)})
    return {"partidos_muestra": len(resultados), "semilla": semilla, "discrepancias": disc,
            "identico": all(v == 0 for v in disc.values()), "excluidos_en_muestra": excluidos_detectados,
            "fusionados_con_resultado_de_la_otra_fuente_visible_en_la_puerta": otra_fuente_visible,
            "filas_comparadas": tam, "ejemplos": ejemplos[:20]}
