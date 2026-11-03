"""Props de jugador sobre una `Plantilla` (Sprint 4 en producción): minutos × tasa por minuto con binomial negativa.

Cada distribución es condicionada a jugar (las casas anulan la apuesta si no juega) y lleva aparte `p_juega` («si juega: x %»).
Se omiten quienes tienen probabilidad de jugar menor que `P_MINIMA` o menos de `MINUTOS_MINIMOS` esperados: no son jugadores de rotación
y su historial no sostiene una distribución. Determinista: mismos datos y mismo artefacto → mismas distribuciones.
"""
import numpy as np

from . import minutos, props
from .parametros import ParametrosProps
from .plantilla_pit import Plantilla, V

P_MINIMA = 0.15
MINUTOS_MINIMOS = 8.0
N_MINUTOS = 25
NOMBRES_MERCADO = {"puntos": "jugador:puntos", "rebotes": "jugador:rebotes", "asistencias": "jugador:asistencias", "triples": "jugador:triples"}


def _cuantil(pmf: np.ndarray, q: float) -> int:
    return int(np.searchsorted(np.cumsum(pmf), q))


def pronosticar(pl: Plantilla, par: ParametrosProps) -> list[dict]:
    salida = []
    for lado, jugadores in pl.lados.items():
        for j in jugadores:
            mp = minutos.punto(list(j.minutos))
            if mp is None:
                continue
            tr = minutos.tramo(mp)
            p_juega = par.p_estado.get(j.estado, par.p_sin_parte.get(tr)) if j.estado is not None else par.p_sin_parte.get(tr)
            if p_juega is None or p_juega < P_MINIMA or mp < MINUTOS_MINIMOS:
                continue
            n = len(j.minutos)
            mh = np.full((1, V), np.nan)
            sh = np.full((1, len(par.estadisticas), V), np.nan)
            mh[0, -n:] = j.minutos
            sh[0, :, -n:] = np.array(j.stats).T
            tasa = props.tasa_por_minuto(mh, sh, par.prior[props.nivel([mp])], par.k_minutos, par.decaimiento)[0]
            muestras = minutos.muestras_condicionadas([mp], par.residuos, N_MINUTOS)
            min_si_juega = [float(np.quantile(muestras, q)) for q in (0.1, 0.5, 0.9)]
            for s, nombre in enumerate(par.estadisticas):
                pmf = props.pmf_mezcla(tasa[s:s + 1], muestras, par.alfa[s], props.TECHO[nombre])[0]
                pmf = pmf / pmf.sum()
                k = np.arange(len(pmf))
                salida.append({
                    "jugador": j.id, "nombre": j.nombre, "lado": lado, "mercado": NOMBRES_MERCADO[nombre],
                    "escenarios": {"nombre": j.nombre, "lado": lado, "estado": j.estado, "p_juega": round(float(p_juega), 4), "minutos_si_juega": [round(x, 2) for x in min_si_juega],
                                   "partidos_en_historia": n, "parametros": par.version},
                    "distribucion": {"pmf": [round(float(x), 6) for x in pmf], "media": round(float((pmf * k).sum()), 4),
                                     "p10": _cuantil(pmf, 0.10), "p50": _cuantil(pmf, 0.50), "p90": _cuantil(pmf, 0.90),
                                     "p_juega": round(float(p_juega), 4), "minutos_esperados": round(float(mp), 2)}})
    return salida
