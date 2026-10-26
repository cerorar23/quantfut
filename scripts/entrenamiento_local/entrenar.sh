#!/usr/bin/env bash
# Paso 3: entrena el Motor A en local sobre el esquema `entreno`, con la configuración del modelo de producción.
# No toca la base de producción: el candidato queda registrado en la copia local (y activado ahí si pasa la puerta).
#   scripts/entrenamiento_local/entrenar.sh .local/entreno_AAAAMMDD [--incluir liga ...]
set -euo pipefail
cd "$(dirname "$0")/../.."
D=${1:?carpeta de trabajo}; shift
BASE=$(grep "^PG_DSN=" .env | cut -d= -f2-)
export PG_DSN="${BASE}?options=-csearch_path%3Dentreno%2Cpublic"
export ARTIFACT_DIR="$D/artifacts"
# Mismos valores que el worker de producción (`printenv` en quantfut-worker-1, 26-oct-2026). El .env local tenía
# DECAY_HALFLIFE_DAYS=180: sin fijarlos aquí se entrenaría otro modelo.
export DECAY_HALFLIFE_DAYS=270 XG_BLEND=0.65 DEVIG_METHOD=shin SHARP_BOOK=pinnacle META_BLEND_ENABLED=0 RESULTS_PROVIDER=propline
export TG_BOT_TOKEN= TG_ALERT_CHAT= SENTRY_DSN=
export PYTHONPATH=src PYTHONUNBUFFERED=1
PY=${PYTHON:-"/c/Users/huye/Documents/apuesta proyec/.venv/Scripts/python.exe"}
mkdir -p "$ARTIFACT_DIR"
echo "inicio $(date -u +%FT%TZ) commit $(git rev-parse --short HEAD)"
"$PY" -X utf8 -m qf.model.train "$@" > "$D/resultado.json"
echo "fin $(date -u +%FT%TZ)"
