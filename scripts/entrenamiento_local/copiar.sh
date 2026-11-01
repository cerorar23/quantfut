#!/usr/bin/env bash
# Paso 1 del entrenamiento local (decisión del titular, 26-oct-2026: se entrena en local y se sube).
# Exporta de producción, en solo lectura, el esquema y las tablas que lee `qf.model.train`, y las baja a CARPETA.
#   scripts/entrenamiento_local/copiar.sh .local/entreno_AAAAMMDD
set -euo pipefail
CARPETA=${1:?carpeta de trabajo, p. ej. .local/entreno_20261026}
SSH=${QF_SSH:-quantfut}
mkdir -p "$CARPETA"
TABLAS="leagues teams estadios estadio_altitud matches odds_snapshots lineups lineups_historicas predictions
prediction_batches model_artifacts picks pick_results estadisticas_jugador fotmob_partido fotmob_baja
clima_era5_partido calendario_equipo calibration_runs fotmob_jugador_partido"
T=$(for t in $TABLAS; do printf -- "-t public.%s " "$t"; done)
ssh "$SSH" "set -e; cd ~/quantfut
  docker compose exec -T db pg_dump -U qf -d quantfut --schema-only --no-owner --no-privileges -n public | gzip > /tmp/entreno_schema.sql.gz
  docker compose exec -T db pg_dump -U qf -d quantfut --data-only --no-owner --no-privileges $T | gzip > /tmp/entreno_data.sql.gz
  sha256sum /tmp/entreno_schema.sql.gz /tmp/entreno_data.sql.gz"
scp -q "$SSH":/tmp/entreno_schema.sql.gz "$SSH":/tmp/entreno_data.sql.gz "$CARPETA"/
ssh "$SSH" 'rm -f /tmp/entreno_schema.sql.gz /tmp/entreno_data.sql.gz'
sha256sum "$CARPETA"/entreno_*.sql.gz
