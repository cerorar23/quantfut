"""Inferencia con ratings y ritmo congelados en LOCAL; no ajusta parámetros ni recorre resultados en el VPS."""
from dataclasses import dataclass
from datetime import datetime, date, UTC, timedelta
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path

import numpy as np
from scipy.special import expit

from .nucleo import Ratings

RUTA = Path(__file__).parent / 'parametros/equipo.json'


@dataclass(frozen=True)
class EstimacionEquipo:
    mu_local: float
    mu_visitante: float
    posesiones: float
    sigma_margen: float
    sigma_total: float
    p_ot: float
    descanso_local: int
    descanso_visitante: int
    version: str
    datos_hasta: str
    corte_entrenamiento: str
    ot_intercepto: float
    ot_abs_margen: float

    def prob_ot(self, margen: float) -> float:
        return float(expit(self.ot_intercepto + self.ot_abs_margen * abs(margen)))


@lru_cache(maxsize=8)
def cargar(ruta: str, huella: str) -> dict:
    raw = Path(ruta).read_bytes().replace(b'\r\n', b'\n')
    if hashlib.sha256(raw).hexdigest() != huella:
        raise ValueError('el artefacto de equipo cambió durante la lectura')
    a = json.loads(raw)
    if a.get('formato') != 'nba-equipo-congelado-1' or a.get('unidad_ratings') != 'puntos_por_100_posesiones':
        raise ValueError('artefacto de equipo incompatible')
    if a.get('objetivo_simulacion') != 'regulacion_mas_prorroga':
        raise ValueError('no se añade OT a una ley ya ajustada a finales completos')
    valores = [a[k] for k in ('liga', 'localia', 'sigma_margen', 'sigma_total', 'posesiones_referencia')]
    if not np.isfinite(valores).all() or min(a['sigma_margen'], a['sigma_total'], a['posesiones_referencia']) <= 0:
        raise ValueError('parámetros de equipo inválidos')
    return a


def artefacto() -> tuple[dict, str]:
    p = Path(os.environ.get('NBA_ESTADO_EQUIPO_JSON', RUTA))
    h = hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
    return cargar(str(p), h), h


def estimar(inst) -> EstimacionEquipo:
    a, h = artefacto()
    entrenado = datetime.fromisoformat(a['conocido_en_utc'])
    if entrenado.tzinfo is None or entrenado > inst.corte:
        raise ValueError('artefacto de equipo posterior al corte')
    if date.fromisoformat(a['datos_hasta']) >= inst.fecha:
        raise ValueError('el artefacto contiene el día objetivo o el futuro')
    if inst.corte > entrenado + timedelta(hours=a.get('vigencia_horas', 72)):
        raise ValueError('artefacto de equipo caducado: actualizarlo en local')
    if any(t not in a['ritmo'] for t in (inst.local, inst.visitante)):
        raise ValueError('equipo sin ritmo medido en el artefacto')
    ultimo = {}
    for fecha, _, local, visitante, _, _ in inst.historia:
        if fecha >= inst.fecha:
            raise ValueError('resultado objetivo o futuro en la instantánea')
        ultimo[local] = ultimo[visitante] = fecha
    dl = (inst.fecha - ultimo[inst.local]).days if inst.local in ultimo else 7
    dv = (inst.fecha - ultimo[inst.visitante]).days if inst.visitante in ultimo else 7
    # Estado congelado. La historia solo aporta descanso; nunca llama actualizar/ajustar.
    r = Ratings(dict(a['ataque']), dict(a['defensa']), a['liga'], a['localia'], a['partidos'])
    ajuste = a['efecto_b2b'] * ((dv == 1) - (dl == 1))
    pl, pv = r.esperado(inst.local, inst.visitante, ajuste)
    ritmo = (a['ritmo'][inst.local] + a['ritmo'][inst.visitante]) / 2
    if not np.isfinite(ritmo) or ritmo <= 0:
        raise ValueError('posesiones proyectadas inválidas')
    pl, pv = pl * ritmo / 100, pv * ritmo / 100
    escala = float(np.sqrt(ritmo / a['posesiones_referencia']))
    ot = a['ot']
    p_ot = float(expit(ot['intercepto'] + ot['abs_margen'] * abs(pl - pv)))
    return EstimacionEquipo(float(pl), float(pv), float(ritmo), a['sigma_margen'] * escala,
                           a['sigma_total'] * escala, p_ot, dl, dv, h[:12], a['datos_hasta'], a['conocido_en_utc'],
                           ot['intercepto'], ot['abs_margen'])
