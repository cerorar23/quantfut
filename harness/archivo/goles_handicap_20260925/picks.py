"""
Selección de picks: casas blandas que pagan más que el precio justo de
Pinnacle en ese momento.

POR QUÉ NO DECIDE EL MODELO (2026-09-23)
----------------------------------------
El criterio anterior ordenaba por el edge del modelo contra la cuota, y ese
edge correlaciona −0,123 con el acierto sobre 4.880 candidatos: cuanto más
discrepaba el modelo del mercado, peor. Seleccionar por distancia al precio
sharp sí tiene valor medido contra el cierre sin margen, la vara de la puerta
comercial: +2,09% en 7 ligas europeas (eval/soft_vs_sharp.py) y +3,83% con las
casas accesibles en Liga MX, Brasil, Argentina y MLS (ingest/odds_history.py).
El modelo queda como dato de diagnóstico (`model_prob`).

EL CRITERIO
-----------
1. Un SNAPSHOT: todas las cuotas de una misma respuesta del proveedor, así la
   casa blanda y Pinnacle tienen la misma antigüedad. Nunca se cruza una casa
   de una fuente con el Pinnacle de otra.
2. Precio justo = Pinnacle sin margen. Si Pinnacle se aparta más de
   MAX_SHARP_DEVIATION del consenso de las demás casas del snapshot, el
   partido no entra: en el histórico eso era un precio de Pinnacle roto.
3. Candidata: casa de la lista blanca de los suscriptores con edge bruto
   ≥ SOFT_MIN_EDGE_PCT. En 1X2, goles (totals) y hándicap asiático
   (spreads); en los dos últimos, solo en la LÍNEA PRINCIPAL de Pinnacle del
   snapshot (la más equilibrada), porque The Odds API solo da el cierre de
   Pinnacle en esa línea y una oferta sin cierre no se puede validar. La guarda
   de consenso se aplica en esa misma línea.
4. Stake: Kelly sobre el edge ESPERADO AL CIERRE = edge bruto × persistencia
   medida de esa casa, no sobre el bruto.

Y las protecciones de siempre: Kelly fraccional con tope, un pick por partido
y riesgo de portafolio con correlación.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import numpy as np

from ..config import settings
from ..db import query
from ..eval.soft_vs_sharp import MAX_SHARP_DEVIATION
from ..model.devig import devig

log = logging.getLogger(__name__)

SEL = ("home", "draw", "away")
# Mercados de dos vías con línea. En `Snapshot.lines` el hándicap se agrupa por
# la línea del LOCAL; la oferta lleva la línea propia del lado elegido.
TWO_WAY = {"totals": ("over", "under"), "spreads": ("home", "away")}

# Nombres de casa unificados entre proveedores.
BOOK_ALIASES = {"onexbet": "1xbet", "williamhill": "william_hill",
                "sport888": "888sport", "bet_365": "bet365"}
# Cobran comisión sobre la ganancia: ni referencia de consenso ni casa blanda.
# El "Betfair" de API-Football no dice si es exchange o sportsbook: fuera.
EXCHANGES = {"betfair", "betfair_ex_eu", "betfair_ex_uk", "betfair_ex_au",
             "matchbook", "smarkets"}
# Casas además de Pinnacle necesarias para verificar la referencia.
MIN_CONSENSUS_BOOKS = 2

# Qué fracción del edge visto antes del cierre sigue siendo valor AL cierre,
# medida por casa a umbral 2% (edge al cierre / edge temprano, con 0 como
# suelo). Es lo que antes intentaba adivinar EDGE_SHRINKAGE=0,55 para todas.
#   1xbet         0,72  The Odds API 2025, 4 ligas LatAm/MLS, n=126
#                       (football-data 2024/25, 7 ligas: 0,68)
#   bet365        0,13  football-data 2019-2025, 7 ligas, n=415
#   william_hill  0,00  football-data 2019-2025: −0,05, n=197
# Sin medir (Betano, 888sport, Betway): el conjunto de casas reales de
# football-data, 0,42. Es una media de población, no un dato de esa casa: se
# sustituye en cuanto la sombra (paso 5) tenga muestra propia.
PERSISTENCE = {"1xbet": 0.72, "bet365": 0.13, "william_hill": 0.0}
UNMEASURED_PERSISTENCE = 0.42
# Stake mínimo publicable, en unidades (1 u = 1% de banca).
MIN_STAKE_UNITS = 0.05


def canonical_book(key: str) -> str:
    k = key.strip().lower()
    return BOOK_ALIASES.get(k, k)


# Correlación asumida entre picks. Ver `correlation()` para el razonamiento.
# Son cotas superiores conservadoras, no estimaciones de datos: con pocos
# cientos de picks liquidados cualquier estimación empírica sería ruido, y
# equivocarse por exceso de prudencia aquí solo cuesta tamaño de apuesta.
CORR_BASE = 0.05             # riesgo de modelo común a TODOS los picks
CORR_SAME_LEAGUE = 0.08      # comparten fuerza, nivel de goles y ventaja local
CORR_SAME_MARKET_SIDE = 0.12  # mismo mercado y misma dirección
CORR_CAP = 0.30


@dataclass
class Candidate:
    match_id: str
    prediction_id: str
    market: str
    selection: str
    line: float | None
    model_prob: float            # diagnóstico: NO decide nada
    best_price: float
    best_book: str
    market_prob: float           # probabilidad justa de Pinnacle
    raw_edge: float              # % contra el precio justo, en el snapshot
    shrunk_edge: float           # % esperado al cierre = raw × persistencia
    stake_units: float
    kickoff_utc: object
    label: str
    league_id: str | None = None
    shrink_source: str = "persistence"
    shrink_factor: float = 0.0
    min_price: float | None = None
    odds_source: str | None = None
    odds_as_of: datetime | None = None


def kelly(prob: float, price: float, fraction: float, cap: float) -> float:
    """
    Kelly fraccional sobre cuota decimal. b = price - 1.

    UNIDADES: devuelve UNIDADES, donde 1 unidad = 1% de la banca. Kelly da una
    fracción de banca (0.0067 = 0.67%), así que se multiplica por 100.

    No es cosmética. Sin esa conversión, `stake_units` queda en fracción de
    banca mientras el resto del sistema la interpreta en unidades: el tope de
    `MAX_STAKE_UNITS=2.0` significaría 200% de la banca por apuesta, la
    exposición diaria de 10.0 sería 1000%, y el descarte de stakes mínimos
    eliminaría TODOS los picks con edge realista (3-10%), porque en fracción de
    banca esos stakes valen 0.004-0.02. El sistema publicaría cero picks para
    siempre, sin dar ningún error. Ver tests/test_kelly_units.py.
    """
    b = price - 1.0
    if b <= 0:
        return 0.0
    f = (prob * b - (1.0 - prob)) / b
    return float(np.clip(f * fraction * 100.0, 0.0, cap))


# --------------------------------------------------------------------------
# Snapshots: todas las cuotas de UNA respuesta del proveedor
# --------------------------------------------------------------------------

@dataclass
class Snapshot:
    source: str
    as_of: datetime                      # cuándo existían esos precios
    books: dict[str, dict[str, float]] = field(default_factory=dict)   # 1X2
    # Goles y hándicap: {(mercado, línea): {casa: {selección: cuota}}}.
    lines: dict[tuple[str, float], dict[str, dict[str, float]]] = field(default_factory=dict)


def _group(rows: list[dict], source: str, as_of_key: str) -> Snapshot | None:
    if not rows:
        return None
    books: dict[str, dict[str, float]] = {}
    lines: dict[tuple[str, float], dict[str, dict[str, float]]] = {}
    for r in rows:
        book, market = canonical_book(r["bookmaker"]), r.get("market", "h2h")
        if market == "h2h":
            books.setdefault(book, {})[r["selection"]] = float(r["price"])
        elif market in TWO_WAY and r.get("line") is not None:
            ln = float(r["line"])
            # Las dos patas del hándicap, bajo la línea del local.
            key = -ln if market == "spreads" and r["selection"] == "away" else ln
            lines.setdefault((market, key + 0.0), {}) \
                 .setdefault(book, {})[r["selection"]] = float(r["price"])
    return Snapshot(source, rows[0][as_of_key], books, lines)


def _af_snapshot(match_id: str, now: datetime) -> Snapshot | None:
    """Última respuesta de API-Football que ya TENÍAMOS en `now`."""
    rows = query(
        """SELECT bookmaker, market, selection, line, price, provider_updated_at
           FROM af_odds_snapshots
           WHERE match_id = %s AND fetched_at <= %s
             AND provider_updated_at = (
                 SELECT max(provider_updated_at) FROM af_odds_snapshots
                 WHERE match_id = %s AND fetched_at <= %s)""",
        (match_id, now, match_id, now),
    )
    return _group(rows, "api_football", "provider_updated_at")


def _odds_api_snapshot(match_id: str, now: datetime) -> Snapshot | None:
    """Última captura de The Odds API anterior a `now` (todas las casas a la vez)."""
    rows = query(
        """SELECT bookmaker, market, selection, line, price, captured_at
           FROM odds_snapshots
           WHERE match_id = %s AND market IN ('h2h', 'totals', 'spreads')
             AND source = 'the_odds_api' AND captured_at <= %s
             AND captured_at = (
                 SELECT max(captured_at) FROM odds_snapshots
                 WHERE match_id = %s AND market = 'h2h'
                   AND source = 'the_odds_api' AND captured_at <= %s)""",
        (match_id, now, match_id, now),
    )
    return _group(rows, "the_odds_api", "captured_at")


@dataclass
class Offer:
    """Una cuota de casa blanda que supera el precio justo en su snapshot."""
    book: str
    selection: str
    price: float
    fair_prob: float
    raw_edge: float            # %
    persistence: float
    source: str
    as_of: datetime
    market: str = "h2h"
    line: float | None = None  # en hándicap, la línea propia del lado

    @property
    def expected_edge(self) -> float:
        return self.raw_edge * self.persistence

    @property
    def min_price(self) -> float:
        return (1.0 + settings.soft_min_edge_pct / 100.0) / self.fair_prob


def offers(snap: Snapshot, now: datetime,
           books: tuple[str, ...] | None = None) -> list[Offer]:
    """
    El criterio entero, sin base de datos. Devuelve [] (no hay nada que
    apostar) si el snapshot es viejo, si falta Pinnacle o si Pinnacle no cuadra
    con el consenso de las demás casas.
    """
    books = settings.soft_books if books is None else books
    if now - snap.as_of > timedelta(hours=settings.soft_quote_max_age_hours):
        return []
    out = _group_offers(snap, "h2h", None, SEL, snap.books, books)
    for market, sels in TWO_WAY.items():
        main = _main_line(snap, market, sels)
        if main is not None:
            out += _group_offers(snap, market, main, sels,
                                 snap.lines[(market, main)], books)
    return out


def _complete(by_book: dict[str, dict[str, float]], sels: tuple[str, ...]) -> dict:
    return {b: q for b, q in by_book.items()
            if set(q) == set(sels) and min(q.values()) > 1.0}


def _main_line(snap: Snapshot, market: str, sels: tuple[str, ...]) -> float | None:
    """
    La línea principal de Pinnacle en el snapshot: la de probabilidades justas
    más cercanas al 50/50. Es la única que The Odds API da al cierre, así que
    es la única en la que una oferta se puede validar después.
    """
    fair = {}
    for (mk, ln), by_book in snap.lines.items():
        q = _complete(by_book, sels).get(settings.sharp_book) if mk == market else None
        if q:
            fair[ln] = float(devig([q[s] for s in sels], settings.devig_method)[0])
    return min(fair, key=lambda ln: (abs(fair[ln] - 0.5), ln)) if fair else None


def _group_offers(snap: Snapshot, market: str, line: float | None,
                  sels: tuple[str, ...], by_book: dict[str, dict[str, float]],
                  books: tuple[str, ...]) -> list[Offer]:
    """
    El criterio sobre un grupo completo (el 1X2, o un par de una línea):
    Pinnacle sin margen como justo, guarda de consenso con las demás casas del
    MISMO grupo y umbral de edge para las casas de la lista.
    """
    full = _complete(by_book, sels)
    sharp = full.get(settings.sharp_book)
    if not sharp:
        return []
    fair = devig([sharp[s] for s in sels], settings.devig_method)
    others = {b: q for b, q in full.items()
              if b != settings.sharp_book and b not in EXCHANGES}
    if len(others) < MIN_CONSENSUS_BOOKS:
        return []
    consensus = np.mean([devig([q[s] for s in sels], settings.devig_method)
                         for q in others.values()], axis=0)
    if float(np.abs(consensus - fair).max()) > MAX_SHARP_DEVIATION:
        return []

    out = []
    for book, q in others.items():
        if book not in books:
            continue
        for j, s in enumerate(sels):
            edge = (q[s] * float(fair[j]) - 1.0) * 100.0
            if edge >= settings.soft_min_edge_pct:
                own = None if line is None else (-line if market == "spreads" and s == "away" else line) + 0.0
                out.append(Offer(book, s, q[s], float(fair[j]), edge,
                                 PERSISTENCE.get(book, UNMEASURED_PERSISTENCE),
                                 snap.source, snap.as_of, market, own))
    return out


def _model_prob(markets: dict, market: str, selection: str, line: float | None) -> float:
    """
    Probabilidad del modelo para la selección. SOLO diagnóstico: no decide
    nada. En goles y hándicap sale de los goles esperados del modelo, porque
    su paquete solo precia líneas redondas y la principal de Pinnacle suele
    ser de cuarto (2,25, 2,75). En líneas de cuarto es la probabilidad
    efectiva E[gana] / (1 − E[devuelta]), la misma de `market_asian_handicap`.
    """
    if market == "h2h":
        return float((markets.get("1x2") or {}).get(selection, 0.0))
    eg = markets.get("expected_goals") or {}
    if "home" not in eg or "away" not in eg or line is None:
        return 0.0
    from ..model.pricing import market_asian_handicap, score_matrix
    m = score_matrix(float(eg["home"]), float(eg["away"]))
    if market == "spreads":
        home_line = line if selection == "home" else -line
        return float(market_asian_handicap(m, home_line)[selection])
    n = m.shape[0]
    hg, ag = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    tot = hg + ag
    quarter = abs(line * 2 - round(line * 2)) > 1e-9
    legs = [line - 0.25, line + 0.25] if quarter else [line]
    win = np.mean([m[(tot > leg) if selection == "over" else (tot < leg)].sum() for leg in legs])
    push = np.mean([m[tot == leg].sum() for leg in legs])
    return float(win / (1.0 - push)) if push < 1.0 else 0.5


def find_candidates(prediction: dict, now: datetime | None = None) -> list[Candidate]:
    """
    Candidatos de un partido desde las dos fuentes, ordenados por edge esperado
    al cierre. Incluye los de stake 0 (casas con persistencia medida nula): la
    sombra los necesita para medir; `select_daily` los descarta al publicar.
    """
    now = now or datetime.now(timezone.utc)
    match_id = prediction["match_id"]
    markets = prediction.get("markets") or {}
    out = []
    for snap in (_af_snapshot(match_id, now), _odds_api_snapshot(match_id, now)):
        if snap is None:
            continue
        for o in offers(snap, now):
            p_exp = (1.0 + o.expected_edge / 100.0) / o.price
            line_txt = "" if o.line is None else f" {o.line:g}"
            out.append(Candidate(
                match_id=match_id,
                prediction_id=str(prediction["prediction_id"]),
                market=o.market, selection=o.selection, line=o.line,
                model_prob=_model_prob(markets, o.market, o.selection, o.line),
                best_price=o.price, best_book=o.book, market_prob=o.fair_prob,
                raw_edge=o.raw_edge, shrunk_edge=o.expected_edge,
                stake_units=round(kelly(p_exp, o.price, settings.kelly_fraction,
                                        settings.max_stake_units), 2),
                kickoff_utc=prediction.get("kickoff_utc"),
                label=f"{o.market} {o.selection}{line_txt}",
                league_id=prediction.get("league_id"),
                shrink_factor=o.persistence, min_price=round(o.min_price, 3),
                odds_source=o.source, odds_as_of=o.as_of,
            ))
    out.sort(key=lambda c: -c.shrunk_edge)
    return out


def _risk_prob(c: Candidate) -> float:
    """
    Probabilidad que se usa para MEDIR RIESGO, no para apostar.

    Deliberadamente es la del mercado, no la del modelo. Si el modelo está
    sobreconfiado —que es el caso por defecto y la razón de existir del
    shrinkage— usar su propia probabilidad para estimar la varianza del
    portafolio subestima justo el riesgo que quieres controlar. El mercado es
    el estimador menos sesgado que tienes a mano.
    """
    p = c.market_prob if c.market_prob and 0.0 < c.market_prob < 1.0 else 1.0 / c.best_price
    return float(np.clip(p, 1e-4, 1 - 1e-4))


def _bet_sigma(c: Candidate) -> float:
    """Desviación típica del retorno de 1 unidad apostada a cuota decimal."""
    p = _risk_prob(c)
    return float(c.best_price * math.sqrt(p * (1.0 - p)))


def correlation(a: Candidate, b: Candidate) -> float:
    """
    Correlación asumida entre dos picks de partidos distintos.

    No se estima de datos (no hay muestra suficiente y sería inestable); es una
    cota superior razonada y conservadora:

    - BASE: todas las apuestas salen del MISMO método: la misma referencia
      (Pinnacle) y a menudo la misma casa blanda (1xBet concentra casi todo el
      valor medido). Si esa referencia o esa casa fallan hoy, fallan en todos
      los picks a la vez; repartir entre ligas no lo diversifica.
    - MISMA LIGA: comparten noticias y horario de mercado; una alineación o
      una lesión que la casa blanda aún no ha recogido afecta a varios.
    - MISMO MERCADO Y MISMA DIRECCIÓN: 6 visitantes el mismo día es una sola
      apuesta a un sesgo de la casa blanda con los visitantes, repartida en 6.
    """
    rho = CORR_BASE
    if a.match_id == b.match_id:
        return 1.0                      # no debería ocurrir: 1 pick por partido
    if _league_of(a) and _league_of(a) == _league_of(b):
        rho += CORR_SAME_LEAGUE
    if a.market == b.market and a.selection == b.selection:
        rho += CORR_SAME_MARKET_SIDE
    return min(rho, CORR_CAP)


def _league_of(c: Candidate) -> str | None:
    return c.league_id


def portfolio_sigma(picks: list[Candidate]) -> float:
    """Desviación típica del retorno conjunto del lote, en unidades."""
    if not picks:
        return 0.0
    s = np.array([p.stake_units for p in picks], dtype=float)
    sig = np.array([_bet_sigma(p) for p in picks], dtype=float)
    n = len(picks)
    cov = np.empty((n, n), dtype=float)
    for i in range(n):
        for j in range(n):
            r = 1.0 if i == j else correlation(picks[i], picks[j])
            cov[i, j] = r * sig[i] * sig[j]
    var = float(s @ cov @ s)
    return math.sqrt(max(var, 0.0))


def apply_portfolio_limits(picks: list[Candidate]) -> list[Candidate]:
    """
    Escala los stakes para respetar DOS topes a la vez:

      1. Exposición bruta (suma de stakes). Evita el apalancamiento absurdo.
      2. Riesgo del portafolio (sigma conjunta CON correlación). Es el que de
         verdad protege: 12 picks de 0.8 u correlacionados arriesgan bastante
         más que 12 apuestas independientes de 0.8 u, y la suma bruta no
         distingue entre esos dos casos.

    Se aplica el más restrictivo de los dos. Escalar es preferible a recortar
    picks: mantiene la selección del modelo intacta y solo ajusta el tamaño.
    """
    if not picks:
        return picks

    gross = sum(p.stake_units for p in picks)
    scale = 1.0
    if gross > settings.max_daily_exposure:
        scale = settings.max_daily_exposure / gross

    sigma = portfolio_sigma(picks)
    if sigma > 0 and sigma * scale > settings.max_portfolio_risk:
        scale = min(scale, settings.max_portfolio_risk / sigma)

    if scale < 1.0:
        for p in picks:
            p.stake_units = round(p.stake_units * scale, 2)
        log.info("Stakes escalados x%.3f (bruto %.2f u, sigma %.2f u -> %.2f u)",
                 scale, gross, sigma, sigma * scale)

    return picks


def select_daily(predictions: list[dict], now: datetime | None = None) -> list[Candidate]:
    """
    Aplica descorrelación y topes diarios:
      - fuera los de stake por debajo de MIN_STAKE_UNITS (persistencia nula)
      - máximo 1 pick por partido (el de mayor edge esperado)
      - máximo N picks por día
      - escalado por exposición bruta y por riesgo correlacionado
    """
    now = now or datetime.now(timezone.utc)
    per_match: dict[str, Candidate] = {}
    for pred in predictions:
        for c in find_candidates(pred, now):
            if c.stake_units <= MIN_STAKE_UNITS:
                continue
            cur = per_match.get(c.match_id)
            if cur is None or c.shrunk_edge > cur.shrunk_edge:
                per_match[c.match_id] = c

    picks = sorted(per_match.values(), key=lambda c: -c.shrunk_edge)
    picks = picks[: settings.max_picks_per_day]
    return apply_portfolio_limits(picks)


def assign_tiers(picks: list[Candidate], free_count: int | None = None) -> list[tuple[Candidate, str]]:
    """
    Reparte el lote ya ordenado por edge: los de mayor edge son el escaparate
    gratuito, el resto es de pago. `picks` debe venir ordenado por
    `select_daily` (edge descendente); no se reordena aquí para no mezclar el
    criterio de selección con el de tier.
    """
    n_free = settings.free_picks_per_day if free_count is None else free_count
    return [(p, "free" if i < n_free else "paid") for i, p in enumerate(picks)]


def persist(tiered: list[tuple[Candidate, str]]) -> int:
    """
    `tiered`: lista de (Candidate, tier) como la devuelve `assign_tiers`. El
    tier se decide aquí, una sola vez, para que la API (/picks/free, /v1/picks)
    y cualquier otro canal de publicación lean siempre el mismo dato.
    """
    from ..db import executemany
    rows = [
        (p.prediction_id, p.match_id, p.market, p.selection, p.line,
         p.model_prob, p.best_price, p.best_book,
         round(p.shrunk_edge, 3), round(p.raw_edge, 3), p.stake_units, tier,
         p.market_prob, p.min_price, p.odds_source, p.odds_as_of)
        for p, tier in tiered
    ]
    return executemany(
        """INSERT INTO picks
             (prediction_id, match_id, market, selection, line, model_prob,
              advised_price, bookmaker, edge_pct, raw_edge_pct, stake_units, tier,
              fair_prob, min_price, odds_source, odds_as_of)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        rows,
    )
