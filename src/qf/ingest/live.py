"""
Marcador en juego para la app. Una sola petición `fixtures?live=all` por pasada,
sin importar cuántos partidos haya ni cuántos usuarios miren la app.

Escribe solo las columnas live_* (db/056). No cambia `matches.status` ni los
goles finales: el cierre sigue siendo de results.py, con su auditoría temporal.
"""
from __future__ import annotations

import logging

from ..db import execute, query
from . import api_football as af

log = logging.getLogger(__name__)

# Estados de API-Football con el balón en juego o en una pausa del partido.
EN_JUEGO = {"1H", "HT", "2H", "ET", "BT", "P", "LIVE", "INT"}


def _candidatos() -> dict[str, str]:
    """Partidos que pueden estar jugándose ahora: {api_football_id: match_id}."""
    rows = query(
        """SELECT match_id, external_ids ->> 'api_football' AS af_id
           FROM matches
           WHERE status IN ('scheduled', 'live')
             AND kickoff_utc BETWEEN now() - interval '4 hours'
                                 AND now() + interval '10 minutes'
             AND external_ids ? 'api_football'"""
    )
    return {r["af_id"]: r["match_id"] for r in rows}


def run() -> dict:
    candidatos = _candidatos()
    en_juego: dict[str, tuple] = {}
    if candidatos:
        resp, meta = af.get("fixtures", {"live": "all"})
        af.check_quota(meta)
        for fx in resp:
            af_id = str(fx["fixture"]["id"])
            short = fx["fixture"]["status"]["short"]
            goals = fx.get("goals") or {}
            if af_id in candidatos and short in EN_JUEGO and goals.get("home") is not None:
                en_juego[candidatos[af_id]] = (
                    goals["home"], goals["away"],
                    fx["fixture"]["status"].get("elapsed"), short)

    for match_id, (h, a, minute, short) in en_juego.items():
        execute(
            """UPDATE matches SET live_home_goals=%s, live_away_goals=%s,
                      live_minute=%s, live_status=%s, live_updated_at=now()
               WHERE match_id=%s""",
            (h, a, minute, short, match_id),
        )
    # Lo que ya no aparece en juego (terminó o no empezó) deja de mostrar vivo.
    limpiados = execute(
        """UPDATE matches SET live_home_goals=NULL, live_away_goals=NULL,
                  live_minute=NULL, live_status=NULL
           WHERE live_status IS NOT NULL AND NOT (match_id = ANY(%s))""",
        (list(en_juego),),
    )
    af.record_health("live", len(en_juego), True,
                     {"candidatos": len(candidatos), "en_juego": len(en_juego)})
    summary = {"candidatos": len(candidatos), "en_juego": len(en_juego),
               "limpiados": limpiados}
    log.info("Marcador en vivo: %s", summary)
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    print(run())
