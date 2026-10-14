"""Capa de ajuste de lambdas por bloques de señales (F1 de la spec 2026-10-14).

λ = λ_base · exp(clip(shrink · Σ x·β, -1, 1)); lo mismo para μ. Dixon-Coles y la
calibración no se tocan. Un bloque entra solo si, sobre las mismas filas, mejora al
modelo SIN él (puerta de `lineup_challenger.informe_antes_despues`).
"""
from __future__ import annotations

import pickle
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from . import lineup_challenger as lc


@dataclass(frozen=True)
class Bloque:
    nombre: str
    columnas: tuple[str, ...]


BLOQUES: dict[str, Bloque] = {}


def registrar(bloque: Bloque) -> Bloque:
    BLOQUES[bloque.nombre] = bloque
    return bloque


registrar(Bloque("xi", tuple(lc.LINEUP_FEATURES)))


def columnas_de(nombres: list[str]) -> list[str]:
    cols: list[str] = []
    for nombre in nombres:
        cols += [c for c in BLOQUES[nombre].columnas if c not in cols]
    return cols


def _ajustar(train: pd.DataFrame, cols: list[str], l2: float):
    raw = train[cols].to_numpy(dtype=float)
    medians = np.nanmedian(raw, axis=0)
    medians = np.where(np.isnan(medians), 0.0, medians)
    filled = np.where(np.isnan(raw), medians, raw)
    scales = np.std(filled, axis=0)
    scales = np.where(scales < 1e-8, 1.0, scales)
    x = np.column_stack([np.ones(len(train)), (filled - medians) / scales])
    bh = lc._fit_poisson_offset(x, np.log(train["base_lam"].to_numpy()),
                                train["home_goals"].to_numpy(dtype=float), l2)
    ba = lc._fit_poisson_offset(x, np.log(train["base_mu"].to_numpy()),
                                train["away_goals"].to_numpy(dtype=float), l2)
    return medians, scales, bh, ba


def _modelo(train: pd.DataFrame, cols: list[str], rho: float, shrink: float, l2: float):
    """Ajuste con intercepto. Sin columnas es el modelo SOLO DE NIVEL: la referencia justa de la puerta."""
    medians, scales, bh, ba = _ajustar(train, cols, l2)
    return lc.LineupLambdaChallenger(lc.LineupParams(
        medians.tolist(), scales.tolist(), bh.tolist(), ba.tolist(), float(rho), float(shrink),
        int(len(train)), False, cols))


def _lambdas(modelo, frame: pd.DataFrame):
    if modelo is None:
        return frame["base_lam"].to_numpy(dtype=float), frame["base_mu"].to_numpy(dtype=float)
    return modelo.apply(frame)


