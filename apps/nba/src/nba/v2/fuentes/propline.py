"""Cuotas de PropLine desde el archivo horario compartido (solo lectura; cero peticiones al proveedor).

El archivo lo escribe el recolector de `~/propline-shared`: un índice SQLite (`requests`/`receipts`) y los cuerpos
originales comprimidos por hash en `objects/`. Aquí se leen los recibos NBA con estado 200, se verifica su hash y se
cargan a `nba.cuota` las casas y mercados útiles, solo cuando cambia el precio.
"""
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
import gzip
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from zoneinfo import ZoneInfo

from .. import carga, equipos, identidad
from ..carga import CuotaNueva

FUENTE = "propline"
ET = ZoneInfo("America/New_York")
RUTA_NBA = "/v1/sports/basketball_nba/odds"
CASAS = frozenset({"pinnacle", "draftkings", "fanduel", "betmgm"})
LINEAS = frozenset({"main", "alternate"})      # los «milestone» (10+ puntos) quedan fuera: derivan de las alternativas
PERIODOS = {None: 0, "q1": 1, "q2": 2, "q3": 3, "q4": 4, "h1": 101, "h2": 102}
JUGADOR = frozenset({"player_points", "player_rebounds", "player_assists", "player_threes", "player_steals",
                     "player_blocks", "player_points_rebounds_assists", "player_points_rebounds",
                     "player_points_assists", "player_rebounds_assists"})
ESPECIALES = {"player_double_double": "si", "player_triple_double": "si", "player_first_basket": "primero"}
HORIZONTE = timedelta(hours=48)
CIERRE = timedelta(minutes=60)
NOMBRES = {nombre: codigo for codigo, nombre in equipos.TRICODES.items()} | {"Los Angeles Clippers": "LAC"}


def decimal(americano: int) -> Decimal:
    """Cuota americana → decimal (3 decimales)."""
    d = Decimal(1) + (Decimal(americano) / 100 if americano > 0 else Decimal(100) / abs(americano))
    return d.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def _num(x) -> Decimal | None:
    return None if x is None else Decimal(str(x))


def _tiempo(texto: str) -> datetime:
    return datetime.fromisoformat(texto.replace("Z", "+00:00"))


@dataclass
class Contexto:
    """Caché de una pasada: ids de jugadores y equipos ya resueltos."""
    db: object
    jugadores: dict
    equipos_: dict


def _equipo(ctx: Contexto, nombre: str) -> int:
    if nombre not in ctx.equipos_:
        ctx.equipos_[nombre] = identidad.equipo(ctx.db, NOMBRES[nombre])
    return ctx.equipos_[nombre]


def _jugador(ctx: Contexto, player_id: str, nombre: str) -> int | None:
    if not player_id or not player_id.startswith("nba:"):
        return None
    if player_id not in ctx.jugadores:
        limpio = re.sub(r"\s*\([A-Z]{2,3}\)$", "", nombre).strip()
        ctx.jugadores[player_id] = identidad.jugador(ctx.db, "nba_oficial", player_id.split(":", 1)[1], limpio)
    return ctx.jugadores[player_id]


def filas_evento(ctx: Contexto, evento: dict, recibido_en: datetime, captura_id: int | None):
    """(partido_id, filas de CuotaNueva) de un evento; None si no es un partido previo útil."""
    inicio = _tiempo(evento["commence_time"])
    antes = inicio - recibido_en
    if evento.get("live") or evento.get("is_outright") or antes <= timedelta(0) or antes > HORIZONTE:
        return None
    if evento["home_team"] not in NOMBRES or evento["away_team"] not in NOMBRES:
        return None
    fecha = inicio.astimezone(ET).date()
    partido = identidad.partido(ctx.db, FUENTE, str(evento["id"]), fecha, _equipo(ctx, evento["home_team"]),
                                _equipo(ctx, evento["away_team"]), identidad.temporada(fecha))
    fase = "cierre" if antes <= CIERRE else "pre"
    filas = []
    for casa in evento.get("bookmakers", []):
        if casa["key"] not in CASAS:
            continue
        for m in casa["markets"]:
            clave, tipo = m["key"], m.get("line_type")
            periodo = PERIODOS.get(m.get("period"), None) if m.get("period") in PERIODOS else None
            if tipo not in LINEAS or (periodo is None and m.get("period") is not None):
                continue
            equipo_total = m.get("team") if clave == "totals" else None
            if equipo_total is not None and equipo_total not in NOMBRES:
                continue
            mercado = "team_totals" if equipo_total else clave
            if mercado not in {"h2h", "spreads", "totals", "team_totals"} | JUGADOR | set(ESPECIALES):
                continue
            for o in m["outcomes"]:
                precio = o.get("price")
                if not precio:
                    continue
                entidad = None
                if clave in JUGADOR or clave in ESPECIALES:
                    entidad = _jugador(ctx, o.get("player_id"), o.get("description") or o.get("name"))
                    if entidad is None:
                        continue
                elif equipo_total:
                    entidad = _equipo(ctx, equipo_total)
                if clave in ("h2h", "spreads"):
                    lado = {"home": "local", "away": "visit"}.get(o.get("side"))
                elif clave in ESPECIALES:
                    lado = ESPECIALES[clave]
                else:
                    lado = {"over": "over", "under": "under"}.get(str(o.get("name")).lower())
                if lado is None:
                    continue
                punto = _num(o.get("point"))
                contrato = "|".join([str(evento["id"]), mercado, str(m.get("period") or ""), tipo,
                                     str(entidad or ""), str(punto) if tipo == "alternate" else ""])
                filas.append(CuotaNueva(partido_id=partido, fuente=FUENTE, casa=casa["key"], mercado=mercado, lado=lado,
                                        cuota=decimal(int(precio)), contrato_id=contrato, fase=fase,
                                        recibido_en=recibido_en, periodo=periodo or 0, entidad_id=entidad,
                                        linea=punto, captura_id=captura_id))
    return partido, filas


