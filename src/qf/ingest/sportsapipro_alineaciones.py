"""Huecos de once y bajas de fútbol: SportsAPIPro (SofaScore, mismos ids) solo cuando FotMob no llegó.

Desde el 31-oct-2026 el once y las bajas llegan de FotMob (`fotmob_alineaciones`); medido en 173 partidos, FotMob
tiene el once oficial antes del saque en el 81 % y SofaScore en el 86 % (juntos 93 %). Este módulo cubre el resto
sin pagar: SportsAPIPro tiene un plan gratuito de 100 peticiones al día para todos los deportes.

Qué hace, cada pocos minutos y SIN peticiones si no hay hueco:
  * Hueco = partido programado de una liga activa que empieza entre 15 y 45 min y aún no tiene `lineups` de los dos lados.
  * Cada hueco se consulta como mucho 2 veces, con 7 min de separación, y como mucho 40 peticiones al día en total.
  * Calendario del día (`/schedule/{fecha}`, 3 fechas porque SportsAPIPro agrupa por día de Nueva York) cada 6 h como
    mucho, y solo si hace falta para encontrar el id del partido; archivado en `artifact_dir/sportsapipro`.
  * Con el id se pide `/api/match/{id}/lineups` y se carga con `sofascore_carga.aplicar` (misma estructura,
    `source = 'sofascore'`, ids de SofaScore): escribe `injuries`, `lineups_previstas` y `lineups` si es oficial.

La clave va en `SPORTSAPIPRO_KEY` (entorno del worker). Con el User-Agent de urllib Cloudflare responde 403 (error 1010).
"""
from __future__ import annotations

import gzip
import hashlib
import json
import logging
import os
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..db import conn, query
from .salud import record_health
from .sofascore_carga import LIGA_DE_TORNEO, aplicar, emparejar

log = logging.getLogger(__name__)

API = "https://api.sportsapipro.com/v2/football"
HEADERS = {"User-Agent": "Mozilla/5.0 qf-futbol"}
UTC = timezone.utc
LOCK_ID = 61031091
DIARIO = 40                       # peticiones al día de las 100 gratuitas; el resto queda para tenis
INTENTOS = 2
ESPERA = timedelta(minutes=7)
VENTANA = (timedelta(minutes=15), timedelta(minutes=45))
CALENDARIO_CADA = timedelta(hours=6)


def now():
    return datetime.now(UTC)


def carpeta() -> Path:
    from ..config import settings
    return Path(settings.artifact_dir) / "sportsapipro"


