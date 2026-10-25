"""
Alineaciones confirmadas a T-60. La actualización de mayor valor por hora de
trabajo del sistema.

POR QUÉ IMPORTA MÁS QUE CASI CUALQUIER MEJORA DEL MODELO
--------------------------------------------------------
Dixon-Coles estima la fuerza de un EQUIPO promediada sobre toda su historia
reciente. No sabe que hoy descansa el delantero que mete un tercio de los
goles. El mercado sí lo sabe: las cuotas se mueven en los minutos siguientes a
la publicación del XI. Esa ventana —entre que sale la alineación y que el
mercado termina de ajustar— es donde vive el edge realista de un sistema de
este tamaño, y hasta ahora el sistema no la miraba.

La tabla `lineups` existe en el esquema desde el primer día
(`db/003_api_football.sql`) pero nada la escribía.

CÓMO SE USA (y qué falta todavía)
---------------------------------
Este módulo SOLO ingiere y almacena. Convertir el XI en un ajuste de lambda
requiere ratings por jugador, que es trabajo aparte y necesita acumular datos
primero. Empezar a capturar hoy es lo que hace posible ese modelo dentro de
unos meses: cada día que no se captura es un día irrecuperable, exactamente
igual que con los snapshots de cuotas.

`availability()` ya expone lo que se puede aprovechar sin ratings: cuántos
titulares habituales faltan respecto a los últimos partidos. Eso es señal
utilizable de inmediato como feature del modelo de residuo.

CUOTA DE API
------------
Una llamada por partido, solo dentro de la ventana T-90..T-20 y solo una vez
por partido (control en `lineups_capture_log`). Con 7 ligas son ~40-60
llamadas al día en fin de semana, muy por debajo del plan básico.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from ..db import execute, query, query_one
from . import api_football as af

log = logging.getLogger(__name__)

# Ventana de captura. Antes de T-90 casi nunca están publicadas; después de
# T-20 el mercado ya ajustó y el dato pierde casi todo su valor operativo.
WINDOW_MIN_BEFORE = 90
WINDOW_MAX_BEFORE = 20


def pending_matches() -> list[dict]:
    """
    Partidos dentro de la ventana de captura que todavía no tienen alineación.

    El filtro por dos lados ya guardados impide gastar cuota en partidos
    completos, pero vuelve a intentar si el proveedor publicó solo un XI.
    """
    return query(
        """SELECT m.match_id, m.league_id, m.kickoff_utc,
                  m.external_ids ->> 'api_football' AS af_id,
                  EXTRACT(EPOCH FROM (m.kickoff_utc - now())) / 60 AS mins_to_ko
           FROM matches m
           -- El XI solo lo usa el modelo: nada de cuota en ligas "solo sharp"
           -- ni en las de captura reducida (db/052).
           JOIN leagues lg ON lg.league_id = m.league_id AND lg.model_enabled
                          AND lg.captura_completa
           WHERE m.status = 'scheduled'
             AND m.external_ids ->> 'api_football' IS NOT NULL
             AND m.kickoff_utc BETWEEN now() + make_interval(mins => %s)
                                   AND now() + make_interval(mins => %s)
             AND (SELECT count(DISTINCT l.side) FROM lineups l
                  WHERE l.match_id = m.match_id) < 2
           ORDER BY m.kickoff_utc""",
        (WINDOW_MAX_BEFORE, WINDOW_MIN_BEFORE),
    )


def _parse_side(entry: dict) -> dict:
    """
    Normaliza un bloque de alineación de API-Football.

    El proveedor devuelve `startXI` como lista de {"player": {...}}; se aplana
    a lo que guarda el esquema: [{player_id, name, pos, number}].
    """
    starters = []
    for item in entry.get("startXI") or []:
        p = item.get("player") or {}
        starters.append({
            "player_id": p.get("id"),
            "name": p.get("name"),
            "pos": p.get("pos"),
            "number": p.get("number"),
        })
    return {
        "formation": entry.get("formation"),
        "starters": starters,
        "coach": (entry.get("coach") or {}).get("name"),
    }


def ingest_match(match: dict) -> dict:
    """
    Captura la alineación de un partido. Devuelve un informe, nunca lanza por
    ausencia de datos: que el XI no esté publicado todavía es lo normal, no un
    fallo.
    """
    resp, meta = af.get("fixtures/lineups", {"fixture": match["af_id"]})
    af.check_quota(meta)

    if meta["empty"] or len(resp) < 2:
        return {"match_id": match["match_id"], "stored": 0, "pending": True}

    mins = int(match["mins_to_ko"])
    stored = 0

    # El orden de API-Football es [local, visitante]; se respeta ese contrato
    # en vez de intentar emparejar por nombre de equipo, que obligaría a
    # resolver alias otra vez y puede fallar en silencio.
    for side, entry in zip(("home", "away"), resp[:2]):
        if query_one("SELECT 1 FROM lineups WHERE match_id=%s AND side=%s LIMIT 1",
                     (match["match_id"], side)):
            continue
        parsed = _parse_side(entry)
        if not parsed["starters"]:
            continue
        stored += execute(
            """INSERT INTO lineups
                 (match_id, side, formation, starters, mins_to_kickoff)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (match_id, side, captured_at) DO NOTHING""",
            (match["match_id"], side, parsed["formation"],
             json.dumps(parsed["starters"]), mins),
        )

    complete = query_one(
        """SELECT count(DISTINCT side) AS n FROM lineups WHERE match_id=%s""",
        (match["match_id"],),
    )
    return {"match_id": match["match_id"], "stored": stored,
            "pending": int((complete or {}).get("n") or 0) < 2}


def _fuente(starters: list[dict]) -> str:
    """Fuente de los ids de jugador de un XI: SofaScore los marca con `src`; el resto es API-Football."""
    return "sofascore" if any(p.get("src") == "sofascore" for p in starters or []) else "api"


def availability(match_id: str, lookback: int = 5) -> dict | None:
    """
    Cuántos titulares habituales faltan en el XI de hoy.

    Señal utilizable SIN ratings por jugador: se compara el XI publicado con
    los jugadores que más han salido de titular en los últimos `lookback`
    partidos con alineación guardada de ese equipo. Devuelve None si todavía
    no hay historia suficiente.

    Es una aproximación deliberadamente tosca: no distingue al portero suplente
    del delantero estrella. Para eso hacen falta ratings por jugador, que es el
    paso siguiente y necesita justo los datos que este módulo empieza a
    acumular.
    """
    rows = query(
        """SELECT l.side, l.starters, m.home_team_id, m.away_team_id
           FROM lineups l JOIN matches m USING (match_id)
           WHERE l.match_id = %s
           ORDER BY l.captured_at DESC""",
        (match_id,),
    )
    if not rows:
        return None

    out: dict[str, dict] = {}
    for r in rows:
        if r["side"] in out:
            continue
        team_id = r["home_team_id"] if r["side"] == "home" else r["away_team_id"]
        today = {p["player_id"] for p in r["starters"] if p.get("player_id")}

        # La historia (XI de partidos ANTERIORES) sale también de
        # `lineups_historicas`, como en el entrenamiento del challenger
        # (decisión del usuario, 2026-10-02). El XI de un partido ya jugado
        # era público antes del de hoy; lo que sigue exigiendo captura previa
        # al inicio es el XI de hoy, que solo se lee de `lineups`. Si un
        # partido está en las dos tablas, manda el capturado en vivo.
        hist = query(
            """SELECT history.starters, history.historico
               FROM (
                   SELECT DISTINCT ON (m.match_id)
                          x.starters, m.kickoff_utc, x.prioridad = 1 AS historico
                   FROM (
                       SELECT l.match_id, l.side, l.starters, l.captured_at,
                              0 AS prioridad
                       FROM lineups l
                       UNION ALL
                       SELECT h.match_id, h.side, h.starters, NULL, 1
                       FROM lineups_historicas h
                       WHERE jsonb_array_length(h.starters) >= 11
                   ) AS x
                   JOIN matches m ON m.match_id = x.match_id
                   WHERE ((x.side = 'home' AND m.home_team_id = %s)
                       OR (x.side = 'away' AND m.away_team_id = %s))
                     AND m.match_id <> %s
                     AND m.kickoff_utc < (SELECT kickoff_utc FROM matches
                                          WHERE match_id = %s)
                   ORDER BY m.match_id, x.prioridad, x.captured_at DESC NULLS LAST
               ) AS history
               ORDER BY history.kickoff_utc DESC
               LIMIT %s""",
            (team_id, team_id, match_id, match_id, lookback),
        )
        # Los ids de SofaScore no son los de API-Football: se compara solo contra historia de la misma fuente
        # (si no, todos los habituales parecerían ausentes). Sin historia suficiente queda «insuficiente».
        hist = [h for h in hist if _fuente(h["starters"]) == _fuente(r["starters"])]
        if len(hist) < 3:
            out[r["side"]] = {"missing_regulars": None,
                              "reason": "historia insuficiente"}
            continue

        counts: dict[int, int] = {}
        positions: dict[int, str] = {}
        for h in hist:
            for p in h["starters"]:
                pid = p.get("player_id")
                if pid:
                    counts[pid] = counts.get(pid, 0) + 1
                    if p.get("pos"):
                        positions[pid] = str(p["pos"]).upper()[:1]
        # "Habitual" = titular en al menos el 60% de los partidos mirados.
        regulars = {pid for pid, c in counts.items() if c >= 0.6 * len(hist)}
        missing = regulars - today
        missing_by_position = {"G": 0, "D": 0, "M": 0, "F": 0}
        for pid in missing:
            pos = positions.get(pid)
            if pos in missing_by_position:
                missing_by_position[pos] += 1
        previous = {p.get("player_id") for p in hist[0]["starters"]
                    if p.get("player_id")}
        out[r["side"]] = {
            "missing_regulars": len(missing),
            "missing_by_position": missing_by_position,
            "lineup_continuity": round(len(today & previous) / max(len(today), 1), 4),
            "n_regulars": len(regulars),
            "n_history": len(hist),
            "n_history_historico": sum(bool(h.get("historico")) for h in hist),
        }
    return out


def run() -> dict:
    matches = pending_matches()
    if not matches:
        log.info("Ningún partido en la ventana de alineaciones.")
        af.record_health("lineups", 0, True, {"in_window": 0})
        return {"checked": 0, "stored": 0, "pending": 0}

    stored = pending = 0
    problems = []

    for m in matches:
        try:
            r = ingest_match(m)
        except Exception as exc:  # noqa: BLE001
            log.error("Alineación fallida %s: %s", m["match_id"], exc)
            problems.append(f"{m['match_id']}: {exc}")
            continue
        stored += r["stored"]
        pending += int(r["pending"])

    ok = not problems
    af.record_health("lineups", stored, ok,
                     {"checked": len(matches), "pending": pending,
                      "problems": problems})

    summary = {"checked": len(matches), "stored": stored, "pending": pending,
               "problems": problems}
    log.info("Alineaciones: %s", summary)
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    print(run())
