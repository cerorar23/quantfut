"""Ensayo de una imagen del worker: se ejecuta DENTRO del contenedor (python - < este archivo) y es de solo lectura.

Lo corre tanto el worker actual como la candidata; los resultados deben ser iguales. Necesita en /app/scripts_crontab.txt
las líneas de scripts/crontab (sin comentarios) para comprobar que cada punto de entrada del cron se puede importar.
"""
import importlib, json, pkgutil, re, sys, py_compile, hashlib
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
out = {}
import qf
# 1. importar todos los módulos de qf
fallos = []
for m in pkgutil.walk_packages(qf.__path__, "qf."):
    try: importlib.import_module(m.name)
    except Exception as e: fallos.append(f"{m.name}: {type(e).__name__}: {str(e)[:80]}")
out["modulos_importados_con_error"] = fallos
# 2. puntos de entrada del cron
cron = Path("/app/scripts_crontab.txt")
mods = sorted(set(re.findall(r"python -m (qf[\w\.]+)", cron.read_text()))) if cron.exists() else []
out["entradas_cron"] = len(mods)
out["entradas_cron_con_error"] = [m for m in mods if (lambda n: (importlib.util.find_spec(n) is None))(m)]
# 3. regenerar cada lote sellado y comparar contenido (sin generated_at_utc)
from qf.publish import hashchain as h
from qf.config import settings
res = {"lotes": 0, "iguales": 0, "distintos": []}
for f in sorted(Path(settings.chain_dir).glob("????-??-??.json")):
    guardado = json.loads(f.read_text(encoding="utf-8")); guardado.pop("generated_at_utc", None)
    nuevo = h._collect(date.fromisoformat(f.stem)); nuevo.pop("generated_at_utc", None)
    res["lotes"] += 1
    if h.canonical_json(guardado) == h.canonical_json(nuevo): res["iguales"] += 1
    else: res["distintos"].append(f.stem)
out["lotes_regenerados"] = res
ok, errores = h.verify()
out["verify_cadena"] = {"ok": ok, "errores": errores[:3]}
# 4. huella del conjunto de entrenamiento (partidos de hace más de 2 días, para que no cambie entre ejecuciones)
from qf.model import train
df = train.load_training_data()
df = df[df["kickoff_utc"] < (datetime.now(timezone.utc) - timedelta(days=2))].sort_values("match_id")
cols = sorted(df.columns)
out["entrenamiento"] = {"filas": int(len(df)), "con_cierre": int(df["odds_home"].notna().sum()),
                        "huella": hashlib.sha256(df[cols].to_csv(index=False).encode()).hexdigest()[:16]}
print(json.dumps(out, ensure_ascii=False))
