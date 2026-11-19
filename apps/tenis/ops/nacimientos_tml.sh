#!/usr/bin/env bash
# Fechas de nacimiento estimadas desde las edades de TML hacia tenis.jugador_asercion (VPS, Linux).
# Cron (lunes 12:00, tras la carga semanal de TML de las 11:30; espera el candado del motor hasta 15 min):
#   0 12 * * 1 /usr/bin/flock -w 900 /tmp/tenis-motor.lock /home/qf/tenis-isolated/nacimientos_tml.sh >> /home/qf/tenis-isolated/nacimientos_tml.log 2>&1
# Idempotente: solo escribe jugadores que aún no tienen fecha de nacimiento. Con --ensayo como primer argumento no escribe.
# Usa la MISMA imagen que el motor (la que fija ejecutar_motor.sh).
set -euo pipefail
S=/home/qf/tenis-isolated
IMAGEN=$(grep -o 'tenis-motor:[A-Za-z0-9._-]*' "$S/ejecutar_motor.sh" | head -n 1)
[[ "$IMAGEN" =~ ^tenis-motor:[A-Za-z0-9._-]+$ ]] || { echo "ERROR: imagen no válida en ejecutar_motor.sh ('$IMAGEN')" >&2; exit 2; }
SEMANA=$(ls -d /home/qf/quantfut-tenis/data/weekly/2??????? | sort | tail -n 1)
[ -d "$SEMANA/tml/originals" ] || { echo "Descarga incompleta en $SEMANA" >&2; exit 1; }
PASS=$(grep TENIS_DB_PASSWORD "$S/tenis-db/.env" | cut -d= -f2)
echo "$(date -u +%FT%TZ) nacimientos desde $SEMANA con $IMAGEN ${1:-}"
docker run --rm --memory 3g --network tenis-db_tenis-interna -v "$SEMANA":/datos:ro -v "$S/almacen_objetos":/almacen \
    -e QF_PG_DSN="postgresql://tenis_admin:${PASS}@tenis-db:5432/tenis" -e OPCION="${1:-}" \
    --entrypoint sh "$IMAGEN" -c 'python -m tenis.carga.nacimientos_tml --snapshot /datos/tml/originals --almacen /almacen --esquema tenis --dsn "$QF_PG_DSN" $OPCION'
