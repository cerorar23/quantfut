"""Consulta de partidos y probabilidad acumulada compartidas por los módulos de lectura de la API.

`PARTIDOS` devuelve, por partido canónico:
  (entidad_id, fecha_juego_et, entidad_local, entidad_visitante, nombre_local, nombre_visitante,
   código_local, código_visitante)
Las entidades son los ids internos de `nba.entidad` (los de `nba.cuota.entidad_id`); los códigos son el id de la
fuente oficial (el que entiende `TRICODES`). Se deduplica por la clave canónica del partido.
"""
from __future__ import annotations

import numpy as np
from ..v2.contratos_apuesta import ProbabilidadesContrato, desde_masas

PARTIDOS = ("SELECT e.entidad_id, e.fecha_juego_et, tl.entidad_id, tv.entidad_id, tl.nombre, tv.nombre, "
            "tl.id_en_fuente, tv.id_en_fuente FROM nba.entidad e "
            "JOIN nba.entidad tl ON tl.entidad_id = (e.atributos->>'local')::bigint "
            "JOIN nba.entidad tv ON tv.entidad_id = (e.atributos->>'visitante')::bigint "
            "WHERE e.tipo = 'partido' AND e.canonica_id = e.entidad_id "
            "AND e.entidad_id = (SELECT min(x.entidad_id) FROM nba.entidad x WHERE x.tipo = 'partido' "
            "AND x.canonica_id = x.entidad_id AND x.fecha_juego_et = e.fecha_juego_et "
            "AND x.atributos->>'local' = e.atributos->>'local' AND x.atributos->>'visitante' = e.atributos->>'visitante')")


def prob_mas_de(cuantiles: list[float], linea: float, paso: float = 0.005) -> tuple[float, bool]:
    """P(X > línea) a partir de los cuantiles (199 valores, niveles paso…1-paso). Fuera del rango se acota a [paso, 1-paso]
    y se marca como extremo. Interpolación lineal del nivel entre cuantiles contiguos."""
    q = np.asarray(cuantiles, float)
    if not np.isfinite(linea) or q.ndim != 1 or not len(q) or not np.isfinite(q).all() or (np.diff(q) < 0).any():
        raise ValueError("cuantiles o línea inválidos")
    if np.allclose(q, np.round(q), rtol=0, atol=1e-12):
        # Los sellos antiguos solo guardaban cuantiles: distribución discreta aproximada,
        # con resolución de 0,5 pp. Nunca se convierte un átomo en un tramo continuo.
        return float(np.mean(q > linea)), bool(linea <= q[0] or linea >= q[-1])
    niveles = paso * np.arange(1, len(q) + 1)
    if linea <= q[0]:
        return 1.0 - paso, True
    if linea >= q[-1]:
        return paso, True
    # np.interp exige abscisas crecientes: se desempata con una mota para cuantiles repetidos (distribución discreta)
    xs = q + np.arange(len(q)) * 1e-9
    return float(1.0 - np.interp(linea, xs, niveles)), False


def contrato_linea(dist: dict, mercado: str, linea: float) -> dict:
    ley = (dist.get("masas") or {}).get(mercado)
    if ley is not None:
        p = desde_masas(ley["soporte"], ley["pmf"], linea)
        return dict(p.salida(), extremo=p.gana == 0 or p.pierde == 0, aproximada=False, error_resolucion=0.)
    q = np.asarray(dist[mercado], float)
    if np.allclose(q, np.round(q), rtol=0, atol=1e-12):
        p = desde_masas(q, np.full(len(q), 1 / len(q)), linea)
    else:
        mas, _ = prob_mas_de(q.tolist(), linea, dist["paso_cuantil"])
        p = ProbabilidadesContrato(mas, 0., 1 - mas)
    return dict(p.salida(), extremo=bool(linea <= q[0] or linea >= q[-1]),
                aproximada=True, error_resolucion=float(dist["paso_cuantil"]))


