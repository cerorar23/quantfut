"""Descarga histórica a archivos, sin base de datos ni actualización recurrente.

Rutas observadas en pseudo-r/Public-FotMob-API (auditoría 30-sep-2026).
Ejecutar con acceso autorizado a FotMob. No evita controles de acceso.
"""
from __future__ import annotations

import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import csv
from datetime import date, datetime, timedelta, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..league_policy import RETIRED_LEAGUES, require_supported_league

BASE = "https://www.fotmob.com/api/data/"
# IDs contrastados con allLeagues; no son los IDs de API-Football.
COMPETITIONS = {
    "gb.premier_league": (47, "ENG", "Premier League"),
    "es.laliga": (87, "ESP", "LaLiga"),
    "it.serie_a": (55, "ITA", "Serie A"),
    "mx.liga_mx": (230, "MEX", "Liga MX"),
    "br.serie_a": (268, "BRA", "Série A"),
    "ar.primera": (112, "ARG", "Liga Profesional"),
    "nl.eredivisie": (57, "NED", "Eredivisie"),
    "us.mls": (130, "USA", "MLS"),
    "de.bundesliga": (54, "GER", "Bundesliga"),
    "fr.ligue_1": (53, "FRA", "Ligue 1"),
    "pt.primeira": (61, "POR", "Liga Portugal"),
    "es.laliga2": (140, "ESP", "LaLiga2"),
    "it.serie_b": (86, "ITA", "Serie B"),
    "tr.super_lig": (71, "TUR", "Süper Lig"),
    "ch.super_league": (69, "SUI", "Super League"),
    "dk.superliga": (46, "DEN", "Superligaen"),
    "no.eliteserien": (59, "NOR", "Eliteserien"),
    "se.allsvenskan": (67, "SWE", "Allsvenskan"),
    "gb.championship": (48, "ENG", "Championship"),
    "fr.ligue_2": (110, "FRA", "Ligue 2"),
    "de.bundesliga2": (146, "GER", "2. Bundesliga"),
    "eu.ucl": (42, "INT", "Champions League"),
    "eu.uel": (73, "INT", "Europa League"),
}
# México dejó de aplicar horario de verano antes del intervalo solicitado.
MEXICO = timezone(timedelta(hours=-6))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def parse_time(value: str) -> datetime:
    value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        raise ValueError("Fecha sin zona horaria")
    return value


def season_labels(hub: dict, start: date, end: date) -> list[str]:
    labels = []
    for item in hub.get("allAvailableSeasons", []):
        label = item if isinstance(item, str) else item.get("id", item.get("seasonName"))
        if not isinstance(label, str):
            raise ValueError("Formato de temporada desconocido")
        years = [int(y) for y in re.findall(r"\b(?:19|20)\d{2}\b", label)]
        if years and min(years) <= end.year and max(years) >= start.year:
            labels.append(label)
    if not labels:
        raise ValueError("No se descubrieron temporadas para el intervalo")
    return list(dict.fromkeys(labels))


def collect_fixtures(hub: dict, league: str, season: str, start: date, end: date) -> list[dict]:
    require_supported_league(league)
    expected = COMPETITIONS[league][0]
    details = hub.get("details", {})
    if int(details.get("id", -1)) != expected or details.get("selectedSeason") != season:
        raise ValueError(f"Liga/temporada solicitada no coincide: {league} {season}")
    matches = hub.get("fixtures", {}).get("allMatches")
    if not isinstance(matches, list):
        raise ValueError("Falta fixtures.allMatches")
    result = []
    for match in matches:
        status = match.get("status", {})
        if not status.get("finished") or status.get("cancelled") or status.get("awarded"):
            continue
        kickoff = parse_time(status["utcTime"])
        if not start <= kickoff.astimezone(MEXICO).date() <= end:
            continue
        match_id = str(match["id"])
        if not match_id.isdigit():
            raise ValueError("ID de partido no numérico")
        result.append({
            "league_id": league, "fotmob_league_id": expected, "season": season,
            "fotmob_match_id": match_id, "kickoff_utc": kickoff.isoformat(),
            "home_team_id": str(match["home"]["id"]), "home_team": match["home"]["name"],
            "away_team_id": str(match["away"]["id"]), "away_team": match["away"]["name"],
            "score": status.get("scoreStr"), "round": match.get("round"),
        })
    return result


