"""xG, estadísticas y alineaciones de partidos terminados desde el archivo SofaScore/Apify.

Sustituye al xG de API-Football (plan gratuito desde el 22-oct-2026; decisión del titular, 24-oct).
El recolector del host (`sofascore_apify.py`, cron diario) guarda los originales con la hora real de
recepción; el worker los lee en solo lectura. Sin peticiones.

Un detalle solo se aplica a un partido nuestro YA TERMINADO de la misma competición, a ±36 h, con los dos
nombres parecidos y EL MISMO MARCADOR. El marcador es la comprobación independiente: con él un nombre
escrito distinto («Club Atlético Belgrano» / «Belgrano») no puede colocar estadísticas en otro partido.
Si los equipos coinciden y el marcador no, no se aplica nada y se cuenta como conflicto.

El xG solo se escribe si el partido no tiene ninguno (primera pareja válida, como `xg_api_football`), con
`xg_recorded_at` = recepción del recolector. Solo partidos terminados en tiempo reglamentario
(`statusCode` 100): el formato del actor no separa la prórroga.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from psycopg.types.json import Jsonb
from rapidfuzz import fuzz

from ..db import conn, query
from ..normalize import slugify
from . import api_football as af
from .estadisticas import arbitro
from .sofascore_history import TOURNAMENTS, stat_pair

log = logging.getLogger(__name__)

LIGA_DE_TORNEO = {v: k for k, v in TOURNAMENTS.items()} | {11621: "mx.liga_mx"}
VENTANA = timedelta(hours=36)
PARECIDO_MIN = 70
LOCK_ID = 61024085


def _archivo() -> Path:
    from ..config import settings
    return Path(settings.sofascore_archive)


def detalles(raiz: Path, desde: datetime) -> list[tuple[dict, dict]]:
    """(recibo, fila) de cada `event_detail` de fútbol recibido desde `desde`, verificando el hash."""
    db_path = raiz / "index.sqlite"
    if not db_path.is_file():
        return []
    db = sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        recibos = db.execute("""SELECT id, received_at, sha256, body_path FROM receipts
                                WHERE kind = 'detail' AND status IN (200, 201) AND rows > 0
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


def _nombres(team_ids: list[int]) -> dict[int, set[str]]:
    out: dict[int, set[str]] = {t: set() for t in team_ids}
    for r in query("""SELECT team_id, canonical_name AS n FROM teams WHERE team_id = ANY(%s)
                      UNION SELECT team_id, alias FROM team_aliases WHERE team_id = ANY(%s)""",
                   (team_ids, team_ids)):
        out[r["team_id"]].add(slugify(r["n"]))
    return out


def parecido(nombre: str, conocidos: set[str]) -> float:
    s = slugify(nombre)
    return max((fuzz.token_set_ratio(s, c) for c in conocidos), default=0.0)


def emparejar(fila: dict) -> tuple[str | None, str]:
    """(match_id, motivo). Solo un candidato terminado con equipos parecidos y el mismo marcador."""
    liga = LIGA_DE_TORNEO.get(fila.get("uniqueTournamentId"))
    if liga is None:
        return None, "competicion_fuera_de_catalogo"
    if fila.get("statusType") != "finished" or fila.get("statusCode") != 100:
        return None, "no_terminado_en_tiempo_reglamentario"
    ko = datetime.fromtimestamp(int(fila["startTimestamp"]), timezone.utc)
    cands = query("""SELECT match_id, status, home_team_id, away_team_id, home_goals, away_goals
                     FROM matches WHERE league_id = %s AND kickoff_utc BETWEEN %s AND %s""",
                  (liga, ko - VENTANA, ko + VENTANA))
    if not cands:
        return None, "sin_partido"
    nombres = _nombres([c[k] for c in cands for k in ("home_team_id", "away_team_id")])
    mismos = [c for c in cands
              if parecido(fila["homeTeam"], nombres[c["home_team_id"]]) >= PARECIDO_MIN
              and parecido(fila["awayTeam"], nombres[c["away_team_id"]]) >= PARECIDO_MIN]
    if len(mismos) != 1:
        return None, "sin_partido" if not mismos else "ambiguo"
    c = mismos[0]
    if c["status"] != "finished":
        return None, "pendiente_de_resultado"
    if (c["home_goals"], c["away_goals"]) != (fila.get("homeScore"), fila.get("awayScore")):
        return None, "conflicto_marcador"
    return c["match_id"], "ok"


def _conteo(stats: dict, key: str, cero_si_falta: bool = False) -> tuple[int | None, int | None]:
    h, a = stat_pair(stats, key)
    if h is None and cero_si_falta and stats.get("statistics"):
        return 0, 0
    return (None if h is None else int(h)), (None if a is None else int(a))


