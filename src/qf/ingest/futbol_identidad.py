"""Identidad única de jugador: enlaza los ids de FotMob y de API-Football con el id canónico (SofaScore).

Cada fuente numera a sus jugadores a su manera y el motor arrastra la fuerza de cada jugador por su id.
El id canónico es el de SofaScore (formato de referencia; SportsAPIPro ya usa los mismos). Los enlaces salen
de evidencia, nunca de adivinar:

  * FotMob <-> SofaScore: el mismo partido, el mismo lado y el mismo nombre normalizado (o el nombre corto de
    SofaScore contenido en el nombre completo de FotMob). Un par (id FotMob, id SofaScore) se acepta si se
    repite en 2 o más partidos y ninguna otra pareja compite; con una sola aparición solo si ese id de FotMob
    no tiene más partidos en los que confirmarse. Los conflictos quedan sin enlazar (conservan su id propio).
  * API-Football <-> FotMob: el puente `puente_jugador` ya existente, solo los de confianza `alta`.

Lo que no se enlaza no se pierde: recibe un id canónico negativo y determinista (`futbol.id_sintetico`) y
`futbol.vincular_jugador` lo pasa al id de SofaScore cuando aparezca la pareja.

    python -m qf.ingest.futbol_identidad --archive ~/sofascore-scraper/data/v3 [--aplicar]
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter, defaultdict

from .sofascore_local import match_dir, read_match

CHUNK = 400


def _plain(name):
    text = unicodedata.normalize('NFKD', (name or '').lower())
    return ''.join(c for c in text if not unicodedata.combining(c))


def name_key(name):
    return re.sub(r'[^a-z0-9]', '', _plain(name))


def name_tokens(name):
    return frozenset(t for t in re.split(r'[^a-z0-9]+', _plain(name)) if len(t) > 1)


def match_players(fotmob_players, sofascore_players):
    """Parejas (id FotMob, id SofaScore) de un partido y lado. Los casos ambiguos se descartan.

    fotmob_players: [(id, nombre)]; sofascore_players: [(id, nombre, nombre_corto)].
    """
    by_key = defaultdict(list)
    for fid, name in fotmob_players:
        by_key[name_key(name)].append(fid)
    pairs = []
    for sid, name, short in sofascore_players:
        hits = by_key.get(name_key(name), [])
        if not hits:
            wanted = name_tokens(short)
            hits = [fid for fid, fname in fotmob_players if wanted and wanted <= name_tokens(fname)]
        if len(hits) == 1:
            pairs.append((hits[0], sid))
    return pairs


def decide_links(pairs, appearances):
    """{id FotMob: (id SofaScore, partidos)} con la regla de evidencia descrita arriba."""
    per_fotmob = defaultdict(Counter)
    for (fid, sid), count in pairs.items():
        per_fotmob[fid][sid] += count
    links = {}
    for fid, counter in per_fotmob.items():
        ranked = counter.most_common(2) + [(None, 0)]
        (top, top_n), (_second, second_n) = ranked[0], ranked[1]
        if second_n:
            continue  # conflicto: sin enlace
        if top_n >= 2 or (top_n == 1 and appearances.get(fid, 0) <= 1):
            links[fid] = (top, top_n)
    return links


def collect(connection, archive):
    """Recorre los partidos de SofaScore cargados en `futbol.partido_fuente` y junta la evidencia."""
    matches = connection.execute(
        "SELECT match_id, source_match_id FROM futbol.partido_fuente WHERE fuente = 'sofascore' ORDER BY match_id"
    ).fetchall()
    pairs, sofascore_names = Counter(), {}
    for start in range(0, len(matches), CHUNK):
        chunk = matches[start:start + CHUNK]
        fotmob = defaultdict(list)
        for match_id, side, fid, name in connection.execute(
                "SELECT match_id, side, jugador_id, nombre FROM fotmob_jugador_partido WHERE match_id = ANY(%s)",
                ([m for m, _ in chunk],)):
            fotmob[(match_id, side)].append((fid, name))
        for match_id, source_id in chunk:
            try:
                blocks, _states, _manifest = read_match(match_dir(archive, source_id))
            except (OSError, ValueError):
                continue
            lineups = blocks.get('lineups') or {}
            for side in ('home', 'away'):
                players = []
                for entry in (lineups.get(side) or {}).get('players') or []:
                    who = entry.get('player') or {}
                    if isinstance(who.get('id'), int) and who.get('name'):
                        players.append((who['id'], who['name'], who.get('shortName') or who['name']))
                        sofascore_names[who['id']] = who['name']
                for fid, sid in match_players(fotmob.get((match_id, side), []), players):
                    pairs[(fid, sid)] += 1
    return pairs, sofascore_names


def apply_links(connection, sofascore_names, links):
    """Registra a los jugadores de SofaScore y enlaza FotMob y API-Football. Devuelve contadores."""
    for sid, name in sofascore_names.items():
        connection.execute("INSERT INTO futbol.jugador (jugador_id, nombre) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                           (sid, name))
        connection.execute("""INSERT INTO futbol.jugador_fuente_id (fuente, id_en_fuente, jugador_id, evidencia)
                              VALUES ('sofascore',%s,%s,'id_canonico') ON CONFLICT DO NOTHING""", (sid, sid))
    moved = 0
    for fid, (sid, count) in links.items():
        moved += connection.execute("SELECT futbol.vincular_jugador('fotmob',%s,%s,'nombre_en_partido',%s)",
                                    (fid, sid, count)).fetchone()[0] or 0
    linked_af = 0
    # API-Football ya no captura: su puente es historia y puede no existir en una base nueva
    puente = connection.execute("SELECT to_regclass('public.puente_jugador')").fetchone()[0]
    for af_id, fid, matches in ([] if puente is None else connection.execute(
            "SELECT af_player_id, fotmob_jugador_id, partidos FROM puente_jugador WHERE confianza = 'alta'").fetchall()):
        canonical = connection.execute("SELECT futbol.jugador_canonico('fotmob',%s,NULL)", (fid,)).fetchone()[0]
        connection.execute("SELECT futbol.vincular_jugador('api_football',%s,%s,'puente_api_football',%s)",
                           (af_id, canonical, matches))
        linked_af += 1
    return {'sofascore_registrados': len(sofascore_names), 'fotmob_enlazados': len(links),
            'filas_movidas': moved, 'api_football_enlazados': linked_af,
            'sofascore_sin_ficha_registrados': register_orphans(connection)}


def register_orphans(connection):
    """Todo id positivo (de SofaScore) que aparece en `futbol.dato` y aún no tiene ficha: tiradores, ausentes y
    jugadores de incidencias que no estaban en ninguna alineación leída. Devuelve cuántos se registraron."""
    made = connection.execute("""WITH huerfanos AS (
        SELECT DISTINCT ON (id) id, nombre FROM (
            SELECT jugador_id AS id, nombre FROM futbol.dato WHERE jugador_id > 0
            UNION ALL SELECT jugador2_id, jugador2 FROM futbol.dato WHERE jugador2_id > 0) t
         WHERE NOT EXISTS (SELECT 1 FROM futbol.jugador j WHERE j.jugador_id = t.id)
         ORDER BY id, nombre NULLS LAST),
      nuevos AS (INSERT INTO futbol.jugador (jugador_id, nombre) SELECT id, COALESCE(nombre, '?') FROM huerfanos
                 ON CONFLICT DO NOTHING RETURNING jugador_id)
      INSERT INTO futbol.jugador_fuente_id (fuente, id_en_fuente, jugador_id, evidencia)
      SELECT 'sofascore', jugador_id, jugador_id, 'id_canonico' FROM nuevos ON CONFLICT DO NOTHING""").rowcount
    return made


def run(connection, archive, apply):
    pairs, names = collect(connection, archive)
    appearances = dict(connection.execute(
        "SELECT jugador_id, count(*) FROM fotmob_jugador_partido GROUP BY 1").fetchall())
    links = decide_links(pairs, appearances)
    result = {'parejas_con_evidencia': len(pairs), 'ids_sofascore_vistos': len(names),
              'enlaces_fotmob': len(links), 'ids_fotmob_totales': len(appearances), 'aplicado': apply}
    if apply:
        with connection.transaction():
            result.update(apply_links(connection, names, links))
    return result


def main():
    import os
    import psycopg
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True)
    parser.add_argument('--aplicar', action='store_true')
    args = parser.parse_args()
    with psycopg.connect(os.environ['PG_DSN']) as connection:
        print(json.dumps(run(connection, args.archive, args.aplicar), ensure_ascii=True))


if __name__ == '__main__':
    main()
