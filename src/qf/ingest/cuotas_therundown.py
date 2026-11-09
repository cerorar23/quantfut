"""Cuarto y último nivel del respaldo de cuotas: TheRundown (cuenta Free), tras PropLine, The Odds API y SportsAPIPro.

Decisión del titular (9-nov-2026): cuando ninguna fuente anterior encuentra la cuota de un mercado, probar TheRundown,
para fútbol, NBA y tenis. Este módulo es el cliente y el traductor; la orquestación vive en `cuotas_respaldo`
(NBA y tenis) y `cuotas_respaldo_futbol` (fútbol).

Qué es la cuenta Free (medido el 9-nov-2026 con la clave del titular; docs.therundown.io):
  * `GET https://therundown.io/api/v2/sports/{sport_id}/events/{AAAA-MM-DD}?market_ids=1,2,3&main_line=true`,
    clave en la cabecera `X-TheRundown-Key` (nunca en la URL). Fecha UTC.
  * Solo tres casas de EE. UU. (`x-bookmakers: betmgm,fanduel,draftkings`), solo partido completo (`x-periods:
    fullgame`), 5 minutos de retraso, 1 petición por segundo, 20.000 puntos al día y 200.000 al mes.
  * SIN histórico: `openers` y `closing` responden 403 («Historical data requires a Starter plan or higher»), así que
    no hay cuota de entrada ni de salida; solo el prepartido de ahora. Su recepción es posterior al sello: las
    entradas llevan `post_sello` (se muestran con su hora real; la regla de publicación las ignora).
  * SIN props de jugador (requieren Starter). Mercados usados: 1 (ganador; en fútbol 1X2 con tres participantes),
    2 (hándicap) y 3 (totales). `main_line=true` es obligatorio: sin él, una sola consulta de NBA costó 3.495 puntos
    frente a 147 (todas las líneas alternativas); por eso solo se encuentra una línea si es la principal de la casa.
  * Cuotas en formato americano; `0.0001` es «fuera del tablero». Los partidos terminados no traen mercados.

Licencia (docs.therundown.io/licensing-and-attribution): Free es «uso interno o personal» y no permite mostrar los datos
a usuarios finales; tampoco guardarlos más de 24 h ni entrenar con ellos. El titular decidió mostrarlas igualmente
(9-nov-2026) y asumió el riesgo. Mitigaciones que sí se cumplen: nada se archiva (ni los originales) y las entradas
caducan a las 24 h (`TTL`); `CUOTAS_THERUNDOWN_MOSTRAR=0` o el archivo `cuotas_therundown_oculto` en el volumen de la caché las
oculta sin tocar código.
"""
from __future__ import annotations

import json
import logging
import math
import os
import time
import unicodedata
import urllib.error
import urllib.request
import re
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

log = logging.getLogger(__name__)
BASE = "https://therundown.io/api/v2"
FUENTE = "therundown"
TTL = timedelta(hours=24)               # la licencia no permite guardar los datos más de 24 h
TOLERANCIA = timedelta(hours=3)
RESERVA = 2000                          # puntos diarios que no se tocan (de 20.000)
PAUSA = 1.1                             # 1 petición por segundo en Free
SPORT_NBA = 4
SPORT_TENIS = (38, 39)                  # ATP, WTA
# Fútbol: `leagues.odds_api_key` -> sport_id de TheRundown. Otras ligas no están en su catálogo.
SPORT_FUTBOL = {"soccer_epl": 11, "soccer_france_ligue_one": 12, "soccer_germany_bundesliga": 13,
                "soccer_spain_la_liga": 14, "soccer_italy_serie_a": 15, "soccer_uefa_champs_league": 16,
                "soccer_uefa_europa_league": 17, "soccer_mexico_ligamx": 34, "soccer_usa_mls": 10}
