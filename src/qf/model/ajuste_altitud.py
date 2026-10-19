"""Ajuste de lambdas por altitud para la predicción diaria (primer bloque de contexto que pasa la puerta).

Medido el 19-oct-2026 con `contexto.py` sobre el walk-forward del 12-oct (4.192 partidos, 13 ligas), con la semántica de
producción (sin intercepto, contra los lambdas sin ajustar): ΔRPS −0,0002 a −0,0003 según la partición de validación, siempre
favorable pero significativo solo en 1 de 4 particiones (30 %). Evidencia DÉBIL. Por eso entra en MODO SOMBRA: calcula el ajuste
y lo anota en cada predicción (`data_completeness.ajuste_altitud`) sin alterar los lambdas publicados, que son públicos e
inmutables. Con los partidos reales de las próximas semanas se decide si pasa a `activo`.

Variable: solo el SALTO de altura, `alt_dif_km` = cuánto más alto juega que lo habitual del visitante (0 si el visitante está
acostumbrado a esa altura o más). Una versión con la altitud de la sede además del salto pasaba mejor la puerta, pero bajaba
un 6 % el λ del local en América–Pachuca (los dos de altura): un artefacto sin sentido físico.

λ_local' = λ_local · exp(clip(shrink · βh·z, −1, 1)), y lo mismo para μ con βa, con z el salto estandarizado. NO lleva
intercepto: el nivel ya lo fijan Dixon-Coles y el calibrador; sin salto de altura el factor es exactamente 1. Un dato ausente se
toma como la mediana (factor 1). Cualquier fallo devuelve los lambdas sin tocar: nunca puede impedir el sellado diario.
"""
from __future__ import annotations

import glob
import logging
import os
import pickle
from dataclasses import dataclass

import numpy as np

from . import ajuste, contexto

log = logging.getLogger(__name__)

COLUMNAS = contexto.BLOQUES_CONTEXTO["altitud_salto"]
PREFIJO = "ajuste_altitud_"


@dataclass
class AjusteAltitud:
    medianas: list[float]
    escalas: list[float]
    beta_local: list[float]     # sin intercepto, una por columna
    beta_visita: list[float]
    shrink: float
    n_ajuste: int
    oos_version: str

    def factores(self, dif_km) -> tuple[float, float]:
        """(factor del λ del local, factor del μ del visitante). Dato ausente o no finito = mediana = factor 1."""
        x = np.array([dif_km], dtype=float)
        x = np.where(np.isfinite(x), x, np.array(self.medianas))
        z = (x - np.array(self.medianas)) / np.array(self.escalas)
        fl = float(np.exp(np.clip(self.shrink * float(np.dot(self.beta_local, z)), -1.0, 1.0)))
        fv = float(np.exp(np.clip(self.shrink * float(np.dot(self.beta_visita, z)), -1.0, 1.0)))
        return fl, fv

    def guardar(self, ruta: str) -> None:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "wb") as f:
            pickle.dump(self.__dict__, f)

    @classmethod
    def cargar(cls, ruta: str) -> "AjusteAltitud":
        with open(ruta, "rb") as f:
            return cls(**pickle.load(f))


def ajustar(frame, oos_version: str, shrink: float = 0.5, l2: float = 10.0) -> AjusteAltitud:
    """Ajusta con TODAS las filas del walk-forward (hay muy pocos partidos con salto de altura: 94 de 4.192)."""
    ordenado = ajuste._ordenado(frame)
    medianas, escalas, bh, ba = ajuste._ajustar(ordenado, list(COLUMNAS), l2)
    return AjusteAltitud([float(v) for v in medianas], [float(v) for v in escalas],
                         [float(v) for v in bh[1:]], [float(v) for v in ba[1:]], float(shrink), int(len(ordenado)),
                         oos_version)


def cargar_ultimo(carpeta: str) -> AjusteAltitud | None:
    archivos = glob.glob(f"{carpeta}/{PREFIJO}*.pkl")
    return AjusteAltitud.cargar(max(archivos, key=os.path.getmtime)) if archivos else None


