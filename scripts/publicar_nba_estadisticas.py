"""Publica el JSON de estadísticas de equipos de NBA para la web. Ejecutar en el HOST (cron, bajo flock).

Corre `python -m nba.web_stats` dentro de la imagen NBA (solo lectura, sin red: necesita numpy/scipy y el verificador de
cohortes del panel) con las cohortes y los datos montados en solo lectura, recoge el JSON por stdout y lo escribe de forma
atómica en el volumen de artefactos de la API, que lo sirve en `/web/deportes/nba/estadisticas/{event_id}`.
No consulta ningún proveedor, no usa claves y no toca cohortes, modelos ni sellos. Si el contenedor falla o no hay eventos,
no se escribe nada: el archivo anterior sigue hasta que vence (6 h) y la web dice que no hay estadísticas.

Uso:  python3 publicar_nba_estadisticas.py [--dry-run]   (con --dry-run solo escribe `ultima_prueba.json` junto al script)
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HOME = Path.home()
LIVE = Path(os.environ.get("QF_NBA_LIVE", HOME / "nba-isolated" / "live13"))
IMAGE = os.environ.get("QF_NBA_STATS_IMAGE", "nba-web-stats:current")
API = os.environ.get("QF_API_CONTAINER", "quantfut-api-1")
HERE = Path(__file__).resolve().parent

WRITER = """import json,sys,os
from pathlib import Path
value=json.load(sys.stdin)
assert isinstance(value.get('events'),dict) and value['events'] and value.get('generated_at')
folder=Path('/srv/quantfut/artifacts/public-sports');folder.mkdir(parents=True,exist_ok=True)
temp=folder/('nba-stats-'+str(os.getpid())+'.tmp')
temp.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False),encoding='utf-8')
os.replace(temp,folder/'nba_stats.json')
"""


def build():
    command = ["docker", "run", "--rm", "--network", "none", "--read-only", "--tmpfs", "/tmp:rw,noexec,nosuid,size=32m",
               "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--pids-limit", "64", "--memory", "768m",
               "--user", f"{getattr(os, 'getuid', lambda: 1001)()}:{getattr(os, 'getgid', lambda: 1001)()}",
               "-v", f"{LIVE / 'cohorts'}:/live13/cohorts:ro", "-v", f"{LIVE / 'data'}:/live13/data:ro",
               "--entrypoint", "python", IMAGE, "-m", "nba.web_stats",
               "--cohorts", "/live13/cohorts", "--data", "/live13/data", "--output", "-"]
    done = subprocess.run(command, capture_output=True, timeout=300)
    if done.returncode:
        sys.stderr.write(done.stderr.decode("utf-8", "replace")[-2000:])
        raise SystemExit(f"contenedor NBA terminó con código {done.returncode}")
    value = json.loads(done.stdout.decode("utf-8"))
    if not isinstance(value.get("events"), dict) or not value["events"]:
        raise SystemExit("sin eventos: no se publica nada")
    return value


def main():
    dry = "--dry-run" in sys.argv
    value = build()
    payload = json.dumps(value, ensure_ascii=False, allow_nan=False)
    print(json.dumps({"at": datetime.now().astimezone().isoformat(), "events": len(value["events"]),
                      "games_used": value.get("games_used"), "dry_run": dry}))
    if dry:
        (HERE / "ultima_prueba.json").write_text(payload, encoding="utf-8")
        return
    subprocess.run(["docker", "exec", "-i", API, "python", "-c", WRITER], input=payload.encode(), check=True, timeout=60)


if __name__ == "__main__":
    main()
