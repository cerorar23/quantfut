#!/bin/sh
# Respaldo diario de nba_datos en el VPS (formato custom de pg_dump), conserva los 7 últimos.
# La copia FUERA del VPS la trae el PC del titular con scripts/respaldo_nba_vps.ps1.
set -eu
DESTINO="$HOME/nba-isolated/nba-captura/respaldos"
mkdir -p "$DESTINO"
ARCHIVO="$DESTINO/nba_datos_$(date -u +%Y%m%dT%H%M%SZ).dump"
docker exec nba-db pg_dump -U nba_admin -d nba_datos -Fc > "$ARCHIVO.tmp"
mv "$ARCHIVO.tmp" "$ARCHIVO"
ls -1t "$DESTINO"/nba_datos_*.dump | tail -n +8 | xargs -r rm -f
echo "$ARCHIVO"
