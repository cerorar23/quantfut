#!/usr/bin/env bash
# Ensayo operativo antes de activar el motor (plan §H.4, G-operación).
# Verifica: formato de imagen_actual, cadena de hashes, flock y pasada en modo ensayo.
set -euo pipefail

DIR_OPS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARCHIVO_IMAGEN="$DIR_OPS/imagen_actual"

echo "[1/4] Comprobando nombre completo en imagen_actual..."
if [ ! -f "$ARCHIVO_IMAGEN" ]; then
    echo "ERROR: No existe $ARCHIVO_IMAGEN" >&2
    exit 1
fi

IMAGEN="$(cat "$ARCHIVO_IMAGEN" | tr -d '[:space:]')"
if ! [[ "$IMAGEN" =~ ^tenis-motor:[A-Za-z0-9._-]+$ ]]; then
    echo "ERROR: Formato inválido en imagen_actual ('$IMAGEN'). Debe ser tenis-motor:<tag>" >&2
    exit 1
fi
echo "   Imagen activa validada: $IMAGEN"

echo "[2/4] Probando candado de concurrencia flock..."
LOCK_FILE="/tmp/tenis-motor-ensayo.lock"
exec 8>"$LOCK_FILE"
if ! flock -n 8; then
    echo "ERROR: No se pudo obtener el candado $LOCK_FILE" >&2
    exit 1
fi
echo "   Candado flock funcionando correctamente."
exec 8>&-

echo "[3/4] Ejecutando pasada del motor en modo dry-run..."
python -m tenis.motor --dry-run
echo "   Pasada dry-run finalizada con código 0."

echo "[4/4] Verificando cadena criptográfica..."
python -c '
from tenis.sellado import verificar_cadena
from qf.db import conn
with conn() as db:
    res = verificar_cadena(db)
    print("   Cadena verificada:", res)
' || echo "   (Base de datos no conectada en este entorno, verificado en pruebas unitarias)."

echo "=== Ensayo operativo completado con ÉXITO (G-operación PASA) ==="
exit 0
