"""Puente de jugadores API-Football ↔ FotMob por coincidencia en los mismos partidos (db/079).

Pasada 1: mismo partido, lado y nombre normalizado completo. Pasada 2, solo con lo que la 1 dejó sin pareja:
mismo partido y lado, inicial + último apellido, y únicos en ese partido en las dos listas. Después se agrupa
por par (id API-Football, id FotMob) y se acepta si:
- alta: al menos `MIN_PARTIDOS` partidos juntos y el par es al menos `MIN_CUOTA` de los partidos de cada id;
- baja: 1 o 2 partidos y ninguno de los dos ids aparece emparejado con otro.
Un id con dos candidatos repartidos no se resuelve: queda sin puente.
"""
from __future__ import annotations

import json
import logging

log = logging.getLogger(__name__)

MIN_PARTIDOS = 3
MIN_CUOTA = 0.9

_ACENTOS_DE = "áàäâãåéèëêíìïîóòöôõøúùüûñçÁÀÄÂÃÅÉÈËÊÍÌÏÎÓÒÖÔÕØÚÙÜÛÑÇßł"
_ACENTOS_A = "aaaaaaeeeeiiiiooooouuuuncaaaaaaeeeeiiiiooooouuuuncsl"


def _norm(col: str) -> str:
    return (f"btrim(regexp_replace(lower(translate({col}, '{_ACENTOS_DE}', '{_ACENTOS_A}')), "
            f"'[^a-z0-9 ]', ' ', 'g'))")


def _k2(n: str) -> str:
    """Inicial + último token: «lionel messi» y «l messi» dan «l messi»."""
    return f"left({n}, 1) || ' ' || regexp_replace(regexp_replace({n}, '\\s+', ' ', 'g'), '^.*\\s', '')"


_PREPARAR = f"""
CREATE TEMP TABLE _na ON COMMIT DROP AS
  SELECT e.match_id, e.side, e.player_id::bigint AS af, {_norm('e.nombre')} AS nom
  FROM estadisticas_jugador e WHERE e.player_id IS NOT NULL AND e.nombre IS NOT NULL
    AND e.match_id IN (SELECT match_id FROM fotmob_partido);
CREATE TEMP TABLE _nf ON COMMIT DROP AS
  SELECT j.match_id, j.side, j.jugador_id AS fm, {_norm('j.nombre')} AS nom
  FROM fotmob_jugador_partido j WHERE j.nombre IS NOT NULL
    AND j.match_id IN (SELECT match_id FROM _na);
ALTER TABLE _na ADD COLUMN k2 text; UPDATE _na SET k2 = {_k2('nom')} WHERE nom <> '';
ALTER TABLE _nf ADD COLUMN k2 text; UPDATE _nf SET k2 = {_k2('nom')} WHERE nom <> '';
CREATE INDEX ON _na (match_id, side, nom); CREATE INDEX ON _nf (match_id, side, nom);
CREATE INDEX ON _na (match_id, side, k2); CREATE INDEX ON _nf (match_id, side, k2);
ANALYZE _na; ANALYZE _nf;

CREATE TEMP TABLE _p1 ON COMMIT DROP AS
  WITH a AS (SELECT *, count(*) OVER (PARTITION BY match_id, side, nom) AS c FROM _na WHERE nom <> ''),
       f AS (SELECT *, count(*) OVER (PARTITION BY match_id, side, nom) AS c FROM _nf WHERE nom <> '')
  SELECT a.match_id, a.side, a.af, f.fm, 1 AS pasada
  FROM a JOIN f ON f.match_id = a.match_id AND f.side = a.side AND f.nom = a.nom
  WHERE a.c = 1 AND f.c = 1;
CREATE INDEX ON _p1 (match_id, side, af); CREATE INDEX ON _p1 (match_id, side, fm);

CREATE TEMP TABLE _sa ON COMMIT DROP AS
  SELECT a.match_id, a.side, a.af, a.k2, count(*) OVER (PARTITION BY a.match_id, a.side, a.k2) AS c
  FROM _na a LEFT JOIN _p1 p ON p.match_id = a.match_id AND p.side = a.side AND p.af = a.af
  WHERE p.af IS NULL AND a.k2 IS NOT NULL;
CREATE TEMP TABLE _sf ON COMMIT DROP AS
  SELECT f.match_id, f.side, f.fm, f.k2, count(*) OVER (PARTITION BY f.match_id, f.side, f.k2) AS c
  FROM _nf f LEFT JOIN _p1 p ON p.match_id = f.match_id AND p.side = f.side AND p.fm = f.fm
  WHERE p.fm IS NULL AND f.k2 IS NOT NULL;
CREATE TEMP TABLE _p2 ON COMMIT DROP AS
  SELECT a.match_id, a.side, a.af, f.fm, 2 AS pasada
  FROM _sa a JOIN _sf f ON f.match_id = a.match_id AND f.side = a.side AND f.k2 = a.k2
  WHERE a.c = 1 AND f.c = 1;

CREATE TEMP TABLE _pares ON COMMIT DROP AS
  SELECT af, fm, count(DISTINCT match_id) AS n, min(pasada) AS pasada
  FROM (SELECT * FROM _p1 UNION ALL SELECT * FROM _p2) u GROUP BY af, fm;
CREATE TEMP TABLE _tot_af ON COMMIT DROP AS SELECT af, sum(n) AS t, count(*) AS k FROM _pares GROUP BY af;
CREATE TEMP TABLE _tot_fm ON COMMIT DROP AS SELECT fm, sum(n) AS t, count(*) AS k FROM _pares GROUP BY fm;
"""