def number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) and value >= 0 else None


def stat_pairs(node) -> dict[str, list]:
    """Recorre grupos reales; la documentación usa un ejemplo más plano."""
    pairs = {}
    if isinstance(node, dict):
        values = node.get("rawStats")
        if isinstance(values, list) and len(values) == 2:
            values = [v.get("value") if isinstance(v, dict) else v for v in values]
        else:
            values = node.get("stats")
        if isinstance(values, list) and len(values) == 2 and not any(isinstance(v, dict) for v in values):
            pairs[node.get("key", node.get("title", ""))] = [number(v) for v in values]
        for value in node.values():
            if isinstance(value, (dict, list)):
                pairs.update(stat_pairs(value))
    elif isinstance(node, list):
        for value in node:
            pairs.update(stat_pairs(value))
    return pairs


def normalize_match(fixture: dict, payload: dict, captured_at: str) -> dict:
    require_supported_league(fixture['league_id'])
    general = payload.get("general", {})
    if str(general.get("matchId")) != fixture["fotmob_match_id"]:
        raise ValueError("El detalle pertenece a otro partido")
    for side in ("home", "away"):
        if str(general.get(side + "Team", {}).get("id")) != fixture[side + "_team_id"]:
            raise ValueError("Equipos del detalle no coinciden con el calendario")
    # Clausura/Apertura y algunas ediciones históricas tienen ID propio.
    # FotMob declara explícitamente su liga principal con parentLeagueId.
    league_id = general.get("parentLeagueId") or general.get("leagueId", -1)
    if int(league_id) != fixture["fotmob_league_id"]:
        raise ValueError("Competición del detalle no coincide")
    if not payload.get("header", {}).get("status", {}).get("finished"):
        raise ValueError("El detalle no está finalizado")
    if abs((parse_time(general["matchTimeUTCDate"]) - parse_time(fixture["kickoff_utc"])).total_seconds()) > 60:
        raise ValueError("Fecha del detalle no coincide")
    content = payload.get("content", {})
    periods = (content.get("stats") or {}).get("Periods", {})
    all_stats = stat_pairs(periods.get("All", {}))
    row = dict(fixture, source="fotmob", captured_at=captured_at)
    fields = {
        "xg": "expected_goals", "xgot": "expected_goals_on_target",
        "shots": "total_shots", "shots_target": "ShotsOnTarget", "corners": "corners",
        "possession": "BallPossesion", "yellow_cards": "yellow_cards", "red_cards": "red_cards",
        "big_chances": "big_chance", "big_chances_missed": "big_chance_missed_title",
    }
    for field, key in fields.items():
        home, away = all_stats.get(key, [None, None])
        row["home_" + field], row["away_" + field] = home, away
    row["download_status"] = "with_xg" if row["home_xg"] is not None and row["away_xg"] is not None else "missing_xg"
    row["stats_json"] = json.dumps(all_stats, ensure_ascii=False, separators=(",", ":"))
    row["shot_count"] = len((content.get("shotmap") or {}).get("shots", []))
    return row


class AccessDenied(RuntimeError):
    pass


class Downloader:
    def __init__(self, root: Path, interval: float):
        self.root, self.interval = root, interval
        self.lock = threading.Lock()
        self.last_call = 0.0
        self.stopped = threading.Event()

    def fetch(self, endpoint: str, params: dict, cache: Path):
        meta = cache.with_suffix(cache.suffix + ".meta.json")
        if cache.exists() and meta.exists():
            with gzip.open(cache, "rt", encoding="utf-8") as handle:
                return json.load(handle), load_json(meta)["captured_at"]
        url = BASE + endpoint + ("?" + urlencode(params) if params else "")
        for attempt in range(3):
            with self.lock:
                delay = self.interval - (time.monotonic() - self.last_call)
                if delay > 0:
                    time.sleep(delay)
                if self.stopped.is_set():
                    raise AccessDenied("Descarga detenida por una denegación previa")
                self.last_call = time.monotonic()
            try:
                request = Request(url, headers={"Accept": "application/json", "Accept-Encoding": "gzip", "User-Agent": "QuantFut-Historical-Download/1.0"})
                with urlopen(request, timeout=30) as response:
                    raw = response.read()
                    if response.headers.get("Content-Encoding") == "gzip":
                        raw = gzip.decompress(raw)
                data = json.loads(raw)
                if not isinstance(data, dict) or data.get("error"):
                    raise ValueError("Respuesta JSON sin datos válidos")
                captured = utc_now()
                cache.parent.mkdir(parents=True, exist_ok=True)
                temp = cache.with_name(cache.name + ".tmp")
                with gzip.open(temp, "wb") as handle:
                    handle.write(raw)
                temp.replace(cache)
                save_json(meta, {"url": url, "captured_at": captured, "sha256": hashlib.sha256(raw).hexdigest()})
                return data, captured
            except HTTPError as exc:
                if exc.code in (401, 403, 429):
                    self.stopped.set()
                    save_json(self.root / "access-denied.json", {"url": url, "http_status": exc.code, "captured_at": utc_now()})
                    raise AccessDenied(f"HTTP {exc.code}: {url}") from exc
                if exc.code < 500:
                    raise
                error = exc
            except (URLError, TimeoutError, ConnectionError) as exc:
                error = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
        raise error


