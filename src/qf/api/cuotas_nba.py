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

Clave de fila: `"{market}|{player_id or ''}|{line or ''}"`.
  - `player_id`: el `player_id` CRUDO de la fila de la cohorte en player_* (personId) y en team_points (allí es el id
    del EQUIPO, p. ej. 1610612747; los clientes deben conservarlo); vacío en winner y game_total.
  - `line`: vacía en winner; si no, el número como `repr` de Python sin `.0` final (220.5 -> "220.5", 220.0 -> "220"),
    igual que `String(n)` en JS.
  Ej.: `winner||`, `game_total||220.5`, `team_points|1610612747|112.5`, `player_points|2544|24.5`.

Salida de `nba_overlay`: `events[event_id] = {cohort, sealed_at, recalculated_at, quotes: {clave: {lado: cuota}}}`.
Por evento gana la cohorte más reciente (`recalculated_at_utc` o `created_at_utc`; sin ninguna, la más antigua) que
el cliente también mostraría: se aplican los mismos filtros que `nbaEvents` (JS) y `sports_feed.dart` (evento sin
`validation_hold`, con `tipoff_utc` y equipos; fila con probabilidad en (0,1), `sealed_at_utc` legible y resultado
sin `validation_hold`). La cohorte de archivos no trae los estados de resultado (salen de los recibos oficiales en el
panel), así que REGLA DEL CLIENTE: usar una cuota solo si `entry.cohort` es la cohorte (`seal`) del evento que se
muestra y su `as_of` no es posterior al `sealed_at_utc` de la fila mostrada; si no, «—».

Carpeta de cohortes (`settings.nba_cohorts_dir`, env `NBA_COHORTS_DIR`; la del productor `live13/cohorts`, montada en
solo lectura): `<raíz>/<cohorte>/bundle.json` + `bundle.seal.json` {sha256, created_at_utc} y recálculos en
`<cohorte>/updates/<tag>/revision.json` + `revision.seal.json` (se ignoran `*.partial`; el último sustituye las filas,
como apps/nba/src/nba/multimarket_live_dashboard.py:148-152). Un recálculo reutiliza las líneas y el recibo del sello
original (revisions.py:159-168). `load_cohorts` solo devuelve las cohortes con algún salto dentro de la ventana.

