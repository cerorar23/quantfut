"""Asigna el estadio a los partidos que aún no lo tienen, desde la página de FotMob ya capturada.

Los partidos nuevos llegan de `fixtures` sin `stadium_id`. Sin sede no hay altitud ni clima. La página de FotMob
(previa o posterior) trae nombre, ciudad, coordenadas y capacidad del estadio: se busca uno existente por nombre o por
cercanía (menos de ~330 m) y solo si no hay ninguno se da de alta, para no sumar duplicados a `estadios`. La procedencia
de cada asignación queda en `matches_enriquecimiento`. Solo rellena NULL: nunca cambia una sede ya asignada.
"""
from __future__ import annotations

import gzip
import json
import logging

from . import estadios_altitud
from .archivo_a_matches import _estadio

log = logging.getLogger(__name__)

RADIO_GRADOS = 0.003      # ~330 m en latitud


def decidir(existentes: list[dict], estadio: dict) -> int | None:
    """stadium_id de un estadio existente que sea el mismo, o None si hay que darlo de alta.

    Prioridad: mismo nombre dentro del radio; si no hay coordenadas, mismo nombre y ciudad; si no, el más
    cercano dentro del radio solo cuando no hay otro con nombre distinto a menos distancia.
    """
    nombre = (estadio.get("name") or "").strip().lower()
    lat, lon = estadio.get("lat"), estadio.get("lon")
    if lat is None or lon is None:
        for e in existentes:
            if (e["name"] or "").strip().lower() == nombre and (e["city"] or "") == (estadio.get("city") or ""):
                return e["stadium_id"]
        return None
    cerca = [e for e in existentes if e["lat"] is not None and abs(e["lat"] - lat) <= RADIO_GRADOS
             and abs(e["lon"] - lon) <= RADIO_GRADOS]
    if not cerca:
        return None
    cerca.sort(key=lambda e: ((e["name"] or "").strip().lower() != nombre,
                              abs(e["lat"] - lat) + abs(e["lon"] - lon), e["stadium_id"]))
    return cerca[0]["stadium_id"]


def _alta(c, estadio: dict, visto) -> int:
    fila = c.execute(
        """INSERT INTO estadios (name, city, country, lat, lon, capacity, surface, source, first_seen_at)
           VALUES (%(name)s, %(city)s, %(country)s, %(lat)s, %(lon)s, %(capacity)s, %(surface)s, 'fotmob', %(visto)s)
           ON CONFLICT (name, city, country) DO UPDATE SET name = EXCLUDED.name RETURNING stadium_id""",
        {**estadio, "visto": visto}).fetchone()
    return fila["stadium_id"]


def asignar(c, limite: int | None = None) -> dict:
    r = {"candidatos": 0, "asignados": 0, "estadios_nuevos": 0, "sin_estadio_en_la_pagina": 0}
    filas = c.execute(
        """SELECT m.match_id, o.payload_gz, o.capturado_en, o.fotmob_match_id
           FROM matches m JOIN LATERAL (
                SELECT * FROM fotmob_original x WHERE x.match_id = m.match_id
                ORDER BY (x.fase = 'posterior') DESC, x.capturado_en DESC LIMIT 1) o ON true
           WHERE m.stadium_id IS NULL ORDER BY m.kickoff_utc LIMIT %s""",
        (limite if limite is not None else 100000,)).fetchall()
    for f in filas:
        r["candidatos"] += 1
        est = _estadio(json.loads(gzip.decompress(f["payload_gz"])))
        if est is None:
            r["sin_estadio_en_la_pagina"] += 1
            continue
        if est["lat"] is not None:
            existentes = c.execute(
                """SELECT stadium_id, name, city, lat, lon FROM estadios
                   WHERE lat BETWEEN %s AND %s AND lon BETWEEN %s AND %s""",
                (est["lat"] - RADIO_GRADOS, est["lat"] + RADIO_GRADOS,
                 est["lon"] - RADIO_GRADOS, est["lon"] + RADIO_GRADOS)).fetchall()
        else:
            existentes = c.execute("SELECT stadium_id, name, city, lat, lon FROM estadios WHERE lower(name) = %s",
                                   (est["name"].lower(),)).fetchall()
        sid = decidir(existentes, est)
        if sid is None:
            sid = _alta(c, est, f["capturado_en"])
            r["estadios_nuevos"] += 1
        c.execute("UPDATE matches SET stadium_id = %s WHERE match_id = %s AND stadium_id IS NULL",
                  (sid, f["match_id"]))
        c.execute("""INSERT INTO matches_enriquecimiento (match_id, campo, provider, source_match_id, captured_at)
                     VALUES (%s, 'stadium_id', 'fotmob', %s, %s) ON CONFLICT DO NOTHING""",
                  (f["match_id"], f["fotmob_match_id"], f["capturado_en"]))
        r["asignados"] += 1
    c.commit()
    return r


def main(argv=None) -> None:
    import argparse

    from ..db import conn

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limite", type=int, default=None)
    ap.add_argument("--sin-altitud", action="store_true", help="no pide la altitud de los estadios nuevos")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    with conn() as c:
        res = asignar(c, a.limite)
        if not a.sin_altitud and res["estadios_nuevos"]:
            res["altitud"] = estadios_altitud.cargar(c, confirmar=True)
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
