"""
Clasificación de cada liga (API-Football `/standings`) para las fichas de la
web. Una petición por liga y día: contenido, no criterio.

Es una FOTO que se reemplaza (upsert y se borran los equipos que ya no
aparecen), no un histórico. Los equipos se resuelven SOLO por coincidencia
exacta (alias de API-Football o nombre canónico): son los mismos que ya dio de
alta el calendario, y un difuso aquí colocaría la fila de un club en otro.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..db import execute, executemany, query
from ..normalize import match_team
from . import api_football as af
from .fixtures import current_season

log = logging.getLogger(__name__)


def season_label(start_year: int) -> str:
    """Misma etiqueta que el resto del sistema: 2026 -> '2627'."""
    return f"{start_year % 100:02d}{(start_year + 1) % 100:02d}"


def parse(resp: list[dict]) -> list[dict]:
    """Filas de la respuesta. Con varias tablas (MLS) cada una conserva su grupo."""
    filas = []
    for item in resp or []:
        tablas = item.get("league", {}).get("standings") or []
        varias = len(tablas) > 1
        for tabla in tablas:
            for r in tabla:
                tot = r.get("all") or {}
                goles = tot.get("goals") or {}
                filas.append({
                    "grupo": (r.get("group") or "") if varias else "",
                    "nombre": r["team"]["name"],
                    "posicion": int(r["rank"]),
                    "puntos": int(r.get("points") or 0),
                    "jugados": int(tot.get("played") or 0),
                    "ganados": int(tot.get("win") or 0),
                    "empatados": int(tot.get("draw") or 0),
                    "perdidos": int(tot.get("lose") or 0),
                    "goles_favor": int(goles.get("for") or 0),
                    "goles_contra": int(goles.get("against") or 0),
                    "forma": r.get("form"),
                    "descripcion": r.get("description"),
                })
    return filas


def vigentes(filas: list[dict]) -> list[dict]:
    """
    Argentina devuelve la fase terminada y la que se juega ('Apertura - Group
    A' ... 'Clausura - Group B'), en orden de calendario, y con la MISMA fecha
    de actualización en todas: la fecha no sirve para distinguirlas. Si hay
    varias fases se conserva la última. Grupos sin fase ('Eastern
    Conference') no se tocan.
    """
    fases = list(dict.fromkeys(f["grupo"].split(" - ")[0] for f in filas
                               if " - " in f["grupo"]))
    if len(fases) < 2:
        return filas
    return [f for f in filas
            if " - " not in f["grupo"] or f["grupo"].split(" - ")[0] == fases[-1]]


def run() -> dict:
    inicio = datetime.now(timezone.utc)
    ligas = query(
        """SELECT league_id, api_football_id, season_style FROM leagues
           WHERE active AND NOT cross_league AND api_football_id IS NOT NULL
           ORDER BY league_id""")
    resumen, sin_resolver = {}, []
    for lg in ligas:
        temporada = current_season(lg["season_style"])
        try:
            resp, meta = af.get("standings", {"league": lg["api_football_id"],
                                              "season": temporada})
        except af.PlanError:
            raise
        except Exception as exc:  # noqa: BLE001
            log.error("Clasificación de %s: %s", lg["league_id"], exc)
            continue
        filas, nombres = [], []
        for f in vigentes(parse(resp)):
            tid, _, score = match_team(f["nombre"], "api_football", lg["league_id"])
            if not tid or score < 100.0:
                sin_resolver.append(f"{lg['league_id']}: {f['nombre']}")
                continue
            filas.append((lg["league_id"], season_label(temporada), f["grupo"], tid,
                          f["posicion"], f["puntos"], f["jugados"], f["ganados"],
                          f["empatados"], f["perdidos"], f["goles_favor"],
                          f["goles_contra"], f["forma"], f["descripcion"]))
            nombres.append((f["nombre"], tid, f["nombre"]))
        if not filas:
            resumen[lg["league_id"]] = 0
            continue
        executemany(
            """INSERT INTO standings
                 (league_id, season, grupo, team_id, posicion, puntos, jugados,
                  ganados, empatados, perdidos, goles_favor, goles_contra,
                  forma, descripcion, updated_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, now())
               ON CONFLICT (league_id, grupo, team_id) DO UPDATE SET
                 season = EXCLUDED.season, posicion = EXCLUDED.posicion,
                 puntos = EXCLUDED.puntos, jugados = EXCLUDED.jugados,
                 ganados = EXCLUDED.ganados, empatados = EXCLUDED.empatados,
                 perdidos = EXCLUDED.perdidos, goles_favor = EXCLUDED.goles_favor,
                 goles_contra = EXCLUDED.goles_contra, forma = EXCLUDED.forma,
                 descripcion = EXCLUDED.descripcion, updated_at = now()""",
            filas,
        )
        # Nombre para la web; solo se escribe si cambia.
        executemany(
            """UPDATE teams SET display_name = %s
               WHERE team_id = %s AND display_name IS DISTINCT FROM %s""",
            nombres,
        )
        # Equipos que ya no están en la foto (cambio de grupo, fase cerrada).
        execute("DELETE FROM standings WHERE league_id = %s AND updated_at < %s",
                (lg["league_id"], inicio))
        resumen[lg["league_id"]] = len(filas)
    resultado = {"ligas": resumen, "sin_resolver": sin_resolver}
    af.record_health("standings", sum(resumen.values()), not sin_resolver, resultado)
    log.info("Clasificación: %s", resultado)
    return resultado


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    print(run())
