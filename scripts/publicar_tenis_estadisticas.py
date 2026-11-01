"""Actualiza el JSON público de estadísticas de jugadores de tenis. Ejecutar en el HOST (cron).

31-oct-2026: API-Tennis vence y no se renueva. Si no responde (o con `QF_AT_CAIDO=1`) la clasificación sale de
SportsAPIPro (`/api/rankings`), el H2H y la forma reciente del archivo propio de partidos y los perfiles de la caché
(ver `tenis_estadisticas_respaldo.py`, en `~/tenis-equivalencias/current/`).

Consulta API-Tennis (`get_standings`, `get_players`, `get_H2H`) solo para los partidos que la web ya publica
(ventana: de ayer a +2 días), con caché en disco y un tope diario de llamadas. Luego resume las respuestas con
`tenis_estadisticas.py` (copia revisada de src/qf/api/tenis_estadisticas.py, en la misma carpeta) y escribe
`tennis_stats.json` en el volumen de artefactos de la API, que lo sirve en
`/web/deportes/tenis/estadisticas/{event_id}`. La clave de API-Tennis no sale de este proceso: ni se imprime
ni se publica; solo se publican las estadísticas ya resumidas. No toca el motor ni los sellos.

Uso:  python3 publicar_tenis_estadisticas.py [--dry-run]   (con --dry-run no escribe en la API)
"""
import fcntl
import glob
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

UTC = timezone.utc
HOME = Path.home()
sys.path.insert(0, str(HOME / "tenis-equivalencias" / "current"))
import tenis_estadisticas_respaldo as respaldo          # noqa: E402
import tenis_formato_api_tennis as formato               # noqa: E402
BASE = HOME / "quantfut-public-sports" / "stats"
CACHE = BASE / "cache"
SECRET = HOME / "quantfut-tenis" / "secrets" / ".env.api-tennis.local"
FIXTURES = HOME / "quantfut-tenis" / "data" / "intake_v1" / "api_tennis" / "originals"
API = "https://api.api-tennis.com/tennis/"
SP_SECRET = HOME / "tenis-equivalencias" / ".env.sportsapipro"
SP_API = "https://api.sportsapipro.com/v2/tennis/api/"
EQUIVALENCIAS = HOME / "tenis-equivalencias" / "data"
SP_DIARIO = 6           # peticiones a SportsAPIPro al día (clasificaciones); el resto de su cuota es de fútbol y del motor
AT_CAIDO = os.environ.get("QF_AT_CAIDO") == "1"
TTL = {"standings": 12 * 3600, "players": 24 * 3600, "h2h": 6 * 3600}
DAILY_BUDGET = 600      # llamadas por día UTC
RUN_BUDGET = 140        # llamadas por corrida
PAUSE = 0.35            # segundos entre llamadas
WINDOW = (timedelta(hours=-24), timedelta(hours=60))