def validate_catalog(catalog: dict) -> None:
    international = catalog["international"]
    groups = [international] if isinstance(international, dict) else list(international)
    groups.extend(catalog["countries"])
    entries = {int(lg["id"]): (group["ccode"], lg["name"]) for group in groups for lg in group["leagues"]}
    for league, (lid, country, name) in COMPETITIONS.items():
        if entries.get(lid) != (country, name):
            raise ValueError(f"El catálogo ha cambiado: {league}: {entries.get(lid)}")


def inventory(downloader: Downloader, start: date, end: date) -> dict:
    root = downloader.root
    catalog, _ = downloader.fetch("allLeagues", {}, root / "raw" / "allLeagues.json.gz")
    validate_catalog(catalog)
    fixtures, seasons, errors = {}, [], []
    for league, (lid, _, _) in COMPETITIONS.items():
        try:
            latest, _ = downloader.fetch("leagues", {"id": lid}, root / "raw" / "leagues" / f"{lid}-latest.json.gz")
            for season in season_labels(latest, start, end):
                slug = re.sub(r"[^A-Za-z0-9_-]", "_", season)
                try:
                    hub, _ = downloader.fetch("leagues", {"id": lid, "season": season}, root / "raw" / "leagues" / f"{lid}-{slug}.json.gz")
                    matches = collect_fixtures(hub, league, season, start, end)
                    for match in matches:
                        key = match["fotmob_match_id"]
                        if key in fixtures and fixtures[key]["league_id"] != league:
                            raise ValueError("ID de partido repetido entre competiciones")
                        fixtures.setdefault(key, match)
                    seasons.append({"league_id": league, "season": season, "finished_matches": len(matches)})
                    print(f"Inventario {league} {season}: {len(matches)} terminados", flush=True)
                except AccessDenied:
                    raise
                except (ValueError, HTTPError, URLError, TimeoutError) as exc:
                    errors.append({"league_id": league, "season": season, "error": str(exc)})
        except AccessDenied:
            raise
        except (ValueError, HTTPError, URLError, TimeoutError) as exc:
            errors.append({"league_id": league, "error": str(exc)})
        manifest = {"start": start.isoformat(), "end": end.isoformat(), "date_timezone": "America/Mexico_City", "created_at": utc_now(),
                    "complete": False, "seasons": seasons, "errors": errors, "fixtures": list(fixtures.values())}
        save_json(root / "manifest.json", manifest)
    manifest["complete"] = not errors
    save_json(root / "manifest.json", manifest)
    print(f"Inventario: {len(fixtures)} partidos, {len(seasons)} temporadas, {len(errors)} errores", flush=True)
    return manifest


def supported_manifest(manifest):
    return dict(manifest, fixtures=[m for m in manifest['fixtures']
                                   if m['league_id'] not in RETIRED_LEAGUES])


