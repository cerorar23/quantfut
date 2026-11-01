#!/bin/sh
# Exporta (solo lectura) lo que necesita el rediseño de los motores de fútbol y lo parte en CSV comprimidos.
# Uso, desde la raíz del repo en Git Bash:  scripts/rediseno_futbol/exportar.sh [CARPETA]
# Por defecto la carpeta es .local/rediseno_AAAAMMDD (ignorada por git). Los datos no salen del PC del titular.
set -eu
D=${1:-.local/rediseno_$(date +%Y%m%d)}
mkdir -p "$D"
ssh quantfut 'docker exec -i quantfut-db-1 psql -U qf -d quantfut -X -v ON_ERROR_STOP=1' \
  < "$(dirname "$0")/exportar.sql" > "$D/todo.csv"
awk -v d="$D" '/^@@ /{ if (f) close(f); f = d "/" $2 ".csv"; next } f { print > f }' "$D/todo.csv"
rm -f "$D/todo.csv" "$D/fin.csv"
for f in "$D"/*.csv; do gzip -f "$f"; done
date -u +%Y-%m-%dT%H:%M:%SZ > "$D/exportado_en.txt"
ls -l "$D"