def _solo_cambios(db, partido: int, filas: list[CuotaNueva]) -> list[CuotaNueva]:
    ultimas = {(c, k, l, f): (cu, li) for c, k, l, f, cu, li in db.execute(
        "SELECT DISTINCT ON (casa, contrato_id, lado, fase) casa, contrato_id, lado, fase, cuota, linea FROM nba.cuota "
        "WHERE partido_id = %s AND fuente = %s ORDER BY casa, contrato_id, lado, fase, recibido_en DESC, cuota_id DESC",
        (partido, FUENTE))}
    return [f for f in filas if ultimas.get((f.casa, f.contrato_id, f.lado, f.fase)) != (f.cuota, f.linea)]


def cargar_lote(db, ctx: Contexto, eventos: list[dict], recibido_en: datetime, captura_id: int | None) -> dict:
    nuevas, vistos = 0, 0
    for e in eventos:
        r = filas_evento(ctx, e, recibido_en, captura_id)
        if r is None:
            continue
        partido, filas = r
        vistos += len(filas)
        nuevas += carga.guardar_cuotas(db, _solo_cambios(db, partido, filas))
    return {"leidas": vistos, "nuevas": nuevas}


def capturar(db, raiz_archivo: Path, ahora: datetime, max_lotes: int = 40, desde_id: int | None = None) -> dict:
    """Carga los recibos NBA nuevos del archivo. Sin captura previa y sin `desde_id`, empieza por el último slot."""
    indice = sqlite3.connect(f"{(raiz_archivo / 'index.sqlite').resolve().as_uri()}?mode=ro", uri=True)
    try:
        if desde_id is None:
            previo = db.execute("SELECT max(substring(objetivo from 'propline:(\\d+)')::bigint) FROM nba.captura "
                                "WHERE fuente = %s AND objetivo LIKE 'propline:%%'", (FUENTE,)).fetchone()[0]
            if previo is None:
                ultimo = indice.execute("SELECT max(q.slot) FROM requests q JOIN receipts r ON r.request_id = q.id "
                                        "WHERE q.path = ? AND r.status = 200", (RUTA_NBA,)).fetchone()[0]
                fila = indice.execute("SELECT min(q.id) FROM requests q WHERE q.slot = ? AND q.path = ?",
                                      (ultimo, RUTA_NBA)).fetchone() if ultimo else (None,)
                previo = (fila[0] - 1) if fila[0] else 0
            desde_id = previo
        lotes = indice.execute(
            "SELECT q.id, r.received_at, r.sha256, r.body_path FROM requests q JOIN receipts r ON r.request_id = q.id "
            "WHERE q.path = ? AND r.status = 200 AND q.id > ? ORDER BY q.id LIMIT ?", (RUTA_NBA, desde_id, max_lotes)).fetchall()
    finally:
        indice.close()
    ctx = Contexto(db, {}, {})
    resumen = {"ok": True, "lotes": 0, "leidas": 0, "nuevas": 0, "fallidos": 0, "ultimo_id": desde_id}
    for rid, recibido, sha, ruta in lotes:
        recibido_en = datetime.fromisoformat(recibido)
        objetivo = f"propline:{rid}"
        try:
            cuerpo = gzip.open(raiz_archivo / ruta).read()
            if hashlib.sha256(cuerpo).hexdigest() != sha:
                raise ValueError("el hash del objeto no coincide con el recibo")
            eventos = json.loads(cuerpo)
            if not isinstance(eventos, list):
                raise ValueError("el cuerpo no es una lista de eventos")
        except (OSError, ValueError) as e:
            carga.registrar_captura(db, fuente=FUENTE, objetivo=objetivo, fase="pre", solicitado_en=recibido_en, ok=False,
                                    recibido_en=recibido_en, http_status=200, sha256=sha, ruta=ruta, error=str(e)[:300])
            resumen["fallidos"] += 1
            resumen["ok"] = False
            resumen["ultimo_id"] = rid
            db.commit()
            continue
        captura = carga.registrar_captura(db, fuente=FUENTE, objetivo=objetivo, fase="pre", solicitado_en=recibido_en,
                                          ok=True, recibido_en=recibido_en, http_status=200, sha256=sha, bytes_=len(cuerpo),
                                          ruta=ruta)
        r = cargar_lote(db, ctx, eventos, recibido_en, captura)
        resumen["lotes"] += 1
        resumen["leidas"] += r["leidas"]
        resumen["nuevas"] += r["nuevas"]
        resumen["ultimo_id"] = rid
        db.commit()
    return resumen
