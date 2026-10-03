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
   ≥ SOFT_MIN_EDGE_PCT. Solo 1X2.
4. Stake: Kelly sobre el edge ESPERADO AL CIERRE = edge bruto × persistencia
   medida de esa casa, no sobre el bruto, y encogido por la incertidumbre de
   esa persistencia (Baker y McHale, 2013; desde 2026-10-03).

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
# Recalibración con la sombra (regla fijada el 2026-09-28, ANTES de tener
# muestra, para no ajustarla a lo que salga): media ponderada entre la previa
# de arriba y la medida en la sombra, con la previa valiendo como
# PRIOR_WEIGHT partidos. Medida = EV al cierre / edge bruto de la PRIMERA
# oferta de cada casa en cada partido (las siguientes del mismo partido no
# son independientes), acotada a [0, 1]. Con pocos partidos casi no se mueve.
PRIOR_WEIGHT = 100

# Incertidumbre de la persistencia (Baker y McHale, 2013): con la ventaja
# estimada y no conocida, el stake óptimo es Kelly × ρ²/(ρ² + SE²). Error
# típico de la previa por bootstrap de semanas en football-data 2019-2025 a
# umbral 2 % (medido el 2026-10-03): Bet365 0,13 ± 0,15 no se distingue de
# cero. Casas sin medir: la dispersión de la persistencia entre casas (0,31).
# El de 1xBet es el de football-data (0,72 ± 0,17), no el de su previa LatAm.
PERSISTENCE_SE = {"1xbet": 0.17, "bet365": 0.15, "william_hill": 0.25}
UNMEASURED_PERSISTENCE_SE = 0.31
# Stake mínimo publicable, en unidades (1 u = 1% de banca).
MIN_STAKE_UNITS = 0.05

# Antelación mínima, tanto del PRECIO como de la DECISIÓN, respecto al inicio.
# Un snapshot de la ventana de cierre (3-12 min) es el mismo contra el que se
# liquida: su oferta tendría EV = edge bruto por construcción. Y una decisión
# a T-5 no se puede apostar a tiempo, aunque el precio fuera de T-55. La usan
# la publicación y la sombra (que certifica "lo que se habría publicado"):
# una sola constante para que no puedan divergir.
MIN_LEAD = timedelta(minutes=15)


def mezclar(previa: float, n: int, ev_medio: float | None,
            edge_medio: float | None, peso: int = PRIOR_WEIGHT) -> float:
    """Persistencia recalibrada. Sin partidos medidos, la previa tal cual."""
    if not n or ev_medio is None or not edge_medio or edge_medio <= 0:
        return previa
    medida = min(max(ev_medio / edge_medio, 0.0), 1.0)
    return (n * medida + peso * previa) / (n + peso)


def mezclar_se(se_previa: float, n: int, sd_ev: float | None,
               edge_medio: float | None, peso: int = PRIOR_WEIGHT) -> float:
    """
    Error típico de `mezclar`, con sus mismos pesos. El de la sombra sale del
    método delta, sd(ev) / (√n · media(edge)): coincide con el bootstrap por
    semanas en football-data (Bet365 0,140 frente a 0,146).
    """
    if not n or sd_ev is None or not edge_medio or edge_medio <= 0:
        return se_previa
    se_medida = sd_ev / (math.sqrt(n) * edge_medio)
    return math.sqrt((n * se_medida) ** 2 + (peso * se_previa) ** 2) / (n + peso)


def factor_incertidumbre(persistencia: float, se: float) -> float:
    """Baker y McHale: fracción de Kelly que conviene con ρ estimada, no conocida."""
    if persistencia <= 0:
        return 0.0
    return persistencia ** 2 / (persistencia ** 2 + se ** 2)


def _medido_en_sombra() -> list[dict]:
    return query(
        """WITH primera AS (
               SELECT DISTINCT ON (o.match_id, o.book)
                      o.book, o.raw_edge_pct, r.ev_close_pct
               FROM sharp_shadow_offers o
               JOIN sharp_shadow_results r USING (offer_id)
               WHERE r.ev_close_pct IS NOT NULL
               ORDER BY o.match_id, o.book, o.decided_at, o.offer_id)
           SELECT book, count(*) AS n, avg(ev_close_pct) AS ev,
                  stddev_samp(ev_close_pct) AS sd_ev, avg(raw_edge_pct) AS edge
           FROM primera GROUP BY book"""
    )


