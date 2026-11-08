#!/bin/bash
set -euo pipefail
BASE="/home/qf/nba-isolated/nba-captura"
RELEASES="/home/qf/nba-isolated/releases"
ACTUAL="$(find "$RELEASES" -maxdepth 1 -name "auditoria-*" | head -n 1)"
OPS="$ACTUAL/apps/nba/ops"
IMAGEN="$(cat "$BASE/imagen_motor")"

echo "[1/5] Exportando datos desde nba_datos..."
docker run --rm --network nba-red \
  -v "${OPS}:/ops" -v "${BASE}/datos:/datos" \
  --env-file "${BASE}/motor.env" \
  -e NBA_DB_DSN_LECTOR="postgresql://nba_motor:c5bfddc2db1062f9a11efedc2a7438813f62d886be8bf033@nba-db:5432/nba_datos" \
  "${IMAGEN}" python /ops/exportar_equipo.py /datos/exportacion_auto.json

echo "[2/5] Entrenando nuevo artefacto de equipo..."
docker run --rm \
  -v "${OPS}:/ops" -v "${BASE}/datos:/datos" \
  "${IMAGEN}" python /ops/entrenar_equipo.py /datos/exportacion_auto.json /datos/equipo_nuevo.json

echo "[3/5] Evaluando artefacto nuevo..."
docker run --rm \
  -v "${OPS}:/ops" -v "${BASE}/datos:/datos" \
  "${IMAGEN}" python /ops/evaluar_equipo_congelado.py /datos/exportacion_auto.json /datos/eval_auto.json

echo "[4/5] Sustituyendo equipo.json de forma atomica..."
mv "${BASE}/datos/equipo_nuevo.json" "${BASE}/datos/equipo.json"
chmod 644 "${BASE}/datos/equipo.json"
rm -f "${BASE}/datos/exportacion_auto.json" "${BASE}/datos/eval_auto.json"

echo "[5/5] Verificando inferencia con --simulacro..."
"${BASE}/ejecutar_motor.sh" --simulacro

echo "=== Renovacion automatica NBA completada con exito ==="
