#!/usr/bin/env bash
# Respaldo de tenis-db (plan §H.4): pg_dump comprimido y copia del árbol de originales.
# Pensado para correr cada 6 h. Conserva los 24 respaldos más recientes (≈ 6 días).
# Escrito en S1; NO probado contra Docker real (ver apps/tenis/db/LEEME.md).
#
# Variables (opcionales): TENIS_CONTENEDOR (tenis-db), TENIS_RESPALDOS (/var/backups/tenis-db),
#                         TENIS_OBJETOS (árbol de originales; si no existe, se omite esa parte).
set -euo pipefail

CONTENEDOR="${TENIS_CONTENEDOR:-tenis-db}"
DESTINO="${TENIS_RESPALDOS:-/var/backups/tenis-db}"
OBJETOS="${TENIS_OBJETOS:-}"
CONSERVAR=24

mkdir -p "$DESTINO"
marca="$(date -u +%Y%m%dT%H%M%SZ)"
parcial="$DESTINO/.tenis-$marca.dump.part"
final="$DESTINO/tenis-$marca.dump"

# Volcado en formato custom (comprimido). Se escribe a un fichero parcial y solo se renombra si está completo.
docker exec "$CONTENEDOR" pg_dump -U tenis_admin -d tenis -Fc -Z 9 > "$parcial"
# Comprobación: el índice del volcado debe poder leerse (pg_restore --list no escribe nada).
docker exec -i "$CONTENEDOR" pg_restore --list < "$parcial" > /dev/null
mv "$parcial" "$final"

if [ -n "$OBJETOS" ] && [ -d "$OBJETOS" ]; then
    tar -C "$OBJETOS" -czf "$DESTINO/objetos-$marca.tar.gz" .
fi

# Rotación: se conservan los CONSERVAR volcados más recientes (y sus copias de objetos).
mapfile -t viejos < <(ls -1t "$DESTINO"/tenis-*.dump 2>/dev/null | tail -n +"$((CONSERVAR + 1))")
for f in "${viejos[@]}"; do
    rm -f -- "$f"
done
mapfile -t viejos_obj < <(ls -1t "$DESTINO"/objetos-*.tar.gz 2>/dev/null | tail -n +"$((CONSERVAR + 1))")
for f in "${viejos_obj[@]}"; do
    rm -f -- "$f"
done

echo "respaldo correcto: $final"