def _num(x) -> float | None:
    return None if x is None else float(x)


def persistencias() -> dict[str, float]:
    """Persistencia vigente por casa: previa + lo medido en la sombra."""
    out = dict(PERSISTENCE)
    for r in _medido_en_sombra():
        previa = PERSISTENCE.get(r["book"], UNMEASURED_PERSISTENCE)
        out[r["book"]] = round(mezclar(previa, int(r["n"]), _num(r["ev"]),
                                       _num(r["edge"])), 4)
    return out


def factores() -> dict[str, float]:
    """Factor de incertidumbre vigente por casa; las no listadas, `factor_sin_medir()`."""
    rho = persistencias()
    se = dict(PERSISTENCE_SE)
    for r in _medido_en_sombra():
        previa = PERSISTENCE_SE.get(r["book"], UNMEASURED_PERSISTENCE_SE)
        se[r["book"]] = mezclar_se(previa, int(r["n"]), _num(r["sd_ev"]), _num(r["edge"]))
    return {b: round(factor_incertidumbre(rho[b], se.get(b, UNMEASURED_PERSISTENCE_SE)), 4)
            for b in rho}


def factor_sin_medir() -> float:
    return factor_incertidumbre(UNMEASURED_PERSISTENCE, UNMEASURED_PERSISTENCE_SE)


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
    # None en ligas "solo sharp" (db/023, db/025): no se predicen, y el
    # criterio de precio no necesita la predicción para elegir.
    prediction_id: str | None
    market: str
    selection: str
    line: float | None
    model_prob: float | None     # diagnóstico: NO decide nada. None sin modelo
    best_price: float
    best_book: str
    market_prob: float           # probabilidad justa de Pinnacle
    raw_edge: float              # % contra el precio justo, en el snapshot
    shrunk_edge: float           # % esperado al cierre = raw × persistencia
    stake_units: float           # el que se publica: Kelly × factor de incertidumbre
    kickoff_utc: object
    label: str
    league_id: str | None = None
    shrink_source: str = "persistence"
    shrink_factor: float = 0.0
    min_price: float | None = None
    odds_source: str | None = None
    odds_as_of: datetime | None = None
    # Kelly SIN el factor de incertidumbre. Decide si el candidato es
    # publicable, como antes del 2026-10-03: el factor cambia cuánto se
    # apuesta, no qué entra en la muestra de la puerta (decisión del usuario).
    stake_kelly_units: float = 0.0
    uncertainty_factor: float = 1.0


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
    books: dict[str, dict[str, float]] = field(default_factory=dict)


def _group(rows: list[dict], source: str, as_of_key: str) -> Snapshot | None:
    if not rows:
        return None
    books: dict[str, dict[str, float]] = {}
    for r in rows:
        books.setdefault(canonical_book(r["bookmaker"]), {})[r["selection"]] = float(r["price"])
    return Snapshot(source, rows[0][as_of_key], books)


def _af_snapshot(match_id: str, now: datetime) -> Snapshot | None:
    """Última respuesta de API-Football que ya TENÍAMOS en `now`."""
    rows = query(
        """SELECT bookmaker, selection, price, provider_updated_at
           FROM af_odds_snapshots
           WHERE match_id = %s AND market = 'h2h' AND fetched_at <= %s
             AND provider_updated_at = (
                 SELECT max(provider_updated_at) FROM af_odds_snapshots
                 WHERE match_id = %s AND market = 'h2h' AND fetched_at <= %s)""",
        (match_id, now, match_id, now),
    )
    return _group(rows, "api_football", "provider_updated_at")


