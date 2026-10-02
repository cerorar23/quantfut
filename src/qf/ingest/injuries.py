"""
Bajas/lesiones vía API-Football (`/injuries`). Fuente decidida 2026-09-22: el
mismo proveedor ya contratado (plan Pro, usado para calendario y alineaciones)
cubre este endpoint sin coste incremental. Ver harness/progreso.md.

Por qué esto y no un LLM leyendo prensa
----------------------------------------
El endpoint ya devuelve datos estructurados (jugador, tipo de baja, motivo):
no hay nada que un LLM tenga que extraer, así que no hay coste de inferencia
recurrente ni riesgo de alucinación en el parseo. No sustituye a `lineups.py`:
esto da el parte médico de la semana, pero la decisión táctica final (quién
juega de los disponibles) solo se sabe con el XI confirmado a T-60.

CÓMO SE USA (y qué falta todavía)
----------------------------------
Este módulo SOLO ingiere y almacena, igual que `lineups.py` en su fase
inicial. Convertir esto en una feature de disponibilidad (p. ej. un
equivalente a `lineups.availability()`) es el paso siguiente, una vez haya
acumulado datos.

CUOTA DE API
------------
Una llamada por partido dentro de una ventana de 7 días, pero no más de una
vez cada `MIN_HOURS_BETWEEN_CHECKS` por partido (control en
`injuries_capture_log`, que registra el intento incluso sin bajas
reportadas). A diferencia de alineaciones, el estado de una baja cambia con
días de antelación, así que hace falta releer, no una sola captura por
partido.
"""
from __future__ import annotations

import logging

from ..db import execute, query
from . import api_football as af

log = logging.getLogger(__name__)

# Las bajas se conocen con días de antelación, a diferencia del XI (T-90..T-20).
WINDOW_DAYS_AHEAD = 7

# No releer el mismo partido más seguido que esto. Evita gastar cuota en
# partidos sin cambios; sigue siendo bastante frecuente para pillar una baja
# de última hora antes de publicar.
MIN_HOURS_BETWEEN_CHECKS = 4


def pending_matches() -> list[dict]:
    """
    Partidos dentro de la ventana de captura sin comprobación reciente.

    Se consulta `injuries_capture_log`, no `injuries` directamente: un
    partido sin bajas reportadas también cuenta como "comprobado", si no se
    reintentaría en cada pasada para siempre.
    """
    return query(
        """SELECT m.match_id, m.league_id, m.home_team_id, m.away_team_id,
                  th.af_team_id AS home_af_team_id,
                  ta.af_team_id AS away_af_team_id,
                  m.kickoff_utc, m.external_ids ->> 'api_football' AS af_id
           FROM matches m
           JOIN teams th ON th.team_id = m.home_team_id
           JOIN teams ta ON ta.team_id = m.away_team_id
           -- Las bajas solo alimentan al modelo: fuera las ligas "solo sharp".
           JOIN leagues lg ON lg.league_id = m.league_id AND lg.model_enabled
           WHERE m.status = 'scheduled'
             AND m.external_ids ->> 'api_football' IS NOT NULL
             AND m.kickoff_utc BETWEEN now()
                                   AND now() + make_interval(days => %s)
             AND NOT EXISTS (
                 SELECT 1 FROM injuries_capture_log c
                 WHERE c.match_id = m.match_id
                   AND c.captured_at > now() - make_interval(hours => %s)
             )
           ORDER BY m.kickoff_utc""",
        (WINDOW_DAYS_AHEAD, MIN_HOURS_BETWEEN_CHECKS),
    )


def _side_of(af_team_id: int | None, match: dict) -> str | None:
    # La respuesta trae el id de API-Football, no nuestro team_id interno.
    # Compararlo con `home_team_id` descartó todas las bajas del 22-sep al
    # 2-oct-2026 sin ningún error.
    if af_team_id is None:
        return None
    if af_team_id == match["home_af_team_id"]:
        return "home"
    if af_team_id == match["away_af_team_id"]:
        return "away"
    return None


def ingest_match(match: dict) -> dict:
    """
    Captura las bajas reportadas de un partido. Devuelve un informe, nunca
    lanza por ausencia de datos: que no haya bajas es lo normal, no un fallo.
    """
    resp, meta = af.get("injuries", {"fixture": match["af_id"]})
    af.check_quota(meta)

    stored = 0
    discarded = 0
    for entry in resp:
        player = entry.get("player") or {}
        team = entry.get("team") or {}
        side = _side_of(team.get("id"), match)
        if side is None or not player.get("id"):
            discarded += 1
            log.warning("Baja descartada en %s: equipo %s no es ninguno de los "
                        "dos (af_team_id %s/%s)", match["match_id"], team.get("id"),
                        match["home_af_team_id"], match["away_af_team_id"])
            continue
        stored += execute(
            """INSERT INTO injuries
                 (match_id, side, player_id, player_name, status_type, reason)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (match_id, side, player_id, captured_at) DO NOTHING""",
            (match["match_id"], side, player["id"], player.get("name"),
             player.get("type"), player.get("reason")),
        )

    execute(
        """INSERT INTO injuries_capture_log (match_id, n_reported)
           VALUES (%s, %s)""",
        (match["match_id"], stored),
    )
    return {"match_id": match["match_id"], "stored": stored, "discarded": discarded}


def run() -> dict:
    matches = pending_matches()
    if not matches:
        log.info("Ningún partido pendiente de comprobar bajas.")
        af.record_health("injuries", 0, True, {"checked": 0})
        return {"checked": 0, "stored": 0}

    stored = 0
    discarded = 0
    problems = []

    for m in matches:
        try:
            r = ingest_match(m)
        except Exception as exc:  # noqa: BLE001
            log.error("Bajas fallidas %s: %s", m["match_id"], exc)
            problems.append(f"{m['match_id']}: {exc}")
            continue
        stored += r["stored"]
        discarded += r["discarded"]

    ok = not problems
    af.record_health("injuries", stored, ok,
                     {"checked": len(matches), "discarded": discarded,
                      "problems": problems})

    summary = {"checked": len(matches), "stored": stored,
               "discarded": discarded, "problems": problems}
    log.info("Bajas: %s", summary)
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    print(run())
