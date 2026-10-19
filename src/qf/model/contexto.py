"""Bloques de contexto para la capa de ajuste de lambdas: descanso, altitud, clima, bajas y valor del once.

Pasa a la capa de ajuste (`ajuste.py`, F1) la información que se captura desde el 18-oct-2026 y que ningún motor usaba:
calendario completo de cada equipo, altitud del estadio, clima de Copernicus y bajas con valor de mercado de FotMob. Cada
bloque se mide contra el modelo SOLO DE NIVEL (mismo walk-forward fuera de muestra, mismas filas, 30 % final de validación)
con la puerta del proyecto: mejora RPS y log-loss, no empeora la calibración, mejora en al menos 2 ligas y es
estadísticamente significativa. Un bloque que no la pasa no entra al motor.

Honestidad sobre el momento en que se conoce cada dato (point-in-time):
- `descanso`, `altitud`: se conocen a la hora de la corrida diaria (03:00): calendario y sede.
- `clima`: aquí es el clima OBSERVADO (reanálisis ERA5). En producción se usaría el pronóstico, que no es lo mismo: el efecto
  medido es una cota optimista. El pronóstico se acumula desde el 18-oct en `fotmob_previo`.
- `bajas`: lista de no disponibles que FotMob guardó DESPUÉS del partido (reconstrucción). El equivalente previo se acumula
  desde el 18-oct. Falta distinguir «sin bajas» de «lista no publicada»: sin filas se toma 0, lo que sesga.
- `xi_valor`: usa el once REAL, que solo se conoce al confirmarse (T-60): no entra a la corrida de las 03:00, solo al sello
  tardío (F7). Se mide aquí para saber si vale la pena construirlo.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import ajuste
from . import lineup_challenger as lc

BLOQUES_CONTEXTO: dict[str, tuple[str, ...]] = {
    "descanso": ("desc_log_local", "desc_log_visita", "carga14_local", "carga14_visita"),
    "altitud": ("alt_sede_km", "alt_dif_km"),
    "altitud_salto": ("alt_dif_km",),        # candidato a producción: solo el salto de altura (físicamente coherente)
    "clima": ("temp_c", "temp_desv2", "lluvia_log", "viento_ms", "humedad_pct"),
    "bajas": ("bajas_rel_local", "bajas_rel_visita", "n_bajas_local", "n_bajas_visita"),
    "xi_valor": ("xi_valor_log_dif", "xi_edad_dif"),
}
TOPE_DESCANSO_DIAS = 14.0
TEMPERATURA_REFERENCIA_C = 15.0


def registrar_bloques() -> None:
    for nombre, columnas in BLOQUES_CONTEXTO.items():
        ajuste.registrar(ajuste.Bloque(nombre, columnas))


# ------------------------------------------------------------------------------------- funciones puras
def log_descanso(dias) -> float:
    """log(1 + días de descanso) con tope de 14 días; sin dato, NaN (la capa de ajuste lo rellena con la mediana)."""
    if dias is None or not np.isfinite(float(dias)) or float(dias) < 0:
        return float("nan")
    return float(np.log1p(min(float(dias), TOPE_DESCANSO_DIAS)))


def relativo_bajas(valor_bajas, valor_xi) -> float:
    """Valor perdido sobre el valor del plantel disponible + perdido, en [0, 1]; NaN si no hay valor del once."""
    if valor_xi is None or not np.isfinite(float(valor_xi)) or float(valor_xi) <= 0:
        return float("nan")
    v = float(valor_bajas or 0.0)
    return v / (float(valor_xi) + v)


def altitud_features(altitud_sede_m, altitud_habitual_visita_m) -> tuple[float, float]:
    """(altitud de la sede en km, cuánto más alto juega que lo habitual del visitante, en km, nunca negativo)."""
    if altitud_sede_m is None or not np.isfinite(float(altitud_sede_m)):
        return float("nan"), float("nan")
    sede = float(altitud_sede_m)
    habitual = altitud_habitual_visita_m
    dif = max(0.0, sede - float(habitual)) if habitual is not None and np.isfinite(float(habitual)) else float("nan")
    return sede / 1000.0, dif / 1000.0


def clima_features(temperatura, humedad, viento, lluvia_mm) -> dict[str, float]:
    ok = lambda v: v is not None and np.isfinite(float(v))  # noqa: E731
    return {
        "temp_c": float(temperatura) if ok(temperatura) else float("nan"),
        "temp_desv2": (float(temperatura) - TEMPERATURA_REFERENCIA_C) ** 2 if ok(temperatura) else float("nan"),
        "lluvia_log": float(np.log1p(max(float(lluvia_mm), 0.0))) if ok(lluvia_mm) else float("nan"),
        "viento_ms": float(viento) if ok(viento) else float("nan"),
        "humedad_pct": float(humedad) if ok(humedad) else float("nan"),
    }


def cobertura(frame: pd.DataFrame, columnas: tuple[str, ...]) -> float:
    """Fracción de filas con TODAS las columnas del bloque con dato."""
    if frame.empty:
        return 0.0
    return round(float(frame[list(columnas)].notna().all(axis=1).mean()), 3)


# --------------------------------------------------------------------------------------- acceso a datos
def _por_lado(filas: list[dict], clave: str, destino: str) -> pd.DataFrame:
    """Pivota (match_id, lado) a dos columnas `<destino>_local` y `<destino>_visita`."""
    if not filas:
        return pd.DataFrame(columns=["match_id"])
    d = pd.DataFrame(filas)
    d["lado"] = d["lado"].map({"home": "local", "away": "visita"})
    p = d.pivot_table(index="match_id", columns="lado", values=clave, aggfunc="first")
    p.columns = [f"{destino}_{c}" for c in p.columns]
    return p.reset_index()


def altitudes_de(ids: list[str]) -> pd.DataFrame:
    """Altitud de la sede y altitud habitual del visitante, en metros, para los partidos `ids`.

    Sede = el estadio del partido si ya está asignado; si no (partidos a más de 24 h, cuya sede se asigna con la captura
    previa), el estadio habitual del local, que en liga es casi siempre el mismo. Habitual = promedio de la altitud de los
    estadios donde ese equipo ha jugado de local. Es la misma definición en la medición y en producción.
    """
    from ..db import query
    return pd.DataFrame(query(
        """WITH hab AS (SELECT mm.home_team_id AS team_id, avg(aa.altitud_m) AS habitual
                        FROM matches mm JOIN estadio_altitud aa USING (stadium_id) GROUP BY 1)
           SELECT m.match_id, COALESCE(a.altitud_m, hl.habitual) AS sede_m, hv.habitual AS hab_visita_m
           FROM matches m
           LEFT JOIN estadio_altitud a ON a.stadium_id = m.stadium_id
           LEFT JOIN hab hl ON hl.team_id = m.home_team_id
           LEFT JOIN hab hv ON hv.team_id = m.away_team_id
           WHERE m.match_id = ANY(%s)""", (ids,)), columns=["match_id", "sede_m", "hab_visita_m"])


def construir_columnas(ids: list[str]) -> pd.DataFrame:
    """Todas las columnas de contexto de los partidos `ids`. Un dato ausente queda NaN, nunca 0."""
    from ..db import query
    base = pd.DataFrame({"match_id": ids})

    # descanso y carga (calendario completo de cada equipo): una sola consulta a la vista
    filas = query("SELECT match_id, lado, dias_descanso, partidos_14d FROM v_descanso_equipo WHERE match_id = ANY(%s)",
                  (ids,))
    desc = _por_lado([{"match_id": f["match_id"], "lado": f["lado"], "d": log_descanso(f["dias_descanso"])}
                      for f in filas], "d", "desc_log")
    carga = _por_lado([{"match_id": f["match_id"], "lado": f["lado"], "c": f["partidos_14d"]} for f in filas],
                      "c", "carga14")
    # altitud (misma definición que usará producción: ver `altitudes_de`)
    alt = altitudes_de(ids)
    if not alt.empty:
        f = [altitud_features(r.sede_m, r.hab_visita_m) for r in alt.itertuples()]
        alt = pd.DataFrame({"match_id": alt["match_id"], "alt_sede_km": [x[0] for x in f],
                            "alt_dif_km": [x[1] for x in f]})
    # clima observado (ERA5)
    cli = pd.DataFrame(query("SELECT match_id, temperatura_c, humedad_pct, viento_ms, precipitacion_mm "
                             "FROM clima_era5_partido WHERE match_id = ANY(%s)", (ids,)))
    if not cli.empty:
        cf = [clima_features(r.temperatura_c, r.humedad_pct, r.viento_ms, r.precipitacion_mm) for r in cli.itertuples()]
        cli = pd.concat([cli[["match_id"]].reset_index(drop=True), pd.DataFrame(cf)], axis=1)
    # bajas (FotMob, reconstrucción) y valor del once
    fm = pd.DataFrame(query("SELECT match_id, valor_xi_local, valor_xi_visita, edad_xi_local, edad_xi_visita "
                            "FROM fotmob_partido WHERE match_id = ANY(%s)", (ids,)))
    bajas = pd.DataFrame(query("SELECT match_id, side, count(*) AS n, coalesce(sum(valor_mercado), 0) AS v "
                               "FROM fotmob_baja WHERE match_id = ANY(%s) GROUP BY 1, 2", (ids,)))
    out = base
    for parte in (desc, carga, alt, cli):
        if not parte.empty:
            out = out.merge(parte, on="match_id", how="left")
    if not fm.empty:
        por_lado = [{"match_id": r.match_id, "lado": r.side, "n": r.n, "v": r.v} for r in bajas.itertuples()]
        nb = _por_lado(por_lado, "n", "n_bajas")
        vb = _por_lado(por_lado, "v", "valor_bajas")
        fm = fm.merge(nb, on="match_id", how="left").merge(vb, on="match_id", how="left")
        for c in ("n_bajas_local", "n_bajas_visita", "valor_bajas_local", "valor_bajas_visita"):
            if c not in fm.columns:
                fm[c] = 0.0
            fm[c] = fm[c].fillna(0.0).astype(float)      # sin filas = 0 (ver el aviso del encabezado)
        fm["bajas_rel_local"] = [relativo_bajas(v, x) for v, x in zip(fm["valor_bajas_local"], fm["valor_xi_local"])]
        fm["bajas_rel_visita"] = [relativo_bajas(v, x) for v, x in zip(fm["valor_bajas_visita"], fm["valor_xi_visita"])]
        vl, vv = fm["valor_xi_local"].astype(float), fm["valor_xi_visita"].astype(float)
        fm["xi_valor_log_dif"] = np.where((vl > 0) & (vv > 0), np.log(vl.clip(lower=1)) - np.log(vv.clip(lower=1)),
                                          np.nan)
        fm["xi_edad_dif"] = fm["edad_xi_local"].astype(float) - fm["edad_xi_visita"].astype(float)
        out = out.merge(fm[["match_id", "bajas_rel_local", "bajas_rel_visita", "n_bajas_local", "n_bajas_visita",
                            "xi_valor_log_dif", "xi_edad_dif"]], on="match_id", how="left")
    for c in {c for cols in BLOQUES_CONTEXTO.values() for c in cols}:
        if c not in out.columns:
            out[c] = np.nan
    return out


def marco_contexto(oos: pd.DataFrame) -> pd.DataFrame:
    """Predicciones fuera de muestra del walk-forward con las columnas de contexto de cada partido."""
    base = lc._historical_matches(oos)
    if base.empty:
        return base
    base["kickoff_utc"] = pd.to_datetime(base["kickoff_utc"], utc=True)
    return base.merge(construir_columnas(list(base["match_id"])), on="match_id", how="left")


# --------------------------------------------------------------------------------------------- evaluación
def evaluar(frame: pd.DataFrame, bloques: list[str] | None = None, **kw) -> dict:
    """Cada bloque solo contra el modelo de nivel, y luego los aceptados juntos (de a uno, en orden)."""
    registrar_bloques()
    bloques = bloques or list(BLOQUES_CONTEXTO)
    individuales = {}
    for nombre in bloques:
        r = ajuste.comparar(frame, [], [nombre], **kw)
        r["cobertura_filas"] = cobertura(frame, BLOQUES_CONTEXTO[nombre])
        individuales[nombre] = r
    aceptados = [n for n in bloques if individuales[n].get("ok")]
    conjunto = ajuste.comparar(frame, [], aceptados, **kw) if aceptados else None
    return {"individuales": individuales, "aceptados": aceptados, "conjunto": conjunto}


def resumen(res: dict) -> dict:
    """Lo esencial de cada bloque, para leerlo de un vistazo."""
    def fila(r: dict) -> dict:
        if not r.get("n_val"):
            return {"estado": r.get("status"), "motivo": r.get("reason")}
        return {"ok": r["ok"], "n_val": r["n_val"], "rps": f'{r["rps_before"]} -> {r["rps_after"]}',
                "delta_rps": r["delta_rps_media"], "p95": r["delta_rps_p95"],
                "log_loss": f'{r["log_loss_before"]} -> {r["log_loss_after"]}',
                "ece_empeora": r["ece_empeora"], "ligas_que_mejoran": f'{r["leagues_improved"]}/{len(r["by_league"])}',
                "cobertura": r.get("cobertura_filas")}
    out = {n: fila(r) for n, r in res["individuales"].items()}
    out["aceptados"] = res["aceptados"]
    if res["conjunto"]:
        out["conjunto_de_aceptados"] = fila(res["conjunto"])
    return out


def main(argv=None) -> None:
    import argparse
    import glob
    import json
    import os

    from ..config import settings
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--oos", help="oos_<versión>.pkl; por defecto el más reciente")
    ap.add_argument("--bloques", nargs="*", default=None)
    a = ap.parse_args(argv)
    ruta = a.oos or max(glob.glob(f"{settings.artifact_dir}/oos_*.pkl"), key=os.path.getmtime)
    frame = marco_contexto(pd.read_pickle(ruta))
    res = evaluar(frame, a.bloques)
    print(json.dumps({"oos": os.path.basename(ruta), "filas": int(len(frame)), "resultado": resumen(res)},
                     indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
