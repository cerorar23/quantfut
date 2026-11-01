"""
Clasificación de cada liga para las fichas de la web, CALCULADA con nuestros
resultados cerrados (`matches`). Sin peticiones: API-Football, que la daba, se
retiró el 22-oct-2026 (decisión del titular, 25-oct). Contra su última foto
(22-oct 06:40 UTC) el cálculo coincide equipo a equipo en las 19 ligas salvo
las sanciones de puntos, que van en `SANCIONES`.

Es una FOTO que se reemplaza (upsert y se borran los equipos que ya no
aparecen), no un histórico. Reglas:
- Temporada en curso con la misma etiqueta que `matches.season`; en los torneos
  cortos (Liga MX, Argentina) solo cuenta el torneo del semestre en curso.
- Cada equipo cuenta como mucho los partidos de su fase regular (`TOPE`): las
  eliminatorias (MLS, liguilla, playoffs) no tienen jornada en nuestros datos.
- Orden: puntos, diferencia de goles, goles a favor. Sin desempates de cara a
  cara: es una tabla de contexto, no la oficial.
- El grupo (conferencias de la MLS, zonas de Argentina) y la descripción de
  cada puesto se heredan de la foto anterior: los resultados no los dicen.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import httpx

from ..config import settings
from ..db import execute, executemany, query
from . import api_football as af
from .fixtures import _season_label

log = logging.getLogger(__name__)

FORMA_N = 5
# Torneos cortos: la tabla es la del semestre (Apertura jul-dic, Clausura ene-jun).
POR_SEMESTRE = {"ar.primera"}
# Partidos de la fase regular por equipo; el resto, ida y vuelta: 2·(equipos − 1).
TOPE = {"us.mls": 34, "mx.liga_mx": 17, "ar.primera": 16}
# (liga, temporada, team_id) -> puntos. Medido contra la foto de API-Football del 22-oct.
SANCIONES = {("gb.championship", "2627", 768): -4}   # Southampton


def season_label(start_year: int) -> str:
    """Misma etiqueta que el resto del sistema: 2026 -> '2627'."""
    return f"{start_year % 100:02d}{(start_year + 1) % 100:02d}"


def desde(liga: dict, ahora: datetime) -> datetime | None:
    """Inicio del torneo corto en curso; None si la temporada entera cuenta."""
    if liga["season_style"] == "apertura_clausura" or liga["league_id"] in POR_SEMESTRE:
        return ahora.replace(month=1 if ahora.month < 7 else 7, day=1, hour=0, minute=0,
                             second=0, microsecond=0)
    return None


def calcular(partidos: list[dict], grupos: dict[int, str], tope: int | None = None,
             sanciones: dict[int, int] | None = None) -> list[dict]:
    """Tabla por grupo desde partidos cerrados ordenados por fecha."""
    equipos = {p[k] for p in partidos for k in ("home_team_id", "away_team_id")}
    tope = tope or 2 * (len(equipos) - 1)
    t: dict[int, dict] = defaultdict(lambda: dict(puntos=0, jugados=0, ganados=0, empatados=0,
                                                  perdidos=0, goles_favor=0, goles_contra=0,
                                                  ultimos=[]))
    for p in partidos:
        lados = ((p["home_team_id"], p["home_goals"], p["away_goals"]),
                 (p["away_team_id"], p["away_goals"], p["home_goals"]))
        if any(t[tid]["jugados"] >= tope for tid, _, _ in lados):
            continue
        for tid, gf, gc in lados:
            f = t[tid]
            r = "W" if gf > gc else "D" if gf == gc else "L"
            f["jugados"] += 1
            f["goles_favor"] += gf
            f["goles_contra"] += gc
            f[{"W": "ganados", "D": "empatados", "L": "perdidos"}[r]] += 1
            f["puntos"] += {"W": 3, "D": 1, "L": 0}[r]
            f["ultimos"].append(r)
    for tid, puntos in (sanciones or {}).items():
        if tid in t:
            t[tid]["puntos"] += puntos
    por_grupo: dict[str, list] = defaultdict(list)
    for tid, f in t.items():
        por_grupo[grupos.get(tid, "")].append((tid, f))
    filas = []
    for grupo, lista in por_grupo.items():
        lista.sort(key=lambda x: (-x[1]["puntos"],
                                  -(x[1]["goles_favor"] - x[1]["goles_contra"]),
                                  -x[1]["goles_favor"], x[0]))
        for pos, (tid, f) in enumerate(lista, 1):
            filas.append({"grupo": grupo, "team_id": tid, "posicion": pos,
                          # El más reciente primero, como la daba API-Football.
                          "forma": "".join(reversed(f["ultimos"][-FORMA_N:])),
                          **{k: v for k, v in f.items() if k != "ultimos"}})
    return filas


def run(ahora: datetime | None = None) -> dict:
    ahora = ahora or datetime.now(timezone.utc)
    inicio = datetime.now(timezone.utc)
    ligas = query("""SELECT league_id, season_style FROM leagues
                     WHERE active AND NOT cross_league ORDER BY league_id""")
    resumen = {}
    for lg in ligas:
        temporada = _season_label(lg, ahora)
        corte = desde(lg, ahora)
        partidos = query(
            """SELECT home_team_id, away_team_id, home_goals, away_goals
               FROM matches
               WHERE league_id = %s AND season = %s AND status = 'finished'
                 AND home_goals IS NOT NULL AND away_goals IS NOT NULL
                 AND kickoff_utc <= %s AND (%s::timestamptz IS NULL OR kickoff_utc >= %s)
               ORDER BY kickoff_utc, match_id""",
            (lg["league_id"], temporada, ahora, corte, corte))
        previa = query("SELECT team_id, grupo, posicion, descripcion FROM standings "
                       "WHERE league_id = %s", (lg["league_id"],))
        grupos = {r["team_id"]: r["grupo"] for r in previa if r["grupo"]}
        descripcion = {(r["grupo"], r["posicion"]): r["descripcion"] for r in previa}
        sanciones = {tid: p for (liga, temp, tid), p in SANCIONES.items()
                     if liga == lg["league_id"] and temp == temporada}
        filas = calcular(partidos, grupos, TOPE.get(lg["league_id"]), sanciones)
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
            [(lg["league_id"], temporada, f["grupo"], f["team_id"], f["posicion"],
              f["puntos"], f["jugados"], f["ganados"], f["empatados"], f["perdidos"],
              f["goles_favor"], f["goles_contra"], f["forma"],
              descripcion.get((f["grupo"], f["posicion"]))) for f in filas],
        )
        # Equipos que ya no están en la foto (descendidos, otro torneo).
        execute("DELETE FROM standings WHERE league_id = %s AND updated_at < %s",
                (lg["league_id"], inicio))
        resumen[lg["league_id"]] = len(filas)
    # Ligas retiradas: su tabla dejó de actualizarse y la web no debe enseñarla vieja.
    execute("""DELETE FROM standings s USING leagues l
               WHERE l.league_id = s.league_id AND NOT l.active""")
    resultado = {"ligas": resumen, "escudos_nuevos": descargar_escudos()}
    af.record_health("standings", sum(resumen.values()), True, resultado)
    log.info("Clasificación: %s", resultado)
    return resultado


ESCUDO_URL = "https://media.api-sports.io/football/teams/{}.png"


def descargar_escudos(directorio: str | None = None) -> int:
    """
    Baja una sola vez el escudo de cada equipo con `af_team_id` y lo guarda
    como `<team_id>.png`. No se vuelve a pedir el que ya existe. La imagen
    del proveedor no consume cuota de la API.
    """
    carpeta = Path(directorio or settings.escudos_dir)
    carpeta.mkdir(parents=True, exist_ok=True)
    nuevos = 0
    with httpx.Client(timeout=20, follow_redirects=True) as c:
        for t in query("SELECT team_id, af_team_id FROM teams WHERE af_team_id IS NOT NULL"):
            destino = carpeta / f"{t['team_id']}.png"
            if destino.exists():
                continue
            try:
                r = c.get(ESCUDO_URL.format(t["af_team_id"]))
                r.raise_for_status()
            except httpx.HTTPError as exc:
                log.warning("Escudo de %s: %s", t["team_id"], exc)
                continue
            if not r.content.startswith(b"\x89PNG"):
                log.warning("Escudo de %s: no es PNG", t["team_id"])
                continue
            temporal = destino.with_suffix(".tmp")
            temporal.write_bytes(r.content)
            temporal.replace(destino)
            nuevos += 1
    return nuevos


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    print(run())
