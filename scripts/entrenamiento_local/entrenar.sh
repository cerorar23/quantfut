#!/usr/bin/env bash
# Paso 3: entrena el Motor A en local sobre el esquema `entreno`, con la configuración del modelo de producción.
# No toca la base de producción: el candidato queda registrado en la copia local (y activado ahí si pasa la puerta).
#   scripts/entrenamiento_local/entrenar.sh .local/entreno_AAAAMMDD [--incluir liga ...]
set -euo pipefail
cd "$(dirname "$0")/../.."
D=${1:?carpeta de trabajo}; shift
source scripts/entrenamiento_local/entorno.sh
echo "inicio $(date -u +%FT%TZ) commit $(git rev-parse --short HEAD)"
"$PY" -X utf8 -m qf.model.train "$@" > "$D/resultado.json"
echo "fin $(date -u +%FT%TZ)"