CASAS = {2: "bovada", 3: "pinnacle", 4: "sportsbetting", 6: "betonlineag", 7: "bookmaker", 9: "betcris", 11: "lowvig",
         14: "intertops", 16: "matchbook", 18: "youwager", 19: "draftkings", 21: "unibet", 22: "betmgm", 23: "fanduel",
         24: "thescore", 25: "kalshi", 26: "polymarket", 28: "hardrock", 29: "prophetx", 30: "novig",
         31: "polymarket_us", 32: "circa", 33: "bet105", 34: "heritage", 35: "caesars"}


_oculto: list = [0.0, False]            # [hora de la última lectura, ¿archivo de ocultar presente?]
ARCHIVO_OCULTAR = "cuotas_therundown_oculto"


def mostrar() -> bool:
    """¿Se muestran las cuotas de TheRundown? Apagado si `CUOTAS_THERUNDOWN_MOSTRAR` es 0/false/no, o si existe el archivo
    `cuotas_therundown_oculto` junto a la caché del respaldo (el volumen compartido con la API): cambiar una variable de
    entorno exige recrear el contenedor de la API y perder los archivos copiados con `docker cp`; crear o borrar ese
    archivo actúa en segundos y sin reiniciar nada. Por defecto, visible."""
    if os.getenv("CUOTAS_THERUNDOWN_MOSTRAR", "1").strip() in ("0", "false", "no", ""):
        return False
    ahora = time.monotonic()
    if ahora - _oculto[0] > 5.0:
        base = os.getenv("CUOTAS_RESPALDO_CACHE")
        _oculto[:] = [ahora, bool(base) and os.path.exists(os.path.join(os.path.dirname(base), ARCHIVO_OCULTAR))]
    return not _oculto[1]


class SinCupo(Exception):
    """429, 401/403 o saldo por debajo de la reserva: se termina la pasada con lo ya obtenido."""


def norm(texto) -> str:
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", t.replace("-", " "))).strip()


def mismo_jugador(a, b) -> bool:
    """«Carlos Alcaraz» y «Alcaraz C.»: mismo apellido y misma inicial (o nombre idéntico)."""
    na, nb = norm(a), norm(b)
    if na and na == nb:
        return True
    ta, tb = na.split(), nb.split()
    if len(ta) < 2 or len(tb) < 2:
        return False
    for (ia, ape_a) in ((ta[0][0], ta[-1]), (ta[-1][0], ta[0])):
        for (ib, ape_b) in ((tb[0][0], tb[-1]), (tb[-1][0], tb[0])):
            if ia == ib and ape_a == ape_b:
                return True
    return False


def americano_a_decimal(precio) -> float | None:
    """-110 -> 1.9091; +150 -> 2.5. `0.0001` (fuera del tablero), 0 y |p| < 100 no son cuotas: None."""
    try:
        p = float(precio)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(p) or abs(p) < 100:
        return None
    return round(1 + p / 100, 4) if p > 0 else round(1 + 100 / -p, 4)


# --- transporte -----------------------------------------------------------------------------------------------

def _transporte(key: str) -> Callable:
    def get(url: str):
        req = urllib.request.Request(url, headers={"X-TheRundown-Key": key, "User-Agent": "qf-cuotas"})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:  # noqa: S310 (host fijo)
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read()
    return get


