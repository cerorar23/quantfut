"""Cuota de referencia de tenis: la observación PropLine usada al sellar, fuera del sello.

Por cada pronóstico sellado (`tennis-intake-sealed-v1`) se relee SOLO el recibo que nombra
`forecast.market_board` (`snapshot_id` = sha256, `received_at`) y, por mercado público, se elige la
mejor casa no DFS con `best_quote` en la misma línea y el mismo lado que muestra el feed. Sin recibo,
sin board, sin línea o sin casas: None (nunca se inventa ni se usa la línea más cercana).
Sin red: solo lee objetos ya archivados. Las claves son los `id` de `tenis_publico.projection`.
"""
from __future__ import annotations

import math
import unicodedata
from collections import OrderedDict
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

from qf.api.tenis_publico import _checksum, _prob
from qf.ingest import propline_shared as pl
from qf.ingest.cuotas_referencia import best_quote

PATH = "/v1/sports/tennis/odds"
SOURCE = "PropLine"
MAX_RECEIPTS = 256
# Contrato del motor -> claves PropLine (apps/tennis/tennis_odds_propline_v1/__init__.py, FAMILIES).
MARKETS = {"winner": ("h2h",), "games_total": ("totals", "total_games"), "games_handicap": ("spreads",),
           "sets_total": ("total_sets",), "sets_handicap": ("set_spread",), "set_winner": ("h2h",),
           "tiebreak": ("total_tiebreaks",)}
_KEYS = {k for v in MARKETS.values() for k in v}
# Mercados con jugador como lado (se etiquetan A/B por nombre, como consensus()).
_POR_JUGADOR = {"winner", "games_handicap", "sets_handicap", "set_winner"}
_SELECCIONES = {"A", "B", "over", "under", "yes", "no"}  # las que tenis_publico publica
_CAMPOS = ("bookmaker", "market", "period", "name", "side", "point", "price_decimal", "flags",
           "dfs_odds_type", "payout_multiplier")

_cache: OrderedDict = OrderedDict()


def clear_cache():
    _cache.clear()


# norm/same_player/side_of: copia exacta de tennis_odds_live_v1.norm y tennis_odds_propline_v1 (la API no lleva apps/).
def _norm(name):
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", str(name)) if not unicodedata.combining(c))
                    .casefold().replace("-", " ").split())


def _same_player(x, y):
    x, y = _norm(x or "").split(), _norm(y or "").split()
    if x == y:
        return bool(x)
    short, long = sorted((x, y), key=len)
    if len(short) < 2 or len(short) == len(long) or short[0] != long[0] or short[-1] != long[-1]:
        return False
    middle = iter(long[1:-1])
    return all(token in middle for token in short[1:-1])


def _side_of(name, a, b):
    sides = [s for s, p in (("A", a), ("B", b)) if _same_player(name, p)]
    return sides[0] if len(sides) == 1 else None


def _filas(archive: Path, snapshot_id: str, received_at: str, event_id: str):
    """Filas de partido completo del evento en el recibo sellado; None si no se puede leer tal cual."""
    key = (snapshot_id, received_at)
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key].get(event_id)
    try:
        # Con as_of = received_at sellado, newest() elige el mismo recibo y los mismos lotes de la hora que al sellar.
        events, receipt = pl.newest(archive, PATH, pl.parse_time(received_at), max_age_seconds=0)
        if receipt is None or receipt["sha256"] != snapshot_id or receipt["received_at"] != received_at:
            return None
        por_evento = {}
        for e in events:
            por_evento[str(e["id"])] = dict(event=dict(home=e.get("home_team"), away=e.get("away_team")), rows=[
                {k: q[k] for k in _CAMPOS} for q in pl.quotes([e], received_at)
                if q["market"] in _KEYS and q["team"] is None and q["player_id"] is None
                and q["line_type"] in (None, "main")])
    except Exception:  # recibo ausente, truncado o con hash distinto: sin precio, nunca error
        return None
    _cache[key] = por_evento
    while len(_cache) > MAX_RECEIPTS:
        _cache.popitem(last=False)
    return por_evento.get(event_id)


