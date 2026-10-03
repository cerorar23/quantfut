"""
¿Cuánto dura una oferta de casa blanda y cuánto tarda cada casa en seguir a
Pinnacle? (idea 3, lectura de las ráfagas de `ingest/rafagas.py`).

Medida fijada antes de ver datos (harness/tareas.md, idea 3):

  - Oferta: tramo continuo en que `cuota_blanda × p_justa_pinnacle − 1 ≥ 2 %`.
    Los precios son escalones: cada uno vale desde su `last_update` hasta el
    siguiente cambio. El tramo observado va de la primera a la última
    consulta del partido; una oferta que toca un borde está CENSURADA (su
    duración real es mayor o igual).
  - Vara: el cliente tarda una hora o más en apostar (dato del usuario,
    3-oct). Lo que cuenta es la fracción de ofertas que duran ≥ 60 min. Las
    censuradas ≥ 60 cuentan como largas; las censuradas < 60 no se pueden
    clasificar y se excluyen.
  - Reacción: tras cada cambio de Pinnacle de ≥ 2 puntos en la probabilidad
    justa de una selección, minutos hasta el siguiente cambio de cada casa.
  - No se lee antes de 200 ofertas clasificables en ≥ 3 casas.

Solo lectura.
"""
from __future__ import annotations

import argparse
import json
import logging

import numpy as np
import pandas as pd

from ..config import settings
from ..model.devig import devig

log = logging.getLogger(__name__)

SEL = ("home", "draw", "away")
UMBRAL = 0.02
VARA_MIN = 60.0
SALTO_PINNACLE = 0.02
MIN_OFERTAS = 200
MIN_CASAS = 3
SHARP = "pinnacle"


def pinnacle_justo(rows: pd.DataFrame, method: str | None = None) -> pd.DataFrame:
    """Probabilidad justa de Pinnacle en cada uno de sus cambios (1X2 completo)."""
    p = rows[rows["bookmaker"] == SHARP].pivot_table(
        index="book_updated_at", columns="selection", values="price", aggfunc="last")
    p = p.sort_index().ffill().dropna()
    if p.empty or not set(SEL) <= set(p.columns):
        return pd.DataFrame(columns=list(SEL))
    fair = np.vstack([devig(r, method or settings.devig_method) for r in p[list(SEL)].to_numpy()])
    return pd.DataFrame(fair, index=p.index, columns=list(SEL))


def _escalon(serie: pd.Series, t: pd.DatetimeIndex) -> np.ndarray:
    """Valor vigente de un escalón en cada instante de `t` (NaN si aún no había)."""
    return serie.sort_index().reindex(serie.index.union(t)).ffill().reindex(t).to_numpy(float)


def ofertas(rows: pd.DataFrame, inicio, fin, umbral: float = UMBRAL) -> pd.DataFrame:
    """Tramos de oferta de un partido, por casa y selección."""
    fair = pinnacle_justo(rows)
    out = []
    if fair.empty:
        return pd.DataFrame(columns=["bookmaker", "selection", "inicio", "fin", "minutos",
                                     "censurada"])
    for (book, sel), g in rows[rows["bookmaker"] != SHARP].groupby(["bookmaker", "selection"]):
        precio = g.set_index("book_updated_at")["price"]
        t = fair.index.union(precio.index).union(pd.DatetimeIndex([inicio]))
        t = t[(t >= inicio) & (t <= fin)]
        edge = _escalon(precio, t) * _escalon(fair[sel], t) - 1.0
        dentro = np.nan_to_num(edge, nan=-1.0) >= umbral
        k = 0
        while k < len(t):
            if not dentro[k]:
                k += 1
                continue
            j = k
            while j + 1 < len(t) and dentro[j + 1]:
                j += 1
            final = t[j + 1] if j + 1 < len(t) else pd.Timestamp(fin)
            out.append({"bookmaker": book, "selection": sel, "inicio": t[k], "fin": final,
                        "minutos": (final - t[k]).total_seconds() / 60.0,
                        "censurada": bool(t[k] <= inicio or j + 1 >= len(t))})
            k = j + 1
    return pd.DataFrame(out)


