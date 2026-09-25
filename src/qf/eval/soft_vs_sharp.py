"""
Backtest "casa blanda contra precio sharp" sobre las cuotas PRE-CIERRE de
football-data.co.uk.

La pregunta: si se apuesta en una casa blanda cuando su cuota supera el precio
justo de Pinnacle EN ESE MOMENTO, ¿esa cuota vale algo contra el cierre?

    edge_temprano = cuota_blanda × p_justa_pinnacle_temprana − 1   (decide)
    ev_cierre     = cuota_blanda × p_justa_pinnacle_cierre − 1     (mide)

`ev_cierre` es la misma cifra que decide la puerta comercial
(`promotion.evaluate_clv_gate`, ver `eval/clv.py`). El ROI se reporta, pero a
unos miles de apuestas sigue siendo ruido.

DE DÓNDE SALEN LOS DATOS
------------------------
Solo el formato PRINCIPAL (`leagues.fd_extra = FALSE`): trae, además del
cierre, cuotas pre-cierre que football-data toma el viernes por la tarde para
los partidos de fin de semana y el martes para los de entre semana, es decir,
entre uno y tres días antes del kickoff. El formato "extra" (Liga MX,
Argentina, Brasil, MLS) solo trae cierre y aquí no sirve. El cierre de
Pinnacle (`PSCH`) existe desde la temporada 2019/20.

FUGAS
-----
`check_leakage()` de `backtest.py` mira columnas del modelo que aquí no hay.
La fuga posible en este backtest es que la SELECCIÓN vea el cierre o el
resultado. `select_*` solo leen `price_early` y `p_fair_early`, y
`tests/test_soft_vs_sharp.py` lo comprueba alterando cierre y resultado.

FUERA DE ALCANCE, a propósito
-----------------------------
- Hándicap asiático: la línea pre-cierre (`AHh`) y la de cierre (`AHCh`)
  cambian a menudo, y sin la misma línea no hay cierre justo contra el que
  medir.
- `max_mercado` y `media_mercado` no son casas: son el máximo y la media de
  un agregador. El máximo es una cota OPTIMISTA (mezcla casas a las que un
  suscriptor puede no tener acceso, y precios que duran minutos).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import logging
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

from ..config import settings
from ..model.devig import devig

log = logging.getLogger(__name__)

URL = "https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
# Temporadas completas: sus ficheros ya no cambian y la firma es estable.
DEFAULT_SEASONS = ("1920", "2021", "2122", "2223", "2324", "2425")
THRESHOLDS = (0.0, 0.02, 0.04)
MIN_WEEKS = 8
AGGREGATES = ("max_mercado", "media_mercado")

# Guarda de calidad de la referencia sharp. Si la probabilidad justa de
# Pinnacle ANTES del cierre se aparta más de esto de la de la media de las
# casas en ese mismo momento, el mercado de ese partido no entra.
#
# Medido el 2026-09-23 sobre 14.294 partidos: la desviación Pinnacle-media
# tiene p99 de 1,5 puntos en 1X2 y 1,6 en over/under 2,5, pero en over/under
# hay una cola de hasta 10 puntos con el precio de Pinnacle congelado (el
# temprano igual al de cierre) o de otra línea. Ahí aparecían "edges" del
# 10-13% que persistían ENTEROS hasta el cierre, porque el cierre de
# referencia estaba igual de roto. En 2024/25, único año con Betfair Exchange,
# cuando Pinnacle y Betfair discrepan más de 3 puntos en over/under la media
# se pone del lado de Betfair en 21 de 24 casos: el que falla es Pinnacle.
# Con 0,03 desaparecen todos los casos de "la media supera el precio justo",
# que no deberían existir. Usa solo información temprana: no es una fuga.
MAX_SHARP_DEVIATION = 0.03


def _cols_1x2(prefix: str, close: bool) -> list[str]:
    c = "C" if close else ""
    return [f"{prefix}{c}{s}" for s in ("H", "D", "A")]


def _cols_ou25(prefix: str, close: bool) -> list[str]:
    c = "C" if close else ""
    return [f"{prefix}{c}{s}2.5" for s in (">", "<")]


# En el 1X2 Pinnacle es `PS`; en los totales es `P`. Así vienen los CSV.
MARKETS: dict[str, dict] = {
    "h2h": {
        "selections": ("home", "draw", "away"),
        "cols": _cols_1x2,
        "sharp": "PS",
        "books": {"B365": "bet365", "BW": "bwin", "WH": "williamhill",
                  "1XB": "1xbet", "IW": "interwetten", "VC": "betvictor",
                  "Max": "max_mercado", "Avg": "media_mercado"},
    },
    "totals_2.5": {
        "selections": ("over", "under"),
        "cols": _cols_ou25,
        "sharp": "P",
        "books": {"B365": "bet365", "Max": "max_mercado", "Avg": "media_mercado"},
    },
}


# --------------------------------------------------------------------------
# Datos
# --------------------------------------------------------------------------

def main_format_leagues() -> dict[str, str]:
    """{league_id: fd_code} de las ligas con cuotas pre-cierre."""
    from ..db import query
    rows = query("SELECT league_id, fd_code FROM leagues "
                 "WHERE fd_code IS NOT NULL AND NOT fd_extra ORDER BY league_id")
    return {r["league_id"]: r["fd_code"] for r in rows}


def load_csvs(leagues: dict[str, str], seasons: tuple[str, ...],
              cache_dir: Path, refresh: bool = False) -> tuple[pd.DataFrame, dict]:
    """
    Descarga (o lee de la caché) un CSV por liga y temporada.

    La firma es el sha256 de los bytes de cada fichero, ordenados: dos
    ejecuciones con la misma firma han visto exactamente los mismos datos.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    frames, digests = [], []
    for league_id, code in sorted(leagues.items()):
        for season in seasons:
            path = cache_dir / f"{code}_{season}.csv"
            if refresh or not path.exists():
                r = httpx.get(URL.format(season=season, code=code),
                              timeout=60, follow_redirects=True)
                if r.status_code == 404:
                    log.warning("%s %s no existe en football-data", code, season)
                    continue
                r.raise_for_status()
                path.write_bytes(r.content)
            raw = path.read_bytes()
            digests.append(f"{code}_{season}:{hashlib.sha256(raw).hexdigest()}")
            df = pd.read_csv(io.BytesIO(raw), encoding="latin-1", on_bad_lines="skip")
            df["league_id"], df["season"] = league_id, season
            frames.append(df)
    if not frames:
        raise RuntimeError("No se cargó ningún CSV")
    data = pd.concat(frames, ignore_index=True)
    dataset = {"sha256": hashlib.sha256("\n".join(digests).encode()).hexdigest(),
               "files": len(digests), "rows": len(data),
               "seasons": list(seasons), "leagues": sorted(leagues)}
    return data, dataset


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"]).copy()
    df["date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["date"])
    df["week"] = df["date"].dt.to_period("W").astype(str)
    df["match"] = (df["league_id"].astype(str) + ":" + df["date"].dt.strftime("%Y%m%d")
                   + ":" + df["HomeTeam"].astype(str) + "-" + df["AwayTeam"].astype(str))
    return df


def _winner_index(df: pd.DataFrame, market: str) -> np.ndarray:
    hg, ag = df["FTHG"].to_numpy(float), df["FTAG"].to_numpy(float)
    if market == "h2h":
        return np.where(hg > ag, 0, np.where(hg == ag, 1, 2))
    return np.where(hg + ag > 2.5, 0, 1)


def _devig_rows(prices: np.ndarray) -> np.ndarray:
    return np.vstack([devig(r, settings.devig_method) for r in prices])


def _with_sharp(df: pd.DataFrame, early: list[str], close: list[str]) -> pd.DataFrame:
    """Partidos con Pinnacle completo y válido antes Y al cierre."""
    if not set(early + close) <= set(df.columns):
        return df.iloc[0:0]
    base = df.copy()
    base[early + close] = base[early + close].apply(pd.to_numeric, errors="coerce")
    base = base.dropna(subset=early + close)
    return base[(base[early + close] > 1.0).all(axis=1)]


def _sharp_deviation(base: pd.DataFrame, spec: dict, p_sharp: np.ndarray) -> np.ndarray:
    """
    Máxima diferencia, entre selecciones, de la probabilidad justa de Pinnacle
    frente a la de la media de las casas, ambas PRE-CIERRE. NaN si no hay
    media completa: entonces la referencia no se puede verificar.
    """
    avg = spec["cols"]("Avg", False)
    out = np.full(len(base), np.nan)
    if not set(avg) <= set(base.columns):
        return out
    a = base[avg].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    ok = np.isfinite(a).all(axis=1) & (a > 1.0).all(axis=1)
    if ok.any():
        out[ok] = np.abs(_devig_rows(a[ok]) - p_sharp[ok]).max(axis=1)
    return out


def build_quotes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Formato largo: una fila por (partido, mercado, selección, casa) con la
    cuota PRE-CIERRE de la casa, la probabilidad justa de Pinnacle antes y al
    cierre, la cuota de cierre de Pinnacle (para el CLV con margen) y si ganó.

    Solo entran partidos con Pinnacle completo en los dos momentos: sin eso no
    hay ni criterio ni vara.
    """
    df = _prepare(df)
    out = []
    for market, spec in MARKETS.items():
        early = spec["cols"](spec["sharp"], False)
        close = spec["cols"](spec["sharp"], True)
        base = _with_sharp(df, early, close)
        if base.empty:
            continue
        p_early = _devig_rows(base[early].to_numpy(float))
        p_close = _devig_rows(base[close].to_numpy(float))
        winner = _winner_index(base, market)
        sharp_dev = _sharp_deviation(base, spec, p_early)
        for j, sel in enumerate(spec["selections"]):
            for prefix, book in spec["books"].items():
                col = spec["cols"](prefix, False)[j]
                if col not in base.columns:
                    continue
                price = pd.to_numeric(base[col], errors="coerce").to_numpy(float)
                ok = np.isfinite(price) & (price > 1.0)
                if not ok.any():
                    continue
                out.append(pd.DataFrame({
                    "match": base["match"].to_numpy()[ok],
                    "league_id": base["league_id"].to_numpy()[ok],
                    "week": base["week"].to_numpy()[ok],
                    "market": market, "selection": sel, "book": book,
                    "price_early": price[ok],
                    "p_fair_early": p_early[ok, j],
                    "p_fair_close": p_close[ok, j],
                    "sharp_close_price": base[close[j]].to_numpy(float)[ok],
                    "sharp_dev_early": sharp_dev[ok],
                    "won": winner[ok] == j,
                }))
    if not out:
        return pd.DataFrame()
    return pd.concat(out, ignore_index=True)


# --------------------------------------------------------------------------
# Selección: SOLO información disponible antes del cierre
# --------------------------------------------------------------------------

def _verified(quotes: pd.DataFrame) -> pd.DataFrame:
    """Solo mercados cuya referencia sharp cuadra con la media (NaN no pasa)."""
    return quotes[quotes["sharp_dev_early"] <= MAX_SHARP_DEVIATION]


def select_by_book(quotes: pd.DataFrame, book: str, threshold: float) -> pd.DataFrame:
    q = _verified(quotes)
    q = q[q["book"] == book]
    edge = q["price_early"] * q["p_fair_early"] - 1.0
    return q[edge >= threshold]


def select_best_of(quotes: pd.DataFrame, books: list[str],
                   threshold: float) -> pd.DataFrame:
    """
    Lo que haría el producto: por cada selección, la mejor cuota entre las
    casas permitidas, y se apuesta si supera el umbral. Una apuesta por
    selección aunque varias casas pasen.
    """
    q = _verified(quotes)
    q = q[q["book"].isin(books)]
    if q.empty:
        return q
    best = q.loc[q.groupby(["match", "market", "selection"])["price_early"].idxmax()]
    edge = best["price_early"] * best["p_fair_early"] - 1.0
    return best[edge >= threshold]


# --------------------------------------------------------------------------
# Medición
# --------------------------------------------------------------------------

def _weekly_ci(values: np.ndarray, weeks: np.ndarray,
               iterations: int = 1000) -> list[float] | None:
    """
    IC95 de la media remuestreando SEMANAS enteras. Las apuestas de una misma
    jornada comparten noticias y movimientos de mercado: tratarlas como
    independientes estrecharía el intervalo sin motivo.
    """
    groups = list(pd.Series(values).groupby(weeks).indices.values())
    if len(groups) < MIN_WEEKS:
        return None
    rng = np.random.default_rng(42)
    est = []
    for _ in range(iterations):
        draw = rng.integers(0, len(groups), size=len(groups))
        idx = np.concatenate([groups[i] for i in draw])
        est.append(float(values[idx].mean()))
    lo, hi = np.percentile(est, [2.5, 97.5])
    return [round(float(lo), 3), round(float(hi), 3)]


def evaluate(bets: pd.DataFrame) -> dict:
    """
    Todas las cifras en %, por apuesta de 1 unidad. El ROI solo sobre las
    apuestas con resultado conocido (`won` puede venir vacío: las cuotas
    históricas de The Odds API no traen resultado).
    """
    n = len(bets)
    if n == 0:
        return {"n": 0}
    price = bets["price_early"].to_numpy(float)
    edge = (price * bets["p_fair_early"].to_numpy(float) - 1.0) * 100
    ev = (price * bets["p_fair_close"].to_numpy(float) - 1.0) * 100
    clv = (price / bets["sharp_close_price"].to_numpy(float) - 1.0) * 100
    weeks = bets["week"].to_numpy()
    known = bets["won"].notna().to_numpy()
    won = bets["won"].where(bets["won"].notna(), False).astype(bool).to_numpy()
    roi = np.where(won, price - 1.0, -1.0)[known] * 100
    by_league = {
        str(lg): {"n": int(len(g)), "ev_close": round(float(ev[g.index].mean()), 3)}
        for lg, g in bets.reset_index(drop=True).groupby("league_id")
    }
    edge_m = float(edge.mean())
    return {
        "n": int(n),
        "edge_early": round(edge_m, 3),
        "ev_close": round(float(ev.mean()), 3),
        "ev_close_ci95": _weekly_ci(ev, weeks),
        # Qué fracción del edge visto antes del cierre sigue siendo valor
        # cuando el mercado ya ha convergido. Es lo que un encogimiento
        # constante como EDGE_SHRINKAGE intenta adivinar, y varía por casa.
        "persistence": round(float(ev.mean()) / edge_m, 3) if edge_m > 0 else None,
        "clv_with_margin": round(float(clv.mean()), 3),
        "n_with_result": int(known.sum()),
        "roi": round(float(roi.mean()), 3) if roi.size else None,
        "roi_ci95": _weekly_ci(roi, weeks[known]) if roi.size else None,
        "n_leagues": len(by_league),
        "by_league": by_league,
    }


def control_no_criterion(df: pd.DataFrame) -> dict:
    """
    Apostar a Pinnacle temprano en TODAS las selecciones, sin criterio. Su
    valor esperado al cierre justo debe salir ≈ −margen: si no, la vara o los
    datos están mal y nada de lo demás es fiable.
    """
    df = _prepare(df)
    out = {}
    for market, spec in MARKETS.items():
        early = spec["cols"](spec["sharp"], False)
        close = spec["cols"](spec["sharp"], True)
        base = _with_sharp(df, early, close)
        if base.empty:
            continue
        pe = base[early].to_numpy(float)
        pc_fair = _devig_rows(base[close].to_numpy(float))
        ev = (pe * pc_fair - 1.0) * 100
        clv = (pe / base[close].to_numpy(float) - 1.0) * 100
        out[market] = {"n": int(ev.size), "ev_close": round(float(ev.mean()), 3),
                       "clv_with_margin": round(float(clv.mean()), 3)}
    return out


def run(leagues: dict[str, str] | None = None,
        seasons: tuple[str, ...] = DEFAULT_SEASONS,
        thresholds: tuple[float, ...] = THRESHOLDS,
        best_of_books: list[str] | None = None,
        cache_dir: Path = Path(".local/fd_cache"),
        refresh: bool = False) -> dict:
    leagues = leagues or main_format_leagues()
    raw, dataset = load_csvs(leagues, seasons, cache_dir, refresh)
    quotes = build_quotes(raw)
    dataset["matches_with_sharp"] = int(quotes["match"].nunique()) if len(quotes) else 0
    mk = quotes.drop_duplicates(["match", "market"])
    dataset["markets_excluded_by_sharp_guard"] = {
        m: int((~(g["sharp_dev_early"] <= MAX_SHARP_DEVIATION)).sum())
        for m, g in mk.groupby("market")}

    real_books = sorted(set(quotes["book"]) - set(AGGREGATES))
    best_of_books = best_of_books or real_books

    per_book = []
    for (market, book), _ in quotes.groupby(["market", "book"]):
        for t in thresholds:
            res = evaluate(select_by_book(quotes[quotes["market"] == market], book, t))
            per_book.append({"market": market, "book": book, "threshold": t, **res})

    best_of = []
    for market in sorted(quotes["market"].unique()):
        for t in thresholds:
            res = evaluate(select_best_of(quotes[quotes["market"] == market],
                                          best_of_books, t))
            best_of.append({"market": market, "books": best_of_books,
                            "threshold": t, **res})

    return {"dataset": dataset,
            "control_pinnacle_sin_criterio": control_no_criterion(raw),
            "per_book": per_book,
            "best_of_real_books": best_of}


def _print(report: dict) -> None:
    d = report["dataset"]
    print(f"dataset {d['sha256'][:16]}  ficheros={d['files']}  "
          f"partidos con Pinnacle={d['matches_with_sharp']}")
    print("control (Pinnacle temprano en todo):", report["control_pinnacle_sin_criterio"])
    cols = ["market", "book", "threshold", "n", "edge_early", "ev_close",
            "ev_close_ci95", "persistence", "clv_with_margin", "roi", "roi_ci95"]
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 20)
    print(pd.DataFrame(report["per_book"])[cols].to_string(index=False))
    print("\nmejor cuota entre casas reales:")
    print(pd.DataFrame(report["best_of_real_books"])
          [[c for c in cols if c != "book"]].to_string(index=False))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--seasons", nargs="+", default=list(DEFAULT_SEASONS))
    ap.add_argument("--books", nargs="+", default=None,
                    help="casas para la estrategia 'mejor cuota' (por defecto, todas las reales)")
    ap.add_argument("--cache", default=".local/fd_cache")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--out", default=None, help="guardar el informe completo en JSON")
    a = ap.parse_args()
    rep = run(seasons=tuple(a.seasons), best_of_books=a.books,
              cache_dir=Path(a.cache), refresh=a.refresh)
    _print(rep)
    if a.out:
        Path(a.out).write_text(json.dumps(rep, indent=2, ensure_ascii=False),
                               encoding="utf-8")
