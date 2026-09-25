#!/usr/bin/env python3
"""
Bootstrap del emparejamiento de nombres entre las tres fuentes.

EJECUTAR UNA VEZ tras el backfill histórico, y de nuevo al empezar cada
temporada (los ascensos traen nombres nuevos).

Qué hace:
  1. Lee los nombres canónicos que dejó football-data.co.uk (la base).
  2. Pide a API-Football sus equipos por liga y los empareja.
  3. Pide a The Odds API sus eventos próximos y empareja esos nombres.
  4. Auto-registra lo que supera el umbral, y saca un reporte de lo que no.

Uso:
    python scripts/bootstrap_aliases.py                 # ejecuta y reporta
    python scripts/bootstrap_aliases.py --dry-run       # solo reporta
    python scripts/bootstrap_aliases.py --fix ARCHIVO   # aplica correcciones

El archivo de correcciones es un CSV: raw_name,source,canonical_name
Esas 20 líneas que escribas a mano son lo que evita que el sistema pierda
partidos en silencio durante toda la temporada.
"""
from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from qf.config import settings                                    # noqa: E402
from qf.db import execute, query, query_one                       # noqa: E402
from qf.ingest import api_football as af                          # noqa: E402
from qf.normalize import (AUTO_ACCEPT, SUGGEST_FLOOR, clear_cache,  # noqa: E402
                          match_team, pending_report, register_alias, slugify)

log = logging.getLogger("bootstrap")


def collect_api_football(season_override: int | None = None
                         ) -> list[tuple[str, str, str | None]]:
    """[(raw_name, source, league_id)] desde API-Football.

    `season_override` existe por los planes con ventana de temporadas cerrada
    (el Free solo da 2022-2024): sin él, la temporada en curso devuelve un
    error de plan y no se recoge ni un nombre. Los nombres de los clubes
    apenas cambian de año a año, así que una temporada reciente accesible
    sirve igual para construir los alias.
    """
    out: list[tuple[str, str, str | None]] = []
    for lg in query("SELECT league_id, api_football_id, season_style, cross_league "
                    "FROM leagues WHERE active AND api_football_id IS NOT NULL"):
        from qf.ingest.fixtures import current_season
        season = season_override or current_season(lg["season_style"])
        try:
            resp, meta = af.get("teams", {"league": lg["api_football_id"],
                                          "season": season})
            af.check_quota(meta)
        except Exception as exc:  # noqa: BLE001
            log.error("API-Football %s: %s", lg["league_id"], exc)
            continue
        # En una competición cross_league el equipo NO pertenece a esa
        # competición: pasar 'eu.ucl' como liga restringiría la búsqueda a un
        # conjunto vacío. Se pasa None para buscar en todo el catálogo, y el
        # umbral exacto de `run()` impide que el difuso cruce continentes.
        target = None if lg["cross_league"] else lg["league_id"]
        for item in resp:
            out.append((item["team"]["name"], "api_football", target))
        log.info("API-Football %s: %d equipos (season=%s)",
                 lg["league_id"], len(resp), season)
    return out


def collect_odds_api() -> list[tuple[str, str, str]]:
    """[(raw_name, source, league_id)] desde los eventos próximos de The Odds API."""
    import httpx
    out = []
    for lg in query("SELECT league_id, odds_api_key, cross_league FROM leagues "
                    "WHERE active AND odds_api_key IS NOT NULL"):
        url = f"{settings.odds_api_base}/sports/{lg['odds_api_key']}/events"
        try:
            with httpx.Client(timeout=30) as c:
                r = c.get(url, params={"apiKey": settings.odds_api_key})
                r.raise_for_status()
                events = r.json()
        except Exception as exc:  # noqa: BLE001
            log.error("The Odds API %s: %s", lg["league_id"], exc)
            continue
        names = set()
        for ev in events:
            names.add(ev.get("home_team", ""))
            names.add(ev.get("away_team", ""))
        # Mismo criterio que en API-Football: en una copa el equipo no
        # pertenece a la competición, así que acotar por ella daría un
        # conjunto vacío y ni siquiera un candidato que revisar.
        target = None if lg["cross_league"] else lg["league_id"]
        for n in names:
            if n:
                out.append((n, "odds_api", target))
        log.info("The Odds API %s: %d nombres", lg["league_id"], len(names))
    return out


