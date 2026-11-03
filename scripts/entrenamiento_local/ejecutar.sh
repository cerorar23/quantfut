#!/usr/bin/env bash
# Ejecuta un módulo de qf sobre la copia local con el entorno de producción (mediciones de fases, ajustes...).
#   scripts/entrenamiento_local/ejecutar.sh .local/entreno_AAAAMMDD qf.model.contexto --oos <ruta>
set -euo pipefail
cd "$(dirname "$0")/../.."
D=${1:?carpeta de trabajo}; MODULO=${2:?módulo}; shift 2
source scripts/entrenamiento_local/entorno.sh
"$PY" -X utf8 -m "$MODULO" "$@"
