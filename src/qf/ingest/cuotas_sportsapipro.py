"""Tercer nivel del respaldo de cuotas: SportsAPIPro (SofaScore), cuando PropLine y The Odds API no la tienen.

Decisión del titular (9-nov-2026): cascada PropLine -> The Odds API -> SportsAPIPro para NBA, tenis y fútbol.
Este módulo es el cliente y el traductor del último escalón; la orquestación vive en `cuotas_respaldo`.

Qué es SportsAPIPro y qué NO es (medido el 9-nov-2026 con el plan gratuito):
  * Una sola casa (la del proveedor de SofaScore, `odds/1`), cuotas fraccionarias, SOLO prepartido y SOLO el precio
    de ahora: no hay histórico ni cierre. Por eso su recepción siempre es POSTERIOR al sello y la entrada se marca
    `post_sello`: se muestra como referencia con su hora real, pero la regla de publicación la ignora.
  * Mercados verificados con respuestas reales del 9-nov-2026: ganador (`marketId` 1, choices «1»/«2», y «X» en
    fútbol), tenis «Total games won» (`marketId` 12), baloncesto «Game total» (`marketId` 18, línea en `choiceGroup`),
    y en fútbol «Match goals» (una entrada por línea), «Both teams to score», «Double chance» y «Corners 2-Way».
    SportsAPIPro también trae hándicap («Point spread», «Asian handicap») con el equipo dentro del nombre de la
    opción; no se traduce todavía. Sin props de jugador.
  * Plan gratuito: 100 peticiones al día compartidas con el once de fútbol y tenis. `x-ratelimit-remaining` y los
    429 paran la pasada; el tope propio es `CUOTAS_SPORTSAPIPRO_DIARIO` (0 = sin tope, la decisión actual).

Los originales se archivan con su recepción real en `<artifact_dir>/sportsapipro_cuotas` (índice aparte de el del
once, para no gastar las 40 peticiones diarias del once de fútbol en los recibos).
"""
from __future__ import annotations

import json
import logging
import re
import unicodedata
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


log = logging.getLogger(__name__)
API = "https://api.sportsapipro.com/v2"
CASA = "sofascore"                      # la única casa que devuelve; la etiqueta que ve el overlay
TOLERANCIA = timedelta(minutes=30)
NY = ZoneInfo("America/New_York")       # SportsAPIPro agrupa el calendario por día de Nueva York

TOTAL_BALONCESTO = {"game total", "total", "total points", "points total", "match total", "full game total"}
TOTAL_FUTBOL = {"match goals", "total goals", "goals over/under", "goals"}


def _sp():
    """Módulo del once de fútbol (cliente HTTP e índice de recibos). Import perezoso: arrastra la base de datos y la
    API web importa `cuotas_respaldo` solo para leer la caché; un fallo aquí no puede tumbar la API."""
    from qf.ingest import sportsapipro_alineaciones as sp
    return sp


class SinCupo(Exception):
    """429 o `x-ratelimit-remaining` en 0: se termina la pasada con lo ya obtenido."""


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
    # SofaScore pone a veces el apellido primero: se prueban las dos lecturas y se exige coincidencia exacta.
    for (ia, ape_a) in ((ta[0][0], ta[-1]), (ta[-1][0], ta[0])):
        for (ib, ape_b) in ((tb[0][0], tb[-1]), (tb[-1][0], tb[0])):
            if ia == ib and ape_a == ape_b:
                return True
    return False


def fraccion_a_decimal(texto) -> float | None:
    """«7/4» -> 2.75; «EVS» -> 2.0; un decimal ya válido se acepta. Fuera de rango o ilegible: None."""
    t = str(texto or "").strip().upper()
    try:
        if t in ("EVS", "EVENS"):
            valor = 2.0
        elif "/" in t:
            num, den = t.split("/", 1)
            valor = 1.0 + float(num) / float(den)
        else:
            valor = float(t)
    except (ValueError, ZeroDivisionError):
        return None
    return round(valor, 4) if valor > 1.0 and valor == valor and valor != float("inf") else None


# --- transporte -------------------------------------------------------------------------------------------

def _transporte(key: str) -> Callable:
    def get(url: str):
        status, body = _sp().http(url, key)
        return status, body
    return get


