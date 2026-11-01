"""
Marcador en juego para la app, desde el listado diario de FotMob (`matches?date=`): UNA
petición por pasada trae todos los partidos del día, sin importar cuántos haya en juego.
API-Football, que lo daba, se retiró el 22-oct-2026. PropLine también tiene `/scores` en
juego, pero cada consulta gasta del presupuesto diario compartido que necesitan las cuotas.

Los partidos se enlazan por `fotmob_referencia` (la acción `referencias` de fotmob_captura).
Respeta el mismo enfriamiento: tras un 401/403/429 de FotMob no se pide nada durante 12 h.

Escribe las columnas live_* (db/056). Al pitido final (decisión del titular, 25-oct-2026: el resultado se cierra con
la primera fuente que lo tenga y la app lo muestra al terminar) cierra el partido con su página de FotMob
(`fotmob_captura.cerrar_partido`: mismo partido, mismos equipos y final en el tiempo reglamentario) y liquida. Prórroga,
penaltis, suspendidos o adjudicados quedan para PropLine o el respaldo. Solo marcador y página: córners, tarjetas y
el resto los siguen poniendo SofaScore y `completar`, y la liquidación de esos mercados espera a tenerlos.
"""
from __future__ import annotations

import logging
import re

from ..db import conn, execute, query
from . import api_football as af
from . import fotmob_captura as fc

log = logging.getLogger(__name__)


def estado(corto: str | None) -> tuple[int | None, str]:
    """`liveTime.short` de FotMob -> (minuto, código de la app): `43’` -> (43, '1H'), `HT` -> (45, 'HT')."""
    texto = (corto or "").strip().upper()
    if "HT" in texto:
        return 45, "HT"
    m = re.match(r"\D*(\d+)", texto)
    if not m:
        return None, "LIVE"
    minuto = int(m.group(1))
    return minuto, "1H" if minuto <= 45 else "2H" if minuto <= 90 else "ET"


def _candidatos() -> dict[str, dict]:
    """Partidos que pueden estar jugándose ahora: {fotmob_match_id: {match_id, fecha}}."""
    rows = query(
        """SELECT m.match_id, f.fotmob_match_id::text AS fid, f.fotmob_match_id, m.kickoff_utc,
                  m.home_team_id, m.away_team_id, l.active AS activa,
                  to_char(m.kickoff_utc AT TIME ZONE 'UTC', 'YYYYMMDD') AS fecha
           FROM matches m JOIN fotmob_referencia f USING (match_id) JOIN leagues l USING (league_id)
           WHERE m.status IN ('scheduled', 'live')
             AND m.kickoff_utc BETWEEN now() - interval '4 hours'
                                   AND now() + interval '10 minutes'"""
    )
    return {r["fid"]: r for r in rows}


def en_juego(payload: dict, candidatos: dict[str, dict]) -> dict[str, tuple]:
    """{match_id: (goles local, goles visitante, minuto, código)} de los candidatos en juego."""
    out = {}
    for liga in payload.get("leagues") or []:
        for m in liga.get("matches") or []:
            cand = candidatos.get(str(m.get("id")))
            st = m.get("status") or {}
            h, a = (m.get("home") or {}).get("score"), (m.get("away") or {}).get("score")
            if (cand and st.get("started") and not st.get("finished") and not st.get("cancelled")
                    and h is not None and a is not None):
                minuto, codigo = estado((st.get("liveTime") or {}).get("short"))
                out[cand["match_id"]] = (int(h), int(a), minuto, codigo)
    return out


def terminados(payload: dict, candidatos: dict[str, dict]) -> list[dict]:
    """Candidatos de competiciones activas que el listado da por terminados en el tiempo reglamentario (`FT`)."""
    out = []
    for liga in payload.get("leagues") or []:
        for m in liga.get("matches") or []:
            cand = candidatos.get(str(m.get("id")))
            st = m.get("status") or {}
            if (cand and cand.get("activa", True) and st.get("finished") and not st.get("cancelled") and not st.get("awarded")
                    and (st.get("reason") or {}).get("short") == "FT"):
                out.append(cand)
    return out


def run(cli: fc.Cliente | None = None) -> dict:
    candidatos = _candidatos()
    vivos: dict[str, tuple] = {}
    cierres = {"cerrados": 0, "abiertos": 0, "equipos_distintos": 0, "descartados": 0, "ya_cerrado": 0}
    if candidatos:
        cli = cli or fc.Cliente()
        with conn() as c:
            if fc.en_enfriamiento(c):
                return {"omitido": f"enfriamiento de {fc.ENFRIAMIENTO_H} h tras una denegación de FotMob"}
            try:
                for fecha in sorted({r["fecha"] for r in candidatos.values()}):
                    listado = cli.get("matches", {"date": fecha, "timezone": "UTC"})
                    vivos.update(en_juego(listado, candidatos))
                    for cand in terminados(listado, candidatos):
                        try:
                            cierres[fc.cerrar_partido(c, cli, cand, rellenar=False)] += 1
                        except fc.AccesoDenegado:
                            raise
                        except Exception:  # noqa: BLE001 - un cierre fallido no deja sin marcador al resto
                            c.rollback()
                            log.exception("cierre al pitido de %s", cand["match_id"])
                            cierres["error"] = cierres.get("error", 0) + 1
            except fc.AccesoDenegado as exc:
                fc._log(c, "vivo", {"error": str(exc)}, denegado=True)
                from ..publish import telegram
                telegram.alert(f"FotMob denegó el acceso ({exc}). La captura se detiene {fc.ENFRIAMIENTO_H} h.")
                return {"denegado": str(exc)}

    for match_id, (h, a, minute, short) in vivos.items():
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
        (list(vivos),),
    )
    summary = {"candidatos": len(candidatos), "en_juego": len(vivos), "limpiados": limpiados,
               "fuente": "fotmob", "cierres": {k: v for k, v in cierres.items() if v}}
    if cierres["cerrados"]:
        from ..eval.clv import settle_pending
        summary["liquidado"] = settle_pending()
    af.record_health("live", len(vivos), True, summary)
    log.info("Marcador en vivo: %s", summary)
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    print(run())
