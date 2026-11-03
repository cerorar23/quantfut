"""Carga de bajas y once de SofaScore (ids de SofaScore) a `injuries`, `lineups_previstas` y `lineups`.

Los originales llegan de `sportsapipro_alineaciones` (mismos ids de SofaScore). Aquí vive lo que escribe en la
base y empareja cada evento con un partido nuestro programado, sin importar de dónde venga el original.

Qué escribe, por partido nuestro todavía programado:
  * `injuries`: las bajas (`missing`/`doubtful`) con motivo y fecha de regreso, `source = 'sofascore'`.
  * `lineups_previstas`: el once de cada captura, previsto (`confirmed = false`) u oficial.
  * `lineups`: SOLO el oficial (`confirmed = true`) con los dos lados completos, que es lo que lee
    `sello_tardio` («alineaciones oficiales capturadas»). Un once previsto nunca entra ahí.

Los ids de jugador son los de SofaScore y se marcan `src = 'sofascore'` en cada titular: no coinciden con los
de otras fuentes, y `lineups.availability` solo compara contra historia de la misma fuente.

Un evento solo se enlaza con un partido nuestro programado de la misma competición, a ±36 h, con los dos
nombres parecidos y como único candidato (sin marcador que lo confirme, porque aún no hay).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from psycopg.types.json import Jsonb
from rapidfuzz import fuzz

from ..db import query
from ..league_policy import RETIRED_LEAGUES
from ..normalize import slugify
from .sofascore_history import TOURNAMENTS

LIGA_DE_TORNEO = {v: k for k, v in TOURNAMENTS.items() if k not in RETIRED_LEAGUES} | {11621: "mx.liga_mx"}
VENTANA = timedelta(hours=36)
PARECIDO_MIN = 70
POS = {"G": "G", "D": "D", "M": "M", "F": "F"}


def _nombres(team_ids: list[int]) -> dict[int, set[str]]:
    out: dict[int, set[str]] = {t: set() for t in team_ids}
    for r in query("""SELECT team_id, canonical_name AS n FROM teams WHERE team_id = ANY(%s)
                      UNION SELECT team_id, alias FROM team_aliases WHERE team_id = ANY(%s)""",
                   (team_ids, team_ids)):
        out[r["team_id"]].add(slugify(r["n"]))
    return out


def parecido(nombre: str, conocidos: set[str]) -> float:
    s = slugify(nombre)
    return max((fuzz.token_set_ratio(s, c) for c in conocidos), default=0.0)

def emparejar(fila: dict) -> tuple[str | None, str]:
    """(match_id, motivo). Un único partido programado de la competición con equipos parecidos."""
    liga = LIGA_DE_TORNEO.get(fila.get("uniqueTournamentId"))
    if liga is None:
        return None, "competicion_fuera_de_catalogo"
    ko = datetime.fromtimestamp(int(fila["startTimestamp"]), timezone.utc)
    cands = query("""SELECT match_id, status, home_team_id, away_team_id FROM matches
                     WHERE league_id = %s AND kickoff_utc BETWEEN %s AND %s""",
                  (liga, ko - VENTANA, ko + VENTANA))
    if not cands:
        return None, "sin_partido"
    nombres = _nombres([c[k] for c in cands for k in ("home_team_id", "away_team_id")])
    mismos = [c for c in cands
              if parecido(fila["homeTeam"], nombres[c["home_team_id"]]) >= PARECIDO_MIN
              and parecido(fila["awayTeam"], nombres[c["away_team_id"]]) >= PARECIDO_MIN]
    if len(mismos) != 1:
        return None, "sin_partido" if not mismos else "ambiguo"
    if mismos[0]["status"] != "scheduled":
        return None, "ya_empezado"
    return mismos[0]["match_id"], "ok"

def titulares(lado: dict | None) -> list[dict]:
    """Titulares en el formato de `lineups.starters`, con `src` para no mezclar ids de otra fuente."""
    out = []
    for p in (lado or {}).get("players") or []:
        if p.get("substitute"):
            continue
        j = p.get("player") or {}
        pid = j.get("id") or j.get("sofascoreId")
        if not pid:
            continue
        out.append({"player_id": int(pid), "name": j.get("name"),
                    "pos": POS.get(str(p.get("position") or j.get("position") or "").upper()[:1]),
                    "number": p.get("shirtNumber") or p.get("jerseyNumber"), "src": "sofascore"})
    return out

def bajas(lado: dict | None) -> list[dict]:
    out = []
    for m in (lado or {}).get("missingPlayers") or []:
        j = m.get("player") or {}
        pid = j.get("id") or j.get("sofascoreId")
        if not pid:
            continue
        fin = None
        try:
            fin = date.fromisoformat(str(m.get("expectedEndDate"))[:10]) if m.get("expectedEndDate") else None
        except ValueError:
            pass
        out.append({"player_id": int(pid), "player_name": j.get("name") or "?",
                    "status_type": str(m.get("type") or "missing"),
                    "reason": m.get("description") or (None if m.get("reason") is None else str(m["reason"])),
                    "expected_return": fin})
    return out

def aplicar(c, recibo: dict, fila: dict, match_id: str) -> dict:
    """Escribe bajas, once previsto y, si es oficial y completo, `lineups`. Idempotente por recibo."""
    recibido = datetime.fromisoformat(recibo["received_at"])
    if c.execute("SELECT 1 FROM lineups_previstas WHERE match_id=%s AND receipt_id=%s LIMIT 1",
                 (match_id, recibo["id"])).fetchone():
        return {"nuevo": False}
    lu = fila.get("lineups") or {}
    confirmado = bool(lu.get("confirmed"))
    lados = {"home": lu.get("home"), "away": lu.get("away")}
    xi = {s: titulares(lados[s]) for s in lados}
    n_bajas = 0
    for s, lado in lados.items():
        for b in bajas(lado):
            n_bajas += c.execute(
                """INSERT INTO injuries (match_id, side, player_id, player_name, status_type, reason,
                                         captured_at, source, expected_return)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, 'sofascore', %s) ON CONFLICT DO NOTHING""",
                (match_id, s, b["player_id"], b["player_name"], b["status_type"], b["reason"],
                 recibido, b["expected_return"])).rowcount
        if xi[s]:
            c.execute(
                """INSERT INTO lineups_previstas (match_id, side, formation, starters, confirmed, receipt_id,
                                                  captured_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                (match_id, s, (lado or {}).get("formation"), Jsonb(xi[s]), confirmado, recibo["id"], recibido))
    # Una fila de captura por partido, haya o no bajas: distingue «no comprobado» de «comprobado sin bajas».
    c.execute("""INSERT INTO injuries_capture_log (match_id, captured_at, n_reported) VALUES (%s, %s, %s)
                 ON CONFLICT DO NOTHING""", (match_id, recibido, n_bajas))
    oficial = confirmado and all(len(xi[s]) >= 11 for s in ("home", "away"))
    if oficial:
        ko = c.execute("SELECT kickoff_utc FROM matches WHERE match_id=%s", (match_id,)).fetchone()["kickoff_utc"]
        mins = int((ko - recibido).total_seconds() // 60)
        for s in ("home", "away"):
            if c.execute("SELECT 1 FROM lineups WHERE match_id=%s AND side=%s LIMIT 1", (match_id, s)).fetchone():
                continue
            c.execute("""INSERT INTO lineups (match_id, side, formation, starters, captured_at, mins_to_kickoff)
                         VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                      (match_id, s, (lados[s] or {}).get("formation"), Jsonb(xi[s]), recibido, mins))
    return {"nuevo": True, "bajas": n_bajas, "oficial": oficial, "previsto": not confirmado}