Caché: el RESULTADO por cohorte (pequeño e inmutable: cohorte sellada + recibo inmutable) en un LRU de
`MAX_COHORTS`; los índices de recibo (pesados) solo `MAX_RECEIPTS`, usados al calcular un fallo de caché. Un mismo
recibo se analiza una sola vez aunque lleguen peticiones simultáneas.
"""
from __future__ import annotations

import copy
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
from qf.ingest.cuotas_referencia import best_quote, elegible

PATH = "/v1/sports/basketball_nba/odds"
SOURCE = "PropLine"
MAX_RECEIPTS = 4     # índices de recibo (decenas de MB cada uno)
MAX_COHORTS = 256    # resultados por cohorte (KB)
MATCH_WINDOW = timedelta(hours=3)  # prop_lines.py:21
# apps/nba/src/nba/prop_lines.py:15-17
PLAYER_MARKETS = ("player_points", "player_rebounds", "player_assists", "player_points_rebounds",
                  "player_points_assists", "player_rebounds_assists", "player_points_rebounds_assists",
                  "player_threes", "player_steals", "player_blocks", "player_turnovers", "player_blocks_steals")
_KEYS = {"h2h", "totals", *PLAYER_MARKETS}

_cache: OrderedDict = OrderedDict()      # índices de recibo
_resultados: OrderedDict = OrderedDict()  # resultado por cohorte
# Solo fallos DEFINITIVOS (recibo inmutable): identidad distinta con todos los lotes presentes, gzip/JSON ilegible.
# Lo transitorio (copia parcial, SQLite bloqueado, E/S) no se guarda y se reintenta.
_ilegibles: OrderedDict = OrderedDict()
_en_curso: dict = {}
_lock = threading.Lock()
_DEFINITIVOS = (gzip.BadGzipFile, EOFError, zlib.error, ValueError, KeyError, TypeError, AttributeError)


def clear_cache():
    with _lock:
        _cache.clear()
        _resultados.clear()
        _ilegibles.clear()


def _guarda(cache, key, value, limite):
    with _lock:
        cache[key] = value
        cache.move_to_end(key)
        while len(cache) > limite:
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


def _intern(value):
    return sys.intern(value) if isinstance(value, str) else value


def _indexa(events, received_at):
    """{event_id: evento} con filas elegibles compactadas por (mercado, equipo, jugador NBA)."""
    out = {}
    for e in events:
        try:  # un evento malformado solo se pierde a sí mismo
            rows = defaultdict(list)
            for q in pl.quotes([e], received_at):
                market = q["market"]
                if market not in _KEYS or not elegible(q) or q["price_decimal"] is None:
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
                    key = (market, _intern(q["team"]), None)
                rows[key].append((_intern(q["bookmaker"]), _intern(q["name"]), _intern(q["side"]),
                                  q["point"], q["price_decimal"]))
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


def _leer_recibo(archive: Path, identity):
    """(índice | None, definitivo)."""
    sha, received, slot, parts = identity
    try:
        # Con as_of = received_at sellado, newest() elige el mismo recibo y los mismos lotes de la hora que al sellar.
        events, receipt = pl.newest(archive, PATH, pl.parse_time(received), max_age_seconds=0)
    except _DEFINITIVOS:  # BadGzipFile antes que OSError: es corrupción, no E/S pasajera
        return None, True
    except Exception:  # sqlite3.Error, OSError…: transitorio
        return None, False
    if receipt is None:  # la copia del archivo aún no tiene el recibo: transitorio
        return None, False
    vistos = tuple(receipt["component_receipts"])
    if (receipt["sha256"], receipt["received_at"], receipt["slot"], vistos) != identity:
        # Copia parcial: falta algún lote sellado o el último lote aún no llegó. Se reintenta.
        definitivo = receipt["received_at"] == received and set(parts) <= set(vistos)
        return None, definitivo
    return _indexa(events, received), False


def _recibo(archive: Path, identity):
    """Índice del recibo sellado; None si no se puede leer tal cual. Un solo análisis por recibo a la vez."""
    key = (str(archive),) + identity
    with _lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
        if key in _ilegibles:
            return None
        candado = _en_curso.setdefault(key, threading.Lock())
    try:
        with candado:  # sin E/S bajo el candado global
            with _lock:
                if key in _cache:
                    return _cache[key]
                if key in _ilegibles:
                    return None
            index, definitivo = _leer_recibo(archive, identity)
            if index is not None:
                _guarda(_cache, key, index, MAX_RECEIPTS)
            elif definitivo:
                _guarda(_ilegibles, key, True, MAX_COHORTS)
            return index
    finally:
        with _lock:
            if _en_curso.get(key) is candado:
                del _en_curso[key]


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
    """{event_id: {clave de fila: {lado: cuota o None}}} de todas las filas; None también sin recibo legible."""
    return copy.deepcopy(_quotes(cohort, archive)[0])


def _filas_por_evento(cohort):
    out = defaultdict(dict)
    forecasts = cohort.get("forecasts")
    for f in forecasts if isinstance(forecasts, list) else []:
        try:
            out[str(f["event_id"])][_clave(f)] = f
        except Exception:
            continue
    return out


def _huella(cohort):
    """Identidad inmutable de la cohorte: sellos del cargador o, si no, hash canónico de lo que se usa."""
    if isinstance(cohort.get("_sellos"), tuple):
        return cohort["_sellos"]
    parts = {k: cohort.get(k) for k in ("games", "forecasts", "prop_lines")}
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()


def _quotes(cohort, archive):
    """(cuotas por evento, {event_id: True si su recibo se leyó y el evento se unió})."""
    if not isinstance(cohort, Mapping) or not isinstance(cohort.get("games"), list):
        return {}, {}
    try:
        identity = _identidad(cohort.get("prop_lines"))
    except Exception:
        identity = None
    key = None
    if identity is not None:
        try:
            key = (str(archive), _huella(cohort)) + identity
        except Exception:
            key = None
        if key is not None:
            with _lock:
                if key in _resultados:
                    _resultados.move_to_end(key)
                    return _resultados[key]
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
        index = None if identity is None else _recibo(Path(archive), identity)
    except Exception:
        index = None
    if index is None:  # transitorio o definitivo: el resultado vacío no se guarda (el recibo ya lo recuerda)
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
    if key is not None:
        _guarda(_resultados, key, (out, ok), MAX_COHORTS)
    return out, ok


def _orden(cohort):
    # Sin ninguna hora: la más antigua (JS/Dart la pondrían en otro sitio, pero nunca debe ganar a una con hora).
    return str(cohort.get("recalculated_at_utc") or cohort.get("created_at_utc") or "")


def _legible(value):
    try:
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return isinstance(value, str)
    except ValueError:
        return False


def _texto(value):
    return isinstance(value, str) and bool(value)


def _prob(p):
    return isinstance(p, (int, float)) and not isinstance(p, bool) and math.isfinite(p) and 0 < p < 1


def _held(x):
    r = x.get("result")
    return isinstance(r, Mapping) and r.get("status") == "validation_hold"


def _visibles(cohort):
    """{event_id: claves de filas} que nbaEvents/sports_feed.dart mostrarían de esta cohorte."""
    out = {}
    for g in cohort["games"]:
        try:
            if (g.get("status") == "validation_hold" or not _legible(g["tipoff_utc"])
                    or not _texto(g["home_team"]) or not _texto(g["away_team"])):
                continue
            eid = g["event_id"]
            keys = []
            for f in cohort.get("forecasts") or []:
                try:
                    if (f["event_id"] == eid and not _held(f) and _prob(f["probability_over"])
                            and _legible(f["sealed_at_utc"])):
                        keys.append(_clave(f))
                except Exception:
                    continue
            if keys:
                out[str(eid)] = keys
        except Exception:
            continue
    return out


def nba_overlay(archive, cohorts: Sequence[Mapping], *, now: datetime | None = None) -> dict:
    """Overlay de las cohortes NBA. `partial` si una cohorte es ilegible o si algún evento que gana quedó sin recibo
    legible o sin unir."""
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
    ganadoras = {}
    for c in sorted(validas, key=_orden):  # estable: a igual hora, el orden recibido (como sort de JS)
        for eid, keys in _visibles(c).items():
            ganadoras[eid] = (c, keys)
    eventos, estado = {}, {}
    for eid, (c, keys) in ganadoras.items():
        quotes, ok = _quotes(c, archive)
        filas = quotes.get(eid, {})
        eventos[eid] = dict(cohort=c.get("cohort"), sealed_at=c.get("created_at_utc"),
                            recalculated_at=c.get("recalculated_at_utc"),
                            quotes=copy.deepcopy({k: filas[k] for k in keys if k in filas}))  # la caché no se comparte
        estado[eid] = ok.get(eid, False)
    completo &= all(estado.values())
    return dict(base, state="ok" if completo else "partial", events=eventos)


def _json_sellado(path: Path, seal):
    data = path.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    if sha != seal["sha256"]:
        raise ValueError("sello distinto")
    return json.loads(data), sha


def _cohorte(folder: Path, seal, desde):
    bundle, sha = _json_sellado(folder / "bundle.json", seal)
    if desde is not None and all(pl.parse_time(g["tipoff_utc"]) < desde for g in bundle["games"]):
        return None
    out = dict(bundle, cohort=folder.name, _sellos=(sha, None))
    seals = sorted(p for p in folder.glob("updates/*/revision.seal.json") if not p.parent.name.endswith(".partial"))
    if seals:
        revision, rsha = _json_sellado(seals[-1].parent / "revision.json", json.loads(seals[-1].read_bytes()))
        if revision["original_bundle_sha256"] != sha:
            raise ValueError("recálculo de otra cohorte")
        out.update(forecasts=revision["forecasts"], recalculated_at_utc=revision["recalculated_at_utc"],
                   _sellos=(sha, rsha))
    return out


def load_cohorts(root, *, dias: float | None = 3, now: datetime | None = None) -> list[dict]:
    """Cohortes de `root` en orden de carpeta con algún salto en los últimos `dias` (None: todas). Una cohorte
    alterada o ilegible queda como `{"cohort": nombre}` (sin `games`), y `nba_overlay` responde `partial`."""
    if root is None:
        return []
    root = Path(root)
    desde = None if dias is None else (now or datetime.now(timezone.utc)) - timedelta(days=dias)
    try:
        folders = sorted(p for p in root.iterdir() if (p / "bundle.seal.json").is_file())
    except OSError:
        return []
    out = []
    for folder in folders:
        try:
            seal = json.loads((folder / "bundle.seal.json").read_bytes())
            # Se sella 65-90 min antes del salto y una cohorte es un solo día ET: sellada 2 días antes de la ventana,
            # todos sus saltos quedan fuera sin leer bundle.json.
            creada = seal.get("created_at_utc")
            if desde is not None and creada is not None and pl.parse_time(creada) < desde - timedelta(days=2):
                continue
        except Exception:
            seal = None
        try:
            if seal is None:
                raise ValueError("sello ilegible")
            cohort = _cohorte(folder, seal, desde)
            if cohort is not None:
                out.append(cohort)
        except Exception:
            out.append(dict(cohort=folder.name))
    return out