def export(root: Path, manifest: dict, rows: dict) -> dict:
    manifest = supported_manifest(manifest)
    output = root / "matches.csv"
    fields = list(dict.fromkeys(k for row in rows.values() for k in row)) if rows else list(manifest["fixtures"][0]) if manifest["fixtures"] else ["fotmob_match_id"]
    fields = list(dict.fromkeys([*fields, "download_status", "error"]))
    temp = output.with_suffix(".csv.tmp")
    with temp.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        for fixture in sorted(manifest["fixtures"], key=lambda m: (m["league_id"], m["kickoff_utc"], m["fotmob_match_id"])):
            row = rows.get(fixture["fotmob_match_id"], dict(fixture, download_status="pending"))
            writer.writerow(row)
    temp.replace(output)
    coverage = []
    for league in COMPETITIONS:
        ids = [m["fotmob_match_id"] for m in manifest["fixtures"] if m["league_id"] == league]
        counts = {status: sum(rows.get(mid, {}).get("download_status", "pending") == status for mid in ids)
                  for status in ("with_xg", "missing_xg", "error", "pending")}
        coverage.append({"league_id": league, "matches": len(ids), **counts})
    summary = {"start": manifest["start"], "end": manifest["end"], "updated_at": utc_now(),
               "inventory_complete": manifest["complete"], "inventory_errors": manifest["errors"],
               "download_complete": manifest["complete"] and all(not x["pending"] and not x["error"] for x in coverage),
               "matches": len(manifest["fixtures"]), "coverage": coverage}
    save_json(root / "coverage.json", summary)
    with (root / "coverage.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(coverage[0]))
        writer.writeheader()
        writer.writerows(coverage)
    return summary


def download_details(downloader: Downloader, manifest: dict, workers: int) -> dict:
    manifest = supported_manifest(manifest)
    root = downloader.root
    checkpoints = root / "rows"
    rows = {p.stem: load_json(p) for p in checkpoints.glob("*.json")}

    def download_one(fixture):
        mid = fixture["fotmob_match_id"]
        try:
            data, captured = downloader.fetch("matchDetails", {"matchId": mid}, root / "raw" / "matches" / f"{mid}.json.gz")
            row = normalize_match(fixture, data, captured)
        except AccessDenied:
            raise
        except (ValueError, KeyError, TypeError, HTTPError, URLError, TimeoutError) as exc:
            row = dict(fixture, download_status="error", error=str(exc))
        save_json(checkpoints / f"{mid}.json", row)
        return mid, row

    pending = iter(m for m in manifest["fixtures"] if rows.get(m["fotmob_match_id"], {}).get("download_status") not in ("with_xg", "missing_xg"))
    active, completed, denied = {}, 0, None
    with ThreadPoolExecutor(max_workers=workers) as pool:
        def submit_one():
            fixture = next(pending, None)
            if fixture is not None:
                active[pool.submit(download_one, fixture)] = fixture

        for _ in range(workers):
            submit_one()
        while active:
            ready, _ = wait(active, return_when=FIRST_COMPLETED)
            for future in ready:
                active.pop(future)
                try:
                    mid, row = future.result()
                    rows[mid] = row
                    completed += 1
                except AccessDenied as exc:
                    denied = exc
                if not denied:
                    submit_one()
            if completed % 100 < len(ready) or denied:
                export(root, manifest, rows)
                good = sum(r["download_status"] == "with_xg" for r in rows.values())
                print(f"Detalles {len(rows)}/{len(manifest['fixtures'])}; con xG {good}", flush=True)
    result = export(root, manifest, rows)
    if denied:
        raise denied
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2024, 1, 1))
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--inventory-only", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--interval", type=float, default=0.5, help="Segundos mínimos entre peticiones globalmente")
    args = parser.parse_args()
    if args.start < date(2024, 1, 1) or args.end < args.start or args.workers < 1 or args.interval < 0:
        parser.error("Intervalo de fechas/peticiones no válido (fechas desde 2024)")
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    downloader = Downloader(root, args.interval)
    try:
        manifest_path = root / "manifest.json"
        manifest = load_json(manifest_path) if manifest_path.exists() else None
        if manifest and (manifest["start"] != args.start.isoformat() or manifest["end"] != args.end.isoformat()):
            parser.error("La carpeta contiene otro intervalo de fechas")
        if not manifest or not manifest["complete"]:
            manifest = inventory(downloader, args.start, args.end)
        if args.inventory_only:
            rows = {p.stem: load_json(p) for p in (root / "rows").glob("*.json")}
            export(root, manifest, rows)
            return 0 if manifest["complete"] else 1
        summary = download_details(downloader, manifest, args.workers)
        print(json.dumps({k: v for k, v in summary.items() if k != "coverage"}, ensure_ascii=False), flush=True)
        return 0 if summary["download_complete"] else 1
    except AccessDenied as exc:
        print(f"Detenido: {exc}", flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