class Cliente:
    """Una pasada: cuenta peticiones, archiva cada respuesta y se detiene en cuanto el cupo se agota."""

    def __init__(self, key: str, *, call: Callable | None = None, clock: Callable | None = None,
                 raiz: Path | None = None, tope: int = 0, usadas_hoy: int = 0):
        self.call = call or _transporte(key)
        self.clock = clock or _sp().now
        self.raiz = raiz
        self.db = _sp().abrir(raiz) if raiz is not None else None
        self.tope = tope            # 0 = sin tope propio
        self.peticiones = 0
        self.previas = usadas_hoy
        self.agotado = False

    def usadas_hoy(self) -> int:
        if self.db is None:
            return self.previas + self.peticiones
        return _sp().usadas_hoy(self.db, self.clock())

    def get(self, ruta: str, kind: str, ref: str):
        if self.agotado:
            raise SinCupo("cupo agotado")
        if self.tope and self.usadas_hoy() >= self.tope:
            self.agotado = True
            raise SinCupo(f"tope diario propio ({self.tope})")
        status, body = self.call(f"{API}/{ruta}")
        recibido = self.clock()
        self.peticiones += 1
        if self.db is not None:
            _sp().archivar(self.raiz, self.db, kind, ref, status, body, recibido)
        if status == 429:
            self.agotado = True
            raise SinCupo("429 del proveedor")
        if status != 200:
            return recibido, None
        try:
            return recibido, json.loads(body)
        except ValueError:
            return recibido, None


# --- calendario y emparejamiento --------------------------------------------------------------------------------

def fechas_calendario(comienzo: datetime) -> list[str]:
    """Día de Nueva York del partido (SportsAPIPro agrupa por él), más el vecino por si el corte cae cerca."""
    d = comienzo.astimezone(NY).date()
    return [d.isoformat(), (d + timedelta(days=1)).isoformat(), (d - timedelta(days=1)).isoformat()]


def _eventos_de(doc) -> list[dict]:
    """El calendario trae la lista de partidos en `events` (o dentro de `data`)."""
    if isinstance(doc, dict):
        for k in ("events", "data"):
            v = doc.get(k)
            if isinstance(v, list):
                return [e for e in v if isinstance(e, dict)]
            if isinstance(v, dict) and isinstance(v.get("events"), list):
                return [e for e in v["events"] if isinstance(e, dict)]
    return []


def busca_evento(eventos: list[dict], local: str, visitante: str, comienzo: datetime, *, tenis: bool):
    """Único evento con los mismos rivales y comienzo a +-30 min; si hay 0 o varios, None (no se adivina)."""
    iguales = mismo_jugador if tenis else (lambda a, b: norm(a) == norm(b))
    buenos = []
    for e in eventos:
        try:
            h, a = e["homeTeam"]["name"], e["awayTeam"]["name"]
            ts = datetime.fromtimestamp(int(e["startTimestamp"]), timezone.utc)
        except (KeyError, TypeError, ValueError):
            continue
        if abs(ts - comienzo) > TOLERANCIA:
            continue
        # Orden directo; en tenis SofaScore puede invertir local/visitante respecto del sello.
        if (iguales(h, local) and iguales(a, visitante)) or (tenis and iguales(h, visitante) and iguales(a, local)):
            buenos.append((e, not (iguales(h, local) and iguales(a, visitante))))
    return buenos[0] if len(buenos) == 1 else None   # (evento, invertido)


# --- traducción de mercados -----------------------------------------------------------------------------------

def mercados(doc) -> list[dict]:
    """Mercados del cuerpo de `odds/pre-match`, ya con decimales: [{id, nombre, grupo, periodo, linea, choices}]."""
    data = doc.get("data") if isinstance(doc, dict) else None
    out = []
    for m in (data or {}).get("markets") or []:
        if not isinstance(m, dict) or m.get("isLive") or m.get("suspended"):
            continue
        choices = []
        for c in m.get("choices") or []:
            precio = fraccion_a_decimal(c.get("fractionalValue"))
            if precio is not None and c.get("name") is not None:
                choices.append(dict(name=str(c["name"]), price=precio))
        linea = m.get("choiceGroup")
        try:
            linea = float(linea) if linea not in (None, "") else None
        except (TypeError, ValueError):
            linea = None
        out.append(dict(id=m.get("marketId"), nombre=str(m.get("marketName") or ""),
                        grupo=str(m.get("marketGroup") or ""), periodo=str(m.get("marketPeriod") or ""),
                        linea=linea, choices=choices))
    return out


