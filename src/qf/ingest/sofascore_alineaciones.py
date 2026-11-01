"""Bajas y once (previsto y oficial) de partidos por jugar, desde el archivo SofaScore/Apify.

Sustituye a `/injuries` y `/fixtures/lineups` de API-Football (plan gratuito desde el 22-oct-2026) y a las
capturas de FotMob (retiradas del cron el 25-oct). El recolector del host (`sofascore_apify.py lineups`, cron
cada 10 min) guarda los originales con la hora real de recepción; el worker los lee en solo lectura. Sin
peticiones.

Qué escribe, por partido nuestro todavía programado:
  * `injuries`: las bajas (`missing`/`doubtful`) con motivo y fecha de regreso, `source = 'sofascore'`.
  * `lineups_previstas`: el once de cada captura, previsto (`confirmed = false`) u oficial.
  * `lineups`: SOLO el oficial (`confirmed = true`) con los dos lados completos, que es lo que lee
    `sello_tardio` («alineaciones oficiales capturadas»). Un once previsto nunca entra ahí.

Los ids de jugador son los de SofaScore y se marcan `src = 'sofascore'` en cada titular: no coinciden con los
de API-Football, y `lineups.availability` solo compara contra historia de la misma fuente.

Un evento solo se enlaza con un partido nuestro programado de la misma competición, a ±36 h, con los dos
nombres parecidos y como único candidato (sin marcador que lo confirme, porque aún no hay).
"""
from __future__ import annotations

import gzip
import hashlib
import json
import logging
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from psycopg.types.json import Jsonb

from ..db import conn, query
from .salud import record_health
from .sofascore_partidos import LIGA_DE_TORNEO, PARECIDO_MIN, VENTANA, _nombres, parecido

log = logging.getLogger(__name__)

LOCK_ID = 61024087
POS = {"G": "G", "D": "D", "M": "M", "F": "F"}


def _archivo() -> Path:
    from ..config import settings
    return Path(settings.sofascore_archive)


def capturas(raiz: Path, desde: datetime) -> list[tuple[dict, dict]]:
    """(recibo, fila) de cada captura de once/bajas recibida desde `desde`, verificando el hash."""
    db_path = raiz / "index.sqlite"
    if not db_path.is_file():
        return []
    db = sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        recibos = db.execute("""SELECT id, received_at, sha256, body_path FROM receipts
                                WHERE kind = 'lineup' AND status IN (200, 201) AND rows > 0
                                  AND received_at >= ? ORDER BY id""", (desde.isoformat(),)).fetchall()
    finally:
        db.close()
    out = []
    for r in recibos:
        body = gzip.decompress((raiz / r["body_path"]).read_bytes())
        if hashlib.sha256(body).hexdigest() != r["sha256"]:
            log.error("Recibo SofaScore %s alterado: hash distinto; se ignora", r["id"])
            continue
        for fila in json.loads(body):
            if isinstance(fila, dict) and fila.get("kind") == "event_detail" and fila.get("sport") == "football":
                out.append((dict(r), fila))
    return out


def emparejar(fila: dict) -> tuple[str | None, str]:
    """(match_id, motivo). Un único partido programado de la competición con equipos parecidos."""
    liga = LIGA_DE_TORNEO.get(fila.get("uniqueTournamentId"))
    if liga is None:
        return None, "competicion_fuera_de_catalogo"
    ko = datetime.fromtimestamp(int(fila["startTimestamp"]), timezone.utc)
    cands = query("""SELECT match_id, status, home_team_id, away_team_id FROM matches
                     WHERE league_id = %s AND kickoff_utc BETWEEN %s AND %s""",
                  (liga, ko - VENTANA, ko + VENTANA))
    if not cands:
        return None, "sin_partido"
    nombres = _nombres([c[k] for c in cands for k in ("home_team_id", "away_team_id")])
    mismos = [c for c in cands
              if parecido(fila["homeTeam"], nombres[c["home_team_id"]]) >= PARECIDO_MIN
              and parecido(fila["awayTeam"], nombres[c["away_team_id"]]) >= PARECIDO_MIN]
    if len(mismos) != 1:
        return None, "sin_partido" if not mismos else "ambiguo"
    if mismos[0]["status"] != "scheduled":
        return None, "ya_empezado"
    return mismos[0]["match_id"], "ok"


def titulares(lado: dict | None) -> list[dict]:
    """Titulares en el formato de `lineups.starters`, con `src` para no mezclar ids de otra fuente."""
    out = []
    for p in (lado or {}).get("players") or []:
        if p.get("substitute"):
            continue
        j = p.get("player") or {}
        pid = j.get("id") or j.get("sofascoreId")
        if not pid:
            continue
        out.append({"player_id": int(pid), "name": j.get("name"),
                    "pos": POS.get(str(p.get("position") or j.get("position") or "").upper()[:1]),
                    "number": p.get("shirtNumber") or p.get("jerseyNumber"), "src": "sofascore"})
    return out