def aplicar(ajuste_: AjusteAltitud | None, lam: float, mu: float, sede_m, hab_visita_m) -> tuple[float, float, dict | None]:
    """(λ', μ', constancia). Sin ajuste o ante cualquier error: lambdas intactos y constancia None."""
    if ajuste_ is None:
        return lam, mu, None
    try:
        sede_km, dif_km = contexto.altitud_features(sede_m, hab_visita_m)
        fl, fv = ajuste_.factores(dif_km)
        if not (np.isfinite(fl) and np.isfinite(fv)):
            return lam, mu, None
        return lam * fl, mu * fv, {"oos_version": ajuste_.oos_version, "shrink": ajuste_.shrink,
                                   "sede_km": None if not np.isfinite(sede_km) else round(float(sede_km), 3),
                                   "dif_km": None if not np.isfinite(dif_km) else round(float(dif_km), 3),
                                   "factor_local": round(fl, 4), "factor_visita": round(fv, 4)}
    except Exception:  # noqa: BLE001 — un ajuste opcional no puede romper el sellado
        log.exception("Ajuste de altitud fallido: se usan los lambdas sin ajustar")
        return lam, mu, None


def main(argv=None) -> None:
    import argparse
    import json

    import pandas as pd

    from ..config import settings
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--oos", help="oos_<versión>.pkl; por defecto el más reciente")
    ap.add_argument("--guardar", action="store_true", help="escribe ajuste_altitud_<versión>.pkl")
    ap.add_argument("--simular", action="store_true", help="muestra los factores de los próximos partidos modelados")
    a = ap.parse_args(argv)
    if a.simular:
        from ..db import query
        aj_ = cargar_ultimo(settings.artifact_dir)
        if aj_ is None:
            raise SystemExit("no hay ajuste_altitud_*.pkl: ejecuta antes con --guardar")
        filas = query("""SELECT m.match_id, m.league_id, th.canonical_name AS local, ta.canonical_name AS visita
                         FROM matches m JOIN teams th ON th.team_id = m.home_team_id
                         JOIN teams ta ON ta.team_id = m.away_team_id JOIN leagues l ON l.league_id = m.league_id
                         WHERE m.status = 'scheduled' AND l.model_enabled AND m.kickoff_utc BETWEEN now() AND now() + interval '10 days'
                         ORDER BY m.kickoff_utc""")
        alt = contexto.altitudes_de([f["match_id"] for f in filas]).set_index("match_id")
        out = []
        for f in filas:
            r = alt.loc[f["match_id"]] if f["match_id"] in alt.index else None
            _, _, info = aplicar(aj_, 1.0, 1.0, None if r is None else r["sede_m"], None if r is None else r["hab_visita_m"])
            out.append({"liga": f["league_id"], "partido": f"{f['local']} - {f['visita']}", **(info or {"sin_datos": True})})
        out.sort(key=lambda o: -abs(np.log(o.get("factor_local", 1.0))) - abs(np.log(o.get("factor_visita", 1.0))))
        print(json.dumps(out[:25], indent=1, ensure_ascii=False))
        return
    ruta = a.oos or max(glob.glob(f"{settings.artifact_dir}/oos_*.pkl"), key=os.path.getmtime)
    version = os.path.basename(ruta)[len("oos_"):-len(".pkl")]
    frame = contexto.marco_contexto(pd.read_pickle(ruta))
    aj_ = ajustar(frame, version)
    print(json.dumps({"oos": os.path.basename(ruta), "n_ajuste": aj_.n_ajuste, "medianas": aj_.medianas,
                      "escalas": aj_.escalas, "beta_local": aj_.beta_local, "beta_visita": aj_.beta_visita,
                      "ejemplos": {"Toluca contra un visitante de nivel del mar (salto 2,6 km)": aj_.factores(2.63),
                                   "Madrid contra un visitante de nivel del mar (salto 0,6 km)": aj_.factores(0.6),
                                   "América contra Pachuca (los dos de altura, salto 0)": aj_.factores(0.0),
                                   "Partido a nivel del mar": aj_.factores(0.0)}},
                     indent=2, ensure_ascii=False))
    if a.guardar:
        destino = f"{settings.artifact_dir}/{PREFIJO}{version}.pkl"
        aj_.guardar(destino)
        print("guardado:", destino)


if __name__ == "__main__":
    main()
