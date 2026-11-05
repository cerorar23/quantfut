"""Artefactos de parámetros entrenados en local (D4): el servidor solo infiere con archivos versionados, nunca entrena.

`parametros/props.json` lo genera `apps/nba/ops/entrenar_props.py`. Su huella sha256 (12 primeros caracteres) forma parte de
`version_modelo` de cada pronóstico de jugador: cambiar el archivo cambia la versión y, con ella, la clave única del sello.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import os

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


RUTA_IMPACTO = Path(__file__).parent / "parametros" / "impacto.json"


@dataclass(frozen=True)
class ParametrosImpacto:
    impacto: object                        # plantilla.Impacto (beta, tau, intercepto y efecto del descanso)
    sigma_margen: float                    # desviación del margen; `objetivo` distingue regulación de finales completos
    datos_hasta: str
    version: str
    aprobado_regulacion: bool = False
    objetivo: str = 'margen_regulacion'
    posesiones_referencia: float = 100.0
    ot: dict | None = None
    conocido_en_utc: str | None = None


def cargar_impacto(ruta: Path | None = None) -> ParametrosImpacto:
    from .plantilla import Impacto
    ruta = ruta or Path(os.environ.get('NBA_IMPACTO_JSON', RUTA_IMPACTO))
    crudo = ruta.read_bytes().replace(b"\r\n", b"\n")
    a = json.loads(crudo)
    imp = Impacto(beta={int(k): v for k, v in a["beta"].items()}, tau={int(k): v for k, v in a["tau"].items()},
                  c_margen=a["c_margen"], d_margen=a["d_margen"], c_total=a["c_total"], d_total=a["d_total"])
    val = a.get('validacion', {}).get('ganador', {})
    ic = val.get('dif_ic95', [float('inf'),float('inf')])
    aprobado = bool(a.get('aprobado_para_mezcla') and a.get('objetivo') == 'margen_regulacion'
                    and val.get('n',0) >= 500 and len(ic)==2 and np.isfinite(ic).all() and ic[1]<=0
                    and a.get('ot') and a.get('conocido_en_utc') and a.get('hashes_entradas'))
    return ParametrosImpacto(imp, a["sigma_margen_mezcla"], a["datos_hasta"], hashlib.sha256(crudo).hexdigest()[:12],
                            aprobado, a.get('objetivo','final_historico_implicito'),
                            a.get('posesiones_referencia',100.), a.get('ot'), a.get('conocido_en_utc'))


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