def _ordenado(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.sort_values(["kickoff_utc", "match_id"]).dropna(
        subset=["base_lam", "base_mu", "home_goals", "away_goals"]).reset_index(drop=True)


def _rps_por_partido(probs: np.ndarray, resultados: np.ndarray) -> np.ndarray:
    onehot = np.zeros_like(probs)
    onehot[np.arange(len(resultados)), resultados] = 1.0
    cum = np.cumsum(probs, axis=1)[:, :-1] - np.cumsum(onehot, axis=1)[:, :-1]
    return np.sum(cum ** 2, axis=1) / (probs.shape[1] - 1)


def _delta_rps(antes: np.ndarray, despues: np.ndarray, resultados: np.ndarray,
               n_boot: int = 2000, semilla: int = 0) -> tuple[float, float]:
    """Media y percentil 95 (remuestreo pareado por partido) de RPS_después - RPS_antes."""
    dif = _rps_por_partido(despues, resultados) - _rps_por_partido(antes, resultados)
    rng = np.random.default_rng(semilla)
    medias = dif[rng.integers(0, len(dif), (n_boot, len(dif)))].mean(axis=1)
    return round(float(dif.mean()), 6), round(float(np.percentile(medias, 95)), 6)


def comparar(frame: pd.DataFrame, antes: list[str], despues: list[str], rho: float = 0.0,
             shrink: float = 0.5, holdout_frac: float = 0.30, min_fit: int = 500,
             min_val: int = 200, l2: float = 10.0) -> dict:
    """Modelo con los bloques `antes` frente al de `despues`, mismas filas y misma partición.

    Con `antes=[]` la referencia es el modelo solo de nivel (intercepto), no las lambdas crudas: si no,
    el primer bloque se llevaría el mérito de re-nivelar lambdas sesgadas.
    """
    cols_a, cols_b = columnas_de(antes), columnas_de(despues)
    faltan = [c for c in cols_b if c not in frame.columns]
    if faltan:
        raise ValueError(f"Faltan columnas en el marco: {faltan}")
    ordered = _ordenado(frame)
    cut = int(len(ordered) * (1.0 - holdout_frac))
    if cut < min_fit or len(ordered) - cut < min_val:
        return {"ok": False, "status": "collecting", "n": int(len(ordered)),
                "reason": f"Muestra insuficiente: {cut} de ajuste y {len(ordered) - cut} de validación; "
                          f"se exigen {min_fit}/{min_val}.",
                "bloques_antes": list(antes), "bloques_despues": list(despues)}
    train, val = ordered.iloc[:cut], ordered.iloc[cut:].reset_index(drop=True)
    # La rho de cada predicción es la de ESE momento; la de hoy traería conocimiento del futuro.
    hist_rho = val["rho"].to_numpy(dtype=float) if "rho" in val.columns else rho
    la, ma = _lambdas(_modelo(train, cols_a, rho, shrink, l2), val)
    lb, mb = _lambdas(_modelo(train, cols_b, rho, shrink, l2), val)
    pa, pb = lc._probabilities(la, ma, hist_rho), lc._probabilities(lb, mb, hist_rho)
    informe = lc.informe_antes_despues(val, pa, pb, int(cut))
    resultados = np.where(val["home_goals"] > val["away_goals"], 0,
                          np.where(val["home_goals"] == val["away_goals"], 1, 2))
    media, p95 = _delta_rps(pa, pb, resultados)
    informe["delta_rps_media"], informe["delta_rps_p95"] = media, p95
    informe["significativa"] = bool(p95 < 0)
    informe["ok_puerta_basica"] = informe["ok"]
    # La puerta básica sola deja pasar ruido (~20 % de las veces): se exige además significancia.
    informe["ok"] = bool(informe["ok"] and informe["significativa"])
    informe["bloques_antes"], informe["bloques_despues"] = list(antes), list(despues)
    return informe


@dataclass
class Ajuste:
    bloques: list[str]
    modelo: object            # LineupLambdaChallenger | None (sin bloques: lambdas base)
    informe: dict

    def aplicar(self, frame: pd.DataFrame):
        return _lambdas(self.modelo, frame)

    def guardar(self, ruta: str) -> None:
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        params = asdict(self.modelo.params) if self.modelo is not None else None
        with open(ruta, "wb") as f:
            pickle.dump({"bloques": self.bloques, "params": params, "informe": self.informe}, f)

    @classmethod
    def cargar(cls, ruta: str) -> "Ajuste":
        with open(ruta, "rb") as f:
            d = pickle.load(f)
        modelo = lc.LineupLambdaChallenger(lc.LineupParams(**d["params"])) if d["params"] else None
        return cls(d["bloques"], modelo, d["informe"])


def construir_ajuste(frame: pd.DataFrame, candidatos: list[str], rho: float = 0.0, **kw) -> Ajuste:
    """Acepta, en orden, cada candidato que mejora al conjunto ya aceptado."""
    aceptados: list[str] = []
    informe: dict = {}
    for nombre in candidatos:
        r = comparar(frame, aceptados, aceptados + [nombre], rho=rho, **kw)
        informe[nombre] = r
        if r["ok"]:
            aceptados.append(nombre)
    cols = columnas_de(aceptados)
    if not cols:
        return Ajuste([], None, informe)
    ordered = _ordenado(frame)
    cut = int(len(ordered) * (1.0 - kw.get("holdout_frac", 0.30)))
    modelo = _modelo(ordered.iloc[:cut], cols, rho, kw.get("shrink", 0.5), kw.get("l2", 10.0))
    modelo.params.offline_validated = True
    return Ajuste(aceptados, modelo, informe)


def _cargar_marco(ruta: str | None):
    import glob
    import os

    from ..config import settings
    from ..db import query_one
    ruta = ruta or max(glob.glob(f"{settings.artifact_dir}/oos_*.pkl"), key=os.path.getmtime)
    version = os.path.basename(ruta)[len("oos_"):-len(".pkl")]
    fila = query_one("SELECT params->>'rho' AS rho FROM model_artifacts WHERE model_version = %s", (version,))
    frame, _ = lc.load_training_frame(pd.read_pickle(ruta))
    return frame, float(fila["rho"]), version


def main(argv=None):
    import argparse
    import json

    from ..config import settings
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--oos", help="oos_<versión>.pkl; por defecto el más reciente")
    p.add_argument("--guardar", action="store_true", help="escribe ajuste_<versión>.pkl")
    args = p.parse_args(argv)
    frame, rho, version = _cargar_marco(args.oos)
    a = construir_ajuste(frame, list(BLOQUES), rho=rho)
    if args.guardar:
        a.guardar(f"{settings.artifact_dir}/ajuste_{version}.pkl")
    print(json.dumps({"version": version, "bloques_aceptados": a.bloques, "informe": a.informe},
                     indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
