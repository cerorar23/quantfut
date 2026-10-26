"""Paso 5, DENTRO del worker: comprueba los artefactos subidos y registra el modelo entrenado en local.

Uso: python registrar.py subida_<version>.json [--activar]
Sin --activar solo comprueba (ensayo). Con --activar, en una transacción: desactiva el activo, inserta el nuevo como
activo y su calibration_runs. Igual que hace `train.py` al final de un entrenamiento en el servidor.
"""
import hashlib
import json
import sys
from pathlib import Path

from psycopg.types.json import Jsonb

from qf.config import settings
from qf.db import conn

datos = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
activar = "--activar" in sys.argv
fila = datos["model_artifacts"]
version = fila["model_version"]
carpeta = Path(settings.artifact_dir)
for nombre, sha in datos["artefactos"].items():
    real = hashlib.sha256((carpeta / nombre).read_bytes()).hexdigest()
    assert real == sha, f"hash distinto: {nombre}"
assert Path(fila["artifact_uri"]).is_file()

from qf.model.dixon_coles import DixonColes  # noqa: E402
modelo = DixonColes.load(fila["artifact_uri"])
print("modelo cargado:", version, "| converged", getattr(modelo.params, "converged", None))

with conn() as c:
    activo = c.execute("SELECT model_version FROM model_artifacts WHERE is_active").fetchone()
    existe = c.execute("SELECT 1 FROM model_artifacts WHERE model_version = %s", (version,)).fetchone()
    print("activo ahora:", activo and activo["model_version"], "| ya registrado:", bool(existe))
    if not activar:
        print("ensayo: no se escribe nada")
        raise SystemExit(0)
    assert not existe, "esa versión ya está registrada"
    with c.transaction():
        c.execute("UPDATE model_artifacts SET is_active = FALSE WHERE is_active")
        c.execute("""INSERT INTO model_artifacts (model_version, trained_at, dataset_sha256, params, val_metrics,
                                                  artifact_uri, is_active, notes)
                     VALUES (%s, %s, %s, %s, %s, %s, TRUE, %s)""",
                  (version, fila["trained_at"], fila["dataset_sha256"], Jsonb(fila["params"]),
                   Jsonb(fila["val_metrics"]), fila["artifact_uri"], fila["notes"]))
        for r in datos["calibration_runs"]:
            c.execute("""INSERT INTO calibration_runs (model_version, window_start, window_end, market, n_obs, rps,
                                                       log_loss, brier, rps_market, bins)
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                      (version, r["window_start"], r["window_end"], r["market"], r["n_obs"], r["rps"], r["log_loss"],
                       r["brier"], r["rps_market"], Jsonb(r["bins"]) if r["bins"] is not None else None))
    print("activado:", c.execute("SELECT model_version FROM model_artifacts WHERE is_active").fetchone()["model_version"])
