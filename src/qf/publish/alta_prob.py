"""
Línea de alta probabilidad: un pronóstico por partido con probabilidad real
entre el 80 % y el 95 %.

Es una línea de ACIERTO, no de valor (decisión del usuario, 2026-10-05; diseño
en docs/superpowers/specs/2026-10-05-linea-alta-probabilidad-design.md). Con
las casas de los suscriptores estos resultados no tienen valor esperado
positivo: football-data 2019-2025, favorito ≥ 80 %, ROI −2,4 % y EV al cierre
−2,6 %. Lo que sí se cumple es lo prometido: Pinnacle sin margen está
calibrado (84,6 % previsto, 84,8 % real; doble oportunidad 87,2 / 87,8).

POR QUÉ PINNACLE Y NO EL MODELO
-------------------------------
El modelo no bate al cierre sin margen (README, model-card). Aquí la promesa
es un porcentaje: tiene que salir de la referencia mejor calibrada.

LA REGLA
--------
Candidatos de 1X2, doble oportunidad (suma exacta del 1X2), goles y "marca
un equipo" (los dos últimos, desde los goles esperados que reproducen el 1X2 y
la línea de Pinnacle, `market_anchor.market_lambdas`). Se publica el de MENOR
probabilidad dentro de [PROB_MIN, PROB_MAX]: el más informativo sin bajar del
80 %. El tope evita obviedades ("menos de 5,5 goles" al 98 %).

Este módulo es la parte pura. La base de datos está en `alta_prob_datos.py`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import numpy as np
import pandas as pd

from ..eval.soft_vs_sharp import MIN_WEEKS, _weekly_ci
from ..model.market_anchor import market_lambdas
from ..model.pricing import market_team_total, market_totals, score_matrix

PROB_MIN = 0.80
PROB_MAX = 0.95
MAX_EDAD_PRECIO = timedelta(hours=6)
HORIZONTE = timedelta(hours=36)
# Error absoluto máximo del ajuste de goles sobre las probabilidades de
# entrada. Por encima, el 1X2 y la línea de goles de Pinnacle no caben en la
# misma pareja de lambdas y los goles derivados no serían de fiar.
MAX_RESIDUO_AJUSTE = 0.01
# Las líneas que se calculan. Solo se publican las de
# MERCADOS_GOLES_HABILITADOS, que pasaron la prueba histórica
# (eval/alta_prob_calibracion.py). Cambiar esa lista exige repetir la prueba.
LINEAS_GOLES: tuple[tuple[str, float], ...] = (("over", 1.5), ("under", 3.5), ("under", 4.5))
# Pasaron la prueba histórica el 2026-10-05 (eval/alta_prob_calibracion.py,
# firma d5cbc3151164dcc19e7304bba45ad2445d1e99a2ce97ddd5e92ea05c2f8ca79d,
# rho −0,0613): h2h 84,46→84,82, double_chance 85,83→86,36, totals over 1.5
# 84,2→84,09, totals under 3.5 82,56→83,36, totals under 4.5 86,95→87,4.
# "Menos de 4,5" pasó la prueba pero se excluye por decisión del usuario
# (2026-10-06): era el pronóstico de goles más frecuente y se paga a
# 1,09-1,17, poco útil para el cliente. Quitar una línea no exige repetir la
# prueba; añadirla, sí.
MERCADOS_GOLES_HABILITADOS: tuple[tuple[str, float], ...] = (
    ("over", 1.5), ("under", 3.5))
# "Marca el local / el visitante" (más de 0,5 goles de ese equipo), del mismo
# ajuste que los goles. Prueba histórica 2026-10-07 (firma d5cbc3151164…, rho
# −0,0613, 14.216 partidos, criterio de eval/alta_prob_calibracion.py): local
# n=4.470 86,97→88,52; visitante n=2.447 86,10→87,45; los tres tramos pasan.
MERCADOS_EQUIPO_HABILITADOS: tuple[str, ...] = ("home", "away")
# Mercados que guardan el ajuste de goles en `fit`.
MERCADOS_CON_AJUSTE = ("totals", "team_totals_home", "team_totals_away")
# Liquidados mínimos antes de que el control pueda pausar la línea.
MIN_N_CONTROL = 50
# Semanas distintas mínimas antes de que el IC pueda pausar, y nivel del IC.
# Medido (Monte Carlo del 2026-10-06: 300 líneas de 26 semanas, ~50
# pronósticos por semana, mezcla 70 % doble oportunidad / 20 % 1X2 / 10 %
# goles, evaluadas cada semana): con una línea PERFECTAMENTE calibrada, el
# control anterior (IC95 desde 8 semanas) pausaba algo en el 27 % de las líneas
# (la línea entera en el 10,7 %), casi todo al llegar a las 8-9 semanas: un IC
# que remuestrea pocas semanas queda corto y hay varios contrastes (todo + un
# grupo por mercado) repetidos cada semana. Con IC99, 10 semanas y la red z se
# bajó a 9,7 % y 3,0 %, con 88 % de detección, pero esa medición suponía
# probabilidades uniformes y 4 grupos. Revisión final del 2026-10-07, con la
# mezcla realista de mercados elegidos y "marca el local / el visitante"
# fusionados en un grupo (`grupo_control`), en 26 semanas: ~16 % de líneas con
# alguna pausa de grupo en falso y ~5 % con la línea entera pausada en falso; un
# déficit real de 3 puntos se detecta en ~82 % de las líneas (algún grupo) y
# ~73 % (la línea entera). Decisión del usuario.
MIN_SEMANAS_CONTROL = 10
NIVEL_IC_CONTROL = 0.99
# Red temprana para fallos groseros, sin esperar a las semanas del IC:
# z = Σ(acertado − prob) / sqrt(Σ prob·(1 − prob)). Con n ≥ MIN_N_CONTROL, un
# z ≤ −4 es un acierto que una línea calibrada casi nunca da (en el mismo Monte
# Carlo, 2 de 300 líneas sanas en 26 semanas: el binomial tiene la cola
# izquierda más gorda que la normal y se mira cada semana).
Z_GROSERO = -4.0
# Desempate exacto entre candidatos de la misma probabilidad.
_PRIORIDAD = {"h2h": 0, "totals": 1, "team_totals_home": 2, "team_totals_away": 2,
              "double_chance": 3}
_SEL = ("home", "draw", "away")


@dataclass(frozen=True)
class Candidato:
    market: str              # 'h2h' | 'double_chance' | 'totals' | 'team_totals_home' | 'team_totals_away' (los de clv._settle_outcome)
    selection: str           # home/draw/away · 1X/X2/12 · over/under
    line: float | None
    prob: float


def candidatos_1x2(p: dict[str, float]) -> list[Candidato]:
    return [Candidato("h2h", s, None, float(p[s])) for s in _SEL]


def candidatos_doble(p: dict[str, float]) -> list[Candidato]:
    return [Candidato("double_chance", "1X", None, float(p["home"] + p["draw"])),
            Candidato("double_chance", "X2", None, float(p["draw"] + p["away"])),
            Candidato("double_chance", "12", None, float(p["home"] + p["away"]))]


def ajuste_goles(p: dict[str, float], linea: float, p_over: float,
                 rho: float) -> dict | None:
    """Goles esperados de mercado, o None si el ajuste no reproduce la entrada."""
    try:
        fit = market_lambdas(p["home"], p["draw"], p["away"], rho=rho,
                             totals={linea: p_over})
    except ValueError:
        return None
    if not fit.converged or fit.residual > MAX_RESIDUO_AJUSTE:
        return None
    return {"lambda": fit.lam, "mu": fit.mu, "rho": rho,
            "linea": linea, "residuo": fit.residual}


def candidatos_goles(ajuste: dict | None,
                     habilitados: tuple[tuple[str, float], ...] | None = None
                     ) -> list[Candidato]:
    habilitados = MERCADOS_GOLES_HABILITADOS if habilitados is None else habilitados
    if ajuste is None or not habilitados:
        return []
    m = score_matrix(ajuste["lambda"], ajuste["mu"], ajuste["rho"])
    return [Candidato("totals", sel, linea, market_totals(m, linea)[sel])
            for sel, linea in habilitados]


def candidatos_equipo(ajuste: dict | None,
                      lados: tuple[str, ...] | None = None) -> list[Candidato]:
    """Más de 0,5 goles de cada equipo, del mismo ajuste que los goles."""
    lados = MERCADOS_EQUIPO_HABILITADOS if lados is None else lados
    if ajuste is None or not lados:
        return []
    m = score_matrix(ajuste["lambda"], ajuste["mu"], ajuste["rho"])
    return [Candidato(f"team_totals_{lado}", "over", 0.5,
                      market_team_total(m, 0.5, lado)["over"]) for lado in lados]


def grupo_control(market: str) -> str:
    """
    Grupo en el que el control vigila un mercado. "Marca el local" y "marca el
    visitante" se vigilan como UN solo grupo, `team_totals` (decisión del
    usuario, 2026-10-07): son la misma apuesta vista desde cada lado y, por
    separado, la muestra de cada uno es corta. En el Monte Carlo del revisor,
    fusionados dan menos pausas en falso y más detección. El resto de mercados
    es su propio grupo.
    """
    return "team_totals" if market in ("team_totals_home", "team_totals_away") else market


def elegir(cands: list[Candidato], excluir: set[str] | frozenset = frozenset()
           ) -> Candidato | None:
    """`excluir` admite mercados sueltos o grupos del control (`grupo_control`)."""
    dentro = [c for c in cands
              if c.market not in excluir and grupo_control(c.market) not in excluir
              and PROB_MIN <= c.prob <= PROB_MAX]
    if not dentro:
        return None
    return min(dentro, key=lambda c: (c.prob, _PRIORIDAD[c.market]))


def _goles(x: float) -> str:
    return f"{x:g}".replace(".", ",")


def texto(market: str, selection: str, line: float | None,
          local: str, visitante: str) -> str:
    """El pronóstico en palabras, como se enseña en la web."""
    if market == "h2h":
        return {"home": f"Gana {local}", "away": f"Gana {visitante}",
                "draw": "Empate"}[selection]
    if market == "double_chance":
        return {"1X": f"{local} o empate", "X2": f"{visitante} o empate",
                "12": f"{local} o {visitante} (sin empate)"}[selection]
    if market == "totals":
        return f"{'Más' if selection == 'over' else 'Menos'} de {_goles(line)} goles"
    if market in ("team_totals_home", "team_totals_away"):
        return f"Marca {local if market.endswith('home') else visitante}"
    raise ValueError(f"Mercado desconocido: {market}")


# --------------------------------------------------------------------------
# Control de calidad e historial
# --------------------------------------------------------------------------

def _marco(liquidados: list[dict]) -> pd.DataFrame:
    f = pd.DataFrame(liquidados)
    f["prob"] = f["prob"].astype(float)
    f["won"] = f["outcome"] == "win"
    f["diff"] = f["won"].astype(float) - f["prob"]
    ko = pd.to_datetime(f["kickoff_utc"], utc=True).dt.tz_convert(None)
    f["week"] = ko.dt.to_period("W").astype(str)
    f["mes"] = ko.dt.strftime("%Y-%m")
    return f


def _z(g: pd.DataFrame) -> float:
    """Acertado frente a prometido, en desviaciones típicas de un acierto calibrado."""
    var = float((g["prob"] * (1.0 - g["prob"])).sum())
    return float(g["diff"].sum()) / var ** 0.5 if var > 0 else 0.0


def control(liquidados: list[dict], min_n: int = MIN_N_CONTROL) -> dict:
    """
    ¿Promete de más? En conjunto ("todo") y por grupo de mercado
    (`grupo_control`: "marca el local" y "marca el visitante" juntos), con n ≥ min_n:
      1. z ≤ Z_GROSERO (fallo grosero) bloquea ya, aunque haya pocas semanas.
      2. Con ≥ MIN_SEMANAS_CONTROL semanas distintas, si el límite superior del
         IC99 de (acertado − prob) es < 0, se bloquea. El IC remuestrea semanas
         enteras, como la puerta de valor.
    Con menos semanas y sin fallo grosero no se bloquea: se informa.
    """
    if not liquidados:
        return {"bloqueados": [], "motivos": ["Sin pronósticos liquidados todavía"]}
    f = _marco(liquidados)
    bloqueados, motivos = [], []
    for nombre, g in [("todo", f), *f.groupby(f["market"].map(grupo_control))]:
        if len(g) < min_n:
            motivos.append(f"{nombre}: muestra insuficiente ({len(g)} < {min_n})")
            continue
        z = _z(g)
        if z <= Z_GROSERO:
            bloqueados.append(str(nombre))
            motivos.append(f"{nombre}: fallo grosero, acierto real muy por debajo del "
                           f"prometido (z {z:.1f} ≤ {Z_GROSERO:.0f}, {len(g)} pronósticos)")
            continue
        if g["week"].nunique() < MIN_SEMANAS_CONTROL:
            motivos.append(f"{nombre}: muestra insuficiente "
                           f"(menos de {MIN_SEMANAS_CONTROL} semanas)")
            continue
        ic = _weekly_ci(g["diff"].to_numpy(float), g["week"].to_numpy(),
                        level=NIVEL_IC_CONTROL)
        if ic is None:
            motivos.append(f"{nombre}: muestra insuficiente (menos de {MIN_WEEKS} semanas)")
            continue
        if ic[1] < 0:
            bloqueados.append(str(nombre))
            motivos.append(f"{nombre}: acierto real por debajo del prometido "
                           f"(IC99 {ic[0] * 100:+.1f} a {ic[1] * 100:+.1f} puntos)")
    return {"bloqueados": bloqueados, "motivos": motivos}


def _bloque(g: pd.DataFrame) -> dict:
    return {"n": int(len(g)), "aciertos": int(g["won"].sum()),
            "acierto_prometido": round(float(g["prob"].mean()) * 100, 1),
            "acierto_real": round(float(g["won"].mean()) * 100, 1)}


def historial(liquidados: list[dict]) -> dict:
    """Lo prometido frente a lo ocurrido, entero y sin filtrar. En %."""
    if not liquidados:
        return {"n": 0, "aciertos": 0, "acierto_prometido": None, "acierto_real": None,
                "diferencia_ic95": None, "por_mercado": {}, "por_mes": [],
                "rendimiento_ref": {"n": 0, "roi": None}}
    f = _marco(liquidados)
    ic = _weekly_ci(f["diff"].to_numpy(float), f["week"].to_numpy())
    con_ref = f[f["ref_price"].notna()] if "ref_price" in f else f.iloc[0:0]
    roi = (np.where(con_ref["won"], con_ref["ref_price"].astype(float) - 1.0, -1.0).mean() * 100
           if len(con_ref) else None)
    return {**_bloque(f),
            "diferencia_ic95": None if ic is None else [round(ic[0] * 100, 1), round(ic[1] * 100, 1)],
            "por_mercado": {str(k): _bloque(g) for k, g in f.groupby("market")},
            "por_mes": [{"mes": k, **_bloque(g)}
                        for k, g in sorted(f.groupby("mes"), key=lambda kg: kg[0], reverse=True)],
            "rendimiento_ref": {"n": int(len(con_ref)),
                                "roi": None if roi is None else round(float(roi), 2)}}
