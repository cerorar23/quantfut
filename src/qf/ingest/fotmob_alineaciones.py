"""Bajas y once (previsto y oficial) de partidos por jugar, desde las capturas previas de FotMob.

Sustituye a `sofascore_alineaciones` desde el 31-oct-2026: Apify devuelve 403 (tope del plan gratuito) y el titular
no vuelve a pagarlo. `fotmob_captura previos` ya guarda, por partido nuestro y en cinco ventanas antes del saque, el
once (`fotmob_jugador_previo`), su tipo y las bajas (`fotmob_baja_previa`); este módulo solo las copia a las tablas
que leen `sello_tardio`, `odds_worker`, la ficha y `health`. No hace peticiones ni toca la fuente.

Qué escribe (todo idempotente: ON CONFLICT DO NOTHING, la hora es la de captura real de FotMob):
  * `injuries`: las bajas con `source = 'fotmob'`.
  * `lineups_previstas`: cada once, `confirmed = (tipo_alineacion = 'standard')`, `source = 'fotmob'`.
  * `lineups`: SOLO el oficial (`standard`) con los dos lados completos; cada titular lleva `src = 'fotmob'`.

Los ids de jugador son los de FotMob: `lineups.availability` solo compara contra historia de la misma fuente.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone

from psycopg.types.json import Jsonb

from ..db import conn, query
from .salud import record_health

log = logging.getLogger(__name__)

LOCK_ID = 61031090
OFICIAL = "standard"


def titulares(jugadores: list[dict], lado: str) -> list[dict]:
    """Titulares de un lado en el formato de `lineups.starters`, con `src` para no mezclar ids de otra fuente."""
    return [{"player_id": int(j["jugador_id"]), "name": j.get("nombre"), "pos": None, "number": None, "src": "fotmob"}
            for j in jugadores if j["side"] == lado and j["titular"]]


def regreso(baja: dict) -> date | None:
    f = baja.get("regreso_fecha")
    return f.date() if isinstance(f, datetime) else f


def aplicar(c, cap: dict, jugadores: list[dict], bajas: list[dict]) -> dict:
    """Escribe bajas, once previsto y, si es oficial y completo, `lineups`, de una captura de FotMob."""
    mid, at = cap["match_id"], cap["capturado_en"]
    confirmado = cap.get("tipo_alineacion") == OFICIAL
    formacion = {"home": cap.get("formacion_local"), "away": cap.get("formacion_visita")}
    xi = {s: titulares(jugadores, s) for s in ("home", "away")}
    n_bajas = 0
    for b in bajas:
        n_bajas += c.execute(
            """INSERT INTO injuries (match_id, side, player_id, player_name, status_type, reason,
                                     captured_at, source, expected_return)
               VALUES (%s, %s, %s, %s, %s, %s, %s, 'fotmob', %s) ON CONFLICT DO NOTHING""",
            (mid, b["side"], int(b["jugador_id"]), b.get("nombre") or "?", str(b.get("tipo") or "missing"),
             b.get("regreso_texto"), at, regreso(b))).rowcount
    for s in ("home", "away"):
        if cap.get("tipo_alineacion") and xi[s]:
            c.execute(
                """INSERT INTO lineups_previstas (match_id, side, formation, starters, confirmed, receipt_id,
                                                  captured_at, source)
                   VALUES (%s, %s, %s, %s, %s, NULL, %s, 'fotmob') ON CONFLICT DO NOTHING""",
                (mid, s, formacion[s], Jsonb(xi[s]), confirmado, at))
    # Una fila por captura, haya o no bajas: distingue «no comprobado» de «comprobado sin bajas».
    c.execute("""INSERT INTO injuries_capture_log (match_id, captured_at, n_reported) VALUES (%s, %s, %s)
                 ON CONFLICT DO NOTHING""", (mid, at, n_bajas))
    oficial = confirmado and all(len(xi[s]) >= 11 for s in ("home", "away"))
    if oficial:
        mins = int(round(float(cap["mins_to_kickoff"])))
        for s in ("home", "away"):
            if c.execute("SELECT 1 FROM lineups WHERE match_id=%s AND side=%s LIMIT 1", (mid, s)).fetchone():
                continue
            c.execute("""INSERT INTO lineups (match_id, side, formation, starters, captured_at, mins_to_kickoff)
                         VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                      (mid, s, formacion[s], Jsonb(xi[s]), at, mins))
    return {"bajas": n_bajas, "oficial": oficial, "previsto": bool(cap.get("tipo_alineacion")) and not confirmado}


def capturas(c, horas: int) -> list[dict]:
    return list(c.execute(
        """SELECT match_id, capturado_en, mins_to_kickoff, tipo_alineacion, formacion_local, formacion_visita
           FROM fotmob_previo WHERE capturado_en >= %s ORDER BY capturado_en""",
        (datetime.now(timezone.utc) - timedelta(hours=horas),)).fetchall())


def run(horas: int = 48) -> dict:
    out = {"capturas": 0, "oficiales": 0, "previstas": 0, "bajas": 0}
    with conn() as c:
        if not c.execute("SELECT pg_try_advisory_lock(%s) AS ok", (LOCK_ID,)).fetchone()["ok"]:
            return {"skipped": "otra carga de alineaciones en marcha"}
        try:
            caps = capturas(c, horas)
            out["capturas"] = len(caps)
            for cap in caps:
                jug = c.execute("""SELECT side, jugador_id, nombre, titular FROM fotmob_jugador_previo
                                   WHERE match_id=%s AND capturado_en=%s""",
                                (cap["match_id"], cap["capturado_en"])).fetchall()
                baj = c.execute("""SELECT side, jugador_id, nombre, tipo, regreso_texto, regreso_fecha
                                   FROM fotmob_baja_previa WHERE match_id=%s AND capturado_en=%s""",
                                (cap["match_id"], cap["capturado_en"])).fetchall()
                with c.transaction():
                    r = aplicar(c, cap, jug, baj)
                out["bajas"] += r["bajas"]
                out["oficiales"] += int(r["oficial"])
                out["previstas"] += int(r["previsto"])
        finally:
            c.execute("SELECT pg_advisory_unlock(%s)", (LOCK_ID,))
    record_health("fotmob_alineaciones", out["capturas"], True, out)
    log.info("FotMob alineaciones/bajas: %s", out)
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    print(json.dumps(run(), default=str))
