"""
Pricing de mercados en forma cerrada.

Una vez que tienes (lambda_local, lambda_visitante, rho) construyes UNA matriz
de marcadores de ~13x13 y de ahí salen ~150 mercados sin Monte Carlo.

Coste: ~0.3 ms por partido. 200 partidos con todos sus mercados < 2 s en CPU.
Esto es lo que hace que no necesites GPU en producción.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import poisson

# ---------------------------------------------------------------------------
# Matriz de marcadores con corrección Dixon-Coles
# ---------------------------------------------------------------------------


def dc_tau(home_goals: np.ndarray, away_goals: np.ndarray,
           lam: float, mu: float, rho: float) -> np.ndarray:
    """
    Corrección tau de Dixon-Coles. Poisson independiente subestima 0-0 y 1-1
    y sobreestima 1-0 y 0-1. Esto lo corrige.
    """
    t = np.ones_like(home_goals, dtype=float)
    t = np.where((home_goals == 0) & (away_goals == 0), 1.0 - lam * mu * rho, t)
    t = np.where((home_goals == 0) & (away_goals == 1), 1.0 + lam * rho, t)
    t = np.where((home_goals == 1) & (away_goals == 0), 1.0 + mu * rho, t)
    t = np.where((home_goals == 1) & (away_goals == 1), 1.0 - rho, t)
    return np.clip(t, 1e-9, None)


def score_matrix(lam: float, mu: float, rho: float = 0.0, max_goals: int = 12) -> np.ndarray:
    """P[i, j] = probabilidad de marcador i-j. Filas = local, columnas = visitante."""
    g = np.arange(max_goals + 1)
    ph = poisson.pmf(g, lam)
    pa = poisson.pmf(g, mu)
    m = np.outer(ph, pa)
    hg, ag = np.meshgrid(g, g, indexing="ij")
    m = m * dc_tau(hg, ag, lam, mu, rho)
    return m / m.sum()


# ---------------------------------------------------------------------------
# Mercados derivados
# ---------------------------------------------------------------------------


def market_1x2(m: np.ndarray) -> dict[str, float]:
    return {
        "home": float(np.tril(m, -1).sum()),
        "draw": float(np.trace(m)),
        "away": float(np.triu(m, 1).sum()),
    }


def market_double_chance(m: np.ndarray) -> dict[str, float]:
    r = market_1x2(m)
    return {
        "1X": r["home"] + r["draw"],
        "12": r["home"] + r["away"],
        "X2": r["draw"] + r["away"],
    }


def market_btts(m: np.ndarray) -> dict[str, float]:
    yes = float(m[1:, 1:].sum())
    return {"yes": yes, "no": 1.0 - yes}


def market_totals(m: np.ndarray, line: float) -> dict[str, float]:
    """Over/Under de goles totales. Soporta líneas enteras (con push)."""
    n = m.shape[0]
    hg, ag = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    tot = hg + ag
    over = float(m[tot > line].sum())
    under = float(m[tot < line].sum())
    push = float(m[tot == line].sum())
    return {"over": over, "under": under, "push": push}


def market_team_total(m: np.ndarray, line: float, side: str) -> dict[str, float]:
    n = m.shape[0]
    goals = np.arange(n)
    marg = m.sum(axis=1) if side == "home" else m.sum(axis=0)
    return {
        "over": float(marg[goals > line].sum()),
        "under": float(marg[goals < line].sum()),
        "push": float(marg[goals == line].sum()),
    }


def market_asian_handicap(m: np.ndarray, line: float) -> dict[str, float]:
    """
    Hándicap asiático para el LOCAL con `line` (ej. -0.5, -0.25, +1.0).

    Las líneas de cuarto se parten en dos mitades, así que un marcador puede
    producir medio gane o media pérdida. La probabilidad efectiva correcta NO
    es el promedio de las probabilidades condicionales de las dos mitades:
    hay que igualar el valor esperado.

        E[retorno] = E[w] * cuota + E[push]
        cuota justa = (1 - E[push]) / E[w]
        prob efectiva = E[w] / (1 - E[push])

    donde E[w] es la fracción esperada del stake que gana y E[push] la que se
    devuelve. Usar el promedio de condicionales sobreestima al favorito en
    ~1 punto porcentual, que es más que el edge que buscas.
    """
    if abs(line * 4 - round(line * 4)) > 1e-9:
        raise ValueError(f"Línea AH inválida: {line}")

    n = m.shape[0]
    hg, ag = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    diff = (hg - ag).astype(float)

    # Componentes de media línea (una sola para líneas enteras/medias)
    is_quarter = abs(line * 2 - round(line * 2)) > 1e-9
    legs = [line - 0.25, line + 0.25] if is_quarter else [line]
    wgt = 1.0 / len(legs)

    w_home = np.zeros_like(diff)
    w_away = np.zeros_like(diff)
    push_frac = np.zeros_like(diff)

    for leg in legs:
        adj = diff + leg
        w_home += wgt * (adj > 1e-9)
        w_away += wgt * (adj < -1e-9)
        push_frac += wgt * (np.abs(adj) < 1e-9)

    e_wh = float((m * w_home).sum())
    e_wa = float((m * w_away).sum())
    e_push = float((m * push_frac).sum())

    denom = 1.0 - e_push
    return {
        "home": e_wh / denom if denom > 1e-12 else 0.5,
        "away": e_wa / denom if denom > 1e-12 else 0.5,
        "home_raw": e_wh,
        "away_raw": e_wa,
        "push": e_push,
        "fair_odds_home": (denom / e_wh) if e_wh > 1e-12 else None,
        "fair_odds_away": (denom / e_wa) if e_wa > 1e-12 else None,
    }


def market_correct_score(m: np.ndarray, top_n: int = 12) -> list[dict]:
    n = m.shape[0]
    flat = [(int(i), int(j), float(m[i, j])) for i in range(n) for j in range(n)]
    flat.sort(key=lambda x: -x[2])
    return [{"score": f"{i}-{j}", "prob": p} for i, j, p in flat[:top_n]]


def market_winning_margin(m: np.ndarray) -> dict[str, float]:
    n = m.shape[0]
    hg, ag = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    d = hg - ag
    out = {"draw": float(m[d == 0].sum())}
    for k in (1, 2, 3):
        out[f"home_by_{k}"] = float(m[d == k].sum())
        out[f"away_by_{k}"] = float(m[d == -k].sum())
    out["home_by_4plus"] = float(m[d >= 4].sum())
    out["away_by_4plus"] = float(m[d <= -4].sum())
    return out


# ---------------------------------------------------------------------------
# Paquete completo
# ---------------------------------------------------------------------------

TOTAL_LINES = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
TEAM_TOTAL_LINES = [0.5, 1.5, 2.5, 3.5]
AH_LINES = [-2.0, -1.75, -1.5, -1.25, -1.0, -0.75, -0.5, -0.25, 0.0,
            0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]


def price_all_markets(lam: float, mu: float, rho: float = 0.0,
                      max_goals: int = 12) -> dict:
    """
    Devuelve el paquete completo de mercados listo para guardar en
    predictions.markets (JSONB) y para servir por la API.
    """
    m = score_matrix(lam, mu, rho, max_goals)

    out: dict = {
        "1x2": market_1x2(m),
        "double_chance": market_double_chance(m),
        "btts": market_btts(m),
        "winning_margin": market_winning_margin(m),
        "correct_score": market_correct_score(m),
        "totals": {},
        "team_totals": {"home": {}, "away": {}},
        "asian_handicap": {},
    }

    for ln in TOTAL_LINES:
        out["totals"][f"{ln}"] = market_totals(m, ln)
    for ln in TEAM_TOTAL_LINES:
        out["team_totals"]["home"][f"{ln}"] = market_team_total(m, ln, "home")
        out["team_totals"]["away"][f"{ln}"] = market_team_total(m, ln, "away")
    for ln in AH_LINES:
        out["asian_handicap"][f"{ln:+.2f}"] = market_asian_handicap(m, ln)

    # Cuotas justas (1/p) para los mercados principales
    out["fair_odds"] = {
        "1x2": {k: (1.0 / v if v > 0 else None) for k, v in out["1x2"].items()},
        "totals_2.5": {
            "over": 1.0 / out["totals"]["2.5"]["over"] if out["totals"]["2.5"]["over"] > 0 else None,
            "under": 1.0 / out["totals"]["2.5"]["under"] if out["totals"]["2.5"]["under"] > 0 else None,
        },
    }
    out["expected_goals"] = {"home": lam, "away": mu, "total": lam + mu}
    return out


def flatten_for_edge(markets: dict) -> list[tuple[str, str, float | None, float]]:
    """
    Aplana el paquete a (market, selection, line, prob) para comparar contra
    las cuotas disponibles y buscar valor.
    """
    rows: list[tuple[str, str, float | None, float]] = []
    for sel, p in markets["1x2"].items():
        rows.append(("h2h", sel, None, p))
    for sel, p in markets["btts"].items():
        rows.append(("btts", sel, None, p))
    for sel, p in markets["double_chance"].items():
        rows.append(("double_chance", sel, None, p))
    for ln, d in markets["totals"].items():
        for sel in ("over", "under"):
            rows.append(("totals", sel, float(ln), d[sel]))
    for side, lines in markets["team_totals"].items():
        for ln, d in lines.items():
            for sel in ("over", "under"):
                rows.append((f"team_totals_{side}", sel, float(ln), d[sel]))
    for ln, d in markets["asian_handicap"].items():
        rows.append(("spreads", "home", float(ln), d["home"]))
        rows.append(("spreads", "away", -float(ln), d["away"]))
    return rows