class Cliente:
    """Una pasada: 1 petición por segundo, nunca archiva nada y se detiene al agotarse el cupo diario."""

    def __init__(self, key: str, *, call: Callable | None = None, reserva: int = RESERVA,
                 sleep: Callable = time.sleep, clock: Callable = time.monotonic):
        self.call = call or _transporte(key)
        self.reserva, self.sleep, self.clock = reserva, sleep, clock
        self.peticiones, self.puntos, self.restante = 0, 0, None
        self.agotado = False
        self._ultimo = None

    def get(self, ruta: str, params: dict | None = None):
        """Cuerpo JSON de la respuesta 200, o None. Lanza SinCupo si hay que parar."""
        if self.agotado:
            raise SinCupo("cupo agotado")
        if self.restante is not None and self.restante < self.reserva:
            self.agotado = True
            raise SinCupo(f"quedan {self.restante} puntos, bajo la reserva de {self.reserva}")
        if self._ultimo is not None and self.clock() - self._ultimo < PAUSA:
            self.sleep(PAUSA - (self.clock() - self._ultimo))
        q = "&".join(f"{k}={v}" for k, v in (params or {}).items())
        status, headers, body = self.call(f"{BASE}{ruta}" + (f"?{q}" if q else ""))
        self._ultimo = self.clock()
        self.peticiones += 1
        h = {str(k).lower(): v for k, v in (headers or {}).items()}
        for clave, destino in (("x-datapoints-remaining", "restante"),):
            try:
                setattr(self, destino, int(float(h[clave])))
            except (KeyError, TypeError, ValueError):
                pass
        try:
            self.puntos += int(float(h.get("x-datapoints", 0)))
        except (TypeError, ValueError):
            pass
        if status in (401, 403, 429):
            self.agotado = True
            raise SinCupo(f"HTTP {status}")
        if status != 200:
            return None
        try:
            return json.loads(body)
        except ValueError:
            return None

    def eventos(self, sport_id: int, fecha: str) -> list[dict]:
        doc = self.get(f"/sports/{sport_id}/events/{fecha}", {"market_ids": "1,2,3", "main_line": "true"})
        ev = doc.get("events") if isinstance(doc, dict) else None
        return [e for e in ev if isinstance(e, dict)] if isinstance(ev, list) else []


# --- lectura del evento -----------------------------------------------------------------------------------------

def _inicio(e: dict) -> datetime | None:
    try:
        return datetime.fromisoformat(str(e["event_date"]).replace("Z", "+00:00")).astimezone(timezone.utc)
    except (KeyError, ValueError):
        return None


def lineas(e: dict, market_id: int) -> list[dict]:
    """[{nombre, tipo, valor, precios: {casa: decimal}}] del mercado de partido completo; sin cuotas inválidas ni
    cerradas. `valor` es el float de la línea o None."""
    out = []
    for m in e.get("markets") or []:
        if m.get("market_id") != market_id or m.get("period_id", 0) != 0:
            continue
        for p in m.get("participants") or []:
            for l in p.get("lines") or []:
                precios = {}
                for aff, pr in (l.get("prices") or {}).items():
                    if not isinstance(pr, dict) or pr.get("closed_at"):
                        continue
                    dec = americano_a_decimal(pr.get("price"))
                    if dec is not None:
                        try:
                            precios[CASAS.get(int(aff), f"casa_{aff}")] = dec
                        except (TypeError, ValueError):
                            continue
                try:
                    valor = float(l["value"]) if l.get("value") not in (None, "") else None
                except (TypeError, ValueError):
                    continue
                out.append(dict(nombre=str(p.get("name") or ""), tipo=str(p.get("type") or ""), valor=valor,
                                precios=precios))
    return out


def nombres_ganador(e: dict) -> list[str]:
    return [l["nombre"] for l in lineas(e, 1) if l["tipo"] == "TYPE_TEAM"]


def busca_evento(eventos: list[dict], local: str, visitante: str, comienzo: datetime, *, tenis: bool,
                 resuelve: Callable | None = None):
    """Único evento cuyo ganador (mercado 1) tiene a los dos rivales y que empieza a +-3 h; si hay 0 o varios, None.
    Un evento sin mercado 1 (terminado, sin precios) no se puede emparejar y se ignora."""
    igual = mismo_jugador if tenis else (resuelve or (lambda a, b: norm(a) == norm(b)))
    buenos = []
    for e in eventos:
        ini = _inicio(e)
        if ini is None or abs(ini - comienzo) > TOLERANCIA:
            continue
        nombres = nombres_ganador(e)
        a = [n for n in nombres if igual(n, local)]
        b = [n for n in nombres if igual(n, visitante)]
        if len(a) == 1 and len(b) == 1 and a[0] != b[0]:
            buenos.append(e)
    return buenos[0] if len(buenos) == 1 else None


