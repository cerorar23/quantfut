"""
ModelEvaluator: precisión pura y calibración por mercado (sin ROI ni cuotas).

Entrada: DataFrame en formato largo, una fila por (evento, mercado[, selección]):

    mercado    obligatoria  nombre del mercado ("over25", "btts", "1x2", "goles_total"...)
    prob       obligatoria  probabilidad predicha de que ocurra la fila (NaN si no aplica)
    resultado  obligatoria  1 si ocurrió, 0 si no (NaN si no aplica)
    evento     opcional     id del partido; obligatoria para mercados_excluyentes
    seleccion  opcional     "H"/"D"/"A"... solo informativa
    esperado   opcional     valor esperado predicho (goles, puntos) para el RMSE
    real       opcional     valor realmente observado

Mercados binarios (over/under, BTTS): una fila por evento; Brier = (p - y)².
Mercados excluyentes (1X2): una fila por selección; Brier = suma de (p - y)² sobre
las selecciones del evento (misma convención que `metrics.brier`), log-loss = -log
de la probabilidad de la selección que ocurrió, accuracy = el argmax acertó.
`n` cuenta eventos en esos mercados y filas en el resto.

Línea base (sin modelo): la frecuencia observada del propio periodo. Brier y log-loss
base = los de predecir siempre esa frecuencia (entropía en el log-loss), accuracy_base =
acertar siempre la opción más frecuente, rmse_base = desviación de la serie (predecir
siempre su media). `*_skill` = 1 − métrica/base: > 0 mejora a la base, 0 la iguala. La base es
IN-SAMPLE, así que es más exigente que una real: no regala nada al modelo. En excluyentes
con selecciones que cambian por evento (marcador exacto: el top 12 varía) no hay base
bien definida y queda en NaN.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from qf.eval.metrics import EPS

_OBLIGATORIAS = ("mercado", "prob", "resultado")
_COLUMNAS = ["n", "brier", "log_loss", "accuracy", "rmse",
             "prob_media", "tasa_real",
             "brier_base", "brier_skill", "log_loss_base", "log_loss_skill",
             "accuracy_base", "rmse_base", "rmse_skill"]
_VACIO = {"n": 0, "brier": np.nan, "log_loss": np.nan, "accuracy": np.nan,
          "prob_media": np.nan, "tasa_real": np.nan, "brier_base": np.nan,
          "log_loss_base": np.nan, "accuracy_base": np.nan}


def _entropia(frecuencias: np.ndarray) -> float:
    f = np.asarray(frecuencias, dtype=float)
    f = f[f > 0]
    return float(-(f * np.log(f)).sum())


def _skill(valor: float, base: float) -> float:
    return float(1.0 - valor / base) if base and np.isfinite(base) and base > 0 else np.nan


class ModelEvaluator:
    def __init__(self, df: pd.DataFrame, umbral: float = 0.5,
                 mercados_excluyentes: set[str] | None = None) -> None:
        faltan = [c for c in _OBLIGATORIAS if c not in df.columns]
        if faltan:
            raise ValueError(f"Faltan columnas obligatorias: {faltan}")
        self.excluyentes = set(mercados_excluyentes or ())
        if self.excluyentes and "evento" not in df.columns:
            raise ValueError("mercados_excluyentes requiere la columna 'evento'")
        prob = df["prob"].dropna()
        if ((prob < 0) | (prob > 1)).any():
            raise ValueError("Hay probabilidades fuera de [0, 1]")
        if df["mercado"].isna().any():
            raise ValueError(f"Hay {int(df['mercado'].isna().sum())} filas sin mercado")
        resultado = df["resultado"].dropna()
        if ((resultado < 0) | (resultado > 1)).any():
            raise ValueError("Hay resultados fuera de [0, 1]")
        for c in ("esperado", "real"):
            if c in df.columns and np.isinf(pd.to_numeric(df[c], errors="coerce")).any():
                raise ValueError(f"Hay valores infinitos en '{c}'")
        self.umbral = umbral
        self.df = df.reset_index(drop=True)

    # -- métricas por mercado -------------------------------------------------
    def _rmse(self, g: pd.DataFrame) -> tuple[float, float]:
        """(rmse, rmse_base): el base es predecir siempre la media de la serie."""
        if "esperado" not in g.columns or "real" not in g.columns:
            return np.nan, np.nan
        v = g[["esperado", "real"]].dropna()
        if v.empty:
            return np.nan, np.nan
        return (float(np.sqrt(np.mean((v["esperado"] - v["real"]) ** 2))),
                float(np.sqrt(np.mean((v["real"] - v["real"].mean()) ** 2))))

    def _binario(self, g: pd.DataFrame) -> dict:
        v = g[["prob", "resultado"]].dropna()
        if v.empty:
            return dict(_VACIO)
        p, y = v["prob"].to_numpy(float), v["resultado"].to_numpy(float)
        pc = np.clip(p, EPS, 1 - EPS)
        tasa = float(y.mean())
        return {
            "n": len(v),
            "brier": float(np.mean((p - y) ** 2)),
            "log_loss": float(-np.mean(y * np.log(pc) + (1 - y) * np.log(1 - pc))),
            "accuracy": float(np.mean((p >= self.umbral) == (y == 1))),
            "prob_media": float(p.mean()), "tasa_real": tasa,
            "brier_base": tasa * (1 - tasa),
            "log_loss_base": _entropia(np.array([tasa, 1 - tasa])),
            "accuracy_base": max(tasa, 1 - tasa),
        }

    def _excluyente(self, g: pd.DataFrame) -> dict:
        v = g.dropna(subset=["prob", "resultado"])
        if v.empty:
            return dict(_VACIO)
        aciertos = v.groupby("evento")["resultado"].sum()
        if not np.allclose(aciertos, 1.0):
            raise ValueError("En mercados excluyentes cada evento necesita exactamente un acierto; "
                             f"{int((~np.isclose(aciertos, 1.0)).sum())} eventos no lo cumplen")
        pc = np.clip(v["prob"].to_numpy(float), EPS, 1.0)
        v = v.assign(_sq=(v["prob"] - v["resultado"]) ** 2,
                     _ll=-np.log(pc) * v["resultado"])
        por_evento = v.groupby("evento")
        acierto = v.loc[por_evento["prob"].idxmax(), "resultado"] == 1
        out = dict(_VACIO)
        out.update({
            "n": int(por_evento.ngroups),
            "brier": float(por_evento["_sq"].sum().mean()),
            "log_loss": float(por_evento["_ll"].sum().mean()),
            "accuracy": float(acierto.mean()),
        })
        fijas = "seleccion" in v.columns and v.groupby("evento")["seleccion"].agg(frozenset).nunique() == 1
        if fijas:
            f = v.groupby("seleccion")["resultado"].mean().to_numpy(float)
            out.update({"brier_base": float(1.0 - (f ** 2).sum()), "log_loss_base": _entropia(f),
                        "accuracy_base": float(f.max())})
        return out

    def evaluar(self) -> pd.DataFrame:
        """Una fila por mercado con n, brier, log_loss, accuracy y rmse."""
        filas = {}
        for mercado, g in self.df.groupby("mercado", sort=True):
            m = self._excluyente(g) if mercado in self.excluyentes else self._binario(g)
            m["rmse"], m["rmse_base"] = self._rmse(g)
            if m["n"] == 0 and not np.isnan(m["rmse"]):
                m["n"] = int(g[["esperado", "real"]].dropna().shape[0])
            m["brier_skill"] = _skill(m["brier"], m["brier_base"])
            m["log_loss_skill"] = _skill(m["log_loss"], m["log_loss_base"])
            m["rmse_skill"] = _skill(m["rmse"], m["rmse_base"])
            filas[mercado] = m
        if not filas:
            return pd.DataFrame(columns=_COLUMNAS).rename_axis("mercado")
        return pd.DataFrame.from_dict(filas, orient="index")[_COLUMNAS].rename_axis("mercado")

    def evaluar_tramos(self, cortes: dict[str, tuple]) -> dict[str, pd.DataFrame]:
        """
        Evalúa por periodos: cortes = {"nombre": (desde, hasta)} con límites Timestamp o None
        (desde inclusive, hasta exclusive). Requiere la columna `fecha` (UTC). Sirve para separar
        el tramo con el que se eligieron parámetros o líneas del tramo limpio posterior.
        """
        if "fecha" not in self.df.columns:
            raise ValueError("evaluar_tramos requiere la columna 'fecha'")
        fecha = pd.to_datetime(self.df["fecha"], utc=True)
        out = {}
        for nombre, (desde, hasta) in cortes.items():
            m = pd.Series(True, index=self.df.index)
            if desde is not None:
                m &= fecha >= pd.Timestamp(desde)
            if hasta is not None:
                m &= fecha < pd.Timestamp(hasta)
            out[nombre] = ModelEvaluator(self.df[m], self.umbral, self.excluyentes).evaluar()
        return out

    def resumen(self) -> dict:
        """Totales globales: cada mercado pesa por su n (no promedia mercados a ciegas)."""
        r = self.evaluar()
        out = {"n": int(r["n"].sum())}
        for col in ("brier", "log_loss", "accuracy", "rmse"):
            v = r[[col, "n"]].dropna()
            out[col] = float(np.average(v[col], weights=v["n"])) if v["n"].sum() else np.nan
        return out
