"""Altitud de cada estadio desde un modelo de elevación abierto (db/076).

Una sola descarga puntual: 758 estadios en lotes de 100 puntos, uno por segundo, que es lo que admite la API
pública de OpenTopoData. Sin clave ni créditos. Un punto sin elevación (mar, fuera de cobertura) se deja
sin fila; nunca se guarda 0 en su lugar.
"""
from __future__ import annotations

import json
import logging
import math
import time
import urllib.request

log = logging.getLogger(__name__)

URL = "https://api.opentopodata.org/v1/mapzen"
FUENTE = "opentopodata/mapzen"
LOTE = 100
ESPERA_S = 1.2
ALTITUD_MIN, ALTITUD_MAX = -430.0, 5000.0  # del Mar Muerto al estadio más alto plausible


def altitud_valida(valor) -> float | None:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor):
        return None
    return float(valor) if ALTITUD_MIN <= valor <= ALTITUD_MAX else None


def pedir(puntos: list[tuple[float, float]]) -> list[float | None]:
    """Altitud de cada punto (lat, lon), en el mismo orden. Falla en voz alta ante una respuesta rara."""
    loc = "|".join(f"{lat:.5f},{lon:.5f}" for lat, lon in puntos)
    req = urllib.request.Request(f"{URL}?locations={loc}", headers={"User-Agent": "QuantFut/1.0"})
    with urllib.request.urlopen(req, timeout=40) as r:
        datos = json.load(r)
    res = datos.get("results")
    if datos.get("status") != "OK" or not isinstance(res, list) or len(res) != len(puntos):
        raise ValueError(f"respuesta inesperada de {URL}: {str(datos)[:200]}")
    return [altitud_valida(x.get("elevation")) for x in res]


def cargar(c, confirmar: bool = False) -> dict:
    filas = c.execute(
        """SELECT e.stadium_id, e.lat, e.lon FROM estadios e
           LEFT JOIN estadio_altitud a USING (stadium_id)
           WHERE a.stadium_id IS NULL AND e.lat IS NOT NULL AND e.lon IS NOT NULL
             AND e.lat BETWEEN -90 AND 90 AND e.lon BETWEEN -180 AND 180
           ORDER BY e.stadium_id""").fetchall()
    r = {"pendientes": len(filas), "guardados": 0, "sin_elevacion": 0}
    for i in range(0, len(filas), LOTE):
        lote = filas[i:i + LOTE]
        alturas = pedir([(f["lat"], f["lon"]) for f in lote])
        with c.cursor() as w:
            for f, h in zip(lote, alturas):
                if h is None:
                    r["sin_elevacion"] += 1
                    continue
                w.execute("""INSERT INTO estadio_altitud (stadium_id, altitud_m, fuente)
                             VALUES (%s, %s, %s) ON CONFLICT (stadium_id) DO NOTHING""",
                          (f["stadium_id"], h, FUENTE))
                r["guardados"] += 1
        if confirmar:
            c.commit()
        time.sleep(ESPERA_S)
    return r


def main(argv=None) -> None:
    import argparse

    from ..db import conn

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aplicar", action="store_true", help="sin esto es un ensayo que se revierte")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    with conn() as c:
        res = cargar(c, a.aplicar)
        if not a.aplicar:
            c.rollback()
    print(json.dumps({**res, "aplicado": a.aplicar}, indent=1))


if __name__ == "__main__":
    main()
