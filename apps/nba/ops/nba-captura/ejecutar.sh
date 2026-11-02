#!/bin/sh
# Lanza un colector una vez. Uso (desde el cron del VPS):  ejecutar.sh rotowire|espn
# Un solo proceso por fuente (flock); sin puertos; solo red `nba-red`; lectura del ledger de run57 en solo lectura.
set -eu
FUENTE="$1"
BASE="$HOME/nba-isolated/nba-captura"
IMAGEN="$(cat "$BASE/imagen_actual")"
exec flock -n "$BASE/$FUENTE.lock" docker run --rm --network nba-red --user "$(id -u):$(id -g)" \
  --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges --memory 256m --pids-limit 64 \
  --env-file "$BASE/captura.env" -e NBA_CAPTURA_DIR=/datos -e NBA_RUN57_DIR=/run57 \
  -v "$BASE/datos:/datos" -v "$HOME/nba-isolated/research-capture/run57-20261008/data/captures:/run57:ro" \
  "$IMAGEN" "$FUENTE"
