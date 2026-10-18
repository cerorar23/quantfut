"""Equivalencia de árbitros API-Football ↔ FotMob por coincidencia en los mismos partidos (db/077).

API-Football escribe inicial y apellido ("A Taylor"); FotMob el nombre completo ("Anthony Taylor"). Un par solo
se acepta si, entre los partidos que traen los dos nombres, cada uno apunta casi siempre al otro:
- al menos `MIN_PARTIDOS` partidos juntos,
- que el par sea al menos `MIN_CUOTA` de los partidos de ese nombre de API-Football **y** de ese de FotMob.
Los pares sueltos de un partido (el mismo partido mal cruzado, o un árbitro de VAR) no cumplen la regla.
`regla_nombre` indica además si encajan inicial y apellido; la vista unificada solo usa los que sí.
"""
from __future__ import annotations

import json
import logging
import re
import unicodedata
from collections import defaultdict

log = logging.getLogger(__name__)

MIN_PARTIDOS = 5
MIN_CUOTA = 0.9


def _tokens(nombre: str) -> list[str]:
    s = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]", " ", s).split()


def regla_nombre(af: str, fotmob: str) -> bool:
    """«A Taylor» encaja con «Anthony Taylor»: misma inicial y el apellido de API-Football al final."""
    a, f = _tokens(af), _tokens(fotmob)
    if len(a) < 2 or len(f) < 2:
        return False
    apellido = a[1:]
    return a[0][0] == f[0][0] and f[-len(apellido):] == apellido


def elegir(pares: list[tuple[str, str, int]], min_partidos: int = MIN_PARTIDOS,
           min_cuota: float = MIN_CUOTA) -> list[dict]:
    """pares = (nombre_af, nombre_fotmob, partidos). Devuelve los que superan las dos cuotas."""
    tot_af: dict[str, int] = defaultdict(int)
    tot_fm: dict[str, int] = defaultdict(int)
    for af, fm, n in pares:
        tot_af[af] += n
        tot_fm[fm] += n
    out = []
    for af, fm, n in pares:
        ca, cf = n / tot_af[af], n / tot_fm[fm]
        if n >= min_partidos and ca >= min_cuota and cf >= min_cuota:
            out.append({"arbitro_af": af, "arbitro_fotmob": fm, "partidos": n,
                        "cuota_af": round(ca, 4), "cuota_fotmob": round(cf, 4),
                        "regla_nombre": regla_nombre(af, fm)})
    return sorted(out, key=lambda x: (-x["partidos"], x["arbitro_af"]))


def calcular(c, aplicar: bool = False) -> dict:
    filas = c.execute("""SELECT referee AS af, referee_fotmob AS fm, count(*) AS n FROM matches
                         WHERE referee IS NOT NULL AND referee_fotmob IS NOT NULL
                         GROUP BY 1, 2""").fetchall()
    elegidos = elegir([(f["af"], f["fm"], f["n"]) for f in filas])
    if aplicar:
        with c.cursor() as w:
            w.executemany(
                """INSERT INTO arbitro_equivalencia
                       (arbitro_af, arbitro_fotmob, partidos, cuota_af, cuota_fotmob, regla_nombre)
                   VALUES (%(arbitro_af)s, %(arbitro_fotmob)s, %(partidos)s, %(cuota_af)s, %(cuota_fotmob)s,
                           %(regla_nombre)s) ON CONFLICT (arbitro_af, arbitro_fotmob) DO NOTHING""", elegidos)
        c.commit()
    return {"pares_observados": len(filas), "aceptados": len(elegidos),
            "con_regla_de_nombre": sum(x["regla_nombre"] for x in elegidos),
            "sin_regla_de_nombre": [(x["arbitro_af"], x["arbitro_fotmob"], x["partidos"])
                                    for x in elegidos if not x["regla_nombre"]]}


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
