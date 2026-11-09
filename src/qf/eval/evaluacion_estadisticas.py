"""
Córners y tarjetas hacia ModelEvaluator. Tarjetas = amarillas + rojas de cada equipo y solo
se emite el TOTAL (`prob()` no tiene mercados por equipo de tarjetas); si `partidos` trae la
columna `arbitro`, el modelo la usa como en producción.

Recorre los partidos en orden cronológico y, ANTES de añadir cada uno al acumulador de
`model.estadisticas_mercado`, pregunta por su probabilidad: es el mismo punto en el tiempo
que usa la prueba histórica del modelo, así que no hay fuga. El propio resultado y los
partidos posteriores no pueden mover una predicción (lo comprueban las pruebas).

Solo se emite la cara «over» de cada línea; el resto es su complemento (líneas medias, sin
devolución). Cada línea es un mercado (`corners_over_9.5`, `corners_local_over_4.5`) y el
total, el local y el visitante llevan una fila de RMSE con la media esperada y el valor real.

Los parámetros (φ, encogimiento, media vida) salieron de datos de 2019-2022: para una
medición honesta usa `desde` posterior a 2022-08, o la cifra será en parte dentro de muestra.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from qf.model.estadisticas_mercado import acumulador, prob

LINEAS_TOTAL = {"corners": (6.5, 7.5, 8.5, 9.5, 10.5, 11.5, 12.5),
                "cards": (2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5)}
LINEAS_EQUIPO = {"corners": (1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5)}   # tarjetas: sin mercado por equipo


def tabla_estadistica(partidos: pd.DataFrame, mercado: str = "corners",
                      desde: pd.Timestamp | None = None) -> pd.DataFrame:
    """
    partidos: evento, fecha (UTC), local, visitante, valor_local, valor_visit
              (córners, o amarillas + rojas, de cada equipo) y opcionalmente arbitro.
    mercado: "corners" o "cards".
    desde: solo se emiten filas de partidos con fecha >= desde; el acumulador aprende de todos.
    """
    acc = acumulador(mercado)
    df = partidos.sort_values(["fecha", "evento"])
    if df["evento"].duplicated().any():
        raise ValueError(f"Hay {int(df['evento'].duplicated().sum())} eventos duplicados")
    if (df["local"] == df["visitante"]).any():
        raise ValueError("Hay partidos con el mismo equipo de local y de visitante")
    if (df[["valor_local", "valor_visit"]] < 0).any().any():
        raise ValueError("Hay valores negativos")
    desde = None if desde is None else _utc(desde)
    filas: list[dict] = []
    sin_dato = con_prediccion = 0

    for r in df.itertuples(index=False):
        if pd.isna(r.valor_local) or pd.isna(r.valor_visit):
            sin_dato += 1
            continue
        fecha = _utc(r.fecha).to_pydatetime()
        arbitro = getattr(r, "arbitro", None)
        arbitro = arbitro if isinstance(arbitro, str) else None
        lam = acc.lambdas(fecha, r.local, r.visitante, arbitro)
        if lam is not None and (desde is None or _utc(r.fecha) >= desde):
            con_prediccion += 1
            filas.extend(_filas(mercado, r, lam))
        acc.agregar(fecha, r.local, r.visitante, int(r.valor_local), int(r.valor_visit), arbitro)

    out = pd.DataFrame(filas, columns=["evento", "mercado", "seleccion", "prob",
                                       "resultado", "esperado", "real"])
    out.attrs["cobertura"] = {"partidos": len(df), "con_prediccion": con_prediccion,
                              "sin_dato": sin_dato}
    return out


def _utc(t) -> pd.Timestamp:
    t = pd.Timestamp(t)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def _filas(mercado: str, r, lam: tuple[float, float]) -> list[dict]:
    vl, vv = float(r.valor_local), float(r.valor_visit)
    filas = []

    def add(nombre, lado_mercado, linea, valor):
        filas.append({"evento": r.evento, "mercado": f"{nombre}_over_{linea}",
                      "seleccion": "over", "prob": prob(lado_mercado, lam, "over", linea),
                      "resultado": float(valor > linea), "esperado": np.nan, "real": np.nan})

    for ln in LINEAS_TOTAL[mercado]:
        add(mercado, mercado, ln, vl + vv)
    for ln in LINEAS_EQUIPO.get(mercado, ()):
        add(f"{mercado}_local", f"{mercado}_home", ln, vl)
        add(f"{mercado}_visitante", f"{mercado}_away", ln, vv)
    for nombre, esperado, real in ((f"{mercado}_total", lam[0] + lam[1], vl + vv),
                                   (f"{mercado}_local", lam[0], vl),
                                   (f"{mercado}_visitante", lam[1], vv)):
        filas.append({"evento": r.evento, "mercado": nombre, "seleccion": None,
                      "prob": np.nan, "resultado": np.nan, "esperado": esperado, "real": real})
    return filas
