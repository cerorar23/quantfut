"""
Alineaciones del último año, descargadas después de jugarse cada partido.

SOLO para entrenar y validar el ajuste por XI (`model.lineup_challenger`).
Decisión del usuario, 2026-09-29: en vivo, el challenger no tendría los 700
partidos que exige hasta diciembre. Se guardan en `lineups_historicas`
(db/034), una tabla que la predicción diaria y la sombra no leen: lo que se
sella o se mide contra el cierre sigue usando solo XI capturados antes del
partido.

Los partidos antiguos llegaron de football-data y no tienen id de
API-Football. Se emparejan con la lista de fixtures de cada liga y
temporada: mismo local y visitante (por `teams.af_team_id` o alias exacto)
y ±36 h. Lo que no empareja se descarta, no se adivina.

Reanudable: salta lo ya descargado y se detiene al llegar a la reserva de
cuota diaria, para no dejar sin peticiones a la operación normal.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from ..db import execute, query
from ..normalize import match_team
from . import api_football as af
from .salud import record_health
from .fixtures import current_season
from .lineups import _parse_side

log = logging.getLogger(__name__)

FINALIZADOS = {"FT", "AET", "PEN"}
TOLERANCIA = timedelta(hours=36)
RESERVA_CUOTA = 2500


def emparejar(fixtures: list[dict], equipo_de, partidos: list[dict]) -> list[tuple[str, int]]:
    """
    [(match_id, fixture_id)]. `equipo_de(nombre, af_id)` -> team_id o None.
    Un fixture sin los dos equipos resueltos, o con cero o varios partidos
    candidatos, no se empareja.
    """
    por_pareja: dict[tuple[int, int], list[dict]] = {}
    for p in partidos:
        por_pareja.setdefault((p["home_team_id"], p["away_team_id"]), []).append(p)
    out = []
    for fx in fixtures:
        if fx["fixture"]["status"]["short"] not in FINALIZADOS:
            continue
        home = equipo_de(fx["teams"]["home"]["name"], fx["teams"]["home"]["id"])
        away = equipo_de(fx["teams"]["away"]["name"], fx["teams"]["away"]["id"])
        if not home or not away:
            continue
        ko = datetime.fromisoformat(fx["fixture"]["date"].replace("Z", "+00:00"))
        cand = [p for p in por_pareja.get((home, away), [])
                if abs(p["kickoff_utc"] - ko) <= TOLERANCIA]
        if len(cand) == 1:
            out.append((cand[0]["match_id"], int(fx["fixture"]["id"])))
    return out


def _resolutor(league_id: str | None):
    por_af = {r["af_team_id"]: r["team_id"] for r in query(
        "SELECT team_id, af_team_id FROM teams WHERE af_team_id IS NOT NULL")}

    def equipo_de(nombre: str, af_id: int | None) -> int | None:
        if af_id in por_af:
            return por_af[af_id]
        tid, _, score = match_team(nombre, "api_football", league_id)
        return tid if tid and score >= 100.0 else None
    return equipo_de


def pares(dias: int = 400) -> list[tuple[str, int]]:
    """Partidos terminados del periodo en ligas con modelo, con su fixture."""
    desde = datetime.now(timezone.utc) - timedelta(days=dias)
    ligas = query(
        """SELECT league_id, api_football_id, season_style, cross_league FROM leagues
           WHERE active AND model_enabled AND captura_completa
             AND api_football_id IS NOT NULL""")
    hechos = {r["match_id"] for r in query("SELECT DISTINCT match_id FROM lineups_historicas")}
    out: dict[str, int] = {}
    for lg in ligas:
        partidos = query(
            """SELECT match_id, home_team_id, away_team_id, kickoff_utc,
                      external_ids ->> 'api_football' AS af_id
               FROM matches WHERE league_id = %s AND status = 'finished'
                 AND kickoff_utc > %s""", (lg["league_id"], desde))
        # Los que ya traen su fixture no necesitan emparejarse.
        for p in partidos:
            if p["af_id"]:
                out[p["match_id"]] = int(p["af_id"])
        sin_id = [p for p in partidos if not p["af_id"] and p["match_id"] not in hechos]
        if not sin_id:
            continue
        actual = current_season(lg["season_style"])
        equipo_de = _resolutor(None if lg["cross_league"] else lg["league_id"])
        for temporada in (actual - 1, actual):
            try:
                fixtures, _ = af.get("fixtures", {"league": lg["api_football_id"],
                                                  "season": temporada, "timezone": "UTC"})
            except af.PlanError:
                raise
            except Exception as exc:  # noqa: BLE001
                log.error("Fixtures de %s %s: %s", lg["league_id"], temporada, exc)
                continue
            for match_id, fixture in emparejar(fixtures, equipo_de, sin_id):
                out.setdefault(match_id, fixture)
    return [(m, f) for m, f in out.items() if m not in hechos]


def _cuota(meta: dict) -> int | None:
    """La cabecera del proveedor llega como texto ('4981')."""
    try:
        return int(meta.get("quota_remaining"))
    except (TypeError, ValueError):
        return None


def descargar(lista: list[tuple[str, int]], reserva: int = RESERVA_CUOTA) -> dict:
    guardados = vacios = 0
    for match_id, fixture in lista:
        resp, meta = af.get("fixtures/lineups", {"fixture": fixture})
        lados = zip(("home", "away"), resp[:2]) if len(resp) >= 2 else \
            (("home", {}), ("away", {}))
        for side, entry in lados:
            parsed = _parse_side(entry) if entry else {"formation": None, "starters": []}
            execute(
                """INSERT INTO lineups_historicas
                     (match_id, side, formation, starters, af_fixture_id)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (match_id, side) DO NOTHING""",
                (match_id, side, parsed["formation"], json.dumps(parsed["starters"]),
                 fixture))
        guardados += len(resp) >= 2
        vacios += len(resp) < 2
        restante = _cuota(meta)
        if restante is not None and restante < reserva:
            log.warning("Reserva de cuota alcanzada (%s): se sigue otro día", restante)
            break
    return {"con_xi": guardados, "sin_xi": vacios}


def run(dias: int = 400, reserva: int = RESERVA_CUOTA) -> dict:
    lista = pares(dias)
    resultado = {"pendientes": len(lista), **descargar(lista, reserva)}
    record_health("lineups_historicas", resultado["con_xi"], True, resultado)
    log.info("Alineaciones históricas: %s", resultado)
    return resultado


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    print(run())
