"""
Normalización de nombres de equipos entre fuentes.

Causa número uno de bugs silenciosos en estos sistemas: 'Man United' en
football-data, 'Manchester United' en The Odds API, 'Manchester Utd' en
API-Football. Si el join falla no se rompe nada: simplemente pierdes partidos
sin enterarte.

Estrategia en tres niveles, de más a menos fiable:
  1. Alias exacto registrado para esa fuente.
  2. Nombre canónico exacto (tras slugify).
  3. Coincidencia difusa por encima de un umbral, dentro de la misma liga.

Todo lo que no llegue al umbral se registra en `unresolved_names` con su mejor
candidato y su puntuación, para que lo revises a mano. Nunca se adivina en
silencio.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from functools import lru_cache

from rapidfuzz import fuzz, process

from .db import execute, query, query_one

log = logging.getLogger(__name__)

# Umbral de auto-aceptación. Por debajo va a revisión manual.
AUTO_ACCEPT = 90
SUGGEST_FLOOR = 60

_NOISE = re.compile(
    r"\b(fc|cf|afc|cd|ud|sc|ac|as|ss|sv|if|bk|club|deportivo|"
    r"futbol|football|soccer|sad|ssd|calcio|cp|rc|ca)\b",
    re.IGNORECASE,
)
_EXPAND = {
    "utd": "united", "man": "manchester", "atl": "atletico",
    "sptg": "sporting", "wolves": "wolverhampton", "spurs": "tottenham",
    "psg": "paris saint germain", "inter": "internazionale",
}


def slugify(name: str) -> str:
    s = unicodedata.normalize("NFKD", str(name))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("&", "and").replace(".", " ").replace("-", " ")
    s = _NOISE.sub(" ", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    tokens = [_EXPAND.get(t, t) for t in s.split()]
    return " ".join(tokens).strip()


@lru_cache(maxsize=32)
def _alias_map(source: str) -> dict[str, set[int]]:
    """
    {slug: {team_id, ...}}. Un slug puede ser de dos clubes: 'Vitoria'
    (Brasil) y 'Vitória SC' (Guimarães) dan el mismo. Con un id por slug
    ganaba el que hubiera y el Guimarães acabó en un partido de la Primeira
    como el Vitória brasileño (27-sep).
    """
    rows = query(
        """SELECT alias, team_id FROM team_aliases
           WHERE source = %s AND team_id IS NOT NULL""",
        (source,),
    )
    out: dict[str, set[int]] = {}
    for r in rows:
        out.setdefault(slugify(r["alias"]), set()).add(r["team_id"])
    return out


@lru_cache(maxsize=1)
def _paises() -> tuple[dict[int, tuple[str, str]], dict[str, str]]:
    """({team_id: (liga, país)}, {liga: país})."""
    ligas = {r["league_id"]: r["country"]
             for r in query("SELECT league_id, country FROM leagues")}
    equipos = {r["team_id"]: (r["league_id"], ligas.get(r["league_id"]))
               for r in query("SELECT team_id, league_id FROM teams")}
    return equipos, ligas


def _alias_valido(ids: set[int], league_id: str | None) -> int | None:
    """
    El único equipo del alias que puede jugar en `league_id`: su liga o una
    división del mismo país. Sin liga (copas) el alias tiene que ser de un
    solo club; si hay dos, no se adivina.
    """
    if not ids:
        return None
    if league_id is None:
        return next(iter(ids)) if len(ids) == 1 else None
    equipos, ligas = _paises()
    pais = ligas.get(league_id)
    validos = [t for t in ids
               if t not in equipos            # alta posterior a la caché
               or equipos[t][0] == league_id
               or (pais is not None and equipos[t][1] == pais)]
    return validos[0] if len(validos) == 1 else None


@lru_cache(maxsize=32)
def _league_teams(league_id: str | None) -> dict[str, int]:
    if league_id:
        rows = query("SELECT team_id, canonical_name FROM teams WHERE league_id = %s",
                     (league_id,))
    else:
        rows = query("SELECT team_id, canonical_name FROM teams")
    return {slugify(r["canonical_name"]): r["team_id"] for r in rows}


@lru_cache(maxsize=32)
def _sibling_teams(league_id: str) -> dict[str, set[int]]:
    """
    Equipos de las OTRAS ligas domésticas del mismo país, por nombre canónico
    y por cualquier alias de cualquier fuente: {slug: {team_id, ...}}. Un slug
    con dos ids es ambiguo y nunca se elige solo.
    """
    rows = query(
        """WITH hermanas AS (
               SELECT l.league_id FROM leagues l JOIN leagues me ON me.league_id = %s
               WHERE l.country = me.country AND l.league_id <> me.league_id
                 AND NOT l.cross_league)
           SELECT t.team_id, t.canonical_name AS name
           FROM teams t JOIN hermanas USING (league_id)
           UNION
           SELECT a.team_id, a.alias
           FROM team_aliases a JOIN teams t ON t.team_id = a.team_id
           JOIN hermanas h ON h.league_id = t.league_id""",
        (league_id,),
    )
    out: dict[str, set[int]] = {}
    for r in rows:
        out.setdefault(slugify(r["name"]), set()).add(r["team_id"])
    return out


def _match_sibling(raw: str, league_id: str) -> tuple[int | None, str | None, float]:
    """
    (team_id, candidato, score) en otra división del mismo país. Solo acepta
    la coincidencia EXACTA de un único club: entre ligas el difuso ya colocó
    una vez un club encima de otro (ver tests/test_resolve_exacto.py).
    """
    pool = _sibling_teams(league_id)
    if not pool:
        return None, None, 0.0
    key = slugify(raw)
    ids = pool.get(key)
    if ids:
        return (next(iter(ids)) if len(ids) == 1 else None), key, 100.0
    best = process.extractOne(key, list(pool.keys()), scorer=fuzz.token_sort_ratio)
    if best is None:
        return None, None, 0.0
    return None, best[0], float(best[1])


def clear_cache() -> None:
    _alias_map.cache_clear()
    _paises.cache_clear()
    _league_teams.cache_clear()
    _sibling_teams.cache_clear()


def match_team(raw: str, source: str, league_id: str | None = None
               ) -> tuple[int | None, str | None, float]:
    """Devuelve (team_id, mejor_candidato_slug, score). team_id None = sin resolver."""
    if not raw:
        return None, None, 0.0
    key = slugify(raw)

    tid = _alias_valido(_alias_map(source).get(key, set()), league_id)
    if tid:
        return tid, key, 100.0

    pool = _league_teams(league_id)
    if key in pool:
        return pool[key], key, 100.0

    if not pool:
        return None, None, 0.0

    best = process.extractOne(key, list(pool.keys()), scorer=fuzz.token_sort_ratio)
    if best is None:
        return None, None, 0.0
    cand, score = best[0], float(best[1])
    if score >= AUTO_ACCEPT:
        return pool[cand], cand, score
    return None, cand if score >= SUGGEST_FLOOR else None, score


def resolve_team(raw: str, source: str, league_id: str | None = None,
                 exact: bool = True, seen_in: str | None = None) -> str | None:
    """Nombre canónico, o None. Registra los fallos para revisión.

    `exact=True` (el valor por defecto) exige alias registrado o nombre
    canónico idéntico. Es obligatorio cuando no se acota por liga: buscando en
    las 13 competiciones a la vez el difuso empareja 'Rangers' con 'Angers'
    (92 puntos) y 'Atletico Madrid' con 'Atlético MG', y como los match
    difusos aceptados se registran como alias, el error queda grabado.

    `seen_in` solo anota en qué competición apareció un nombre sin resolver;
    no acota el emparejamiento (eso es `league_id`, y acotar por una copa
    dejaría la búsqueda sin equipos).
    """
    tid, cand, score = match_team(raw, source, league_id)
    if tid and exact and score < 100.0:
        tid, cand = None, cand or slugify(raw)
    if tid:
        row = query_one("SELECT canonical_name FROM teams WHERE team_id = %s", (tid,))
        if score < 100.0:
            register_alias(raw, source, tid)  # aprende del match difuso aceptado
        return row["canonical_name"] if row else None
    _record_unresolved(raw, source, league_id or seen_in, cand, score)
    return None


def resolve_or_register(raw: str, source: str, league_id: str) -> int | None:
    """
    Como resolve_team, pero si el equipo no existe en esa liga lo CREA.
    Se usa en la ingesta de calendario, donde un recién ascendido es legítimo.

    Solo crea cuando la mejor coincidencia está claramente por debajo del
    umbral: si hay un candidato razonable, prefiere fallar y avisar antes que
    duplicar un equipo existente escrito de otra forma. Un equipo duplicado
    parte su historial en dos y arruina la estimación de fuerza sin dar error.
    """
    tid, cand, score = match_team(raw, source, league_id)
    if tid:
        if score < 100.0:
            register_alias(raw, source, tid)
        return tid

    # Un club que sube o baja entre ligas del catálogo YA existe en la otra
    # división del mismo país: se reutiliza, no se duplica.
    sib_tid, sib_cand, sib_score = _match_sibling(raw, league_id)
    if sib_tid:
        register_alias(raw, source, sib_tid)
        log.info("'%s' (%s) reutiliza el equipo %s de otra división del mismo país",
                 raw, league_id, sib_tid)
        return sib_tid
    if sib_score > score:
        cand, score = sib_cand, sib_score

    if score >= SUGGEST_FLOOR:
        _record_unresolved(raw, source, league_id, cand, score)
        log.warning("'%s' (%s) se parece a '%s' (%.0f) pero no llega al umbral. "
                    "No se crea equipo nuevo; revísalo a mano.",
                    raw, source, cand, score)
        return None

    canonical = str(raw).strip()
    execute(
        """INSERT INTO teams (league_id, canonical_name) VALUES (%s, %s)
           ON CONFLICT (league_id, canonical_name) DO NOTHING""",
        (league_id, canonical),
    )
    row = query_one(
        "SELECT team_id FROM teams WHERE league_id = %s AND canonical_name = %s",
        (league_id, canonical),
    )
    if not row:
        return None
    clear_cache()
    register_alias(raw, source, row["team_id"])
    log.info("Equipo nuevo creado: %s (%s / %s)", canonical, league_id, source)
    return row["team_id"]


def register_alias(alias: str, source: str, team_id: int) -> None:
    execute(
        """INSERT INTO team_aliases (alias, source, team_id) VALUES (%s, %s, %s)
           ON CONFLICT (alias, source) DO UPDATE SET team_id = EXCLUDED.team_id""",
        (str(alias).strip(), source, team_id),
    )
    execute("UPDATE unresolved_names SET resolved = TRUE "
            "WHERE raw_name = %s AND source = %s", (str(alias).strip(), source))
    _alias_map.cache_clear()


def _record_unresolved(raw: str, source: str, league_id: str | None,
                       cand: str | None, score: float) -> None:
    execute(
        """INSERT INTO unresolved_names
             (raw_name, source, league_id, best_guess, score)
           VALUES (%s, %s, %s, %s, %s)
           ON CONFLICT (raw_name, source) DO UPDATE
             SET occurrences = unresolved_names.occurrences + 1,
                 last_seen = now(),
                 -- Una liga doméstica pisa a una copa: es la que hace alarmar.
                 league_id = CASE
                     WHEN EXISTS (SELECT 1 FROM leagues l
                                  WHERE l.league_id = EXCLUDED.league_id
                                    AND NOT l.cross_league)
                         THEN EXCLUDED.league_id
                     ELSE COALESCE(unresolved_names.league_id, EXCLUDED.league_id)
                 END,
                 best_guess = EXCLUDED.best_guess,
                 score = EXCLUDED.score""",
        (str(raw).strip(), source, league_id, cand, score),
    )


def pending_report() -> list[dict]:
    return query(
        """SELECT raw_name, source, league_id, best_guess, score, occurrences
           FROM unresolved_names WHERE NOT resolved
           ORDER BY occurrences DESC, score DESC"""
    )
