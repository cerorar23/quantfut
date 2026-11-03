"""Artefactos de parámetros entrenados en local (D4): el servidor solo infiere con archivos versionados, nunca entrena.

`parametros/props.json` lo genera `apps/nba/ops/entrenar_props.py`. Su huella sha256 (12 primeros caracteres) forma parte de
`version_modelo` de cada pronóstico de jugador: cambiar el archivo cambia la versión y, con ella, la clave única del sello.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np

from . import minutos

RUTA_PROPS = Path(__file__).parent / "parametros" / "props.json"


@dataclass(frozen=True)
class ParametrosProps:
    prior: np.ndarray                      # (niveles de rol, estadísticas)
    residuos: minutos.Residuos
    alfa: tuple[float, ...]
    k_minutos: float
    decaimiento: float
    p_estado: dict
    p_sin_parte: dict                      # tramo de minutos esperados (0, 1, 2) → probabilidad de jugar
    estadisticas: tuple[str, ...]
    datos_hasta: str
    version: str


def cargar_props(ruta: Path = RUTA_PROPS) -> ParametrosProps:
    crudo = ruta.read_bytes().replace(b"\r\n", b"\n")      # la huella no depende de los finales de línea del sistema
    a = json.loads(crudo)
    r = a["residuos_minutos"]
    return ParametrosProps(
        prior=np.array(a["prior_por_nivel"]),
        residuos=minutos.Residuos(tuple(r["cortes"]), tuple(np.array(c) for c in r["cuantiles"])),
        alfa=tuple(a["alfa"][e] for e in a["estadisticas"]), k_minutos=a["k_minutos"], decaimiento=a["decaimiento"],
        p_estado=a["p_juega_estado"], p_sin_parte={int(k): v for k, v in a["p_juega_sin_parte_por_tramo"].items()},
        estadisticas=tuple(a["estadisticas"]), datos_hasta=a["datos_hasta"], version=hashlib.sha256(crudo).hexdigest()[:12])