def bajas(lado: dict | None) -> list[dict]:
    out = []
    for m in (lado or {}).get("missingPlayers") or []:
        j = m.get("player") or {}
        pid = j.get("id") or j.get("sofascoreId")
        if not pid:
            continue
        fin = None
        try:
            fin = date.fromisoformat(str(m.get("expectedEndDate"))[:10]) if m.get("expectedEndDate") else None
        except ValueError:
            pass
        out.append({"player_id": int(pid), "player_name": j.get("name") or "?",
                    "status_type": str(m.get("type") or "missing"),
                    "reason": m.get("description") or (None if m.get("reason") is None else str(m["reason"])),
                    "expected_return": fin})
    return out


def aplicar(c, recibo: dict, fila: dict, match_id: str) -> dict:
    """Escribe bajas, once previsto y, si es oficial y completo, `lineups`. Idempotente por recibo."""
    recibido = datetime.fromisoformat(recibo["received_at"])
    if c.execute("SELECT 1 FROM lineups_previstas WHERE match_id=%s AND receipt_id=%s LIMIT 1",
                 (match_id, recibo["id"])).fetchone():
        return {"nuevo": False}
    lu = fila.get("lineups") or {}
    confirmado = bool(lu.get("confirmed"))
    lados = {"home": lu.get("home"), "away": lu.get("away")}
    xi = {s: titulares(lados[s]) for s in lados}
    n_bajas = 0
    for s, lado in lados.items():
        for b in bajas(lado):
            n_bajas += c.execute(
                """INSERT INTO injuries (match_id, side, player_id, player_name, status_type, reason,
                                         captured_at, source, expected_return)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, 'sofascore', %s) ON CONFLICT DO NOTHING""",
                (match_id, s, b["player_id"], b["player_name"], b["status_type"], b["reason"],
                 recibido, b["expected_return"])).rowcount
        if xi[s]:
            c.execute(
                """INSERT INTO lineups_previstas (match_id, side, formation, starters, confirmed, receipt_id,
                                                  captured_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                (match_id, s, (lado or {}).get("formation"), Jsonb(xi[s]), confirmado, recibo["id"], recibido))
    # Una fila de captura por partido, haya o no bajas: distingue «no comprobado» de «comprobado sin bajas».
    c.execute("""INSERT INTO injuries_capture_log (match_id, captured_at, n_reported) VALUES (%s, %s, %s)
                 ON CONFLICT DO NOTHING""", (match_id, recibido, n_bajas))
    oficial = confirmado and all(len(xi[s]) >= 11 for s in ("home", "away"))
    if oficial:
        ko = c.execute("SELECT kickoff_utc FROM matches WHERE match_id=%s", (match_id,)).fetchone()["kickoff_utc"]
        mins = int((ko - recibido).total_seconds() // 60)
        for s in ("home", "away"):
            if c.execute("SELECT 1 FROM lineups WHERE match_id=%s AND side=%s LIMIT 1", (match_id, s)).fetchone():
                continue
            c.execute("""INSERT INTO lineups (match_id, side, formation, starters, captured_at, mins_to_kickoff)
                         VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                      (match_id, s, (lados[s] or {}).get("formation"), Jsonb(xi[s]), recibido, mins))
    return {"nuevo": True, "bajas": n_bajas, "oficial": oficial, "previsto": not confirmado}


def run(horas: int = 48) -> dict:
    out = {"capturas": 0, "nuevas": 0, "oficiales": 0, "previstas": 0, "bajas": 0, "motivos": {}}
    filas = capturas(_archivo(), datetime.now(timezone.utc) - timedelta(hours=horas))
    out["capturas"] = len(filas)
    with conn() as c:
        if not c.execute("SELECT pg_try_advisory_lock(%s) AS ok", (LOCK_ID,)).fetchone()["ok"]:
            return {"skipped": "otra carga de alineaciones en marcha"}
        try:
            for recibo, fila in filas:
                match_id, motivo = emparejar(fila)
                out["motivos"][motivo] = out["motivos"].get(motivo, 0) + 1
                if match_id is None:
                    continue
                with c.transaction():
                    r = aplicar(c, recibo, fila, match_id)
                if r["nuevo"]:
                    out["nuevas"] += 1
                    out["bajas"] += r["bajas"]
                    out["oficiales"] += int(r["oficial"])
                    out["previstas"] += int(r["previsto"])
        finally:
            c.execute("SELECT pg_advisory_unlock(%s)", (LOCK_ID,))
    sin_empate = out["motivos"].get("ambiguo", 0)
    record_health("sofascore_alineaciones", out["nuevas"], not sin_empate, out)
    log.info("SofaScore alineaciones/bajas: %s", out)
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    print(json.dumps(run(), default=str))
