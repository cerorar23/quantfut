"""Cuotas históricas de NBA que ya existen en archivos (sin créditos nuevos):

* BetsAPI / bet365: ganador, hándicap y total del partido, de la 1.ª mitad y del 1.er cuarto, con la trayectoria completa
  (`path`: segundos antes del salto, línea, cuota local/over, cuota visitante/under). 3 temporadas.
* The Odds API, props de jugador ya enlazadas (puntos, rebotes, triples, asistencias; ~1 foto 45 min antes del salto).
* The Odds API, moneyline de ~325 instantáneas (2024-25 y 2025-26).

`nba.cuota.recibido_en` es el instante en que la casa mostró el precio (no el de la descarga); la descarga queda en
`nba.captura` con fase `historico` y el hash del archivo. Los nombres de mercado coinciden con los del archivo de PropLine.
"""
from collections.abc import Iterable, Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from .. import carga, equipos, identidad
from ..carga import CuotaNueva

ET = ZoneInfo("America/New_York")
CIERRE = timedelta(minutes=60)
PERIODO = {"game": 0, "h1": 101, "q1": 1}
MERCADO = {"moneyline": "h2h", "spread": "spreads", "total": "totals"}
CASAS_H2H = frozenset({"pinnacle", "draftkings", "fanduel", "betmgm"})
MERCADOS_PROPS = frozenset({"player_points", "player_rebounds", "player_threes", "player_assists"})
NOMBRES = {nombre: codigo for codigo, nombre in equipos.TRICODES.items()} | {"Los Angeles Clippers": "LAC"}


def _abrir(ruta: Path):
    return gzip.open(ruta, "rt", encoding="utf8") if str(ruta).endswith(".gz") else open(ruta, encoding="utf8")


