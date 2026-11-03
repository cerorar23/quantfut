#!/bin/sh
# F4.4: restaura el respaldo MÁS RECIENTE de nba_datos en una base aparte (nba_ensayo), la comprueba, intenta manipularla y la borra.
# No toca nba_datos. Uso (en el VPS): sh ensayo_operativo.sh
cd ~/nba-isolated/nba-captura || exit 1
DUMP="respaldos/$(ls -t respaldos | head -1)"
echo "respaldo: $DUMP ($(du -h "$DUMP" | cut -f1), $(date -u -r "$DUMP" +%FT%TZ))"
docker exec nba-db psql -U nba_admin -d postgres -c "DROP DATABASE IF EXISTS nba_ensayo" >/dev/null
docker exec nba-db psql -U nba_admin -d postgres -c "CREATE DATABASE nba_ensayo" >/dev/null
INICIO=$(date +%s)
docker exec -i nba-db pg_restore -U nba_admin -d nba_ensayo --exit-on-error < "$DUMP" && echo "restauración OK en $(( $(date +%s) - INICIO )) s" || echo "RESTAURACIÓN CON ERRORES"
DSN=$(grep '^NBA_DB_DSN=' ~/nba-isolated/nba-db/migrar.env | cut -d= -f2- | sed 's#/nba_datos$#/nba_ensayo#')
docker run --rm --network nba-red --user "$(id -u):$(id -g)" --read-only --tmpfs /tmp --cap-drop ALL --memory 1g \
  -e NBA_DB_DSN="$DSN" -v "$PWD/ops_motor:/ops:ro" --entrypoint python "$(cat imagen_motor)" /ops/ensayo_operativo.py
echo "código del ensayo: $?"
docker exec nba-db psql -U nba_admin -d postgres -c "DROP DATABASE nba_ensayo" >/dev/null && echo "base de ensayo borrada"
