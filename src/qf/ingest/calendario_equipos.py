"""Calendario de cada equipo en todas las competiciones, de API-Football (db/078).

Una llamada por equipo y temporada (`/fixtures?team=&season=`). El plan gasta ~1.260 llamadas para las cuatro
temporadas de 315 equipos; el refresco diario de la temporada en curso gasta ~315. Se detiene antes de
agotar la cuota diaria (`api_football.check_quota`). Un dato ausente queda NULL, nunca 0.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

from . import api_football as af

log = logging.getLogger(__name__)

COLS = ("af_fixture_id", "af_team_id", "team_id", "fecha", "temporada", "liga_af_id", "liga_nombre", "pais",
        "ronda", "local", "rival_af_id", "rival_nombre", "estado", "goles_favor", "goles_contra")


def _entero(v) -> int | None:
    return v if isinstance(v, int) and not isinstance(v, bool) and v >= 0 else None


def filas_de(respuesta: list[dict], af_team_id: int, team_id: int | None) -> list[dict]:
    """Filas de un equipo a partir de la respuesta de `/fixtures`. Ignora partidos donde el equipo no juega."""
    out = []
    for it in respuesta:
        fx, lg = it.get("fixture") or {}, it.get("league") or {}
        eq, goles = it.get("teams") or {}, it.get("goals") or {}
        h, a = eq.get("home") or {}, eq.get("away") or {}
        if af_team_id not in (h.get("id"), a.get("id")):
            continue
        try:
            fecha = datetime.fromisoformat(str(fx.get("date")).replace("Z", "+00:00"))
        except ValueError:
            continue
        if fecha.tzinfo is None or not isinstance(fx.get("id"), int) or not isinstance(lg.get("id"), int):
            continue
        local = h.get("id") == af_team_id
        rival = a if local else h
        out.append({"af_fixture_id": fx["id"], "af_team_id": af_team_id, "team_id": team_id, "fecha": fecha,
                    "temporada": lg.get("season"), "liga_af_id": lg["id"], "liga_nombre": lg.get("name"),
                    "pais": lg.get("country"), "ronda": lg.get("round"), "local": local,
                    "rival_af_id": _entero(rival.get("id")), "rival_nombre": rival.get("name"),
                    "estado": (fx.get("status") or {}).get("short"),
                    "goles_favor": _entero(goles.get("home" if local else "away")),
                    "goles_contra": _entero(goles.get("away" if local else "home"))})
    return [f for f in out if isinstance(f["temporada"], int)]


_SQL = ("INSERT INTO calendario_equipo (" + ", ".join(COLS) + ") VALUES (" + ", ".join(f"%({k})s" for k in COLS)
        + ") ON CONFLICT (af_fixture_id, af_team_id) DO UPDATE SET fecha = EXCLUDED.fecha, "
          "estado = EXCLUDED.estado, goles_favor = EXCLUDED.goles_favor, goles_contra = EXCLUDED.goles_contra, "
          "ronda = EXCLUDED.ronda, team_id = COALESCE(EXCLUDED.team_id, calendario_equipo.team_id), "
          "recibido_en = now()")


def cargar(c, temporadas: list[int], refrescar: bool = False, limite_llamadas: int | None = None) -> dict:
    """Pide equipo × temporada. Sin `refrescar` salta lo ya registrado en el log."""
    equipos = c.execute("""SELECT t.team_id, t.af_team_id FROM teams t JOIN leagues l USING (league_id)
                           WHERE l.model_enabled AND t.af_team_id IS NOT NULL ORDER BY t.team_id""").fetchall()
    hechos = {(r["af_team_id"], r["temporada"]) for r in
              c.execute("SELECT af_team_id, temporada FROM calendario_equipo_log").fetchall()}
    r = {"llamadas": 0, "partidos": 0, "equipos_temporada": 0, "saltados": 0, "parada": None}
    for temporada in temporadas:
        for e in equipos:
            if not refrescar and (e["af_team_id"], temporada) in hechos:
                r["saltados"] += 1
                continue
            if limite_llamadas is not None and r["llamadas"] >= limite_llamadas:
                r["parada"] = "límite de llamadas"
                return r
            try:
                resp, meta = af.get("fixtures", {"team": e["af_team_id"], "season": temporada})
                af.check_quota(meta)
            except af.QuotaWarning as exc:
                r["parada"] = f"cuota: {exc}"
                return r
            r["llamadas"] += 1
            filas = filas_de(resp, e["af_team_id"], e["team_id"])
            with c.cursor() as w:
                if filas:
                    w.executemany(_SQL, filas)
                w.execute("""INSERT INTO calendario_equipo_log (af_team_id, temporada, partidos)
                             VALUES (%s, %s, %s) ON CONFLICT (af_team_id, temporada)
                             DO UPDATE SET recibido_en = now(), partidos = EXCLUDED.partidos""",
                          (e["af_team_id"], temporada, len(filas)))
            c.commit()
            r["partidos"] += len(filas)
            r["equipos_temporada"] += 1
    return r


def main(argv=None) -> None:
    import argparse

    from ..db import conn

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--temporadas", nargs="+", type=int, required=True)
    ap.add_argument("--refrescar", action="store_true", help="vuelve a pedir lo ya registrado (temporada en curso)")
    ap.add_argument("--limite", type=int, default=None, help="máximo de llamadas de esta pasada")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    with conn() as c:
        print(json.dumps(cargar(c, a.temporadas, a.refrescar, a.limite), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
