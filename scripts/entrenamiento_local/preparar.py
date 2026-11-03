"""Paso 2: carga la copia de producción en el esquema `entreno` de la base local (no toca `public` ni otros esquemas).

    python scripts/entrenamiento_local/preparar.py .local/entreno_AAAAMMDD

Reescribe `public` -> `entreno`, quita las FK (solo se copian las tablas del entrenamiento) y las extensiones (ya
existen en la base local) y carga esquema y datos con psql. Las tablas de cuentas fallan por `citext`: no se usan.
"""
import gzip
import os
import re
import subprocess
import sys
from pathlib import Path

d = Path(sys.argv[1])
raiz = Path(__file__).resolve().parents[2]
psql = os.getenv("PSQL", r"C:\Program Files\PostgreSQL\16\bin\psql.exe")
dsn = [l.split("=", 1)[1].strip() for l in (raiz / ".env").read_text(encoding="utf-8").splitlines()
       if l.startswith("PG_DSN=")][0]
RUTA = "SELECT pg_catalog.set_config('search_path', '', false);"
NUEVA = "SELECT pg_catalog.set_config('search_path', 'entreno, public', false);"

esquema = gzip.decompress((d / "entreno_schema.sql.gz").read_bytes()).decode("utf-8")
esquema = re.sub(r"^CREATE SCHEMA public;\n|^COMMENT ON SCHEMA public IS .*\n", "", esquema, flags=re.M)
esquema = esquema.replace("public.", "entreno.")
esquema = re.sub(r"^CREATE EXTENSION .*\n|^COMMENT ON EXTENSION .*\n", "", esquema, flags=re.M)
esquema = re.sub(r"ALTER TABLE (ONLY )?\S+\n    ADD CONSTRAINT \S+ FOREIGN KEY [^;]*;\n", "", esquema)
assert "FOREIGN KEY" not in esquema
(d / "esquema_entreno.sql").write_text("DROP SCHEMA IF EXISTS entreno CASCADE;\nCREATE SCHEMA entreno;\n"
                                       + esquema.replace(RUTA, NUEVA), encoding="utf-8")

datos = gzip.decompress((d / "entreno_data.sql.gz").read_bytes()).decode("utf-8")
datos = re.sub(r"^COPY public\.", "COPY entreno.", datos, flags=re.M)
datos = re.sub(r"pg_catalog\.setval\('public\.", "pg_catalog.setval('entreno.", datos).replace(RUTA, NUEVA)
(d / "datos_entreno.sql").write_text(datos, encoding="utf-8")

env = {**os.environ, "PGCLIENTENCODING": "UTF8"}
# En Windows psql exige las opciones ANTES de la cadena de conexión.
r = subprocess.run([psql, "-q", "-v", "ON_ERROR_STOP=0", "-f", str(d / "esquema_entreno.sql"), "-d", dsn],
                   capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")
errores = [l for l in r.stderr.splitlines() if "ERROR" in l]
inesperados = [l for l in errores if "accounts" not in l and "citext" not in l]
print(f"esquema: {len(errores)} errores ({len(inesperados)} fuera de las tablas de cuentas)")
assert not inesperados, "\n".join(inesperados[:10])
subprocess.run([psql, "-q", "-1", "-v", "ON_ERROR_STOP=1", "-f", str(d / "datos_entreno.sql"), "-d", dsn],
               check=True, env=env)
print("datos cargados en el esquema entreno")