def aplicar(c, recibo: dict, fila: dict, match_id: str) -> bool:
    stats = {"statistics": fila.get("statistics") or []}
    xg = stat_pair(stats, "expectedGoals")
    xg = xg if None not in xg else (None, None)
    tiros, a_puerta = _conteo(stats, "totalShotsOnGoal"), _conteo(stats, "shotsOnGoal")
    corners = _conteo(stats, "cornerKicks")
    amarillas, rojas = _conteo(stats, "yellowCards", True), _conteo(stats, "redCards", True)
    nuevo = c.execute(
        """INSERT INTO sofascore_detalles (sofascore_id, match_id, league_id, received_at, receipt_id,
               raw_sha256, home_source_team_id, away_source_team_id, home_goals, away_goals,
               home_xg, away_xg, lineups, statistics)
           SELECT %s, %s, league_id, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s FROM matches WHERE match_id = %s
           ON CONFLICT DO NOTHING RETURNING match_id""",
        (fila["id"], match_id, recibo["received_at"], recibo["id"], recibo["sha256"],
         str(fila.get("homeTeamId")), str(fila.get("awayTeamId")), fila["homeScore"], fila["awayScore"],
         xg[0], xg[1], Jsonb(fila.get("lineups")) if fila.get("lineups") else None,
         Jsonb(fila.get("statistics") or []), match_id)).fetchone()
    if not nuevo:
        return False
    c.execute(
        """UPDATE matches SET
               home_shots = COALESCE(home_shots, %s), away_shots = COALESCE(away_shots, %s),
               home_shots_target = COALESCE(home_shots_target, %s), away_shots_target = COALESCE(away_shots_target, %s),
               home_corners = COALESCE(home_corners, %s), away_corners = COALESCE(away_corners, %s),
               home_yellow = COALESCE(home_yellow, %s), away_yellow = COALESCE(away_yellow, %s),
               home_red = COALESCE(home_red, %s), away_red = COALESCE(away_red, %s),
               referee = COALESCE(referee, %s)
           WHERE match_id = %s AND status = 'finished'""",
        (*tiros, *a_puerta, *corners, *amarillas, *rojas, arbitro(fila.get("referee")), match_id))
    if xg[0] is not None:
        c.execute("""UPDATE matches SET home_xg = %s, away_xg = %s, xg_source = 'sofascore',
                         xg_recorded_at = %s
                     WHERE match_id = %s AND status = 'finished' AND home_xg IS NULL AND away_xg IS NULL""",
                  (xg[0], xg[1], recibo["received_at"], match_id))
    return True


def run(dias: int = 10) -> dict:
    out = {"detalles": 0, "aplicados": 0, "ya_cargados": 0, "con_xg": 0, "motivos": {}}
    filas = detalles(_archivo(), datetime.now(timezone.utc) - timedelta(days=dias))
    out["detalles"] = len(filas)
    cargados = {r["sofascore_id"] for r in query("SELECT sofascore_id FROM sofascore_detalles")} if filas else set()
    with conn() as c:
        if not c.execute("SELECT pg_try_advisory_lock(%s) AS ok", (LOCK_ID,)).fetchone()["ok"]:
            return {"skipped": "otra carga SofaScore en marcha"}
        try:
            for recibo, fila in filas:
                if fila["id"] in cargados:
                    out["ya_cargados"] += 1
                    continue
                match_id, motivo = emparejar(fila)
                out["motivos"][motivo] = out["motivos"].get(motivo, 0) + 1
                if match_id is None:
                    if motivo == "conflicto_marcador":
                        log.warning("SofaScore %s (%s-%s) choca en marcador con nuestro partido",
                                    fila["id"], fila.get("homeTeam"), fila.get("awayTeam"))
                    continue
                try:
                    with c.transaction():
                        aplicado = aplicar(c, recibo, fila, match_id)
                except ValueError as exc:   # estadística repetida con valores distintos
                    log.warning("SofaScore %s descartado: %s", fila["id"], exc)
                    out["motivos"]["dato_invalido"] = out["motivos"].get("dato_invalido", 0) + 1
                    continue
                if aplicado:
                    cargados.add(fila["id"])
                    out["aplicados"] += 1
                    out["con_xg"] += None not in stat_pair({"statistics": fila.get("statistics") or []},
                                                           "expectedGoals")
        finally:
            c.execute("SELECT pg_advisory_unlock(%s)", (LOCK_ID,))
    af.record_health("sofascore_partidos", out["aplicados"], not out["motivos"].get("conflicto_marcador"), out)
    log.info("SofaScore a partidos: %s", out)
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    print(json.dumps(run(), default=str))
