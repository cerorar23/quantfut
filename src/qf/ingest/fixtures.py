"""
Calendario de partidos futuros. MÓDULO BLOQUEANTE DE LA FASE 1.

Sin esto, `matches` solo contiene partidos terminados, el odds_worker no
encuentra nada con status='scheduled' y el job diario no tiene qué predecir.

Se ejecuta 2 veces al día. Es idempotente: reingiere el mismo rango y solo
actualiza lo que cambió (reprogramaciones, cambios de horario).

Ojo con las reprogramaciones: un partido movido de fecha cambia su kickoff, y
si no lo actualizas el odds_worker captura las ventanas equivocadas y el CLV
compara contra un "cierre" que no lo era.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from ..db import execute, query, query_one
from ..normalize import (
    _record_unresolved,
    match_team,
    resolve_or_register,
    slugify,
)
from . import api_football as af

log = logging.getLogger(__name__)


def current_season(season_style: str, now: datetime | None = None) -> int:
    """
    API-Football pide `season` como año de inicio.
      - europea: 2025/26 -> 2025 (la temporada arranca en julio)
      - calendario / apertura-clausura: el año en curso
    """
    now = now or datetime.now(timezone.utc)
    if season_style == "european":
        return now.year if now.month >= 7 else now.year - 1
    return now.year


def _season_label(league: dict, ko: datetime) -> str:
    """
    Etiqueta de temporada para la columna `season`: la MISMA que pone el
    histórico de football-data (ver `history_fd.season_labels_extra`).

      european / apertura_clausura  2026/27 -> '2627' (Apertura 2026 y
                                    Clausura 2027 van juntos, como en MEX.csv)
      calendar                      2026    -> '2627' (BRA/ARG/USA.csv: '2026')

    Antes el año natural salía '2026' y Liga MX '2026A'/'2027C': la misma
    temporada quedaba con dos etiquetas según qué fuente creó cada partido.
    """
    style = league["season_style"]
    if style == "calendar":
        y = ko.year
    else:
        y = ko.year if ko.month >= 7 else ko.year - 1
    return f"{y % 100:02d}{(y + 1) % 100:02d}"


def _build_match_id(league_id: str, season: str, home: str, away: str,
                    ko: datetime) -> str:
    return (f"{league_id}:{season}:"
            f"{slugify(home)[:12].replace(' ', '')}-"
            f"{slugify(away)[:12].replace(' ', '')}:"
            f"{ko.strftime('%Y%m%d')}")


def _resolve(league: dict, raw_name: str) -> int | None:
    """
    Equipo de un partido de calendario.

    En una liga normal es `resolve_or_register`: un recién ascendido que no
    está en el catálogo es legítimo y se da de alta.

    En una competición CROSS-LEAGUE (Champions, Europa League) no: ahí los
    equipos vienen de sus ligas y darlos de alta bajo 'eu.ucl' crearía un
    duplicado del mismo club con la historia partida en dos. Se busca en todo
    el catálogo y SOLO se acepta una coincidencia exacta (alias registrado o
    nombre canónico). Nada de emparejamiento difuso: buscando en las 8 ligas a
    la vez, un difuso puede colocar un club europeo encima de uno
    latinoamericano de nombre parecido, y eso contamina dos historiales sin
    dar ningún error. Lo que no case se queda en `unresolved_names` para darle
    un alias a mano.
    """
    if not league.get("cross_league"):
        return resolve_or_register(raw_name, "api_football", league["league_id"])

    tid, cand, score = match_team(raw_name, "api_football", None)
    if tid and score >= 100.0:
        return tid
    _record_unresolved(raw_name, "api_football", league["league_id"], cand, score)
    log.warning("%s: '%s' no está en el catálogo (mejor candidato '%s', %.0f). "
                "Los equipos de copa NO se dan de alta: añade el alias a mano.",
                league["league_id"], raw_name, cand, score)
    return None


def ingest_league(league: dict, days_ahead: int = 21,
                  desde: datetime | None = None) -> dict:
    """`desde` (por defecto hoy) solo lo usa `cargar_temporada()`."""
    now = datetime.now(timezone.utc)
    season = current_season(league["season_style"], now)

    resp, meta = af.get("fixtures", {
        "league": league["api_football_id"],
        "season": season,
        "from": (desde or now).strftime("%Y-%m-%d"),
        "to": (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d"),
        "timezone": "UTC",
    })
    af.check_quota(meta)

    if meta["empty"]:
        # Silencio, no error. Puede ser parón de selecciones... o cobertura rota.
        log.warning("%s: 0 partidos en los próximos %d días (season=%s). "
                    "Verifica si es parón o si el api_football_id cambió.",
                    league["league_id"], days_ahead, season)
        return {"league": league["league_id"], "inserted": 0, "updated": 0,
                "unresolved": 0, "empty": True}

    inserted = updated = unresolved = 0

    for fx in resp:
        fixture, teams = fx["fixture"], fx["teams"]
        ko = datetime.fromisoformat(fixture["date"].replace("Z", "+00:00"))
        status = fixture["status"]["short"]

        # NS=no iniciado, TBD=por definir, PST=aplazado, CANC=cancelado
        if status in ("CANC", "ABD", "AWD", "WO"):
            continue
        db_status = "postponed" if status in ("PST", "TBD") else "scheduled"

        home_id = _resolve(league, teams["home"]["name"])
        away_id = _resolve(league, teams["away"]["name"])
        if not home_id or not away_id:
            unresolved += 1
            continue

        season_lbl = _season_label(league, ko)

        # ¿Ya existe por external_id? (cubre reprogramaciones que cambian la fecha)
        existing = query_one(
            """SELECT match_id, kickoff_utc, status FROM matches
               WHERE league_id = %s
                 AND external_ids ->> 'api_football' = %s""",
            (league["league_id"], str(fixture["id"])),
        )

        if existing:
            # El calendario pide el día entero: los partidos de hoy ya
            # terminados llegan como FT. Sin esta guarda volvían a
            # 'scheduled' y perdían su registro de captura hasta que
            # results.py los cerraba otra vez.
            if existing["status"] == "finished":
                continue
            if (abs((existing["kickoff_utc"] - ko).total_seconds()) > 300
                    or existing["status"] != db_status):
                execute(
                    """UPDATE matches SET kickoff_utc = %s, status = %s
                       WHERE match_id = %s""",
                    (ko, db_status, existing["match_id"]),
                )
                # La reprogramación invalida las ventanas de cuotas ya capturadas
                execute("DELETE FROM odds_capture_log WHERE match_id = %s",
                        (existing["match_id"],))
                updated += 1
                log.info("Reprogramado %s -> %s", existing["match_id"], ko)
            continue

        home_name = query_one("SELECT canonical_name FROM teams WHERE team_id=%s",
                              (home_id,))["canonical_name"]
        away_name = query_one("SELECT canonical_name FROM teams WHERE team_id=%s",
                              (away_id,))["canonical_name"]
        match_id = _build_match_id(league["league_id"], season_lbl,
                                   home_name, away_name, ko)

        n = execute(
            """INSERT INTO matches
                 (match_id, league_id, season, kickoff_utc, home_team_id,
                  away_team_id, status, external_ids)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (match_id) DO UPDATE
                 SET kickoff_utc = EXCLUDED.kickoff_utc,
                     status = EXCLUDED.status,
                     external_ids = matches.external_ids || EXCLUDED.external_ids
               """,
            (match_id, league["league_id"], season_lbl, ko, home_id, away_id,
             db_status, f'{{"api_football": "{fixture["id"]}"}}'),
        )
        inserted += n

    return {"league": league["league_id"], "inserted": inserted,
            "updated": updated, "unresolved": unresolved, "empty": False}


def run(days_ahead: int = 21) -> dict:
    leagues = query(
        """SELECT league_id, name, country, api_football_id, season_style,
                  cross_league
           FROM leagues WHERE active AND api_football_id IS NOT NULL"""
    )
    results, total, problems = [], 0, []

    for lg in leagues:
        try:
            r = ingest_league(lg, days_ahead)
        except Exception as exc:  # noqa: BLE001
            log.error("Fallo en %s: %s", lg["league_id"], exc)
            problems.append(f"{lg['league_id']}: {exc}")
            continue
        results.append(r)
        total += r["inserted"] + r["updated"]
        if r["unresolved"]:
            problems.append(f"{r['league']}: {r['unresolved']} equipos sin emparejar")

    ok = not problems
    af.record_health("fixtures", total, ok, {"results": results, "problems": problems})

    if problems:
        from ..publish.telegram import alert
        alert("Ingesta de calendario con incidencias:\n" + "\n".join(problems[:8]))

    summary = {"total": total, "leagues": len(results), "problems": problems}
    log.info("Calendario: %s", summary)
    return summary


def cargar_temporada(league_ids: list[str], dias_atras: int = 120) -> dict:
    """
    Partidos ya jugados de la temporada en curso para ligas dadas de alta con
    ella empezada (LaLiga 2 y Serie B, 25-sep). Sin ellos, la forma de sus
    equipos en la web salía de otra categoría. Se insertan como programados
    y los cierra `results.close_recent()` por el camino normal (marcador y
    estadísticas); `model_enabled = false` los deja fuera del modelo.
    """
    from .results import close_recent

    leagues = query(
        """SELECT league_id, name, country, api_football_id, season_style,
                  cross_league
           FROM leagues WHERE active AND api_football_id IS NOT NULL
             AND NOT cross_league AND league_id = ANY(%s)""",
        (league_ids,),
    )
    desde = datetime.now(timezone.utc) - timedelta(days=dias_atras)
    calendario = [ingest_league(lg, days_ahead=0, desde=desde) for lg in leagues]
    cierre = close_recent(hours_back=24 * dias_atras, leagues=league_ids)
    return {"calendario": calendario, "cierre": cierre}


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if len(sys.argv) > 2 and sys.argv[1] == "--temporada":
        print(cargar_temporada(sys.argv[2:]))
    else:
        print(run())