def _huella(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def _dec(x) -> Decimal | None:
    return None if x is None else Decimal(str(x))


def _fase(antes: timedelta) -> str:
    return "cierre" if antes <= CIERRE else "pre"


def _captura(db, ruta: Path, nombre: str) -> int:
    existente = db.execute("SELECT captura_id FROM nba.captura WHERE fuente = %s AND objetivo = %s AND ok",
                           (nombre.split(":")[0], nombre)).fetchone()
    if existente:
        return existente[0]
    adquirido = datetime.fromtimestamp(ruta.stat().st_mtime, UTC)
    fuente = {"betsapi": "betsapi", "oddsapi_props": "the_odds_api", "oddsapi_h2h": "the_odds_api"}[nombre.split(":")[0]]
    return carga.registrar_captura(db, fuente=fuente, objetivo=nombre, fase="historico", solicitado_en=adquirido, ok=True,
                                   recibido_en=adquirido, sha256=_huella(ruta), bytes_=ruta.stat().st_size, ruta=str(ruta.name))


def _lotes(filas: Iterator[CuotaNueva], tam: int = 5000) -> Iterator[list[CuotaNueva]]:
    lote = []
    for f in filas:
        lote.append(f)
        if len(lote) >= tam:
            yield lote
            lote = []
    if lote:
        yield lote


def _cargar(db, filas: Iterator[CuotaNueva]) -> dict:
    leidas = nuevas = 0
    for lote in _lotes(filas):
        leidas += len(lote)
        nuevas += carga.guardar_cuotas_lote(db, lote)
        db.commit()
    return {"ok": True, "leidas": leidas, "nuevas": nuevas}


# ── BetsAPI / bet365 ──────────────────────────────────────────────────────────────────────────────────────────────────
def filas_betsapi(db, r: dict, captura: int, cache: dict) -> Iterator[CuotaNueva]:
    """Un registro de BetsAPI → una cuota por tick y lado. p1 = local / over; p2 = visitante / under."""
    local, visitante = (equipos.NBA_IDS[r[k]] for k in ("home_team_id", "away_team_id"))
    fecha = date.fromisoformat(r["date"])
    clave = (r["game_id"], local, visitante)
    if clave not in cache:
        cache[clave] = identidad.partido(db, "nba_oficial", r["game_id"], fecha, identidad.equipo(db, local),
                                         identidad.equipo(db, visitante), identidad.temporada(fecha))
    partido = cache[clave]
    tip = datetime.fromisoformat(r["tip_utc"])
    mercado, periodo = MERCADO[r["kind"]], PERIODO[r["period"]]
    contrato = f"betsapi:{r['event_id']}:{r['market']}"
    ticks = r.get("path") or [[r[k]["seconds_before_tip"], r[k]["line"], r[k]["p1"], r[k]["p2"]] for k in ("open", "close")]
    lados = ("local", "visit") if r["kind"] != "total" else ("over", "under")
    for segundos, linea, p1, p2 in ticks:
        if p1 is None or p2 is None or p1 <= 1 or p2 <= 1:
            continue
        instante = tip - timedelta(seconds=segundos)
        base = dict(partido_id=partido, fuente="betsapi", casa="bet365", mercado=mercado, contrato_id=contrato,
                    fase=_fase(timedelta(seconds=segundos)), recibido_en=instante, periodo=periodo, captura_id=captura)
        if r["kind"] == "spread":
            lineas = (_dec(linea), -_dec(linea) if linea is not None else None)
        else:
            lineas = (_dec(linea), _dec(linea))
        for lado, precio, ln in zip(lados, (p1, p2), lineas):
            yield CuotaNueva(lado=lado, cuota=Decimal(str(precio)).quantize(Decimal("0.001")), linea=ln, **base)


def cargar_betsapi(db, ruta: Path) -> dict:
    captura = _captura(db, ruta, f"betsapi:{ruta.name}")
    cache: dict = {}

    def generar():
        with _abrir(ruta) as f:
            for linea in f:
                yield from filas_betsapi(db, json.loads(linea), captura, cache)

    return _cargar(db, generar())


# ── The Odds API: props de jugador ya enlazadas ───────────────────────────────────────────────────────────────────────
def filas_props(db, r: dict, captura: int, cache: dict) -> Iterator[CuotaNueva]:
    if r["market"] not in MERCADOS_PROPS or r.get("player_id") is None or r.get("over") is None or r.get("under") is None:
        return
    if r["over"] <= 1 or r["under"] <= 1:  # precio no válido (en los datos aparece alguna cuota 1.000)
        return
    if r["game_id"] not in cache:
        fila = db.execute("SELECT canonica_id FROM nba.entidad WHERE fuente = 'nba_oficial' AND tipo = 'partido' "
                          "AND id_en_fuente = %s", (r["game_id"],)).fetchone()
        cache[r["game_id"]] = fila[0] if fila else None
    partido = cache[r["game_id"]]
    if partido is None:
        return
    jugador = cache.get(("j", r["player_id"])) or cache.setdefault(
        ("j", r["player_id"]), identidad.jugador(db, "nba_oficial", str(r["player_id"]), r["player"]))
    instante = datetime.fromisoformat(r["snapshot_utc"])
    base = dict(partido_id=partido, fuente="the_odds_api", casa=r["book"], mercado=r["market"], fase=_fase(
        timedelta(minutes=r["minutes_to_tipoff"])), recibido_en=instante, entidad_id=jugador, linea=_dec(r["line"]),
        contrato_id=f"{r['game_id']}|{r['market']}||main|{jugador}|{_dec(r['line'])}", captura_id=captura)
    for lado, precio in (("over", r["over"]), ("under", r["under"])):
        yield CuotaNueva(lado=lado, cuota=Decimal(str(precio)).quantize(Decimal("0.001")), **base)


def cargar_props(db, ruta: Path) -> dict:
    captura = _captura(db, ruta, f"oddsapi_props:{ruta.name}")
    cache: dict = {}

    def generar():
        with _abrir(ruta) as f:
            for linea in f:
                yield from filas_props(db, json.loads(linea), captura, cache)

    return _cargar(db, generar())


# ── The Odds API: moneyline ───────────────────────────────────────────────────────────────────────────────────────────
def filas_h2h(db, d: dict, captura: int) -> Iterator[CuotaNueva]:
    instante = datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00"))
    for e in d["data"]:
        if e["home_team"] not in NOMBRES or e["away_team"] not in NOMBRES:
            continue
        inicio = datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00"))
        if inicio <= instante:
            continue
        fecha = inicio.astimezone(ET).date()
        local, visitante = NOMBRES[e["home_team"]], NOMBRES[e["away_team"]]
        partido = identidad.partido(db, "the_odds_api", e["id"], fecha, identidad.equipo(db, local),
                                    identidad.equipo(db, visitante), identidad.temporada(fecha))
        for b in e["bookmakers"]:
            if b["key"] not in CASAS_H2H:
                continue
            for m in b["markets"]:
                if m["key"] != "h2h":
                    continue
                for o in m["outcomes"]:
                    lado = "local" if o["name"] == e["home_team"] else "visit" if o["name"] == e["away_team"] else None
                    if lado and o.get("price") and o["price"] > 1:
                        yield CuotaNueva(partido_id=partido, fuente="the_odds_api", casa=b["key"], mercado="h2h", lado=lado,
                                         cuota=Decimal(str(o["price"])).quantize(Decimal("0.001")),
                                         contrato_id=f"oddsapi:{e['id']}:h2h", fase=_fase(inicio - instante),
                                         recibido_en=instante, captura_id=captura)


def cargar_h2h(db, carpeta: Path) -> dict:
    total = {"ok": True, "leidas": 0, "nuevas": 0, "archivos": 0}
    for ruta in sorted(carpeta.glob("20*.json")):
        captura = _captura(db, ruta, f"oddsapi_h2h:{ruta.name}")
        r = _cargar(db, filas_h2h(db, json.loads(ruta.read_text(encoding="utf8")), captura))
        total["leidas"] += r["leidas"]
        total["nuevas"] += r["nuevas"]
        total["archivos"] += 1
    return total


def cargar_juegos(db, ruta: Path) -> dict:
    """Catálogo de partidos (id de la NBA, fecha ET, local y visitante) para unir cuotas y resultados de temporadas pasadas."""
    juegos = json.loads(ruta.read_text(encoding="utf8"))
    juegos = list(juegos.values()) if isinstance(juegos, dict) else juegos
    for g in juegos:
        fecha = date.fromisoformat(g["date"])
        local, visitante = equipos.NBA_IDS[g["home"]["team_id"]], equipos.NBA_IDS[g["away"]["team_id"]]
        identidad.partido(db, "nba_oficial", g["game_id"], fecha, identidad.equipo(db, local), identidad.equipo(db, visitante),
                          identidad.temporada(fecha))
    db.commit()
    return {"ok": True, "juegos": len(juegos)}
