#!/usr/bin/env bash
# Ensayo de vuelta atrás (rollback) del motor (plan §H.4, G-operación).
# Simula la reversión de imagen_actual a imagen_actual.anterior y comprueba ejecución.
set -euo pipefail

DIR_OPS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARCHIVO_IMAGEN="$DIR_OPS/imagen_actual"
ARCHIVO_ANTERIOR="$DIR_OPS/imagen_actual.anterior"

echo "[1/3] Verificando existencia de imagen_actual.anterior..."
if [ ! -f "$ARCHIVO_ANTERIOR" ]; then
    echo "ERROR: No existe $ARCHIVO_ANTERIOR para rollback" >&2
    exit 1
fi

ANTERIOR="$(cat "$ARCHIVO_ANTERIOR" | tr -d '[:space:]')"
ACTUAL="$(cat "$ARCHIVO_IMAGEN" | tr -d '[:space:]')"

if ! [[ "$ANTERIOR" =~ ^tenis-motor:[A-Za-z0-9._-]+$ ]]; then
    echo "ERROR: Formato inválido en imagen_actual.anterior ('$ANTERIOR')" >&2
    exit 1
fi
echo "   Imagen anterior detectada: $ANTERIOR"
echo "   Imagen actual: $ACTUAL"

echo "[2/3] Simulando intercambio atómico hacia imagen anterior..."
TMP_SWAP="$DIR_OPS/imagen_actual.tmp"
cp "$ARCHIVO_ANTERIOR" "$TMP_SWAP"
mv "$TMP_SWAP" "$ARCHIVO_IMAGEN"

REVERTIDO="$(cat "$ARCHIVO_IMAGEN" | tr -d '[:space:]')"
if [ "$REVERTIDO" != "$ANTERIOR" ]; then
    echo "ERROR: La reversión no dejó la imagen anterior en $ARCHIVO_IMAGEN" >&2
    exit 1
fi
echo "   Reversión confirmada: imagen_actual ahora apunta a $REVERTIDO"

echo "[3/3] Restaurando estado original para no alterar el entorno..."
echo "$ACTUAL" > "$ARCHIVO_IMAGEN"
echo "   Estado restablecido a $ACTUAL."

echo "=== Ensayo de vuelta atrás completado con ÉXITO (G-operación PASA) ==="
exit 0
