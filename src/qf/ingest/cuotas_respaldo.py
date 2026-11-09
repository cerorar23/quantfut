"""Respaldo de cuotas NBA/tenis con The Odds API HISTÓRICO, por lotes (decisión del titular, 31-oct-2026).

Si PropLine no tiene cuota para una fila, este comando consulta el histórico de The Odds API a la hora del sello
(así el snapshot cumple as_of <= sealed_at) y guarda el resultado en una caché JSON en disco. El overlay
(`aplica_nba` / `aplica_tenis`, llamados desde api/cuotas_web.py) SOLO LEE esa caché: ningún endpoint web gasta
créditos (sería un vector de abuso). PropLine siempre gana; el respaldo solo rellena lados que quedaron en None.

Uso (desde el servidor, con la clave en el entorno; nunca se imprime):
  python -m qf.ingest.cuotas_respaldo                         # seco: plan y coste estimado, sin peticiones
  python -m qf.ingest.cuotas_respaldo --ejecutar              # pide, hasta --max-creditos (defecto 300)
  opciones: --deporte nba|tenis|todos  --regiones us  --max-creditos N

Coste (documentación v4): histórico de evento 10 x regiones x mercados; listado histórico de eventos 1.
Se para antes de gastar más de --max-creditos o si el saldo (`x-requests-remaining`) quedaría bajo SUELO.

Emparejamiento: equipos/jugadores con nombre normalizado IGUAL (sin parecidos) y comienzo a +-TOLERANCIA del
evento sellado; si hay 0 o más de 1 candidato, no se usa. Jugadores NBA: The Odds API solo conoce nombres, así que
solo se piden si la fila sellada trae `player_name`; si no, siguen sin cuota.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from qf.api import cuotas_nba as cn
from qf.api import cuotas_tenis as ct
from qf.config import settings
from qf.ingest import cuotas_sportsapipro as csp
from qf.ingest import propline_shared as pl
from qf.ingest.cuotas_referencia import best_quote

log = logging.getLogger(__name__)
HOST = "https://api.the-odds-api.com"
SRC = "the-odds-api"
SRC_SP = "sportsapipro"             # tercer nivel: cuota de ahora, posterior al sello (ver cuotas_sportsapipro)
# Cascada (decisión del titular, 9-nov-2026): PropLine -> The Odds API -> SportsAPIPro. Un hueco se intenta como
# mucho INTENTOS_MAX veces por nivel, con ESPERA_REINTENTO entre una y otra: sin hueco resuelto, repetir cada 10 min
# gastaría créditos (nivel 2) o el cupo diario del plan gratuito (nivel 3) sin ganar nada.
INTENTOS_MAX = 2
ESPERA_REINTENTO = timedelta(hours=1)
SP_DEPORTE = {"nba": "basketball", "tenis": "tennis"}
SP_MERCADOS = ("winner", "game_total", "games_total")
SUELO = 500                         # no gastar si el saldo quedaría por debajo
MAX_CREDITOS = 300
TOLERANCIA = timedelta(minutes=30)  # comienzo del evento de The Odds API frente al sellado
VIGENCIA = timedelta(days=5)        # las entradas más viejas se podan al escribir
NBA_SPORT = "basketball_nba"
# Mercado sellado -> clave de The Odds API.
NBA_MERCADOS = {"winner": "h2h", "game_total": "totals", "player_points": "player_points",
                "player_rebounds": "player_rebounds", "player_assists": "player_assists",
                "player_threes": "player_threes"}
TENIS_MERCADOS = {"winner": "h2h", "games_total": "totals", "games_handicap": "spreads"}


class Parar(Exception):
    """Presupuesto o saldo agotado: se escribe lo ya obtenido y se termina."""


def norm(name) -> str:
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", str(name or "")) if not unicodedata.combining(c))
                    .casefold().replace("-", " ").split())


# --- caché en disco -----------------------------------------------------------------------------------------

def leer_cache(path) -> dict:
    """{clave: entrada}; ausente o ilegible -> {} (el overlay nunca falla por esto)."""
    if not path:
        return {}
    try:
        doc = json.loads(Path(path).read_bytes())
        entries = doc.get("entries") if isinstance(doc, dict) else None
        return entries if isinstance(entries, dict) else {}
    except (OSError, ValueError):
        return {}


def _ruta_intentos(cache_path) -> Path:
    return Path(str(cache_path) + ".intentos.json")


def leer_intentos(cache_path) -> dict:
    """{clave: {n2, t2, n3, t3}}; ausente o ilegible -> {} (se repite el intento, nunca falla)."""
    try:
        d = json.loads(_ruta_intentos(cache_path).read_bytes())
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def escribir_intentos(cache_path, intentos: Mapping, now: datetime) -> None:
    vivos = {}
    for k, d in intentos.items():
        try:
            if max(pl.parse_time(d[t]) for t in ("t2", "t3") if d.get(t)) >= now - VIGENCIA:
                vivos[k] = d
        except (ValueError, TypeError, KeyError):
            continue
    destino = _ruta_intentos(cache_path)
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(destino.name + ".tmp")
    tmp.write_text(json.dumps(vivos, separators=(",", ":")), encoding="utf-8")
    os.replace(tmp, destino)


def intento_permitido(intentos: Mapping, clave: str, nivel: int, now: datetime) -> bool:
    d = intentos.get(clave) or {}
    if int(d.get(f"n{nivel}", 0)) >= INTENTOS_MAX:
        return False
    t = d.get(f"t{nivel}")
    try:
        return not t or now - pl.parse_time(t) >= ESPERA_REINTENTO
    except (ValueError, TypeError):
        return True


def marca_intento(intentos: dict, clave: str, nivel: int, now: datetime) -> None:
    d = intentos.setdefault(clave, {})
    d[f"n{nivel}"] = int(d.get(f"n{nivel}", 0)) + 1
    d[f"t{nivel}"] = pl.stamp(now)


def escribir_cache(path, entries: Mapping, now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    vivas = {}
    for k, e in entries.items():
        try:
            if pl.parse_time(e["sealed_at"]) >= now - VIGENCIA:
                vivas[k] = e
        except Exception:
            continue
    destino = Path(path)
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(destino.name + ".tmp")
    tmp.write_text(json.dumps(dict(generated_at=pl.stamp(now), source=SRC, entries=vivas),
                              separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, destino)  # atómico: el overlay nunca lee una escritura a medias


# --- cliente (la red es inyectable; la clave solo vive en el transporte real) -----------------------------------

def _transporte(key: str) -> Callable:
    def get(path: str, params: Mapping):
        url = f"{HOST}{path}?{urllib.parse.urlencode({**params, 'apiKey': key})}"
        try:
            with urllib.request.urlopen(url, timeout=30) as r:  # noqa: S310 (host fijo)
                return r.status, dict(r.headers), json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), None
    return get


@dataclass
class Presupuesto:
    maximo: int = MAX_CREDITOS
    gastado: int = 0
    saldo: int | None = None   # x-requests-remaining de la última respuesta

    def cobra(self, coste: int) -> None:
        if self.gastado + coste > self.maximo:
            raise Parar(f"presupuesto: {self.gastado}+{coste} > {self.maximo}")
        if self.saldo is not None and self.saldo - coste < SUELO:
            raise Parar(f"saldo {self.saldo} - {coste} bajo el suelo {SUELO}")

    def registra(self, headers: Mapping, coste: int) -> None:
        h = {str(k).lower(): v for k, v in (headers or {}).items()}
        try:
            self.saldo = int(float(h["x-requests-remaining"]))
        except (KeyError, TypeError, ValueError):
            pass
        try:
            self.gastado += int(float(h["x-requests-last"]))
        except (KeyError, TypeError, ValueError):
            self.gastado += coste


class Cliente:
    def __init__(self, get: Callable, presupuesto: Presupuesto, regiones: str = "us"):
        self.get, self.p, self.regiones = get, presupuesto, regiones
        self.peticiones = 0

    def _pide(self, path, params, coste):
        self.p.cobra(coste)
        self.peticiones += 1
        status, headers, body = self.get(path, params)
        self.p.registra(headers, coste)
        if status != 200 or not isinstance(body, dict):
            return None
        return body

    def saldo(self):
        """Lectura gratuita (/v4/sports no cuesta créditos): fija el saldo y devuelve las claves de tenis activas."""
        status, headers, body = self.get("/v4/sports", {})
        self.p.registra(headers, 0)
        self.p.gastado = 0  # no cuesta; x-requests-last no cuenta
        lista = body if isinstance(body, list) else []
        return [s["key"] for s in lista if isinstance(s, dict) and str(s.get("key", "")).startswith("tennis_")
                and s.get("active")]

    def eventos(self, sport_key, date):
        b = self._pide(f"/v4/historical/sports/{sport_key}/events", {"date": pl.stamp(date)}, 1)
        return (b or {}).get("data") if isinstance((b or {}).get("data"), list) else []

    def eventos_actuales(self, sport_key, mercados: str, regiones: str, coste: int) -> list:
        """Cuota ACTUAL de toda una competición (fútbol, `cuotas_respaldo_futbol`): mercados x regiones créditos."""
        self.p.cobra(coste)
        self.peticiones += 1
        status, headers, body = self.get(f"/v4/sports/{sport_key}/odds",
                                         {"regions": regiones, "markets": mercados, "oddsFormat": "decimal",
                                          "dateFormat": "iso"})
        self.p.registra(headers, coste)
        return body if status == 200 and isinstance(body, list) else []

    def cuotas(self, sport_key, event_id, mercados, date):
        coste = 10 * len(self.regiones.split(",")) * len(mercados)
        return self._pide(f"/v4/historical/sports/{sport_key}/events/{event_id}/odds",
                          {"regions": self.regiones, "markets": ",".join(mercados), "oddsFormat": "decimal",
                           "dateFormat": "iso", "date": pl.stamp(date)}, coste)


# --- huecos --------------------------------------------------------------------------------------------------

@dataclass
class Hueco:
    deporte: str
    eid: str
    sport_key: str | None
    local: str          # NBA: local; tenis: jugador A
    visitante: str      # NBA: visitante; tenis: jugador B
    comienzo: datetime
    sellado: datetime
    items: list = field(default_factory=list)

    @property
    def mercados(self):
        return sorted({i["odds_market"] for i in self.items})


def huecos_nba(archive, cohortes, cache: Mapping, *, now=None) -> list[Hueco]:
    """Filas visibles de NBA cuyo overlay de PropLine dejó algún lado sin cuota y The Odds API soporta."""
    ganadoras = {}
    for c in sorted((c for c in cohortes if isinstance(c, Mapping) and isinstance(c.get("games"), list)), key=cn._orden):
        for eid, keys in cn._visibles(c).items():
            ganadoras[eid] = (c, keys)
    out = []
    for eid, (c, keys) in ganadoras.items():
        quotes, _ = cn._quotes(c, Path(archive))
        filas = cn._filas_por_evento(c).get(eid, {})
        game = next((g for g in c["games"] if str(g.get("event_id")) == eid), None)
        if game is None:
            continue
        items = []
        for k in keys:
            f, lados = filas.get(k), quotes.get(eid, {}).get(k) or {}
            mercado = (f or {}).get("market")
            if f is None or mercado not in NBA_MERCADOS or f"{eid}|{k}" in cache:
                continue
            if all(v is not None for v in lados.values()) and lados:
                continue
            nombre = f.get("player_name") if mercado.startswith("player_") else None
            if mercado.startswith("player_") and not (isinstance(nombre, str) and nombre):
                continue
            items.append(dict(key=k, market=mercado, odds_market=NBA_MERCADOS[mercado],
                              line=cn._linea(f.get("line")), player_name=nombre,
                              sealed=pl.parse_time(f["sealed_at_utc"])))
        if items:
            out.append(Hueco("nba", eid, NBA_SPORT, game["home_team"], game["away_team"],
                             pl.parse_time(game["tipoff_utc"]), min(i["sealed"] for i in items), items))
    return out


def huecos_tenis(archive, feed, sellos, cache: Mapping, *, now=None) -> list[Hueco]:
    overlay = ct.tennis_overlay(archive, feed, sealed=sellos, now=now)
    out = []
    for eid, mercados in overlay.get("events", {}).items():
        doc = sellos.get(eid)
        try:
            fc, sellado = doc["forecast"], pl.parse_time(doc["sealed_at"])
            a, b = fc["players"]
            inicio = pl.parse_time((fc.get("market_board") or {}).get("commence_time") or doc["provider_start"])
            contratos = dict(ct._contratos(fc))
        except Exception:
            continue
        items = []
        for mid, q in mercados.items():
            c = contratos.get(mid)
            if q is not None or c is None or c["kind"] not in TENIS_MERCADOS or f"{eid}|{mid}" in cache:
                continue
            if c["kind"] in ("games_total", "games_handicap") and ct._linea(c.get("line")) is None:
                continue
            items.append(dict(key=mid, market=c["kind"], odds_market=TENIS_MERCADOS[c["kind"]],
                              line=ct._linea(c.get("line")), selection=c["selection"]))
        if items:
            out.append(Hueco("tenis", eid, None, a, b, inicio, sellado, items))
    return out


def coste_estimado(huecos, regiones="us", claves_tenis=1) -> int:
    n = len(regiones.split(","))
    total = 0
    fechas = set()
    for h in huecos:
        copias = claves_tenis if h.deporte == "tenis" else 1
        if (h.deporte, h.sellado) not in fechas:
            fechas.add((h.deporte, h.sellado))
            total += copias
        total += 10 * n * len(h.mercados)
    return total


# --- emparejamiento y normalización ---------------------------------------------------------------------------

def _empareja(eventos, hueco: Hueco):
    """Único evento de The Odds API con los mismos equipos/jugadores (nombre exacto) y comienzo cercano."""
    buenos = []
    for e in eventos or []:
        try:
            par = {norm(e["home_team"]), norm(e["away_team"])}
            if len(par) == 2 and par == {norm(hueco.local), norm(hueco.visitante)} \
                    and abs(pl.parse_time(e["commence_time"]) - hueco.comienzo) <= TOLERANCIA:
                buenos.append(e)
        except Exception:
            continue
    return buenos[0] if len(buenos) == 1 else None


def _fila(casa, nombre, lado, punto, precio):
    return dict(bookmaker=casa, name=nombre, side=lado, point=punto, price_decimal=precio, flags=[], period=None,
                dfs_odds_type=None, payout_multiplier=None)


def _filas_item(evento, hueco: Hueco, item) -> list[dict]:
    """Filas de las casas para un ítem, en el formato que consume best_quote."""
    out = []
    for b in evento.get("bookmakers") or []:
        for m in b.get("markets") or []:
            if m.get("key") != item["odds_market"]:
                continue
            for o in m.get("outcomes") or []:
                nombre, precio = o.get("name"), o.get("price")
                if not isinstance(precio, (int, float)) or isinstance(precio, bool):
                    continue
                lado = None
                es_total = item["market"] in ("game_total", "games_total") or item["market"].startswith("player_")
                if es_total:
                    if norm(nombre) not in ("over", "under"):
                        continue
                    if item["market"].startswith("player_") and norm(o.get("description")) != norm(item["player_name"]):
                        continue
                elif hueco.deporte == "nba":  # winner
                    lado = "home" if norm(nombre) == norm(hueco.local) else                         "away" if norm(nombre) == norm(hueco.visitante) else None
                else:  # tenis: ganador y hándicap por jugador A/B
                    lado = "A" if norm(nombre) == norm(hueco.local) else "B" if norm(nombre) == norm(hueco.visitante) else None
                if not es_total and lado is None:
                    continue
                out.append(_fila(b.get("key"), nombre, lado, o.get("point"), precio))
    return out


def _entrada(hueco, item, evento, ts, filas):
    e = dict(sealed_at=pl.stamp(item.get("sealed") or hueco.sellado), timestamp=pl.stamp(ts), rows=filas,
             odds_event=str(evento.get("id")))
    if hueco.deporte == "tenis":
        e.update(line=item["line"], selection=item["selection"])
    return e


def _procesa(cli: Cliente, hueco: Hueco, claves_tenis, memo, entries) -> int:
    nuevas = 0
    claves = [hueco.sport_key] if hueco.sport_key else claves_tenis
    for sk in claves:
        if (sk, hueco.sellado) not in memo:
            memo[(sk, hueco.sellado)] = cli.eventos(sk, hueco.sellado)
        ev = _empareja(memo[(sk, hueco.sellado)], hueco)
        if ev is None:
            continue
        b = cli.cuotas(sk, ev["id"], hueco.mercados, hueco.sellado)
        if b is None:
            return nuevas
        try:
            ts, data = pl.parse_time(b["timestamp"]), b["data"]
            if ts > hueco.sellado or _empareja([data], hueco) is None:
                return nuevas  # snapshot posterior al sello o evento distinto: no se usa
        except Exception:
            return nuevas
        for item in hueco.items:
            filas = _filas_item(data, hueco, item)
            if filas:
                entries[f"{hueco.eid}|{item['key']}"] = _entrada(hueco, item, data, ts, filas)
                nuevas += 1
        return nuevas
    return nuevas


# --- overlay: solo lee ------------------------------------------------------------------------------------------

def _quote(entrada, side, line, sealed):
    recibido = pl.parse_time(entrada["timestamp"])
    if entrada.get("post_sello"):
        # SportsAPIPro: solo existe la cuota de ahora, recibida DESPUÉS del sello. Se muestra con su hora real y la
        # marca `post_sello`, que la regla de publicación ignora; el filtro punto-en-el-tiempo se evalúa contra la
        # propia recepción, así que aquí no oculta nada.
        q = best_quote(entrada["rows"], line=line, side=side, sealed_at=recibido, received_at=recibido)
        return None if q is None else dict(price=q.price, book=q.book, as_of=q.as_of, books=q.books, side=side,
                                           src=SRC_SP, post_sello=True)
    q = best_quote(entrada["rows"], line=line, side=side, sealed_at=sealed, received_at=recibido)
    return None if q is None else dict(price=q.price, book=q.book, as_of=q.as_of, books=q.books, side=side, src=SRC)


def aplica_nba(overlay: dict, cache: Mapping) -> dict:
    """Rellena SOLO los lados sin cuota de PropLine con la caché del respaldo. Nunca lanza."""
    for eid, ev in (overlay.get("events") or {}).items():
        for k, lados in (ev.get("quotes") or {}).items():
            entrada = cache.get(f"{eid}|{k}")
            if not entrada or not isinstance(lados, dict):
                continue
            try:
                texto = k.split("|")[2]
                line = float(texto) if texto else None
                sealed = pl.parse_time(entrada["sealed_at"])
                for side, actual in lados.items():
                    if actual is None:
                        lados[side] = _quote(entrada, side, line, sealed)
            except Exception:
                continue
    return overlay


def aplica_tenis(overlay: dict, cache: Mapping) -> dict:
    for eid, mercados in (overlay.get("events") or {}).items():
        for mid, actual in list(mercados.items()):
            entrada = cache.get(f"{eid}|{mid}")
            if actual is not None or not entrada:
                continue
            try:
                mercados[mid] = _quote(entrada, entrada["selection"], entrada.get("line"),
                                       pl.parse_time(entrada["sealed_at"]))
            except Exception:
                continue
    return overlay


# --- comando -------------------------------------------------------------------------------------------------------

def _sin_resolver(huecos, entries: Mapping) -> list[Hueco]:
    """Copias de los huecos con solo los ítems que ningún nivel anterior resolvió."""
    out = []
    for h in huecos:
        items = [i for i in h.items if f"{h.eid}|{i['key']}" not in entries]
        if items:
            out.append(Hueco(h.deporte, h.eid, h.sport_key, h.local, h.visitante, h.comienzo, h.sellado, items))
    return out


def _evento_sportsapipro(cli: csp.Cliente, sport: str, h: Hueco, memo: dict):
    """(evento, invertido) del calendario de SportsAPIPro, o (None, False). Un calendario por deporte y fecha."""
    for fecha in csp.fechas_calendario(h.comienzo):
        if (sport, fecha) not in memo:
            _, doc = cli.get(f"{sport}/schedule/{fecha}", "calendario", f"{sport}/{fecha}")
            memo[(sport, fecha)] = csp._eventos_de(doc)
        r = csp.busca_evento(memo[(sport, fecha)], h.local, h.visitante, h.comienzo, tenis=h.deporte == "tenis")
        if r is not None:
            return r
    return None, False


def nivel3_sportsapipro(cli: csp.Cliente, huecos, entries: dict, intentos: dict, now: datetime, salida=print) -> int:
    """Tercer nivel: lo que ni PropLine ni The Odds API resolvieron. Prepartido de ahora, una casa, marcado
    `post_sello`. Sin props de jugador ni hándicap (no se piden: SportsAPIPro no los devuelve de forma comprobable)."""
    nuevas, memo = 0, {}
    for h in huecos:
        if h.comienzo <= now:
            continue    # SportsAPIPro solo tiene el prepartido de ahora: de un partido ya empezado no hay nada que pedir
        items = [i for i in h.items if i["market"] in SP_MERCADOS and f"{h.eid}|{i['key']}" not in entries
                 and intento_permitido(intentos, f"{h.eid}|{i['key']}", 3, now)]
        if not items:
            continue
        try:
            sport = SP_DEPORTE[h.deporte]
            evento, invertido = _evento_sportsapipro(cli, sport, h, memo)
            doc, recibido = None, None
            if evento is not None:
                recibido, doc = cli.get(f"{sport}/api/match/{evento['id']}/odds/pre-match", "cuotas", str(evento["id"]))
        except csp.SinCupo as e:
            salida(f"sportsapipro: {e}")
            break
        for i in items:
            marca_intento(intentos, f"{h.eid}|{i['key']}", 3, now)
        if doc is None:
            continue
        ms = csp.mercados(doc)
        for item in items:
            filas = csp.filas_item(ms, h.deporte, item, h.local, h.visitante, invertido)
            if filas:
                e = _entrada(h, item, {"id": evento["id"]}, recibido, filas)
                e.update(fuente=SRC_SP, post_sello=True)
                entries[f"{h.eid}|{item['key']}"] = e
                nuevas += 1
    return nuevas


def _cliente_sportsapipro(sp_key, sp_call, sp_raiz, now):
    raiz = sp_raiz
    if raiz is None and getattr(settings, "artifact_dir", None):
        raiz = Path(settings.artifact_dir) / "sportsapipro_cuotas"
    return csp.Cliente(sp_key, call=sp_call, clock=lambda: now, raiz=raiz,
                       tope=int(getattr(settings, "cuotas_sportsapipro_diario", 0) or 0))


def correr(*, ejecutar=False, max_creditos=MAX_CREDITOS, deporte="todos", regiones="us", get=None, now=None,
           salida=print, key=None, cache_path=None, info=None, sp_key=None, sp_call=None, sp_raiz=None) -> int:
    key = key if key is not None else settings.odds_api_respaldo_key
    sp_key = sp_key if sp_key is not None else getattr(settings, "sportsapipro_key", None)
    cache_path = cache_path if cache_path is not None else settings.cuotas_respaldo_cache
    if not key and not sp_key:
        salida("sin ODDS_API_RESPALDO_KEY ni SPORTSAPIPRO_KEY: no hay nada que hacer")
        return 0
    if not cache_path:
        salida("sin CUOTAS_RESPALDO_CACHE: no hay dónde guardar")
        return 0
    now = now or datetime.now(timezone.utc)
    cache = leer_cache(cache_path)
    huecos = []
    archive = settings.propline_archive
    if deporte in ("nba", "todos") and settings.nba_cohorts_dir:
        huecos += huecos_nba(archive, cn.load_cohorts(settings.nba_cohorts_dir, dias=3, now=now), cache, now=now)
    if deporte in ("tenis", "todos") and settings.tennis_sealed_dir:
        from qf.api import tenis_publico
        feed = tenis_publico.public_data()
        ids = [e.get("id") for e in feed.get("events", []) if isinstance(e, dict) and e.get("id") is not None]
        huecos += huecos_tenis(archive, feed, ct.load_sealed(settings.tennis_sealed_dir, ids), cache, now=now)
    huecos = [h for h in huecos if h.sellado <= now]
    salida(f"huecos: {sum(len(h.items) for h in huecos)} filas en {len(huecos)} eventos; "
           f"coste estimado ~{coste_estimado(huecos, regiones)} créditos (tope {max_creditos}, suelo {SUELO})")
    for h in huecos:
        salida(f"  {h.deporte} {h.eid} {h.local} - {h.visitante}: {h.mercados} sello {pl.stamp(h.sellado)}")
    if not ejecutar:
        salida("modo seco: no se hizo ninguna petición (use --ejecutar)")
        return 0
    if not huecos:
        return 0  # sin hueco no hay ni una petición (ni siquiera la lectura gratuita del saldo)
    intentos, entries, nuevas, suelo = leer_intentos(cache_path), dict(cache), 0, False
    cli = Cliente(get or _transporte(key or ""), Presupuesto(max_creditos), regiones)
    # Nivel 2: The Odds API (histórico a la hora del sello). Se salta sin clave, sin presupuesto o con los intentos
    # agotados; lo que quede sin resolver pasa al nivel 3, también cuando el saldo cae bajo el suelo a mitad de pasada.
    pend2 = []
    for h in _sin_resolver(huecos, entries):
        items = [i for i in h.items if intento_permitido(intentos, f"{h.eid}|{i['key']}", 2, now)]
        if items:
            pend2.append(Hueco(h.deporte, h.eid, h.sport_key, h.local, h.visitante, h.comienzo, h.sellado, items))
    if key and max_creditos > 0 and pend2:
        claves_tenis = cli.saldo()  # lectura gratuita: fija el saldo y lista los torneos de tenis activos
        memo = {}
        try:
            for h in pend2:
                nuevas += _procesa(cli, h, claves_tenis, memo, entries)
                for i in h.items:
                    marca_intento(intentos, f"{h.eid}|{i['key']}", 2, now)
        except Parar as e:
            salida(f"parado: {e} (lo que falte pasa a SportsAPIPro)")
            suelo = "suelo" in str(e)
    # Nivel 3: SportsAPIPro para todo lo que siga sin cuota.
    n3, cli3 = 0, None
    if sp_key:
        cli3 = _cliente_sportsapipro(sp_key, sp_call, sp_raiz, now)
        n3 = nivel3_sportsapipro(cli3, _sin_resolver(huecos, entries), entries, intentos, now, salida)
    if nuevas or n3:
        escribir_cache(cache_path, entries, now)
    if intentos:
        try:
            escribir_intentos(cache_path, intentos, now)
        except OSError:
            log.exception("respaldo de cuotas: no se pudo guardar el registro de intentos")
    if info is not None:
        info.update(gastado=cli.p.gastado, saldo=cli.p.saldo, peticiones=cli.peticiones, nuevas=nuevas, suelo=suelo,
                    nuevas_sportsapipro=n3, peticiones_sportsapipro=cli3.peticiones if cli3 else 0)
    salida(f"entradas nuevas: {nuevas}; peticiones de pago: {cli.peticiones}; créditos gastados: "
           f"{cli.p.gastado}; saldo: {cli.p.saldo}; SportsAPIPro: {n3} entradas en "
           f"{cli3.peticiones if cli3 else 0} peticiones")
    return 0


# --- ejecución automática tras el sellado (apagada por defecto) ------------------------------------------------

def _gasto_hoy(path: Path, now: datetime) -> int:
    try:
        d = json.loads(path.read_bytes())
        return int(d["gastado"]) if d.get("dia") == now.date().isoformat() else 0
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return 0


def _futbol(*, get, now, cache_path, key, sp_key, kw, tope, estado, hoy) -> dict:
    """Fútbol (cuotas de consulta): comparte clave, suelo y tope diario con NBA/tenis. Nunca lanza."""
    try:
        from qf.ingest import cuotas_respaldo_futbol as rf
        out = rf.correr(ejecutar=True, max_creditos=tope, get=get, now=now, salida=log.info, key=key, sp_key=sp_key,
                        sp_call=kw.get("sp_call"), sp_raiz=kw.get("sp_raiz"), cache_path=cache_path,
                        lista_huecos=kw.get("huecos_futbol"))
        gastado = int(out.get("gastado", 0) or 0)
        if gastado:
            tmp = estado.with_name(estado.name + ".tmp")
            tmp.write_text(json.dumps(dict(dia=now.date().isoformat(), gastado=hoy + gastado)), encoding="utf-8")
            os.replace(tmp, estado)
        return out
    except Exception:  # noqa: BLE001
        log.exception("respaldo de cuotas de fútbol: fallo (ignorado)")
        return {"estado": "error"}


def auto(*, get=None, now=None, cache_path=None, key=None, alerta=None, **kw) -> dict:
    """Pasada automática: solo si CUOTAS_RESPALDO_AUTO=1. Pide únicamente los huecos de pronósticos ya sellados
    que PropLine dejó sin cuota; sin huecos no hay peticiones. Tope por corrida y tope diario (persistido junto a
    la caché) para que varias pasadas no lo superen. NUNCA lanza: un fallo se registra y no toca el sellado."""
    info: dict = {"estado": "desactivado"}
    if not settings.cuotas_respaldo_auto:
        return info
    try:
        cache_path = cache_path if cache_path is not None else settings.cuotas_respaldo_cache
        if not cache_path:
            return {"estado": "sin_cache"}
        now = now or datetime.now(timezone.utc)
        estado = Path(str(cache_path) + ".gasto.json")
        hoy = _gasto_hoy(estado, now)
        tope = min(settings.cuotas_respaldo_auto_max, settings.cuotas_respaldo_diario - hoy)
        sp_key = kw.get("sp_key") if kw.get("sp_key") is not None else getattr(settings, "sportsapipro_key", None)
        if tope <= 0 and not sp_key:
            return {"estado": "tope_diario", "gastado_hoy": hoy}
        # Con el tope de créditos agotado, The Odds API se salta y SportsAPIPro (nivel 3) sigue cubriendo huecos.
        run: dict = {}
        correr(ejecutar=True, max_creditos=max(tope, 0), get=get, now=now, salida=log.info, key=key,
               cache_path=cache_path, info=run, sp_key=sp_key, sp_call=kw.get("sp_call"), sp_raiz=kw.get("sp_raiz"))
        gastado = int(run.get("gastado", 0))
        if gastado:
            tmp = estado.with_name(estado.name + ".tmp")
            tmp.write_text(json.dumps(dict(dia=now.date().isoformat(), gastado=hoy + gastado)), encoding="utf-8")
            os.replace(tmp, estado)
        saldo = run.get("saldo")
        if run.get("suelo") or (saldo is not None and saldo < SUELO):
            if alerta is None:
                from qf.publish import telegram
                alerta = telegram.alert
            alerta(f"Respaldo de cuotas: el saldo de The Odds API ({saldo}) cayó bajo el suelo {SUELO}")
        futbol = _futbol(get=get, now=now, cache_path=cache_path, key=key, sp_key=sp_key, kw=kw,
                         tope=max(tope - gastado, 0), estado=estado, hoy=hoy + gastado)
        return {"estado": "ok", **run, "gastado_hoy": hoy + gastado + int(futbol.get("gastado", 0)), "futbol": futbol}
    except Exception:  # noqa: BLE001 — el respaldo nunca rompe ni retrasa el sellado ni la publicación
        log.exception("respaldo de cuotas: fallo (ignorado)")
        return {"estado": "error"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ejecutar", action="store_true", help="hace las peticiones (por defecto: seco)")
    ap.add_argument("--max-creditos", type=int, default=MAX_CREDITOS)
    ap.add_argument("--deporte", choices=("nba", "tenis", "todos"), default="todos")
    ap.add_argument("--regiones", default="us")
    ap.add_argument("--auto", action="store_true", help="pasada automática (solo si CUOTAS_RESPALDO_AUTO=1)")
    a = ap.parse_args(argv)
    if a.auto:
        logging.basicConfig(level=logging.INFO)
        print(auto())
        return 0
    return correr(ejecutar=a.ejecutar, max_creditos=a.max_creditos, deporte=a.deporte, regiones=a.regiones)


if __name__ == "__main__":
    sys.exit(main())
