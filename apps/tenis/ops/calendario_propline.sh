#!/usr/bin/env bash
# Calendario de tenis desde el archivo compartido de PropLine hacia tenis.partido/programa (VPS, Linux).
# Cron (minuto 12, tras la captura horaria de PropLine del minuto 7):
#   12 * * * * /usr/bin/flock -n /tmp/tenis-calendario.lock /home/qf/tenis-isolated/calendario_propline.sh >> /home/qf/.local/share/quantfut/tenis_calendario.log 2>&1
# 1) el worker lee el archivo (sin red) y entrega un documento JSON; 2) un contenedor de la imagen del motor lo carga.
# Usa la MISMA imagen que el motor (la que fija ejecutar_motor.sh): una sola fuente de verdad.
set -euo pipefail
S=/home/qf/tenis-isolated
IMAGEN=$(grep -o 'tenis-motor:[A-Za-z0-9._-]*' "$S/ejecutar_motor.sh" | head -n 1)
[[ "$IMAGEN" =~ ^tenis-motor:[A-Za-z0-9._-]+$ ]] || { echo "ERROR: imagen no válida en ejecutar_motor.sh ('$IMAGEN')" >&2; exit 2; }
PASS=$(grep TENIS_DB_PASSWORD "$S/tenis-db/.env" | cut -d= -f2)
echo "$(date -u +%FT%TZ) calendario PropLine con $IMAGEN"
docker exec -i quantfut-worker-1 python - < "$S/exportar_calendario_propline.py" \
  | docker run --rm -i --memory 1g --network tenis-db_tenis-interna -v "$S/almacen_objetos":/almacen \
      -e QF_PG_DSN="postgresql://tenis_admin:${PASS}@tenis-db:5432/tenis" \
      --entrypoint sh "$IMAGEN" -c 'python -m tenis.captura.propline_calendario --stdin --almacen /almacen --esquema tenis --dsn "$QF_PG_DSN"'
