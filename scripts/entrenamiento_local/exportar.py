"""Paso 4: exporta el candidato entrenado en local (esquema `entreno`) para subirlo: fila de model_artifacts,
calibration_runs y hashes de los artefactos, con las rutas reescritas a las del servidor.

    python scripts/entrenamiento_local/exportar.py .local/entreno_AAAAMMDD <versión>

Solo exporta un candidato que la puerta de `train.py` dejó activo en la copia local.
"""
import hashlib
import json
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

d, VERSION = Path(sys.argv[1]), sys.argv[2]
LOCAL, SRV = f"{d.as_posix().rstrip('/')}/artifacts/", "/srv/quantfut/artifacts/"
env = (Path(__file__).resolve().parents[2] / ".env").read_text(encoding="utf-8").splitlines()
dsn = [l.split("=", 1)[1].strip() for l in env if l.startswith("PG_DSN=")][0] + "?options=-csearch_path%3Dentreno%2Cpublic"
with psycopg.connect(dsn, row_factory=dict_row) as c:
    fila = c.execute("SELECT * FROM model_artifacts WHERE model_version = %s", (VERSION,)).fetchone()
    cal = c.execute("SELECT * FROM calibration_runs WHERE model_version = %s ORDER BY run_id", (VERSION,)).fetchall()
assert fila and fila["is_active"], "el candidato no quedó activo en local: no se sube como activo"
texto = json.dumps({"model_artifacts": fila, "calibration_runs": cal}, default=str, ensure_ascii=False)
assert LOCAL in texto
texto = texto.replace(LOCAL, SRV)
assert ".local/" not in texto
artefactos = sorted(p for p in (d / "artifacts").glob(f"*_{VERSION}.pkl"))
salida = {**json.loads(texto),
          "artefactos": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in artefactos}}
(d / f"subida_{VERSION}.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(artefactos), "artefactos;", len(cal), "calibration_runs;", salida["model_artifacts"]["artifact_uri"])