# --- filas para best_quote -----------------------------------------------------------------------------------------

def _fila(casa, nombre, lado, punto, precio):
    return dict(bookmaker=casa, name=nombre, side=lado, point=punto, price_decimal=precio, flags=[], period=None,
                dfs_odds_type=None, payout_multiplier=None)


def _es_linea(valor, linea) -> bool:
    """TheRundown solo da la línea principal de cada casa: una fila de otra línea no sirve para el ítem sellado y no
    se guarda (una entrada inútil marcaría el hueco como resuelto durante 24 h)."""
    return valor is not None and linea is not None and math.isclose(float(valor), float(linea), abs_tol=1e-9)


def filas_item(e: dict, deporte: str, item: dict, local: str, visitante: str) -> list[dict]:
    """Filas de un ítem sellado (winner / game_total / games_total / games_handicap) de NBA o tenis."""
    tenis = deporte == "tenis"
    igual = mismo_jugador if tenis else (lambda a, b: norm(a) == norm(b))
    lado_l, lado_v = ("A", "B") if tenis else ("home", "away")

    def lado_de(nombre):
        return lado_l if igual(nombre, local) else lado_v if igual(nombre, visitante) else None
    out = []
    mercado = item["market"]
    if mercado == "winner":
        for l in lineas(e, 1):
            lado = lado_de(l["nombre"]) if l["tipo"] == "TYPE_TEAM" else None
            if lado:
                out += [_fila(c, l["nombre"], lado, None, p) for c, p in l["precios"].items()]
    elif mercado in ("game_total", "games_total"):
        for l in lineas(e, 3):
            if l["valor"] is not None and norm(l["nombre"]) in ("over", "under") and _es_linea(l["valor"], item.get("line")):
                out += [_fila(c, l["nombre"], None, l["valor"], p) for c, p in l["precios"].items()]
    elif mercado == "games_handicap" and tenis:
        for l in lineas(e, 2):
            lado = lado_de(l["nombre"]) if l["tipo"] == "TYPE_TEAM" else None
            # La línea sellada y su opuesta (el otro jugador cotiza la línea con el signo cambiado).
            if lado and l["valor"] is not None and (_es_linea(l["valor"], item.get("line"))
                                                    or _es_linea(l["valor"], -item["line"] if item.get("line") is not None else None)):
                out += [_fila(c, l["nombre"], lado, l["valor"], p) for c, p in l["precios"].items()]
    return out


def filas_futbol(e: dict, home: str, away: str, resuelve: Callable | None = None) -> list[dict]:
    """Filas `{bookmaker, market, selection, line, price}` de fútbol con los nombres de `odds_snapshots`: 1X2 (el
    empate llega como un tercer participante), hándicap (`spreads`, línea con signo del propio equipo) y totales."""
    igual = resuelve or (lambda a, b: norm(a) == norm(b))
    filas = []

    def anade(mercado, seleccion, linea, precios):
        filas.extend(dict(bookmaker=c, market=mercado, selection=seleccion, line=linea, price=p)
                     for c, p in precios.items())
    for l in lineas(e, 1):
        if igual(l["nombre"], home):
            anade("h2h", "home", None, l["precios"])
        elif igual(l["nombre"], away):
            anade("h2h", "away", None, l["precios"])
        elif "draw" in norm(l["nombre"]) or l["nombre"].strip().lower() in ("x", "tie"):
            anade("h2h", "draw", None, l["precios"])
    for l in lineas(e, 2):
        if l["valor"] is None:
            continue
        if igual(l["nombre"], home):
            anade("spreads", "home", l["valor"], l["precios"])
        elif igual(l["nombre"], away):
            anade("spreads", "away", l["valor"], l["precios"])
    for l in lineas(e, 3):
        if l["valor"] is not None and norm(l["nombre"]) in ("over", "under"):
            anade("totals", norm(l["nombre"]), l["valor"], l["precios"])
    return filas
