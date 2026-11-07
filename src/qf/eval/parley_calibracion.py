"""Calibración de las patas del parley v2 (fase 2): artefacto aprobable y abstención.

Para cada categoría amplia (deporte, familia de mercado y banda de cuota) se compara,
sobre una partición temporal 60/20/20 con embargo, el baseline de mercado (la
probabilidad sin margen tal cual), Platt e isotónica:

* se ajusta con el 60 % más antiguo, se elige el método por Brier en el 20 % siguiente
  y se informa sobre el 20 % final, que no interviene en ninguna elección;
* el embargo descarta los días pegados a cada corte para que una misma jornada no
  quede a ambos lados;
* el bootstrap da la incertidumbre: de la mejora de Brier en el test y de la
  probabilidad calibrada (refits sobre remuestreos del entrenamiento);
* la categoría se ABSTIENE si falta muestra o si el error de calibración (ECE) del
  test supera ``ECE_MAX``. Una categoría sin artefacto nunca vuelve ``publicado``.

El artefacto es JSON (``construir_artefacto``) y se aplica con ``Calibrador``. Es
investigación hasta que el titular lo apruebe: este módulo no decide promoción.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from ..publish import parley_v2 as v2

FRACCIONES = (0.6, 0.2, 0.2)
EMBARGO_DIAS = 7
MIN_ENTRENO, MIN_VALIDACION, MIN_TEST = 400, 150, 150
ECE_MAX = 0.04
BOOTSTRAP = 200
Z_PRUDENTE = 1.28                      # p prudente = p calibrada − 1,28 desviaciones (≈ percentil 10)
BANDAS = ((1.20, 1.80, "1.20-1.80"), (1.80, 2.10, "1.80-2.10"), (2.10, 2.50, "2.10-2.50"))
METODOS = ("mercado", "platt", "isotonica")
_EPS = 1e-4


def banda(cuota: float) -> str | None:
    for lo, hi, nombre in BANDAS:
        if lo <= cuota < hi:
            return nombre
    return BANDAS[-1][2] if cuota == BANDAS[-1][1] else None


def categoria(deporte: str, mercado: str, cuota: float) -> str | None:
    b = banda(cuota)
    return None if b is None else f"{deporte}|{v2.familia(mercado)}|{b}"


# ------------------------------------------------------------------ partición temporal
def particion_temporal(fechas, fracciones=FRACCIONES, embargo_dias: int = EMBARGO_DIAS):
    """Índices (entreno, validación, test) por fecha, con embargo tras cada corte."""
    f = np.asarray(fechas, dtype="datetime64[D]")
    orden = np.sort(f)
    c1 = orden[int(len(orden) * fracciones[0])]
    c2 = orden[min(int(len(orden) * (fracciones[0] + fracciones[1])), len(orden) - 1)]
    emb = np.timedelta64(embargo_dias, "D")
    entreno = np.where(f < c1)[0]
    validacion = np.where((f >= c1 + emb) & (f < c2))[0]
    test = np.where(f >= c2 + emb)[0]
    return entreno, validacion, test


# ------------------------------------------------------------------ métodos
def _logit(p):
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def _ajustar(metodo: str, p, y):
    if metodo == "mercado":
        return {}
    if metodo == "platt":
        m = LogisticRegression(C=1e4, max_iter=200).fit(_logit(p).reshape(-1, 1), y)
        return {"a": float(m.coef_[0, 0]), "b": float(m.intercept_[0])}
    m = IsotonicRegression(y_min=_EPS, y_max=1 - _EPS, out_of_bounds="clip").fit(p, y)
    return {"xs": [float(x) for x in m.X_thresholds_], "ys": [float(x) for x in m.y_thresholds_]}


def _aplicar(metodo: str, params: dict, p):
    p = np.asarray(p, dtype=float)
    if metodo == "mercado":
        return np.clip(p, _EPS, 1 - _EPS)
    if metodo == "platt":
        return 1 / (1 + np.exp(-(params["a"] * _logit(p) + params["b"])))
    return np.clip(np.interp(p, params["xs"], params["ys"]), _EPS, 1 - _EPS)


def metricas(p, y) -> dict:
    p, y = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6), np.asarray(y, dtype=float)
    cortes = np.linspace(0, 1, 11)
    idx = np.clip(np.digitize(p, cortes) - 1, 0, 9)
    ece = sum(abs(p[idx == k].mean() - y[idx == k].mean()) * (idx == k).mean() for k in range(10) if (idx == k).any())
    return {"brier": float(np.mean((p - y) ** 2)),
            "logloss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))), "ece": float(ece), "n": int(len(y))}


def mejora_bootstrap(p_base, p_cal, y, repeticiones: int = BOOTSTRAP, semilla: int = 7) -> tuple[float, float, float]:
    """(media, IC95 bajo, IC95 alto) de Brier(base) − Brier(cal) en el test; > 0 = mejora."""
    d = (np.asarray(p_base) - y) ** 2 - (np.asarray(p_cal) - y) ** 2
    rng = np.random.default_rng(semilla)
    medias = np.array([d[rng.integers(0, len(d), len(d))].mean() for _ in range(repeticiones)])
    return float(d.mean()), float(np.percentile(medias, 2.5)), float(np.percentile(medias, 97.5))


# ------------------------------------------------------------------ una categoría
def ajustar_categoria(fechas, p, y, repeticiones: int = BOOTSTRAP, semilla: int = 11) -> dict:
    fechas, p, y = np.asarray(fechas, dtype="datetime64[D]"), np.asarray(p, dtype=float), np.asarray(y, dtype=float)
    tr, va, te = particion_temporal(fechas)
    n = {"entreno": int(len(tr)), "validacion": int(len(va)), "test": int(len(te))}
    if len(tr) < MIN_ENTRENO or len(va) < MIN_VALIDACION or len(te) < MIN_TEST:
        return {"estado": "abstencion", "motivo": "muestra insuficiente", "n": n}
    ajustes = {m: _ajustar(m, p[tr], y[tr]) for m in METODOS}
    brier_val = {m: metricas(_aplicar(m, ajustes[m], p[va]), y[va])["brier"] for m in METODOS}
    metodo = min(METODOS, key=lambda m: (round(brier_val[m], 6), METODOS.index(m)))
    p_te_base, p_te = _aplicar("mercado", {}, p[te]), _aplicar(metodo, ajustes[metodo], p[te])
    mejora = mejora_bootstrap(p_te_base, p_te, y[te], repeticiones)
    if metodo != "mercado" and mejora[1] <= 0:        # no mejora con claridad: se queda el mercado
        metodo, p_te, mejora = "mercado", p_te_base, mejora_bootstrap(p_te_base, p_te_base, y[te], repeticiones)
    res = {"n": n, "metodo": metodo, "metricas_test": metricas(p_te, y[te]), "metricas_test_mercado": metricas(p_te_base, y[te]),
           "metricas_validacion": {m: brier_val[m] for m in METODOS}, "mejora_brier_ic95": list(mejora)}
    if res["metricas_test"]["ece"] > ECE_MAX:
        return {**res, "estado": "abstencion", "motivo": f"ECE del test {res['metricas_test']['ece']:.3f} > {ECE_MAX}"}
    # Despliegue: refit con entreno + validación; incertidumbre por bootstrap del ajuste.
    uso = np.concatenate([tr, va])
    final = _ajustar(metodo, p[uso], y[uso])
    nodos = np.quantile(p[uso], np.linspace(0.05, 0.95, 10))
    rng = np.random.default_rng(semilla)
    muestras = []
    for _ in range(repeticiones if metodo != "mercado" else 0):
        i = rng.choice(uso, len(uso), replace=True)
        muestras.append(_aplicar(metodo, _ajustar(metodo, p[i], y[i]), nodos))
    sd = np.std(muestras, axis=0) if muestras else np.sqrt(nodos * (1 - nodos) / len(uso))
    return {**res, "estado": "ok", "params": final, "nodos": [float(x) for x in nodos], "sd": [float(x) for x in sd]}


def construir_artefacto(registros: list[dict], nombre: str = "parley-calibracion") -> dict:
    """``registros``: dicts con fecha, deporte, mercado, cuota, p (sin margen) y gana (0/1)."""
    por_cat: dict[str, list[dict]] = {}
    for r in registros:
        c = categoria(r["deporte"], r["mercado"], float(r["cuota"]))
        if c is not None:
            por_cat.setdefault(c, []).append(r)
    cats = {c: ajustar_categoria([r["fecha"] for r in rs], [r["p"] for r in rs], [r["gana"] for r in rs])
            for c, rs in sorted(por_cat.items())}
    return {"nombre": nombre, "creado": datetime.now(timezone.utc).isoformat(),
            "particion": {"fracciones": FRACCIONES, "embargo_dias": EMBARGO_DIAS},
            "umbrales": {"ece_max": ECE_MAX, "min": [MIN_ENTRENO, MIN_VALIDACION, MIN_TEST]},
            "aprobado": False, "categorias": cats}


# ------------------------------------------------------------------ aplicación
@dataclass
class Calibrador:
    artefacto: dict

    @classmethod
    def desde_archivo(cls, ruta) -> "Calibrador":
        return cls(json.loads(open(ruta, encoding="utf-8").read()))

    def calibrar(self, deporte: str, mercado: str, cuota: float, p: float) -> v2.Calibracion | None:
        """Calibración de una pata o None (categoría ausente o en abstención)."""
        c = categoria(deporte, mercado, cuota)
        cat = self.artefacto["categorias"].get(c) if c else None
        if not cat or cat.get("estado") != "ok":
            return None
        pc = float(_aplicar(cat["metodo"], cat.get("params", {}), np.array([p]))[0])
        sd = float(np.interp(p, cat["nodos"], cat["sd"]))
        lo, hi = max(pc - Z_PRUDENTE * sd, _EPS), min(pc + Z_PRUDENTE * sd, 1 - _EPS)
        return v2.Calibracion(p_prudente=lo, p_bajo=lo, p_alto=hi, p_calibrada=pc,
                              artefacto=f"{self.artefacto.get('nombre', '')}:{c}")

    def para_opciones(self, ops) -> dict:
        """{clave de pata: Calibracion} para ``parley_v2.armar_plan(calibracion=...)``."""
        out = {}
        for o in ops:
            cal = self.calibrar(getattr(o, "deporte", "") or "futbol", o.cand.market, o.price, o.cand.prob)
            if cal is not None:
                out[v2._clave(o)] = cal
        return out

    def p_calibrada(self, deporte: str, mercado: str, cuota: float, p: float) -> float | None:
        c = categoria(deporte, mercado, cuota)
        cat = self.artefacto["categorias"].get(c) if c else None
        if not cat or cat.get("estado") != "ok":
            return None
        return float(_aplicar(cat["metodo"], cat.get("params", {}), np.array([p]))[0])


def filtrar_calibradas(ops, calibracion: dict) -> list:
    """Abstención a nivel de pata: solo lo que tiene artefacto vigente."""
    return [o for o in ops if v2._clave(o) in calibracion]