_ELEGIR = """
SELECT p.af, p.fm, p.n::int AS partidos, (p.n::real / ta.t) AS cuota_af, (p.n::real / tf.t) AS cuota_fotmob,
       CASE WHEN p.n >= %(minp)s THEN 'alta' ELSE 'baja' END AS confianza, p.pasada::int AS pasada_nombre
FROM _pares p JOIN _tot_af ta USING (af) JOIN _tot_fm tf USING (fm)
WHERE (p.n >= %(minp)s AND p.n::real / ta.t >= %(minc)s AND p.n::real / tf.t >= %(minc)s)
   OR (p.n < %(minp)s AND ta.k = 1 AND tf.k = 1)
"""


def calcular(c, aplicar: bool = False) -> dict:
    c.execute(_PREPARAR)
    r = {"filas_af": c.execute("SELECT count(*) AS n FROM _na").fetchone()["n"],
         "filas_fotmob": c.execute("SELECT count(*) AS n FROM _nf").fetchone()["n"],
         "pasada1": c.execute("SELECT count(*) AS n FROM _p1").fetchone()["n"],
         "pasada2": c.execute("SELECT count(*) AS n FROM _p2").fetchone()["n"]}
    elegidos = c.execute(_ELEGIR, {"minp": MIN_PARTIDOS, "minc": MIN_CUOTA}).fetchall()
    r["pares_observados"] = c.execute("SELECT count(*) AS n FROM _pares").fetchone()["n"]
    r["puentes"] = len(elegidos)
    r["alta"] = sum(1 for e in elegidos if e["confianza"] == "alta")
    r["baja"] = sum(1 for e in elegidos if e["confianza"] == "baja")
    r["ids_af_con_estadisticas"] = c.execute(
        "SELECT count(DISTINCT af) AS n FROM _na").fetchone()["n"]
    if aplicar:
        with c.cursor() as w:
            w.executemany(
                """INSERT INTO puente_jugador (af_player_id, fotmob_jugador_id, partidos, cuota_af, cuota_fotmob,
                                               confianza, pasada_nombre)
                   VALUES (%(af)s, %(fm)s, %(partidos)s, %(cuota_af)s, %(cuota_fotmob)s, %(confianza)s,
                           %(pasada_nombre)s) ON CONFLICT DO NOTHING""", elegidos)
        c.commit()
    else:
        c.rollback()
    return r


def main(argv=None) -> None:
    import argparse

    from ..db import conn

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aplicar", action="store_true", help="sin esto solo calcula y muestra")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    with conn() as c:
        print(json.dumps({**calcular(c, a.aplicar), "aplicado": a.aplicar}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