def _module():
    spec = importlib.util.spec_from_file_location("tenis_estadisticas", Path(__file__).with_name("tenis_estadisticas.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _key():
    match = re.search(r"=\s*([A-Za-z0-9]{20,})", SECRET.read_text(encoding="utf-8"))
    if not match:
        raise RuntimeError("No hay clave de API-Tennis en el archivo de secretos")
    return match.group(1)


class Budget:
    def __init__(self):
        self.path = CACHE / "budget.json"
        today = datetime.now(UTC).date().isoformat()
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            value = {}
        self.day, self.used, self.run = today, value.get("used", 0) if value.get("day") == today else 0, 0

    def allow(self):
        return self.run < RUN_BUDGET and self.used < DAILY_BUDGET

    def spend(self):
        self.run += 1
        self.used += 1
        self.path.write_text(json.dumps({"day": self.day, "used": self.used}), encoding="utf-8")


def _cached(path, ttl):
    try:
        if time.time() - path.stat().st_mtime < ttl:
            return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    return None


def call(key, budget, method, **params):
    global AT_CAIDO
    if AT_CAIDO or not budget.allow():
        return None
    budget.spend()
    time.sleep(PAUSE)
    query = urllib.parse.urlencode({"method": method, "APIkey": key, **params})
    try:
        with urllib.request.urlopen(f"{API}?{query}", timeout=30) as response:
            value = json.load(response)
    except (urllib.error.URLError, ValueError, OSError):
        AT_CAIDO = True                                  # no insistir en esta corrida: el resto va por el respaldo
        return None
    if value.get("success") not in (1, "1", True):
        AT_CAIDO = True
        return None
    return value


def sp_key():
    match = re.search(r"SPORTSAPIPRO_KEY=\s*(\S+)", SP_SECRET.read_text(encoding="utf-8"))
    return match.group(1).strip("\"'") if match else None


def sp_rankings(circuit):
    """Clasificación del circuito desde SportsAPIPro (1 petición), con tope diario propio."""
    path = CACHE / "budget_sp.json"
    today = datetime.now(UTC).date().isoformat()
    try:
        used = json.loads(path.read_text(encoding="utf-8"))
        used = used.get("used", 0) if used.get("day") == today else 0
    except (OSError, ValueError):
        used = 0
    key = sp_key()
    if not key or used >= SP_DIARIO:
        return None
    path.write_text(json.dumps({"day": today, "used": used + 1}), encoding="utf-8")
    # ATP: tipo 5 = clasificación oficial (`/rankings` es la «live»: Zverev 9.550 frente a los 9.750 oficiales); WTA: `/rankings/wta` coincide
    url = SP_API + ("rankings/type/5" if circuit == "ATP" else "rankings/wta")
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 qf-tenis", "x-api-key": key})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            rows = ((json.load(response).get("data") or {}).get("rankings")) or []
    except (urllib.error.URLError, ValueError, OSError):
        return None
    jugadores = formato.indice(EQUIVALENCIAS)["jugadores"]
    return respaldo.clasificacion(rows, circuit, jugadores) or None


def public_events():
    """Eventos que la web publica hoy (id, inicio, circuito, superficie), leídos de la API en ejecución."""
    raw = subprocess.run(["docker", "exec", "quantfut-api-1", "cat", "/srv/quantfut/artifacts/public-sports/tennis.json"],
                         check=True, capture_output=True, timeout=30).stdout
    feed = json.loads(raw)
    now = datetime.now(UTC)
    rows = {}
    for event in feed.get("events", []):
        start = datetime.fromisoformat(event["start"].replace("Z", "+00:00")).astimezone(UTC)
        if WINDOW[0] <= start - now <= WINDOW[1]:
            rows[str(event["id"])] = {"start": start, "surface": event.get("surface"), "circuit": str(event.get("league", "")).split(" · ")[0]}
    return rows


def archive_rows():
    """event_key -> última fila archivada (API-Tennis o convertida de SportsAPIPro, mismo formato) de cada partido."""
    found = {}
    for path in sorted(glob.glob(str(FIXTURES / "*" / "response.json")), key=os.path.getmtime):
        try:
            for row in json.loads(Path(path).read_text(encoding="utf-8")).get("result") or []:
                if row.get("event_key") is not None:
                    found[str(row["event_key"])] = row
        except (OSError, ValueError, AttributeError):
            continue
    return found


def fixture_keys(wanted, rows):
    """event_key -> fila de fixture con las claves de jugador, de los originales ya archivados."""
    return {k: r for k, r in rows.items() if k in wanted and r.get("first_player_key") and r.get("second_player_key")}


def main():
    dry = "--dry-run" in sys.argv
    CACHE.mkdir(parents=True, exist_ok=True)
    for sub in ("players", "h2h"):
        (CACHE / sub).mkdir(exist_ok=True)
    with (BASE / "stats.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        stats = _module()
        key, budget, today = _key(), Budget(), datetime.now(UTC).date()
        events = public_events()
        rows = archive_rows()
        fixtures = fixture_keys(set(events), rows)
        partidos = respaldo.indice_partidos(rows.values())
        standings = {}
        for circuit in sorted({e["circuit"] for e in events.values() if e["circuit"] in ("ATP", "WTA")}):
            path = CACHE / f"standings_{circuit}.json"
            rows = _cached(path, TTL["standings"])
            if rows is None:
                reply = call(key, budget, "get_standings", event_type=circuit)
                rows = (reply or {}).get("result") or sp_rankings(circuit)
                if rows:
                    path.write_text(json.dumps(rows), encoding="utf-8")
                else:
                    rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
            for row in rows:
                standings.setdefault(circuit, {})[row.get("player_key")] = row
        out, missing = {}, 0
        for event_id in sorted(events, key=lambda i: events[i]["start"]):
            row = fixtures.get(event_id)
            if row is None:
                missing += 1
                continue
            first, second = row["first_player_key"], row["second_player_key"]
            players = {}
            for player in (first, second):
                path = CACHE / "players" / f"{player}.json"
                value = _cached(path, TTL["players"])
                if value is None:
                    reply = call(key, budget, "get_players", player_key=player)
                    value = (reply or {}).get("result")
                    if value:
                        path.write_text(json.dumps(value), encoding="utf-8")
                    elif path.exists():
                        value = json.loads(path.read_text(encoding="utf-8"))
                players[player] = value
            path = CACHE / "h2h" / f"{first}_{second}.json"
            h2h = _cached(path, TTL["h2h"])
            if h2h is None:
                h2h = call(key, budget, "get_H2H", first_player_key=first, second_player_key=second)
                if h2h:
                    path.write_text(json.dumps(h2h), encoding="utf-8")
                else:   # sin API-Tennis: archivo propio + lo que hubiera en la caché (más historia), sin escribir la caché
                    viejo = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
                    h2h = respaldo.h2h_local(partidos, first, second, viejo)
            if not any((h2h or {}).get("result", {}).values()) and not any(players.values()):
                missing += 1
                continue
            circuit = events[event_id]["circuit"]
            fixture = dict(row, surface=events[event_id]["surface"], circuit=circuit)
            out[event_id] = stats.build_event(fixture, players, standings.get(circuit, {}), h2h, today)
        payload = json.dumps({"generated_at": datetime.now(UTC).isoformat(), "events": out}, ensure_ascii=False, allow_nan=False)
        print(json.dumps({"events": len(out), "sin_datos": missing, "llamadas_corrida": budget.run, "llamadas_dia": budget.used, "dry_run": dry}))
        if dry:
            (BASE / "ultima_prueba.json").write_text(payload, encoding="utf-8")
        if dry or not out:
            return
        writer = """import json,sys,os
from pathlib import Path
value=json.load(sys.stdin)
assert isinstance(value.get('events'),dict) and value.get('generated_at')
folder=Path('/srv/quantfut/artifacts/public-sports');folder.mkdir(parents=True,exist_ok=True)
temp=folder/('tennis-stats-'+str(os.getpid())+'.tmp')
temp.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False),encoding='utf-8')
os.replace(temp,folder/'tennis_stats.json')
"""
        subprocess.run(["docker", "exec", "-i", "quantfut-api-1", "python", "-c", writer], input=payload.encode(), check=True, timeout=60)


if __name__ == "__main__":
    main()