def http(url, key, timeout=60):
    req = urllib.request.Request(url, headers={**HEADERS, "x-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def abrir(raiz: Path) -> sqlite3.Connection:
    raiz.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(raiz / "index.sqlite", timeout=30)
    db.row_factory = sqlite3.Row
    db.executescript("""
      CREATE TABLE IF NOT EXISTS receipts (
        id INTEGER PRIMARY KEY, received_at TEXT NOT NULL, kind TEXT NOT NULL, ref TEXT NOT NULL,
        status INTEGER NOT NULL, sha256 TEXT NOT NULL, body_path TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS eventos (
        id INTEGER PRIMARY KEY, utid INTEGER NOT NULL, start_ts INTEGER NOT NULL, home TEXT NOT NULL,
        away TEXT NOT NULL, visto TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS intentos (match_id TEXT PRIMARY KEY, n INTEGER NOT NULL, ultimo TEXT NOT NULL);
      CREATE TRIGGER IF NOT EXISTS inmutable_receipts_u BEFORE UPDATE ON receipts
        BEGIN SELECT RAISE(ABORT,'immutable receipt'); END;
      CREATE TRIGGER IF NOT EXISTS inmutable_receipts_d BEFORE DELETE ON receipts
        BEGIN SELECT RAISE(ABORT,'immutable receipt'); END;
    """)
    return db


def archivar(raiz: Path, db, kind: str, ref: str, status: int, body: bytes, recibido: datetime) -> int:
    sha = hashlib.sha256(body).hexdigest()
    rel = Path("objects") / sha[:2] / (sha + ".json.gz")
    if not (raiz / rel).exists():
        (raiz / rel).parent.mkdir(parents=True, exist_ok=True)
        (raiz / rel).write_bytes(gzip.compress(body, mtime=0))
    with db:
        return db.execute("INSERT INTO receipts(received_at,kind,ref,status,sha256,body_path) VALUES(?,?,?,?,?,?)",
                          (recibido.isoformat(), kind, ref, status, sha, rel.as_posix())).lastrowid


def usadas_hoy(db, ahora: datetime) -> int:
    return db.execute("SELECT count(*) FROM receipts WHERE received_at >= ?",
                      (ahora.replace(hour=0, minute=0, second=0, microsecond=0).isoformat(),)).fetchone()[0]


def huecos(ahora: datetime, db) -> list[dict]:
    """Partidos que empiezan en la ventana, sin once de los dos lados y con intentos pendientes."""
    rows = query(
        """SELECT m.match_id, m.league_id, m.kickoff_utc FROM matches m
           JOIN leagues l ON l.league_id = m.league_id AND l.active
           WHERE m.status = 'scheduled' AND m.kickoff_utc BETWEEN %s AND %s
             AND (SELECT count(DISTINCT x.side) FROM lineups x WHERE x.match_id = m.match_id) < 2
           ORDER BY m.kickoff_utc""", (ahora + VENTANA[0], ahora + VENTANA[1]))
    out = []
    for r in rows:
        previo = db.execute("SELECT n, ultimo FROM intentos WHERE match_id=?", (r["match_id"],)).fetchone()
        if previo and (previo["n"] >= INTENTOS or ahora - datetime.fromisoformat(previo["ultimo"]) < ESPERA):
            continue
        out.append(dict(r))
    return out


def guardar_eventos(db, body: bytes, visto: datetime) -> int:
    n = 0
    with db:
        for e in json.loads(body).get("events") or []:
            ut = (e.get("tournament") or {}).get("uniqueTournament") or {}
            if ut.get("id") not in LIGA_DE_TORNEO or not e.get("homeTeam") or not e.get("awayTeam"):
                continue
            db.execute("INSERT OR REPLACE INTO eventos(id,utid,start_ts,home,away,visto) VALUES(?,?,?,?,?,?)",
                       (e["id"], ut["id"], int(e["startTimestamp"]), e["homeTeam"]["name"], e["awayTeam"]["name"],
                        visto.isoformat()))
            n += 1
    return n


def candidatos(db, hueco: dict) -> list[sqlite3.Row]:
    """Eventos de la misma competición que empiezan a +-3 h del partido: se confirman con `emparejar`."""
    ts = int(hueco["kickoff_utc"].timestamp())
    return [e for e in db.execute("SELECT * FROM eventos WHERE start_ts BETWEEN ? AND ?", (ts - 10800, ts + 10800))
            if LIGA_DE_TORNEO.get(e["utid"]) == hueco["league_id"]]


def event_id(db, hueco: dict) -> int | None:
    for e in candidatos(db, hueco):
        fila = {"uniqueTournamentId": e["utid"], "startTimestamp": e["start_ts"], "homeTeam": e["home"],
                "awayTeam": e["away"]}
        mid, _ = emparejar(fila)
        if mid == hueco["match_id"]:
            return e["id"]
    return None


def refrescar_calendario(raiz, db, key, call, clock) -> int:
    """3 fechas (ayer, hoy, mañana UTC); como mucho cada 6 h."""
    ahora = clock()
    ultimo = db.execute("SELECT max(received_at) FROM receipts WHERE kind='calendario'").fetchone()[0]
    if ultimo and ahora - datetime.fromisoformat(ultimo) < CALENDARIO_CADA:
        return 0
    n = 0
    for d in (-1, 0, 1):
        fecha = (ahora + timedelta(days=d)).date().isoformat()
        if usadas_hoy(db, ahora) >= DIARIO:
            break
        status, body = call("%s/schedule/%s" % (API, fecha), key)
        recibido = clock()
        archivar(raiz, db, "calendario", fecha, status, body, recibido)
        if status == 200:
            n += guardar_eventos(db, body, recibido)
    return n


def run(call=http, clock=now) -> dict:
    key = os.environ.get("SPORTSAPIPRO_KEY", "")
    out = {"huecos": 0, "consultados": 0, "oficiales": 0, "sin_evento": 0, "peticiones_hoy": 0}
    if not key:
        return {**out, "skipped": "sin SPORTSAPIPRO_KEY"}
    raiz = carpeta()
    db = abrir(raiz)
    ahora = clock()
    pend = huecos(ahora, db)
    out["huecos"] = len(pend)
    if not pend:
        out["peticiones_hoy"] = usadas_hoy(db, ahora)
        return out
    with conn() as c:
        if not c.execute("SELECT pg_try_advisory_lock(%s) AS ok", (LOCK_ID,)).fetchone()["ok"]:
            return {**out, "skipped": "otra carga en marcha"}
        try:
            refrescado = False
            for h in pend:
                eid = event_id(db, h)
                if eid is None and not refrescado:
                    refrescado = True
                    refrescar_calendario(raiz, db, key, call, clock)
                    eid = event_id(db, h)
                if eid is None:
                    out["sin_evento"] += 1
                    continue
                if usadas_hoy(db, ahora) >= DIARIO:
                    break
                status, body = call("%s/api/match/%d/lineups" % (API, eid), key)
                recibido = clock()
                rid = archivar(raiz, db, "once", str(eid), status, body, recibido)
                with db:
                    db.execute("INSERT INTO intentos(match_id,n,ultimo) VALUES(?,1,?) ON CONFLICT(match_id) DO UPDATE"
                               " SET n=n+1, ultimo=excluded.ultimo", (h["match_id"], ahora.isoformat()))
                out["consultados"] += 1
                if status != 200:
                    continue
                datos = (json.loads(body) or {}).get("data") or {}
                if not datos.get("home") or not datos.get("away"):
                    continue
                with c.transaction():
                    r = aplicar(c, {"id": rid, "received_at": recibido.isoformat()}, {"lineups": datos}, h["match_id"])
                out["oficiales"] += int(bool(r.get("oficial")))
        finally:
            c.execute("SELECT pg_advisory_unlock(%s)", (LOCK_ID,))
    out["peticiones_hoy"] = usadas_hoy(db, ahora)
    record_health("sportsapipro_alineaciones", out["consultados"], True, out)
    log.info("SportsAPIPro alineaciones: %s", out)
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    print(json.dumps(run(), default=str))