def _ganador(ms: list[dict], con_empate: bool = False):
    """Precios {«1»,«2»[,«X»]} del mercado `marketId` 1 («Full time»), o None si falta algún lado."""
    claves = {"1", "X", "2"} if con_empate else {"1", "2"}
    for m in ms:
        if m["id"] != 1:
            continue
        nombres = {c["name"].strip().upper(): c["price"] for c in m["choices"]}
        if claves <= set(nombres):
            return nombres
    return None


def _periodo_completo(m: dict) -> bool:
    """Partido completo: «Match» (baloncesto, tenis) o «Full-time» (fútbol, con guion; visto el 9-nov-2026)."""
    return m["periodo"].lower().replace("-", " ").strip() in ("", "match", "full time", "full game")


def _es_total(m: dict, deporte: str) -> bool:
    n = m["nombre"].strip().lower()
    if deporte == "tenis":
        return m["id"] == 12 or n == "total games won"
    if deporte == "nba":
        return n in TOTAL_BALONCESTO and _periodo_completo(m)
    return n in TOTAL_FUTBOL and _periodo_completo(m)


def filas_futbol(ms: list[dict]) -> list[dict]:
    """Filas `{bookmaker, market, selection, line, price}` de fútbol, con los nombres de `odds_snapshots`:
    1X2 (`h2h`), totales de goles, ambos marcan (`btts`), doble oportunidad y córners totales. Verificados con una
    respuesta real (FA Cup, 9-nov-2026). El hándicap asiático se ignora: viene como «(-0.5) Equipo» y el signo
    depende del equipo, que aquí no se conoce."""
    filas = []

    def anade(mercado, seleccion, linea, precio):
        filas.append(dict(bookmaker=CASA, market=mercado, selection=seleccion, line=linea, price=precio))
    g = _ganador(ms, con_empate=True)
    if g:
        for sel, k in (("home", "1"), ("draw", "X"), ("away", "2")):
            anade("h2h", sel, None, g[k])
    for m in ms:
        if not _periodo_completo(m):
            continue
        nombres = {c["name"].strip().upper(): c["price"] for c in m["choices"]}
        if _es_total(m, "futbol") and m["linea"] is not None:
            for c in m["choices"]:
                if c["name"].strip().lower() in ("over", "under"):
                    anade("totals", c["name"].strip().lower(), m["linea"], c["price"])
        elif m["nombre"].strip().lower() == "both teams to score" and {"YES", "NO"} <= set(nombres):
            anade("btts", "yes", None, nombres["YES"])
            anade("btts", "no", None, nombres["NO"])
        elif m["nombre"].strip().lower() == "double chance" and {"1X", "X2", "12"} <= set(nombres):
            for k in ("1X", "X2", "12"):
                anade("double_chance", k, None, nombres[k])
        elif m["nombre"].strip().lower() == "corners 2-way" and m["linea"] is not None:
            for c in m["choices"]:
                if c["name"].strip().lower() in ("over", "under"):
                    anade("corners", c["name"].strip().lower(), m["linea"], c["price"])
    return filas


def filas_item(ms: list[dict], deporte: str, item: dict, local: str, visitante: str, invertido: bool = False) -> list[dict]:
    """Filas en el formato de `best_quote` para un ítem (winner / game_total / games_total), o [] si no hay."""
    def fila(nombre, lado, punto, precio):
        return dict(bookmaker=CASA, name=nombre, side=lado, point=punto, price_decimal=precio, flags=[], period=None,
                    dfs_odds_type=None, payout_multiplier=None)
    mercado = item["market"]
    if mercado == "winner":
        g = _ganador(ms)
        if not g:
            return []
        # «1» es el local DE SOFASCORE: si el evento viene invertido respecto del sello, su «1» es nuestro visitante.
        p_local, p_visit = (g["2"], g["1"]) if invertido else (g["1"], g["2"])
        lado_l, lado_v = ("A", "B") if deporte == "tenis" else ("home", "away")
        return [fila(local, lado_l, None, p_local), fila(visitante, lado_v, None, p_visit)]
    if mercado in ("game_total", "games_total"):
        out = []
        for m in ms:
            if not _es_total(m, deporte) or m["linea"] is None:
                continue
            if item.get("line") is not None and abs(m["linea"] - float(item["line"])) > 1e-9:
                continue    # otra línea: no sirve para el ítem sellado y no se guarda
            for c in m["choices"]:
                if c["name"].strip().lower() in ("over", "under"):
                    out.append(fila(c["name"], None, m["linea"], c["price"]))
        return out
    return []
