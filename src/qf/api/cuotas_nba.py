"""Cuota de referencia de NBA: la observación PropLine usada al sellar cada cohorte, fuera del sello.

Cada cohorte v1.3 guarda en `bundle.json` la identidad del recibo horario con el que se sellaron sus líneas
(`prop_lines`: `sha256`, `received_at_utc`, `slot`, `component_requests`; apps/nba/src/nba/prop_lines.py:101-103).
Se relee SOLO ese recibo (`propline_shared.newest` con `as_of = received_at_utc`, que fusiona los mismos lotes de la
hora) y se comprueba que la identidad coincide. Por fila publicada se elige con `best_quote` la mejor casa no DFS en
la MISMA línea y el mismo lado; nunca la línea más cercana. Sin red: solo lee objetos ya archivados.

Unión de eventos como prop_lines.py:84-94: par de IDs oficiales `nba:<teamId>` (local, visitante) del partido sellado
y `commence_time` a ±3 h del `tipoff_utc` sellado; jugadores por `player_id == "nba:<personId>"`. Sin nombres.
Si dos eventos PropLine encajan con el mismo partido, no hay precio (ambiguo).

Mercados (los que muestra `frontend/sports-data.js` `nbaEvents`: todas las filas de la cohorte):
  winner -> h2h (línea principal, lados home/away); game_total -> totals sin equipo; team_points -> totals con
  `team` igual al nombre local/visitante del propio evento PropLine; player_* -> la misma clave
  (prop_lines.py:15-17). Con línea, vale cualquier `line_type` si la línea es EXACTAMENTE la publicada (el total
  publicado es un umbral `floor(media)+0,5` que solo existe en escaleras alternativas).

Clave de fila: `"{market}|{player_id}|{line}"`; `player_id` solo en player_* y team_points (id del equipo), vacío en
winner y game_total; `line` vacía en winner y, si es entera, sin decimales (como `String(n)` en JS).

Carpeta de cohortes (`settings.nba_cohorts_dir`, env `NBA_COHORTS_DIR`; la del productor `live13/cohorts`, montada en
solo lectura): `<raíz>/<cohorte>/bundle.json` + `bundle.seal.json` {sha256} y recálculos en
`<cohorte>/updates/<tag>/revision.json` + `revision.seal.json` (se ignoran `*.partial`; el último sustituye las filas,
como apps/nba/src/nba/multimarket_live_dashboard.py:148-152). Un recálculo reutiliza las líneas y el recibo del sello
original (revisions.py:159-168).
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import sys
import threading
import zlib
from collections import OrderedDict, defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path

from qf.ingest import propline_shared as pl
from qf.ingest.cuotas_referencia import _elegible, best_quote

PATH = "/v1/sports/basketball_nba/odds"
SOURCE = "PropLine"
# Recibos NBA pesados (hasta ~170 mil resultados por hora): se guardan compactados y pocos.
MAX_RECEIPTS = 24
MATCH_WINDOW = timedelta(hours=3)  # prop_lines.py:21
# apps/nba/src/nba/prop_lines.py:15-17
PLAYER_MARKETS = ("player_points", "player_rebounds", "player_assists", "player_points_rebounds",
                  "player_points_assists", "player_rebounds_assists", "player_points_rebounds_assists",
                  "player_threes", "player_steals", "player_blocks", "player_turnovers", "player_blocks_steals")
_KEYS = {"h2h", "totals", *PLAYER_MARKETS}

_cache: OrderedDict = OrderedDict()
# Solo fallos DEFINITIVOS (recibo inmutable): identidad distinta, gzip/JSON ilegible. Lo transitorio (índice sin el
# recibo todavía, SQLite bloqueado, E/S) no se guarda y se reintenta.
_ilegibles: OrderedDict = OrderedDict()
_lock = threading.Lock()
_DEFINITIVOS = (gzip.BadGzipFile, EOFError, zlib.error, ValueError, KeyError, TypeError, AttributeError)


def clear_cache():
    with _lock:
        _cache.clear()
        _ilegibles.clear()


def _guarda(cache, key, value):
    with _lock:
        cache[key] = value
        while len(cache) > MAX_RECEIPTS:
            cache.popitem(last=False)


def _nba_id(value):
    # prop_lines.py:40-43
    if not isinstance(value, str) or not value.startswith("nba:") or not value[4:].isdigit():
        return None
    return int(value[4:])


def _entero(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return int(value) if isinstance(value, str) and value.isdigit() else None


def _linea(value):
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _texto_linea(line):
    return str(int(line)) if line.is_integer() else repr(line)


def _indexa(events, received_at):
    """{event_id: evento} con filas elegibles compactadas por (mercado, equipo, jugador NBA)."""
    out = {}
    for e in events:
        try:  # un evento malformado solo se pierde a sí mismo
            rows = defaultdict(list)
            for q in pl.quotes([e], received_at):
                market = q["market"]
                if market not in _KEYS or not _elegible(q) or q["price_decimal"] is None:
                    continue
                if market in PLAYER_MARKETS:
                    pid = _nba_id(q["player_id"])
                    if pid is None:
                        continue
                    key = (market, None, pid)  # prop_lines.book_lines no filtra `team` en jugadores
                elif q["player_id"] is not None:
                    continue
                elif market == "h2h":
                    if q["team"] is not None or q["line_type"] not in (None, "main"):
                        continue
                    key = (market, None, None)
                else:
                    key = (market, q["team"], None)
                rows[key].append((sys.intern(q["bookmaker"]), q["name"], q["side"], q["point"], q["price_decimal"]))
            out[str(e["id"])] = dict(home_id=_nba_id(e.get("home_team_id")), away_id=_nba_id(e.get("away_team_id")),
                                     commence=pl.parse_time(e["commence_time"]), home=e.get("home_team"),
                                     away=e.get("away_team"), rows={k: tuple(v) for k, v in rows.items()})
        except Exception:
            continue
    return out


def _identidad(prop):
    if not isinstance(prop, Mapping) or prop.get("state") != "archivo_aplicado":
        return None
    sha, received, slot, parts = prop["sha256"], prop["received_at_utc"], prop["slot"], prop["component_requests"]
    if not (isinstance(sha, str) and isinstance(received, str) and isinstance(slot, str) and isinstance(parts, list)):
        return None
    pl.parse_time(received)  # sin zona: falla cerrado
    return sha, received, slot, tuple(parts)


def _recibo(archive: Path, identity):
    """Índice del recibo sellado; None si no se puede leer tal cual."""
    sha, received, slot, parts = identity
    key = (str(archive), sha, received, slot, parts)
    with _lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
        if key in _ilegibles:
            return None
    try:
        # Con as_of = received_at sellado, newest() elige el mismo recibo y los mismos lotes de la hora que al sellar.
        events, receipt = pl.newest(archive, PATH, pl.parse_time(received), max_age_seconds=0)
    except _DEFINITIVOS:  # BadGzipFile antes que OSError: es corrupción, no E/S pasajera
        _guarda(_ilegibles, key, True)
        return None
    except Exception:  # sqlite3.Error, OSError…: transitorio, no se cachea
        return None
    if receipt is None:  # la copia del archivo aún no tiene el recibo: transitorio
        return None
    if (receipt["sha256"], receipt["received_at"], receipt["slot"], tuple(receipt["component_receipts"])) != identity:
        _guarda(_ilegibles, key, True)
        return None
    index = _indexa(events, received)
    _guarda(_cache, key, index)
    return index


def _evento(index, game):
    home, away = _entero(game["home_nba_team_id"]), _entero(game["away_nba_team_id"])
    tipoff = pl.parse_time(game["tipoff_utc"])
    found = [e for e in index.values() if home is not None and (e["home_id"], e["away_id"]) == (home, away)
             and abs(e["commence"] - tipoff) <= MATCH_WINDOW]
    return found[0] if len(found) == 1 else None


def _clave(f):
    market = f["market"]
    if market == "winner":
        return "winner||"
    line = _linea(f["line"])
    if line is None:
        raise ValueError("línea inválida")
    if market == "game_total":
        return f"game_total||{_texto_linea(line)}"
    if market == "team_points" or market in PLAYER_MARKETS:
        pid = _entero(f["player_id"])
        if pid is None:
            raise ValueError("id inválido")
        return f"{market}|{pid}|{_texto_linea(line)}"
    raise ValueError("mercado no publicado")


def _vacio(market):
    return dict(home=None, away=None) if market == "winner" else dict(over=None, under=None)


def _lados(evento, f, game, received_at):
    market, sealed = f["market"], pl.parse_time(f["sealed_at_utc"])
    line, sides = _linea(f["line"]), ("over", "under")
    if market == "winner":
        key, line, sides = ("h2h", None, None), None, ("home", "away")
    elif market == "game_total":
        key = ("totals", None, None)
    elif market == "team_points":
        team = _entero(f["team_id"])
        name = evento["home"] if team == _entero(game["home_nba_team_id"]) else \
            evento["away"] if team == _entero(game["away_nba_team_id"]) else None
        if team is None or not isinstance(name, str) or not name:
            return _vacio(market)
        key = ("totals", name, None)
    else:
        key = (market, None, _entero(f["player_id"]))
    filas = [dict(bookmaker=b, name=n, side=s, point=p, price_decimal=x) for b, n, s, p, x in evento["rows"].get(key, ())]
    out = {}
    for side in sides:
        q = best_quote(filas, line=line, side=side, sealed_at=sealed, received_at=received_at)
        out[side] = None if q is None else dict(price=q.price, book=q.book, as_of=q.as_of, books=q.books, side=side)
    return out


def nba_quotes(cohort: Mapping, archive) -> dict[str, dict[str, dict | None]]:
    """{event_id: {clave de fila: {lado: cuota o None}}}; None también sin recibo legible (ver `nba_overlay`)."""
    return _quotes(cohort, archive)[0]


def _filas_por_evento(cohort):
    out = defaultdict(dict)
    forecasts = cohort.get("forecasts")
    for f in forecasts if isinstance(forecasts, list) else []:
        try:
            out[str(f["event_id"])][_clave(f)] = f
        except Exception:
            continue
    return out


def _quotes(cohort, archive):
    """(cuotas por evento, {event_id: True si su recibo se leyó y el evento se unió})."""
    if not isinstance(cohort, Mapping) or not isinstance(cohort.get("games"), list):
        return {}, {}
    filas = _filas_por_evento(cohort)
    out, ok, games = {}, {}, {}
    for g in cohort["games"]:
        try:
            eid = str(g["event_id"])
        except Exception:
            continue
        games[eid] = g
        out[eid] = {k: _vacio(f["market"]) for k, f in filas.get(eid, {}).items()}
        ok[eid] = False
    try:
        identity = _identidad(cohort.get("prop_lines"))
        index = None if identity is None else _recibo(Path(archive), identity)
    except Exception:
        index = None
    if index is None:
        return out, ok
    received_at = pl.parse_time(identity[1])
    for eid, g in games.items():
        try:
            evento = _evento(index, g)
        except Exception:
            continue
        if evento is None:
            continue
        for k, f in filas.get(eid, {}).items():
            try:
                out[eid][k] = _lados(evento, f, g, received_at)
            except Exception:
                continue
        ok[eid] = True
    return out, ok


def _orden(cohort):
    return str(cohort.get("recalculated_at_utc") or cohort.get("created_at_utc"))


def nba_overlay(archive, cohorts: Sequence[Mapping], *, now: datetime | None = None) -> dict:
    """Overlay de las cohortes NBA. La cohorte más reciente (recálculo o sello) gana por evento, como `nbaEvents`.
    `partial` si una cohorte es ilegible o si algún evento publicado quedó sin recibo legible o sin unir."""
    now = now or datetime.now(timezone.utc)
    base = dict(generated_at=now.isoformat(), source=SOURCE)
    archive = Path(archive)
    if not (archive / "index.sqlite").is_file():
        return dict(base, state="unavailable", events={})
    validas, completo = [], True
    for c in cohorts if isinstance(cohorts, Sequence) else []:
        if isinstance(c, Mapping) and isinstance(c.get("games"), list):
            validas.append(c)
        else:
            completo = False
    eventos, estado = {}, {}
    for c in sorted(validas, key=_orden):  # estable: a igual hora, el orden recibido (como sort de JS)
        quotes, ok = _quotes(c, archive)
        for eid, filas in quotes.items():
            if filas:  # nbaEvents no publica un evento sin filas: no sustituye al anterior
                eventos[eid], estado[eid] = filas, ok.get(eid, False)
    completo &= all(estado.values())
    return dict(base, state="ok" if completo else "partial", events=eventos)


def _json_sellado(path: Path, seal_path: Path):
    data = path.read_bytes()
    seal = json.loads(seal_path.read_bytes())
    sha = hashlib.sha256(data).hexdigest()
    if sha != seal["sha256"]:
        raise ValueError("sello distinto")
    return json.loads(data), sha


def _cohorte(folder: Path):
    bundle, sha = _json_sellado(folder / "bundle.json", folder / "bundle.seal.json")
    out = dict(bundle, cohort=folder.name)
    seals = sorted(p for p in folder.glob("updates/*/revision.seal.json") if not p.parent.name.endswith(".partial"))
    if seals:
        revision, _ = _json_sellado(seals[-1].parent / "revision.json", seals[-1])
        if revision["original_bundle_sha256"] != sha:
            raise ValueError("recálculo de otra cohorte")
        out.update(forecasts=revision["forecasts"], recalculated_at_utc=revision["recalculated_at_utc"])
    return out


def load_cohorts(root) -> list[dict]:
    """Cohortes de `root` en orden de carpeta. Una cohorte alterada o ilegible queda como `{"cohort": nombre}` (sin
    `games`), y `nba_overlay` responde `partial`."""
    if root is None:
        return []
    root = Path(root)
    try:
        folders = sorted(p for p in root.iterdir() if (p / "bundle.seal.json").is_file())
    except OSError:
        return []
    out = []
    for folder in folders:
        try:
            out.append(_cohorte(folder))
        except Exception:
            out.append(dict(cohort=folder.name))
    return out
