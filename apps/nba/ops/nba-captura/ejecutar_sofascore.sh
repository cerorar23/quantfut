#!/bin/sh
# Carga a nba_datos los box scores de jugador que el scraper de SofaScore del VPS dejó en su árbol data/v3 (torneo 132, últimos 4 días).
# Respaldo de cdn.nba.com: la caja oficial gana donde existe. Solo lee el árbol (montaje de solo lectura) y solo añade filas.
# Uso (cron del VPS, después del sync del scraper):  ejecutar_sofascore.sh
set -eu
BASE="$HOME/nba-isolated/nba-captura"
IMAGEN="${IMAGEN:-$(cat "$BASE/imagen_actual")}"
exec flock -n "$BASE/sofascore.lock" docker run --rm --network nba-red --user "$(id -u):$(id -g)" \
  --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges --memory 512m --pids-limit 64 \
  --env-file "$BASE/captura.env" -e NBA_CAPTURA_DIR=/datos -e NBA_SOFASCORE_DIR=/sofascore \
  -v "$BASE/datos:/datos" -v "$HOME/sofascore-scraper/data/v3:/sofascore:ro" \
  "$IMAGEN" sofascore
