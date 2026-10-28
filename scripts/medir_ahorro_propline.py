"""Mide, en solo lectura, las llamadas del recolector compartido de PropLine por día (fútbol y total).

Corre en el host leyendo ~/propline-shared/logs/AAAA-MM.log; desde el PC, sin copiar nada:
    ssh quantfut python3 - 2026-10-27 2026-10-29 < scripts/medir_ahorro_propline.py

Línea base del 27-oct-2026 (martes, antes de la regla de 48 h del 28-oct): 1.910 llamadas de fútbol y 2.742 en total.
Criterio de cierre de la auditoría: fútbol <= 1.300 en un día laborable, sin fallos ni paradas; en domingo de jornada
llena el ahorro puede ser pequeño (casi todas las ligas tienen partido en 48 h) y hay que decirlo sin maquillarlo.
"""
import json
import sys
from pathlib import Path

LOGS = Path.home() / "propline-shared" / "logs"
dias = sys.argv[1:] or ["2026-10-27"]
data = {}
for nombre in sorted({d[:7] for d in dias}):
    ruta = LOGS / f"{nombre}.log"
    if not ruta.is_file():
        print("sin log:", ruta)
        continue
    run = None
    for linea in ruta.read_text(encoding="utf8").splitlines():
        if "runner_started_at" in linea:
            run = json.loads(linea)["runner_started_at"]
            data[run] = [0, 0, None]
            continue
        if run and linea.startswith("{") and '"path"' in linea:
            p = json.loads(linea)["path"]
            if p.endswith("/odds") and "/soccer_" in p:
                data[run][0] += 1
            data[run][1] += 1
        if run and linea.startswith("{") and '"started_at"' in linea and '"requests"' in linea:
            r = json.loads(linea)
            data[run][2] = (r["failures"], r["stop"], r["quota"].get("x-daily-used"))
for d in dias:
    v = [x for k, x in data.items() if k.startswith(d)]
    fallos = sum((x[2] or (0,))[0] for x in v)
    paradas = [x[2][1] for x in v if x[2] and x[2][1]]
    print(f"{d}: corridas {len(v):2d} | fútbol {sum(x[0] for x in v):5d} | total {sum(x[1] for x in v):5d} | "
          f"fallos {fallos} | paradas {paradas}")
