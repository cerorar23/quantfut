"""Calendario y resultados desde el archivo compartido de PropLine (`/scores`), sin peticiones.

Sustituye a API-Football, que pasó al plan gratuito el 22-oct-2026 (decisión del titular, 24-oct).
El recolector horario guarda `/v1/sports/{sport}/scores` (próximos ~30 días y terminados de los
últimos 3) con nuestra hora real de recepción; aquí solo se lee.

Reglas que no se relajan:
- Nunca se da de alta un equipo. Un nombre que no resuelve queda en `unresolved_names` y su
  partido no se toca: un equipo duplicado parte su historial sin dar ningún error.
- En copas (`cross_league`) solo vale la coincidencia exacta, como en `fixtures._resolve`.
- Un partido solo se cierra con estado `final` y marcador entero; `result_recorded_at` es ahora.
- El marcador de PropLine es el del partido (en ligas no hay prórroga). En una eliminatoria con
  prórroga no se distinguiría: las copas que se modelan juegan la fase de liga hasta enero.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from rapidfuzz import fuzz

from ..db import execute, query, query_one
from ..normalize import _record_unresolved, match_team, register_alias, slugify
from .salud import record_health
from .fixtures import _build_match_id, _season_label
from .propline_ingest import ALIASES
from .propline_shared import newest, parse_time, read_stats, team_stats

log = logging.getLogger(__name__)

SOURCE = "odds_api"     # PropLine escribe los clubes como The Odds API: comparten alias.
APRENDIDO = "propline"  # Alias aprendidos al enlazar por pareja de equipos.
PAREJA_MIN = 85
FINAL = {"final"}
ANULADOS = {"cancelled", "canceled", "postponed", "abandoned", "suspended"}
# El recolector pide `/scores` cada pocas horas; más viejo que esto es un archivo parado.
MAX_EDAD_SCORES = 13 * 3600
VENTANA_EMPAREJAR = timedelta(hours=36)
VENTANA_DUPLICADO = timedelta(days=10)


def _ligas() -> list[dict]:
    rows = query("""SELECT league_id, odds_api_key, season_style, cross_league
                    FROM leagues WHERE active AND odds_api_key IS NOT NULL""")
    for r in rows:
        r["sport"] = ALIASES.get(r["odds_api_key"], r["odds_api_key"])
    return rows


def _scores(sport: str, now: datetime) -> tuple[list[dict] | None, dict | None]:
    events, receipt = newest(_archivo(), f"/v1/sports/{sport}/scores", now,
                             max_age_seconds=MAX_EDAD_SCORES)
    return ([e for e in events or [] if isinstance(e, dict) and e.get("id") and e.get("commence_time")],
            receipt)


def _archivo() -> str:
    from ..config import settings
    return settings.propline_archive


def equipo(liga: dict, nombre: str, registrar: bool = True) -> int | None:
    """Equipo del catálogo, o None. Exacto en copas; difuso aceptado solo dentro de la liga."""
    league = None if liga["cross_league"] else liga["league_id"]
    tid, cand, score = match_team(nombre, APRENDIDO, league)
    if tid and score >= 100.0:
        return tid
    tid, cand, score = match_team(nombre, SOURCE, league)
    if tid and (score >= 100.0 or not liga["cross_league"]):
        return tid
    if registrar:
        _record_unresolved(nombre, SOURCE, liga["league_id"], cand, score)
    return None


def parecido(nombre: str, conocidos: set[str]) -> float:
    s = slugify(nombre or "")
    return max((fuzz.token_set_ratio(s, c) for c in conocidos), default=0.0)


def _nombres(team_ids: list[int]) -> dict[int, set[str]]:
    out: dict[int, set[str]] = {t: set() for t in team_ids}
    for r in query("""SELECT team_id, canonical_name AS n FROM teams WHERE team_id = ANY(%s)
                      UNION SELECT team_id, alias FROM team_aliases WHERE team_id = ANY(%s)""",
                   (team_ids, team_ids)):
        out[r["team_id"]].add(slugify(r["n"]))
    return out


def por_pareja(eventos: list[dict], partido: dict, nombres: dict[int, set[str]]) -> dict | None:
    """
    El único evento a ±36 h cuyos DOS equipos se parecen a los del partido. Con un solo nombre
    parecido no basta: «Manchester City» y «Manchester United» comparten la mitad del nombre.
    """
    cands = [e for e in eventos
             if abs(parse_time(e["commence_time"]) - partido["kickoff_utc"]) <= VENTANA_EMPAREJAR
             and parecido(e.get("home_team"), nombres.get(partido["home_team_id"], set())) >= PAREJA_MIN
             and parecido(e.get("away_team"), nombres.get(partido["away_team_id"], set())) >= PAREJA_MIN]
    return cands[0] if len(cands) == 1 else None


def aprender(evento: dict, partido: dict) -> None:
    """Un evento enlazado por pareja enseña sus dos nombres (fuente propia, no la de The Odds API)."""
    register_alias(evento["home_team"], APRENDIDO, partido["home_team_id"])
    register_alias(evento["away_team"], APRENDIDO, partido["away_team_id"])


def _partido(liga: dict, evento: dict, home: int, away: int, ko: datetime) -> dict | None:
    """El partido nuestro de ese evento: por id de PropLine, o mismos equipos en ±36 h."""
    row = query_one("""SELECT match_id, kickoff_utc, status, external_ids FROM matches
                       WHERE league_id = %s AND external_ids ->> 'propline' = %s""",
                    (liga["league_id"], str(evento["id"])))
    if row:
        return row
    rows = query("""SELECT match_id, kickoff_utc, status, external_ids FROM matches
                    WHERE league_id = %s AND home_team_id = %s AND away_team_id = %s
                      AND kickoff_utc BETWEEN %s AND %s
                      AND NOT (external_ids ? 'propline')""",
                 (liga["league_id"], home, away, ko - VENTANA_EMPAREJAR, ko + VENTANA_EMPAREJAR))
    if len(rows) != 1:
        return None
    execute("""UPDATE matches SET external_ids = external_ids || jsonb_build_object('propline', %s::text)
               WHERE match_id = %s""", (str(evento["id"]), rows[0]["match_id"]))
    return rows[0]


def exacto(liga: dict, nombre: str) -> int | None:
    """Solo alias registrado o nombre canónico idéntico: lo que basta para crear un partido."""
    league = None if liga["cross_league"] else liga["league_id"]
    for source in (APRENDIDO, SOURCE):
        tid, _, score = match_team(nombre, source, league)
        if tid and score >= 100.0:
            return tid
    return None


def _no_dar_de_alta(liga: dict, ev: dict, eventos: list[dict], home: int, away: int,
                    ko: datetime) -> str | None:
    """
    Motivo para no crear el partido, o None. PropLine a veces publica el mismo cruce con local y
    visitante invertidos, o dos veces (medido el 25-oct: MLS y Eliteserien). Ante la duda no se crea:
    un partido duplicado o al revés deja predicciones y liquidaciones mal para siempre.
    """
    if exacto(liga, ev.get("home_team")) != home or exacto(liga, ev.get("away_team")) != away:
        return "nombre_no_exacto"
    if query_one("""SELECT 1 AS x FROM matches WHERE league_id = %s
                      AND ((home_team_id = %s AND away_team_id = %s) OR (home_team_id = %s AND away_team_id = %s))
                      AND kickoff_utc BETWEEN %s AND %s""",
                 (liga["league_id"], home, away, away, home, ko - VENTANA_DUPLICADO, ko + VENTANA_DUPLICADO)):
        return "cruce_ya_existe"
    for otro in eventos:
        if (str(otro["id"]) != str(ev["id"])
                and abs(parse_time(otro["commence_time"]) - ko) <= VENTANA_DUPLICADO
                and {equipo(liga, otro.get("home_team"), False), equipo(liga, otro.get("away_team"), False)}
                == {home, away}):
            return "evento_gemelo"
    return None


def _partido_por_pareja(liga: dict, evento: dict, ko: datetime) -> dict | None:
    """Partido nuestro sin enlazar a ±36 h cuyos dos equipos se parecen a los del evento (único)."""
    cands = query("""SELECT match_id, kickoff_utc, status, external_ids, home_team_id, away_team_id
                     FROM matches WHERE league_id = %s AND kickoff_utc BETWEEN %s AND %s
                       AND NOT (external_ids ? 'propline')""",
                  (liga["league_id"], ko - VENTANA_EMPAREJAR, ko + VENTANA_EMPAREJAR))
    if not cands:
        return None
    nombres = _nombres([c[k] for c in cands for k in ("home_team_id", "away_team_id")])
    hits = [c for c in cands if por_pareja([evento], c, nombres) is not None]
    if len(hits) != 1:
        return None
    execute("""UPDATE matches SET external_ids = external_ids || jsonb_build_object('propline', %s::text)
               WHERE match_id = %s""", (str(evento["id"]), hits[0]["match_id"]))
    aprender(evento, hits[0])
    return hits[0]


def calendario(now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    out = {"insertados": 0, "reprogramados": 0, "enlazados": 0, "sin_resolver": 0,
           "altas_rechazadas": {}, "reprogramados_detalle": [], "sin_archivo": [], "problemas": []}
    for liga in _ligas():
        eventos, receipt = _scores(liga["sport"], now)
        if receipt is None:
            out["sin_archivo"].append(liga["league_id"])
            continue
        for ev in eventos:
            estado = ev.get("status")
            ko = parse_time(ev["commence_time"])
            if estado != "upcoming" or ko <= now:
                continue
            home, away = equipo(liga, ev.get("home_team"), False), equipo(liga, ev.get("away_team"), False)
            if not home or not away or home == away:
                existente = _partido_por_pareja(liga, ev, ko)
                if existente is None:
                    equipo(liga, ev.get("home_team")), equipo(liga, ev.get("away_team"))  # a revisión
                    out["sin_resolver"] += 1
                    continue
            else:
                existente = _partido(liga, ev, home, away, ko)
            if existente:
                out["enlazados"] += int("propline" not in (existente["external_ids"] or {}))
                if existente["status"] == "finished":
                    continue
                if (abs((existente["kickoff_utc"] - ko).total_seconds()) > 300
                        or existente["status"] != "scheduled"):
                    execute("UPDATE matches SET kickoff_utc = %s, status = 'scheduled' WHERE match_id = %s",
                            (ko, existente["match_id"]))
                    # La reprogramación invalida las ventanas de cuotas ya capturadas.
                    execute("DELETE FROM odds_capture_log WHERE match_id = %s", (existente["match_id"],))
                    out["reprogramados"] += 1
                    out["reprogramados_detalle"].append(
                        [existente["match_id"], str(existente["kickoff_utc"]), str(ko)])
                continue
            motivo = _no_dar_de_alta(liga, ev, eventos, home, away, ko)
            if motivo:
                out["altas_rechazadas"][motivo] = out["altas_rechazadas"].get(motivo, 0) + 1
                continue
            nombres = {r["team_id"]: r["canonical_name"] for r in query(
                "SELECT team_id, canonical_name FROM teams WHERE team_id = ANY(%s)", ([home, away],))}
            match_id = _build_match_id(liga["league_id"], _season_label(liga, ko),
                                       nombres[home], nombres[away], ko)
            out["insertados"] += execute(
                """INSERT INTO matches (match_id, league_id, season, kickoff_utc, home_team_id,
                                        away_team_id, status, external_ids)
                   VALUES (%s, %s, %s, %s, %s, %s, 'scheduled', jsonb_build_object('propline', %s::text))
                   ON CONFLICT (match_id) DO NOTHING""",
                (match_id, liga["league_id"], _season_label(liga, ko), ko, home, away, str(ev["id"])))
    record_health("fixtures_propline", out["insertados"] + out["reprogramados"],
                     not out["problemas"], out)
    log.info("Calendario PropLine: %s", out)
    return out


def _marcador(ev: dict) -> tuple[int, int] | None:
    """Marcador entero de los dos lados; cualquier otra cosa (null, texto, bool) no cierra el partido."""
    vals = []
    for side in ("home_score", "away_score"):
        v = ev.get(side)
        if isinstance(v, str) and v.strip().isdigit():
            v = int(v.strip())
        if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v < 100:
            return None
        vals.append(v)
    return vals[0], vals[1]


def _corners(sport: str, evento_id: str, now: datetime) -> tuple[int | None, int | None]:
    """Córners del box score de PropLine si los dos lados se distinguen con certeza."""
    doc, receipt = read_stats(_archivo(), sport, evento_id, now)
    if receipt is None or not isinstance(doc, dict) or doc.get("status") not in FINAL:
        return None, None
    lados = team_stats(doc)
    vals = [lados.get(s, {}).get("corners") for s in ("home", "away")]
    if None in vals:
        return None, None
    return int(vals[0]), int(vals[1])


def resultados(now: datetime | None = None, hours_back: int = 72) -> dict:
    """Cierra los partidos ya jugados con el marcador final de PropLine y liquida."""
    now = now or datetime.now(timezone.utc)
    pendientes = query(
        """SELECT m.match_id, m.league_id, m.kickoff_utc, m.home_team_id, m.away_team_id,
                  m.external_ids ->> 'propline' AS propline_id
           FROM matches m JOIN leagues l USING (league_id)
           WHERE m.status IN ('scheduled', 'live', 'postponed') AND l.active
             AND m.kickoff_utc < %s - interval '105 minutes' AND m.kickoff_utc > %s""",
        (now, now - timedelta(hours=hours_back)))
    out = {"cerrados": 0, "anulados": 0, "abiertos": 0, "sin_evento": 0, "corners": 0}
    if not pendientes:
        record_health("results_propline", 0, True, {"note": "nada pendiente"})
        return out
    ligas = {l["league_id"]: l for l in _ligas()}
    por_liga: dict[str, list[dict]] = {}
    for p in pendientes:
        por_liga.setdefault(p["league_id"], []).append(p)
    for league_id, partidos in por_liga.items():
        liga = ligas.get(league_id)
        eventos, receipt = _scores(liga["sport"], now) if liga else ([], None)
        if receipt is None:
            out["sin_evento"] += len(partidos)
            continue
        usados = {r["pid"] for r in query(
            """SELECT external_ids ->> 'propline' AS pid FROM matches
               WHERE league_id = %s AND external_ids ? 'propline'""", (league_id,))}
        for p in partidos:
            ev = _evento_de(liga, p, eventos, usados)
            if ev is None:
                out["sin_evento"] += 1
                continue
            usados.add(str(ev["id"]))
            estado = ev.get("status")
            if estado in ANULADOS:
                execute("UPDATE matches SET status = 'postponed' WHERE match_id = %s", (p["match_id"],))
                from .results import _void_picks
                _void_picks(p["match_id"])
                out["anulados"] += 1
                continue
            marcador = _marcador(ev) if estado in FINAL else None
            if marcador is None:
                out["abiertos"] += 1
                continue
            hc, ac = _corners(liga["sport"], str(ev["id"]), now)
            out["corners"] += hc is not None
            execute(
                """UPDATE matches SET status = 'finished', home_goals = %s, away_goals = %s,
                          home_corners = COALESCE(%s, home_corners),
                          away_corners = COALESCE(%s, away_corners),
                          external_ids = external_ids || jsonb_build_object('propline', %s::text),
                          result_recorded_at = now()
                   WHERE match_id = %s AND status <> 'finished'""",
                (*marcador, hc, ac, str(ev["id"]), p["match_id"]))
            out["cerrados"] += 1
    settled = {}
    if out["cerrados"]:
        from ..eval.clv import settle_pending
        settled = settle_pending()
    out["settled"] = settled
    record_health("results_propline", out["cerrados"], True, out)
    log.info("Resultados PropLine: %s", out)
    return out


def _evento_de(liga: dict, partido: dict, eventos: list[dict], usados: set[str] = frozenset()) -> dict | None:
    """
    Evento de PropLine de un partido nuestro: su id; si no, los dos equipos resueltos en ±36 h
    (único); si no, la pareja de nombres parecidos (único, y se aprenden los alias). Nunca un
    evento ya enlazado a otro partido.
    """
    if partido["propline_id"]:
        return next((e for e in eventos if str(e["id"]) == partido["propline_id"]), None)
    libres = [e for e in eventos if str(e["id"]) not in usados]
    candidatos = []
    for ev in libres:
        ko = parse_time(ev["commence_time"])
        if abs(ko - partido["kickoff_utc"]) > VENTANA_EMPAREJAR:
            continue
        if (equipo(liga, ev.get("home_team"), False) == partido["home_team_id"]
                and equipo(liga, ev.get("away_team"), False) == partido["away_team_id"]):
            candidatos.append(ev)
    if len(candidatos) == 1:
        return candidatos[0]
    if candidatos:
        return None
    ev = por_pareja(libres, partido, _nombres([partido["home_team_id"], partido["away_team_id"]]))
    if ev is not None:
        aprender(ev, partido)
    return ev


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("accion", choices=["calendario", "resultados"])
    a = ap.parse_args()
    print(json.dumps(calendario() if a.accion == "calendario" else resultados(), default=str))
