#!/usr/bin/env bash
# Salud del motor de tenis v2 (VPS, Linux): cadena de hashes, recibos, calendario de PropLine, identidad y artefacto activo.
# Cron (cada hora, minuto 40):
#   40 * * * * /usr/bin/flock -n /tmp/tenis-salud.lock /home/qf/tenis-isolated/verificar_salud.sh >> /home/qf/tenis-isolated/salud.log 2>&1
# Imprime el informe en JSON y sale con 1 si algo no esta bien; los avisos salen por Telegram (como mucho 1 por tipo y dia, con el
# estado guardado en el almacen). Usa la MISMA imagen que el motor (la que fija ejecutar_motor.sh).
set -euo pipefail
S=/home/qf/tenis-isolated
IMAGEN=$(grep -o 'tenis-motor:[A-Za-z0-9._-]*' "$S/ejecutar_motor.sh" | head -n 1)
[[ "$IMAGEN" =~ ^tenis-motor:[A-Za-z0-9._-]+$ ]] || { echo "ERROR: imagen no valida en ejecutar_motor.sh ('$IMAGEN')" >&2; exit 2; }
PASS=$(grep TENIS_DB_PASSWORD "$S/tenis-db/.env" | cut -d= -f2)
export TG_BOT_TOKEN=$(grep '^TG_BOT_TOKEN=' /home/qf/quantfut/.env | cut -d= -f2-)
export TG_ALERT_CHAT=$(grep '^TG_ALERT_CHAT=' /home/qf/quantfut/.env | cut -d= -f2-)
echo "$(date -u +%FT%TZ) salud con $IMAGEN"
docker run --rm --memory 512m --network tenis-db_tenis-interna \
    -e PG_DSN="postgresql://tenis_admin:${PASS}@tenis-db:5432/tenis" \
    -e TG_BOT_TOKEN -e TG_ALERT_CHAT -e TENIS_ESTADO_ALERTAS=/almacen/estado_alertas.json \
    -v "$S/almacen_objetos":/almacen \
    --entrypoint python "$IMAGEN" -m tenis.salud --artefactos /app/apps/tenis/artefactos