def run(dry_run: bool = False, season: int | None = None) -> dict:
    base = query("SELECT count(*) AS n FROM teams")[0]["n"]
    if base == 0:
        raise SystemExit(
            "No hay equipos en la base. Ejecuta primero el backfill histórico:\n"
            "  python -m qf.ingest.history_fd"
        )
    log.info("Equipos canónicos en base: %d", base)

    candidates = collect_api_football(season) + collect_odds_api()
    auto, manual, already = 0, [], 0

    for raw, source, league_id in candidates:
        tid, cand, score = match_team(raw, source, league_id)
        # Sin liga que acote, el difuso busca en las 13 competiciones a la vez
        # y puede poner un club europeo encima de uno latinoamericano de nombre
        # parecido. Ahí solo vale la coincidencia exacta.
        if tid and league_id is None and score < 100.0:
            tid, cand = None, cand or slugify(raw)
        if tid and score == 100.0 and slugify(raw) in _existing_aliases(source):
            already += 1
            continue
        if tid:
            if not dry_run:
                register_alias(raw, source, tid)
            auto += 1
        else:
            manual.append({"raw_name": raw, "source": source,
                           "league_id": league_id,
                           "best_guess": cand or "", "score": round(score, 1)})

    clear_cache()
    return {"auto_registered": auto, "already": already, "manual": manual}


def _existing_aliases(source: str) -> set[str]:
    return {slugify(r["alias"]) for r in
            query("SELECT alias FROM team_aliases WHERE source=%s AND team_id IS NOT NULL",
                  (source,))}


def write_report(manual: list[dict], path: str = "aliases_pendientes.csv") -> None:
    p = Path(path)
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["raw_name", "source", "league_id", "best_guess",
                    "score", "canonical_name_CORRIGE_AQUI"])
        for m in sorted(manual, key=lambda x: -x["score"]):
            w.writerow([m["raw_name"], m["source"], m["league_id"],
                        m["best_guess"], m["score"], ""])
    print(f"\nReporte escrito en {p.resolve()}")
    print("Rellena la última columna con el nombre canónico correcto y aplícalo con:")
    print(f"  python scripts/bootstrap_aliases.py --fix {path}")


def apply_fixes(path: str) -> int:
    applied = 0
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            canonical = (row.get("canonical_name_CORRIGE_AQUI") or "").strip()
            if not canonical:
                continue
            # Las filas de competiciones cross_league salen sin liga: ahí el
            # nombre canónico tiene que ser único en todo el catálogo, porque
            # no hay liga que desempate.
            if row.get("league_id"):
                t = query_one(
                    """SELECT team_id FROM teams
                       WHERE league_id = %s AND canonical_name = %s""",
                    (row["league_id"], canonical),
                )
            else:
                hits = query("SELECT team_id, league_id FROM teams "
                             "WHERE canonical_name = %s", (canonical,))
                if len(hits) > 1:
                    ligas = ", ".join(h["league_id"] for h in hits)
                    print(f"  ! '{canonical}' existe en varias ligas ({ligas}); "
                          "pon la liga en la columna league_id")
                    continue
                t = hits[0] if hits else None
            if not t:
                print(f"  ! '{canonical}' no existe en {row['league_id'] or 'el catálogo'}, se omite")
                continue
            register_alias(row["raw_name"], row["source"], t["team_id"])
            applied += 1
    clear_cache()
    print(f"{applied} aliases aplicados.")
    return applied


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--fix", metavar="CSV")
    ap.add_argument("--report", default="aliases_pendientes.csv")
    ap.add_argument("--season", type=int, default=None,
                    help="Fuerza la temporada de API-Football (planes con "
                         "ventana cerrada; el Free solo cubre 2022-2024).")
    args = ap.parse_args()

    if args.fix:
        apply_fixes(args.fix)
        return

    res = run(dry_run=args.dry_run, season=args.season)

    print("\n" + "=" * 62)
    print(f"  Ya emparejados previamente : {res['already']}")
    print(f"  Auto-registrados (>= {AUTO_ACCEPT}) : {res['auto_registered']}")
    print(f"  Requieren revisión manual  : {len(res['manual'])}")
    print("=" * 62)

    if res["manual"]:
        print("\nPendientes con mejor candidato (los de score alto suelen ser")
        print("el mismo equipo escrito distinto):\n")
        for m in sorted(res["manual"], key=lambda x: -x["score"])[:25]:
            guess = m["best_guess"] or "(sin candidato)"
            print(f"  {m['score']:5.1f}  {m['raw_name'][:30]:30s} "
                  f"[{m['source']:14s}] -> {guess}")
        write_report(res["manual"], args.report)
        print("\nNO SIGAS hasta dejar esta lista vacía. Un equipo sin emparejar")
        print("significa partidos que el sistema nunca va a ver, sin ningún error.")
    else:
        print("\nTodo emparejado. Puedes continuar con la fase 1.")


if __name__ == "__main__":
    main()