def reacciones(rows: pd.DataFrame, inicio, fin,
               salto: float = SALTO_PINNACLE) -> pd.DataFrame:
    """Minutos que tarda cada casa en cambiar tras un salto de Pinnacle observado."""
    fair = pinnacle_justo(rows)
    if len(fair) < 2:
        return pd.DataFrame(columns=["bookmaker", "minutos", "censurada"])
    saltos = fair.index[1:][(fair.diff().abs().iloc[1:] >= salto).any(axis=1).to_numpy()]
    saltos = saltos[(saltos >= inicio) & (saltos <= fin)]
    fin = pd.Timestamp(fin)
    out = []
    for book, g in rows[rows["bookmaker"] != SHARP].groupby("bookmaker"):
        cambios = pd.DatetimeIndex(g["book_updated_at"].unique()).sort_values()
        for ts in saltos:
            despues = cambios[(cambios > ts) & (cambios <= fin)]
            hasta = despues[0] if len(despues) else fin
            out.append({"bookmaker": book, "censurada": not len(despues),
                        "minutos": (hasta - ts).total_seconds() / 60.0})
    return pd.DataFrame(out)


def resumen(of: pd.DataFrame, re: pd.DataFrame, vara: float = VARA_MIN) -> dict:
    largas = of["minutos"] >= vara
    clasificables = of[~of["censurada"] | largas]
    por_casa = {}
    for book, g in clasificables.groupby("bookmaker"):
        r = re[re["bookmaker"] == book] if not re.empty else re
        sin_c = r[~r["censurada"]] if not r.empty else r
        por_casa[str(book)] = {
            "ofertas": int(len(g)),
            "pct_largas": round(100 * float((g["minutos"] >= vara).mean()), 1),
            "mediana_min": round(float(g["minutos"].median()), 1),
            "reacciones": int(len(r)),
            "reaccion_mediana_min": (round(float(sin_c["minutos"].median()), 1)
                                     if len(sin_c) else None)}
    n, casas = len(clasificables), len(por_casa)
    listo = n >= MIN_OFERTAS and casas >= MIN_CASAS
    return {"ofertas_clasificables": int(n), "censuradas_cortas_excluidas": int(len(of) - n),
            "casas": casas,
            "pct_largas": round(100 * float((clasificables["minutos"] >= vara).mean()), 1) if n else None,
            "mediana_min": round(float(clasificables["minutos"].median()), 1) if n else None,
            "por_casa": por_casa,
            "lectura": "lista" if listo else
                       f"muestra insuficiente (se exigen {MIN_OFERTAS} ofertas en {MIN_CASAS} casas)"}


def run() -> dict:
    from ..db import query
    rows = pd.DataFrame(query("SELECT * FROM odds_rafagas"))
    if rows.empty:
        return {"lectura": "sin datos"}
    rows["book_updated_at"] = pd.to_datetime(rows["book_updated_at"], utc=True)
    ventanas = pd.DataFrame(query(
        """SELECT unnest(match_ids) AS match_id, min(captured_at) AS inicio,
                  max(captured_at) AS fin FROM rafagas_log GROUP BY 1"""))
    of, re = [], []
    for v in ventanas.itertuples():
        g = rows[rows["match_id"] == v.match_id]
        if g.empty:
            continue
        inicio, fin = pd.Timestamp(v.inicio), pd.Timestamp(v.fin)
        of.append(ofertas(g, inicio, fin).assign(match_id=v.match_id))
        re.append(reacciones(g, inicio, fin))
    of = pd.concat(of, ignore_index=True) if of else pd.DataFrame(
        columns=["bookmaker", "minutos", "censurada"])
    re = pd.concat(re, ignore_index=True) if re else pd.DataFrame(
        columns=["bookmaker", "minutos", "censurada"])
    return {"partidos": int(len(ventanas)), **resumen(of, re)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    argparse.ArgumentParser(description=__doc__.splitlines()[1]).parse_args()
    print(json.dumps(run(), ensure_ascii=False, indent=1, default=str))
