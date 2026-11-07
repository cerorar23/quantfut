#!/usr/bin/env bash
# Ensayo de restauración (plan §H.4): restaura un volcado en una base temporal y compara recuentos por tabla.
# Uso: restaurar_ensayo.sh <fichero.dump> [--contra-vivo]
#   Sin --contra-vivo: solo imprime los recuentos de la copia restaurada.
#   Con --contra-vivo: compara esos recuentos con los de la base viva `tenis` y sale con error si difieren.
# La base temporal se crea y se borra dentro del propio contenedor; nunca se toca `tenis`.
# Escrito en S1; NO probado contra Docker real (ver apps/tenis/db/LEEME.md).
set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "uso: $0 <fichero.dump> [--contra-vivo]" >&2
    exit 2
fi
DUMP="$1"
CONTRA_VIVO="${2:-}"
CONTENEDOR="${TENIS_CONTENEDOR:-tenis-db}"
BASE_ENSAYO="tenis_ensayo_$(date -u +%Y%m%d%H%M%S)_$$"

if [ ! -s "$DUMP" ]; then
    echo "volcado ausente o vacio: $DUMP" >&2
    exit 2
fi

# Recuentos por tabla del esquema tenis, en una sola consulta (query_to_xml evita un SQL dinámico).
consulta_recuentos="SELECT table_name, (xpath('/row/c/text()', query_to_xml(format('SELECT count(*) AS c FROM tenis.%I', table_name), false, true, '')))[1]::text AS filas FROM information_schema.tables WHERE table_schema = 'tenis' AND table_type = 'BASE TABLE' ORDER BY table_name"

recuentos() {
    docker exec "$CONTENEDOR" psql -X -U tenis_admin -d "$1" -At -F $'\t' -c "$consulta_recuentos"
}

limpiar() {
    docker exec "$CONTENEDOR" psql -X -U tenis_admin -d tenis -c "DROP DATABASE IF EXISTS $BASE_ENSAYO WITH (FORCE)" > /dev/null || true
}
trap limpiar EXIT

docker exec "$CONTENEDOR" psql -X -U tenis_admin -d tenis -c "CREATE DATABASE $BASE_ENSAYO" > /dev/null
# pg_restore lee el volcado por la entrada estándar del contenedor.
docker exec -i "$CONTENEDOR" pg_restore -U tenis_admin -d "$BASE_ENSAYO" --no-owner --exit-on-error < "$DUMP"

copia="$(recuentos "$BASE_ENSAYO")"
echo "recuentos de la copia restaurada:"
echo "$copia"

if [ "$CONTRA_VIVO" = "--contra-vivo" ]; then
    viva="$(recuentos tenis)"
    if [ "$copia" != "$viva" ]; then
        echo "DIFERENCIA de recuentos entre la copia y la base viva" >&2
        diff <(echo "$viva") <(echo "$copia") >&2 || true
        exit 1
    fi
    echo "recuentos iguales a la base viva"
fi
