"""
Fichas de partido para la web pública: agenda, forma, cara a cara,
promedios, clasificación, alineaciones y bajas.

Es CONTENIDO para que el sitio sea útil y atractivo (al estilo de las webs de
estadísticas), no criterio: ningún pick sale de aquí y el modelo no se
presenta como pronóstico. Todo se calcula desde la base; la única petición
extra a API-Football es la clasificación (`ingest/standings.py`, una por liga
y día). Las estadísticas ampliadas (posesión, faltas, tarjetas…) se guardan
al cerrar cada partido con la MISMA respuesta que ya pedía `results.py`.

Solo datos públicos: nada de picks de pago ni de tokens. Las funciones puras
(forma, promedios, cara a cara, normalización) van separadas de las
consultas para poder probarlas sin base de datos.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query

from ..db import query, query_one
from ..ingest.estadisticas import normalizar_estadisticas  # noqa: F401  (re-export)

router = APIRouter(prefix="/web", tags=["web pública"])

FORMA_N = 5          # últimos partidos en la racha
PROMEDIOS_N = 10     # partidos para los promedios
H2H_N = 10           # cruces directos
# La forma y los promedios solo miran atrás hasta aquí. Sin tope, un equipo
# cuya temporada anterior no está en la base (Segunda y Serie B no tienen
# histórico de football-data) enseñaba como "forma" partidos de hace más
# de un año en otra categoría. El cara a cara no lleva tope: es historia.
VENTANA_FORMA_DIAS = 270


# --------------------------------------------------------------------------
# Funciones puras
# --------------------------------------------------------------------------

def _desde(team_id: int, r: dict) -> dict:
    """Un partido visto desde `team_id`: goles a favor/en contra, rival…"""
    local = r["home_team_id"] == team_id
    lado, otro = ("home", "away") if local else ("away", "home")
    gf, gc = r[f"{lado}_goals"], r[f"{otro}_goals"]
    res = "G" if gf > gc else "E" if gf == gc else "P"

    def par(campo):
        return r.get(f"{lado}_{campo}"), r.get(f"{otro}_{campo}")

    return {"match_id": r["match_id"], "fecha": r["kickoff_utc"],
            "competicion": r.get("league_name") or r.get("league_id"),
            "local": local, "rival": r[f"{otro}_team"], "gf": gf, "gc": gc,
            "res": res, "marcador": f"{r['home_goals']}-{r['away_goals']}",
            "xg": par("xg"), "tiros": par("shots"),
            "tiros_puerta": par("shots_target"), "corners": par("corners")}


def forma(team_id: int, filas: list[dict], n: int = FORMA_N) -> dict:
    """Últimos `n` resultados (filas ordenadas del más reciente al más antiguo)."""
    partidos = [_desde(team_id, r) for r in filas[:n]]
    cuenta = {k: sum(p["res"] == k for p in partidos) for k in ("G", "E", "P")}
    return {"partidos": partidos,
            "resumen": {**cuenta, "gf": sum(p["gf"] for p in partidos),
                        "gc": sum(p["gc"] for p in partidos),
                        "puntos": 3 * cuenta["G"] + cuenta["E"],
                        "racha": "".join(p["res"] for p in partidos),
                        "n": len(partidos)}}


def _media(valores: list) -> float | None:
    vals = [v for v in valores if v is not None]
    return sum(vals) / len(vals) if vals else None


def _bloque(ps: list[dict]) -> dict:
    if not ps:
        return {"n": 0}
    pct = lambda cond: 100.0 * sum(1 for p in ps if cond(p)) / len(ps)  # noqa: E731
    return {
        "n": len(ps),
        "goles_favor": _media([p["gf"] for p in ps]),
        "goles_contra": _media([p["gc"] for p in ps]),
        "xg_favor": _media([p["xg"][0] for p in ps]),
        "xg_contra": _media([p["xg"][1] for p in ps]),
        "tiros_favor": _media([p["tiros"][0] for p in ps]),
        "tiros_contra": _media([p["tiros"][1] for p in ps]),
        "tiros_puerta_favor": _media([p["tiros_puerta"][0] for p in ps]),
        "corners_favor": _media([p["corners"][0] for p in ps]),
        "corners_contra": _media([p["corners"][1] for p in ps]),
        "pct_ambos_marcan": pct(lambda p: p["gf"] > 0 and p["gc"] > 0),
        "pct_mas_2_5": pct(lambda p: p["gf"] + p["gc"] > 2.5),
        "pct_porteria_cero": pct(lambda p: p["gc"] == 0),
    }


def promedios(team_id: int, filas: list[dict]) -> dict:
    """Promedios en todos los partidos, en casa y fuera. `None` si falta el dato."""
    ps = [_desde(team_id, r) for r in filas]
    return {"todos": _bloque(ps),
            "casa": _bloque([p for p in ps if p["local"]]),
            "fuera": _bloque([p for p in ps if not p["local"]])}


def cara_a_cara(home_id: int, away_id: int, filas: list[dict]) -> dict:
    """
    Cruces directos. 'victorias_local' son las del equipo que juega EN CASA el
    partido analizado, aunque en cada cruce antiguo jugara de visitante.
    """
    partidos = [_desde(home_id, r) for r in filas]
    if not partidos:
        return {"partidos": [], "resumen": {"n": 0}}
    n = len(partidos)
    return {"partidos": partidos,
            "resumen": {"n": n,
                        "victorias_local": sum(p["res"] == "G" for p in partidos),
                        "empates": sum(p["res"] == "E" for p in partidos),
                        "victorias_visitante": sum(p["res"] == "P" for p in partidos),
                        "goles_media": sum(p["gf"] + p["gc"] for p in partidos) / n,
                        "pct_ambos_marcan": 100.0 * sum(p["gf"] > 0 and p["gc"] > 0
                                                        for p in partidos) / n,
                        "pct_mas_2_5": 100.0 * sum(p["gf"] + p["gc"] > 2.5
                                                   for p in partidos) / n}}


# --------------------------------------------------------------------------
# Consultas
# --------------------------------------------------------------------------

_COLS = """m.match_id, m.kickoff_utc, m.league_id, l.name AS league_name,
           m.home_team_id, m.away_team_id,
           COALESCE(th.display_name, th.canonical_name) AS home_team,
           COALESCE(ta.display_name, ta.canonical_name) AS away_team,
           m.home_goals, m.away_goals, m.home_xg, m.away_xg,
           m.home_shots, m.away_shots, m.home_shots_target, m.away_shots_target,
           m.home_corners, m.away_corners"""
_FROM = """FROM matches m
           JOIN leagues l ON l.league_id = m.league_id
           JOIN teams th ON th.team_id = m.home_team_id
           JOIN teams ta ON ta.team_id = m.away_team_id"""
_TERMINADO = "m.status = 'finished' AND m.home_goals IS NOT NULL"

# Caché en memoria por proceso: la web pide lo mismo muchas veces y los datos
# cambian cada pocas horas, no cada segundo.
_cache: dict[tuple, tuple[float, object]] = {}


def _cacheado(clave: tuple, ttl: float, calcular):
    ahora = time.monotonic()
    hit = _cache.get(clave)
    if hit and hit[0] > ahora:
        return hit[1]
    valor = calcular()
    if len(_cache) > 500:
        _cache.clear()
    _cache[clave] = (ahora + ttl, valor)
    return valor


def _ultimos(team_id: int, antes: datetime, n: int) -> list[dict]:
    return query(
        f"""SELECT {_COLS} {_FROM}
            WHERE (m.home_team_id = %s OR m.away_team_id = %s)
              AND {_TERMINADO} AND m.kickoff_utc < %s
              AND m.kickoff_utc > %s
            ORDER BY m.kickoff_utc DESC LIMIT %s""",
        (team_id, team_id, antes, antes - timedelta(days=VENTANA_FORMA_DIAS), n),
    )


def _cruces(a: int, b: int, antes: datetime, n: int) -> list[dict]:
    return query(
        f"""SELECT {_COLS} {_FROM}
            WHERE ((m.home_team_id = %s AND m.away_team_id = %s)
                OR (m.home_team_id = %s AND m.away_team_id = %s))
              AND {_TERMINADO} AND m.kickoff_utc < %s
            ORDER BY m.kickoff_utc DESC LIMIT %s""",
        (a, b, b, a, antes, n),
    )


def _posicion(team_id: int, league_id: str) -> dict | None:
    """Puesto en la tabla de la competición; en copas, el de su liga doméstica."""
    return query_one(
        """SELECT s.league_id, l.name AS liga, s.grupo, s.posicion, s.puntos,
                  s.jugados, s.ganados, s.empatados, s.perdidos,
                  s.goles_favor, s.goles_contra, s.forma, s.descripcion
           FROM standings s JOIN leagues l ON l.league_id = s.league_id
           WHERE s.team_id = %s
           ORDER BY (s.league_id = %s) DESC, s.grupo LIMIT 1""",
        (team_id, league_id),
    )


def _tabla(league_id: str) -> list[dict]:
    return query(
        """SELECT s.grupo, s.posicion, s.team_id,
                  COALESCE(t.display_name, t.canonical_name) AS equipo,
                  s.puntos, s.jugados, s.ganados, s.empatados, s.perdidos,
                  s.goles_favor, s.goles_contra, s.forma, s.descripcion,
                  s.updated_at
           FROM standings s JOIN teams t ON t.team_id = s.team_id
           WHERE s.league_id = %s
           ORDER BY s.grupo, s.posicion""",
        (league_id,),
    )


def _alineaciones(match_id: str) -> dict:
    filas = query(
        """SELECT DISTINCT ON (side) side, formation, starters, captured_at
           FROM lineups WHERE match_id = %s
           ORDER BY side, captured_at DESC""",
        (match_id,),
    )
    return {f["side"]: {"formacion": f["formation"], "titulares": f["starters"],
                        "capturada": f["captured_at"]} for f in filas}


def _bajas(match_id: str) -> dict | None:
    """
    Bajas de la ÚLTIMA comprobación. Cada fila lleva su propia hora de
    inserción, así que la comprobación se delimita con el registro de
    capturas: lo insertado entre la penúltima y la última. Si la última no
    encontró a nadie, no hay bajas aunque una anterior sí las tuviera.
    """
    log = query(
        """SELECT captured_at, n_reported FROM injuries_capture_log
           WHERE match_id = %s ORDER BY captured_at DESC LIMIT 2""",
        (match_id,),
    )
    if not log:
        return None
    ultima = log[0]
    salida = {"comprobada": ultima["captured_at"], "home": [], "away": []}
    if not ultima["n_reported"]:
        return salida
    previa = (log[1]["captured_at"] if len(log) > 1
              else datetime(1970, 1, 1, tzinfo=timezone.utc))
    for f in query(
        """SELECT side, player_name, status_type, reason FROM injuries
           WHERE match_id = %s AND captured_at > %s AND captured_at <= %s
           ORDER BY side, player_name""",
        (match_id, previa, ultima["captured_at"]),
    ):
        salida[f["side"]].append({"jugador": f["player_name"],
                                  "tipo": f["status_type"], "motivo": f["reason"]})
    return salida


def _agenda(inicio: datetime, fin: datetime, liga: str | None) -> list[dict]:
    partidos = query(
        f"""SELECT m.match_id, m.kickoff_utc, m.status, m.league_id,
                   l.name AS liga, l.country AS pais,
                   m.home_team_id, m.away_team_id,
                   COALESCE(th.display_name, th.canonical_name) AS local,
                   COALESCE(ta.display_name, ta.canonical_name) AS visitante,
                   m.home_goals, m.away_goals,
                   ph.posicion AS pos_local, pa.posicion AS pos_visitante
            {_FROM}
            LEFT JOIN LATERAL (
                SELECT posicion FROM standings s WHERE s.team_id = m.home_team_id
                ORDER BY (s.league_id = m.league_id) DESC, s.grupo LIMIT 1) ph ON TRUE
            LEFT JOIN LATERAL (
                SELECT posicion FROM standings s WHERE s.team_id = m.away_team_id
                ORDER BY (s.league_id = m.league_id) DESC, s.grupo LIMIT 1) pa ON TRUE
            WHERE l.active AND m.kickoff_utc >= %s AND m.kickoff_utc < %s
              AND (%s::text IS NULL OR m.league_id = %s)
            ORDER BY m.kickoff_utc, l.name, m.match_id""",
        (inicio, fin, liga, liga),
    )
    if not partidos:
        return []
    # Racha de los 5 partidos ANTERIORES a cada uno, en una sola consulta.
    rachas: dict[tuple[str, str], str] = {}
    for f in query(
        f"""SELECT m.match_id, s.side, x.res
            FROM matches m
            CROSS JOIN LATERAL (VALUES ('home', m.home_team_id),
                                       ('away', m.away_team_id)) s(side, team_id)
            CROSS JOIN LATERAL (
                SELECT m2.kickoff_utc,
                       CASE WHEN m2.home_goals = m2.away_goals THEN 'E'
                            WHEN (m2.home_team_id = s.team_id)
                               = (m2.home_goals > m2.away_goals) THEN 'G'
                            ELSE 'P' END AS res
                FROM matches m2
                WHERE (m2.home_team_id = s.team_id OR m2.away_team_id = s.team_id)
                  AND m2.status = 'finished' AND m2.home_goals IS NOT NULL
                  AND m2.kickoff_utc < m.kickoff_utc
                  AND m2.kickoff_utc > m.kickoff_utc
                                       - make_interval(days => {VENTANA_FORMA_DIAS})
                ORDER BY m2.kickoff_utc DESC LIMIT {FORMA_N}) x
            WHERE m.match_id = ANY(%s)
            ORDER BY m.match_id, s.side, x.kickoff_utc DESC""",
        ([p["match_id"] for p in partidos],),
    ):
        clave = (f["match_id"], f["side"])
        rachas[clave] = rachas.get(clave, "") + f["res"]
    salida = []
    for p in partidos:
        terminado = p["status"] == "finished" and p["home_goals"] is not None
        salida.append({
            "match_id": p["match_id"], "kickoff_utc": p["kickoff_utc"],
            "estado": p["status"],
            "liga": {"id": p["league_id"], "nombre": p["liga"], "pais": p["pais"]},
            "marcador": [p["home_goals"], p["away_goals"]] if terminado else None,
            "local": {"id": p["home_team_id"], "nombre": p["local"],
                      "posicion": p["pos_local"],
                      "racha": rachas.get((p["match_id"], "home"), "")},
            "visitante": {"id": p["away_team_id"], "nombre": p["visitante"],
                          "posicion": p["pos_visitante"],
                          "racha": rachas.get((p["match_id"], "away"), "")},
        })
    return salida


def _ficha(match_id: str) -> dict | None:
    m = query_one(
        f"""SELECT {_COLS}, m.status, m.season, m.home_goals_ht, m.away_goals_ht,
                   m.stats, l.country AS pais, l.cross_league
            {_FROM}
            WHERE m.match_id = %s AND l.active""",
        (match_id,),
    )
    if not m:
        return None
    ko = m["kickoff_utc"]
    equipos = {}
    for lado in ("home", "away"):
        tid = m[f"{lado}_team_id"]
        filas = _ultimos(tid, ko, PROMEDIOS_N)
        equipos[lado] = {"id": tid, "nombre": m[f"{lado}_team"],
                         "forma": forma(tid, filas),
                         "promedios": promedios(tid, filas),
                         "clasificacion": _posicion(tid, m["league_id"])}
    terminado = m["status"] == "finished" and m["home_goals"] is not None
    return {
        "partido": {
            "match_id": m["match_id"], "kickoff_utc": ko, "estado": m["status"],
            "temporada": m["season"],
            "liga": {"id": m["league_id"], "nombre": m["league_name"],
                     "pais": m["pais"], "copa": m["cross_league"]},
            "marcador": [m["home_goals"], m["away_goals"]] if terminado else None,
            "descanso": ([m["home_goals_ht"], m["away_goals_ht"]]
                         if terminado and m["home_goals_ht"] is not None else None),
            "xg": [m["home_xg"], m["away_xg"]] if m["home_xg"] is not None else None,
            "estadisticas": m["stats"],
        },
        "local": equipos["home"],
        "visitante": equipos["away"],
        "cara_a_cara": cara_a_cara(m["home_team_id"], m["away_team_id"],
                                   _cruces(m["home_team_id"], m["away_team_id"],
                                           ko, H2H_N)),
        "tabla": None if m["cross_league"] else _tabla(m["league_id"]),
        "alineaciones": _alineaciones(match_id),
        "bajas": _bajas(match_id),
    }


def ventana(fecha: str | None, tz: int, dias: int,
            ahora: datetime | None = None) -> tuple[datetime, datetime]:
    """Día LOCAL del visitante (desfase `tz` en minutos) como intervalo UTC."""
    if fecha:
        dia = datetime.strptime(fecha, "%Y-%m-%d")
    else:
        dia = (ahora or datetime.now(timezone.utc)) + timedelta(minutes=tz)
    inicio = (datetime(dia.year, dia.month, dia.day, tzinfo=timezone.utc)
              - timedelta(minutes=tz))
    return inicio, inicio + timedelta(days=dias)


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------

@router.get("/partidos")
def partidos(fecha: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$",
                                       description="Día local, YYYY-MM-DD"),
             dias: int = Query(1, ge=1, le=7),
             tz: int = Query(0, ge=-720, le=840,
                             description="Desfase del visitante respecto a UTC, en minutos"),
             liga: str | None = Query(None, max_length=40)):
    """Agenda de partidos con racha y puesto en la tabla de cada equipo."""
    try:
        inicio, fin = ventana(fecha, tz, dias)
    except ValueError:
        raise HTTPException(422, "Fecha inválida") from None
    lista = _cacheado(("agenda", inicio, dias, liga), 120,
                      lambda: _agenda(inicio, fin, liga))
    return {"desde": inicio, "hasta": fin, "partidos": lista}


@router.get("/partidos/{match_id}")
def ficha(match_id: str):
    """Ficha completa: forma, promedios, cara a cara, tabla, alineaciones y bajas."""
    if len(match_id) > 120:
        raise HTTPException(404, "Partido no encontrado")
    datos = _cacheado(("ficha", match_id), 300, lambda: _ficha(match_id))
    if datos is None:
        raise HTTPException(404, "Partido no encontrado")
    return datos
