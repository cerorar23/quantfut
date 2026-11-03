#!/bin/sh
# Respaldo de nba_datos en el VPS (formato custom de pg_dump) cada 6 h (cron: 15 3,9,15,21 * * *); conserva los 24 últimos (≈ 6 días).
# Los sellos son irrepetibles y viven solo en la base: la distancia entre respaldos es lo máximo que se podría perder.
# La copia FUERA del VPS la trae el PC del titular con scripts/respaldo_nba_vps.ps1.
set -eu
DESTINO="$HOME/nba-isolated/nba-captura/respaldos"
mkdir -p "$DESTINO"
ARCHIVO="$DESTINO/nba_datos_$(date -u +%Y%m%dT%H%M%SZ).dump"
docker exec nba-db pg_dump -U nba_admin -d nba_datos -Fc > "$ARCHIVO.tmp"
mv "$ARCHIVO.tmp" "$ARCHIVO"
ls -1t "$DESTINO"/nba_datos_*.dump | tail -n +25 | xargs -r rm -f
echo "$ARCHIVO"
