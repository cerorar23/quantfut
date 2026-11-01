"""
Disponibilidad de titulares a partir de las alineaciones guardadas en `lineups`.

Las alineaciones las escriben `fotmob_alineaciones` y `sportsapipro_alineaciones`
(la captura de API-Football se retiró el 25-oct-2026). `availability()` expone lo
que se puede aprovechar sin ratings por jugador: cuántos titulares habituales
faltan respecto a los últimos partidos, y solo compara contra historia de la
MISMA fuente de ids de jugador. Lo usa `model.shadow`.
"""
from __future__ import annotations

from ..db import query


def _fuente(starters: list[dict]) -> str:
    """Fuente de los ids de jugador de un XI: SofaScore y FotMob los marcan con `src`; el resto es API-Football."""
    for fuente in ("sofascore", "fotmob"):
        if any(p.get("src") == fuente for p in starters or []):
            return fuente
    return "api"


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
