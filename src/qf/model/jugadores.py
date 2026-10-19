"""Impacto por jugador del once real frente al once habitual del equipo (candidato a bloque de contexto, 19-oct-2026).

Idea: el once confirmado a T-60 dice quién falta de verdad. Lo que importa no es cuánto vale el once en absoluto (eso ya lo
sabe el nivel del equipo, y el bloque `xi_valor` no mejoró nada), sino cuánto se aparta del once HABITUAL del propio equipo.

Todo es point-in-time: se recorren los partidos en orden y, ANTES de actualizar el estado con un partido, se calculan sus
columnas con lo que se sabía de partidos anteriores.

- Fuerza del jugador: calificación de FotMob RELATIVA a la media de su equipo en ese partido (así no mide el nivel del
  equipo, que ya recoge Dixon-Coles), acumulada y encogida a 0 con `K_ENCOGIMIENTO` observaciones.
- Once habitual: los 11 jugadores con más titularidades en los últimos `VENTANA_HABITUAL` partidos del equipo.
- Delta de un lado y grupo de posición = suma de fuerzas del once real menos la del habitual, ambas con la fuerza previa a
  este partido. Positivo = hoy juega mejor once que el habitual.
- Delta de valor: logaritmo del valor de mercado del once real entre el del habitual.

El grupo sale del `posicion_id` de FotMob (la decena identifica la fila del campo: 11 portero, 3x-5x defensas, 6x-7x medios,
8x-11x delanteros). El portero cuenta con la defensa.
"""
from __future__ import annotations

from collections import deque

import numpy as np
import pandas as pd

K_ENCOGIMIENTO = 8.0
VENTANA_HABITUAL = 5
MIN_PARTIDOS_PREVIOS = 3
MIN_ONCE = 9            # un once con menos jugadores identificados se considera dato incompleto

COLUMNAS = {
    "epi_total": ("epi_total_local", "epi_total_visita"),
    "epi_grupos": ("epi_def_local", "epi_med_local", "epi_ata_local", "epi_def_visita", "epi_med_visita", "epi_ata_visita"),
    "xi_habitual_valor": ("xiv_delta_local", "xiv_delta_visita"),
}
_VALORES = ("epi_def", "epi_med", "epi_ata", "epi_total", "xiv_delta")


def grupo_posicion(posicion_id) -> str | None:
    if posicion_id is None or pd.isna(posicion_id):
        return None
    p = int(posicion_id)
    if 30 <= p < 60 or p == 11:
        return "def"
    if 60 <= p < 80:
        return "med"
    if 80 <= p < 120:
        return "ata"
    return None


def _habitual(historial) -> list:
    """Los 11 con más titularidades en la ventana; a igualdad, los más recientes."""
    conteo: dict = {}
    for orden, once in enumerate(historial):
        for j in once:
            c = conteo.setdefault(j, [0, 0])
            c[0] += 1
            c[1] = orden
    return [j for j, _ in sorted(conteo.items(), key=lambda kv: (-kv[1][0], -kv[1][1]))[:11]]


def features_xi(filas: pd.DataFrame) -> pd.DataFrame:
    """Una fila por partido con las columnas de COLUMNAS (NaN si el equipo aún no tiene MIN_PARTIDOS_PREVIOS onces).

    `filas`: una por aparición, con match_id, kickoff_utc, side ('home'|'away'), equipo_id, jugador_id, titular,
    posicion_id, valor_mercado y rating.
    """
    suma: dict = {}          # jugador -> suma de calificaciones relativas
    n: dict = {}             # jugador -> apariciones calificadas
    valor: dict = {}         # jugador -> último valor de mercado conocido
    grupo: dict = {}         # jugador -> último grupo en que fue titular
    historial: dict = {}     # equipo -> deque de onces recientes

    def fuerza(j) -> float:
        return suma.get(j, 0.0) / (n.get(j, 0) + K_ENCOGIMIENTO)

    d = filas.sort_values(["kickoff_utc", "match_id"])
    salida = []
    for mid, partido in d.groupby("match_id", sort=False):
        lados = {}
        for side, p in partido.groupby("side"):
            lados[side] = p
        fila = {"match_id": mid}
        a_actualizar = []
        for side, p in lados.items():
            sufijo = "local" if side == "home" else "visita"
            equipo = p["equipo_id"].iloc[0]
            titulares = p[p["titular"].astype(bool)]
            hist = historial.setdefault(equipo, deque(maxlen=VENTANA_HABITUAL))
            if len(hist) >= MIN_PARTIDOS_PREVIOS and len(titulares) >= MIN_ONCE:
                usual = _habitual(hist)
                suma_g = {"def": 0.0, "med": 0.0, "ata": 0.0}
                for r in titulares.itertuples():
                    g = grupo_posicion(r.posicion_id)
                    if g:
                        suma_g[g] += fuerza(r.jugador_id)
                for j in usual:
                    g = grupo.get(j)
                    if g:
                        suma_g[g] -= fuerza(j)
                for g in ("def", "med", "ata"):
                    fila[f"epi_{g}_{sufijo}"] = suma_g[g]
                fila[f"epi_total_{sufijo}"] = float(sum(suma_g.values()))
                v_real = float(titulares["valor_mercado"].fillna(0).sum())
                v_hab = float(sum(valor.get(j, 0.0) for j in usual))
                fila[f"xiv_delta_{sufijo}"] = float(np.log(v_real) - np.log(v_hab)) if v_real > 0 and v_hab > 0 else np.nan
            a_actualizar.append((equipo, p, titulares))
        salida.append(fila)
        # recién ahora el partido pasa a ser pasado
        for equipo, p, titulares in a_actualizar:
            calif = p["rating"]
            media = calif.mean()
            for r in p.itertuples():
                if pd.notna(r.rating):
                    suma[r.jugador_id] = suma.get(r.jugador_id, 0.0) + float(r.rating - media)
                    n[r.jugador_id] = n.get(r.jugador_id, 0) + 1
                if pd.notna(r.valor_mercado):
                    valor[r.jugador_id] = float(r.valor_mercado)
                if r.titular:
                    g = grupo_posicion(r.posicion_id)
                    if g:
                        grupo[r.jugador_id] = g
            if len(titulares) >= MIN_ONCE:
                historial[equipo].append(list(titulares["jugador_id"]))
    out = pd.DataFrame(salida)
    for lado in ("local", "visita"):
        for v in _VALORES:
            if f"{v}_{lado}" not in out.columns:
                out[f"{v}_{lado}"] = np.nan
    return out


def cargar_filas(desde: str = "2023-01-01") -> pd.DataFrame:
    """Apariciones de FotMob de los partidos desde `desde`, con el equipo de cada lado."""
    from ..db import query
    return pd.DataFrame(query(
        """SELECT j.match_id, m.kickoff_utc, j.side,
                  CASE WHEN j.side = 'home' THEN m.home_team_id ELSE m.away_team_id END AS equipo_id,
                  j.jugador_id, j.titular, j.posicion_id, j.valor_mercado, j.rating
           FROM fotmob_jugador_partido j JOIN matches m USING (match_id)
           WHERE m.kickoff_utc >= %s""", (desde,)))