def _cuota(filas, players, kind, selection, line, set_number, sealed_at, received_at):
    period = f"s{set_number}" if kind == "set_winner" else None
    if kind == "set_winner" and not (isinstance(set_number, int) and 1 <= set_number <= 9):
        return None
    elegidas = []
    for f in filas:
        if f["market"] not in MARKETS[kind] or f["period"] != period:
            continue
        f = dict(f, period=None)  # el periodo ya se filtró arriba; best_quote solo admite partido completo
        if kind in _POR_JUGADOR:
            f["side"] = _side_of(f["name"], *players)
            if f["side"] is None:
                continue
        elegidas.append(f)
    side = selection
    if kind == "tiebreak":  # sí = al menos un tie-break = más de 0,5
        side, line = {"yes": "over", "no": "under"}.get(selection), 0.5
    if side is None:
        return None
    q = best_quote(elegidas, line=line, side=side, sealed_at=sealed_at, received_at=pl.parse_time(received_at))
    return None if q is None else dict(price=q.price, book=q.book, as_of=q.as_of, books=q.books, side=selection)


def _contratos(forecast: Mapping):
    """(id público, contrato) con el mismo filtro e índice que tenis_publico.projection."""
    p = (forecast.get("winner") or {}).get("final_winner")
    if _prob(p):
        yield "winner", dict(kind="winner", selection="A" if p >= .5 else "B", line=None, set_number=None)
    markets = forecast.get("markets") or []
    for index, market in enumerate(markets if isinstance(markets, list) else []):
        if not isinstance(market, Mapping):
            continue
        contract, probabilities = market.get("contract") or {}, market.get("probabilities") or {}
        if (isinstance(contract, Mapping) and isinstance(probabilities, Mapping) and contract.get("kind") in MARKETS
                and contract.get("kind") != "winner" and _prob(probabilities.get("win"))
                and contract.get("selection") in _SELECCIONES):
            yield f"{contract['kind']}-{index}", contract


def _linea(value):
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def tennis_quotes(forecast: Mapping, sealed_at: datetime, archive) -> dict[str, dict | None]:
    """{id público: cuota o None}; None también cuando no hay board/recibo legible (ver `tennis_overlay`)."""
    return _quotes(forecast, sealed_at, archive)[0]


def _quotes(forecast, sealed_at, archive):
    try:
        contratos = list(_contratos(forecast)) if isinstance(forecast, Mapping) else []
    except Exception:
        contratos = []
    out = {mid: None for mid, _ in contratos}
    try:
        players = forecast["players"]
        board = forecast["market_board"]
        if len(players) != 2 or not isinstance(board, Mapping):
            return out, False
        snapshot_id, received_at, event_id = board["snapshot_id"], board["received_at"], str(board["event_id"])
        if not (isinstance(snapshot_id, str) and isinstance(received_at, str)):
            return out, False
        evento = _filas(Path(archive), snapshot_id, received_at, event_id)
        # El evento sellado tiene que ser exactamente este par (provider_pair); si no, sin precio.
        if evento is None or {_side_of(evento["event"]["home"], *players),
                              _side_of(evento["event"]["away"], *players)} != {"A", "B"}:
            return out, False
        for mid, c in contratos:
            out[mid] = _cuota(evento["rows"], players, c["kind"], c["selection"], _linea(c.get("line")),
                              c.get("set_number"), sealed_at, received_at)
        return out, True
    except Exception:
        return {mid: None for mid, _ in contratos}, False


def tennis_overlay(archive, feed: Mapping, *, sealed: Mapping | None = None, now: datetime | None = None) -> dict:
    """Overlay del feed público de tenis. `sealed`: {event_id: documento sellado}; solo se usa si su hash es el
    `seal` del evento. `partial` si algún evento quedó sin sello, board o recibo legible."""
    now = now or datetime.now(timezone.utc)
    base = dict(generated_at=now.isoformat(), source=SOURCE)
    archive = Path(archive)
    if not (archive / "index.sqlite").is_file():
        return dict(base, state="unavailable", events={})
    eventos, completo = {}, True
    events = feed.get("events") if isinstance(feed, Mapping) else None
    if not isinstance(events, list):
        return dict(base, state="partial", events={})
    for event in events:
        try:
            ids = [m["id"] for m in event["markets"]]
            eid = str(event["id"])
        except Exception:
            completo = False
            continue
        quotes, ok = {}, False
        try:
            doc = (sealed or {}).get(eid)
            if isinstance(doc, Mapping) and doc.get("payload_sha256") == event.get("seal") \
                    and _checksum({k: v for k, v in doc.items() if k != "payload_sha256"}) == event.get("seal"):
                quotes, ok = _quotes(doc["forecast"], pl.parse_time(doc["sealed_at"]), archive)
        except Exception:
            quotes, ok = {}, False
        completo &= ok
        eventos[eid] = {mid: quotes.get(mid) if ok else None for mid in ids}
    return dict(base, state="ok" if completo else "partial", events=eventos)