def _odds_api_snapshot(match_id: str, now: datetime) -> Snapshot | None:
    """Última captura de The Odds API anterior a `now` (todas las casas a la vez)."""
    rows = query(
        """SELECT bookmaker, selection, price, captured_at
           FROM odds_snapshots
           WHERE match_id = %s AND market = 'h2h' AND source = 'the_odds_api'
             AND captured_at <= %s
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

    @property
    def expected_edge(self) -> float:
        return self.raw_edge * self.persistence

    @property
    def min_price(self) -> float:
        return (1.0 + settings.soft_min_edge_pct / 100.0) / self.fair_prob


def offers(snap: Snapshot, now: datetime,
           books: tuple[str, ...] | None = None,
           persistencia: dict[str, float] | None = None) -> list[Offer]:
    """
    El criterio entero, sin base de datos. Devuelve [] (no hay nada que
    apostar) si el snapshot es viejo, si falta Pinnacle o si Pinnacle no cuadra
    con el consenso de las demás casas.
    """
    books = settings.soft_books if books is None else books
    persistencia = PERSISTENCE if persistencia is None else persistencia
    if now - snap.as_of > timedelta(hours=settings.soft_quote_max_age_hours):
        return []
    full = {b: q for b, q in snap.books.items()
            if set(q) == set(SEL) and min(q.values()) > 1.0}
    sharp = full.get(settings.sharp_book)
    if not sharp:
        return []
    fair = devig([sharp[s] for s in SEL], settings.devig_method)
    others = {b: q for b, q in full.items()
              if b != settings.sharp_book and b not in EXCHANGES}
    if len(others) < MIN_CONSENSUS_BOOKS:
        return []
    consensus = np.mean([devig([q[s] for s in SEL], settings.devig_method)
                         for q in others.values()], axis=0)
    if float(np.abs(consensus - fair).max()) > MAX_SHARP_DEVIATION:
        return []

    out = []
    for book, q in others.items():
        if book not in books:
            continue
        for j, s in enumerate(SEL):
            edge = (q[s] * float(fair[j]) - 1.0) * 100.0
            if edge >= settings.soft_min_edge_pct:
                out.append(Offer(book, s, q[s], float(fair[j]), edge,
                                 persistencia.get(book, UNMEASURED_PERSISTENCE),
                                 snap.source, snap.as_of))
    return out


def find_candidates(prediction: dict, now: datetime | None = None) -> list[Candidate]:
    """
    Candidatos de un partido desde las dos fuentes, ordenados por edge esperado
    al cierre. Incluye los de stake 0 (casas con persistencia medida nula): la
    sombra los necesita para medir; `select_daily` los descarta al publicar.
    """
    now = now or datetime.now(timezone.utc)
    match_id = prediction["match_id"]
    kickoff = prediction.get("kickoff_utc")
    if kickoff is not None and kickoff - now < MIN_LEAD:
        return []
    model_1x2 = (prediction.get("markets") or {}).get("1x2") or {}
    pid = prediction.get("prediction_id")
    out = []
    vigente = persistencias()
    k_vigente = factores()
    for snap in (_af_snapshot(match_id, now), _odds_api_snapshot(match_id, now)):
        if snap is None:
            continue
        if kickoff is not None and kickoff - snap.as_of < MIN_LEAD:
            continue
        for o in offers(snap, now, persistencia=vigente):
            p_exp = (1.0 + o.expected_edge / 100.0) / o.price
            stake = kelly(p_exp, o.price, settings.kelly_fraction, settings.max_stake_units)
            k = k_vigente.get(o.book, factor_sin_medir())
            out.append(Candidate(
                match_id=match_id,
                prediction_id=None if pid is None else str(pid),
                market="h2h", selection=o.selection, line=None,
                # Vacío, no 0: un 0 se leería como "el modelo da 0%".
                model_prob=(float(model_1x2[o.selection])
                            if o.selection in model_1x2 else None),
                best_price=o.price, best_book=o.book, market_prob=o.fair_prob,
                raw_edge=o.raw_edge, shrunk_edge=o.expected_edge,
                stake_units=round(stake * k, 2),
                stake_kelly_units=round(stake, 2), uncertainty_factor=k,
                kickoff_utc=prediction.get("kickoff_utc"),
                label=f"h2h {o.selection}",
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
            if c.stake_kelly_units <= MIN_STAKE_UNITS:
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
