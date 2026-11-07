#!/usr/bin/env bash
# Envoltorio de colectores de tenis (VPS, Linux). Uso: colector.sh <fuente> <comando...>
#
# - Candado: flock -n sobre $TENIS_LOCK_DIR/tenis-<fuente>.lock (por defecto /var/lock). Si está tomado,
#   sale con código 0 y un mensaje: otra pasada de la misma fuente sigue en marcha.
# - Log: $TENIS_LOG_DIR/<fuente>.log (por defecto /var/log/tenis). Registra inicio, fin y código de salida.
#   No registra los argumentos del comando ni el entorno: las claves nunca llegan al log.
# - Código de salida: el del comando, salvo ocupado (0) y uso incorrecto (2).
set -u

if [ "$#" -lt 2 ]; then
    echo "uso: colector.sh <fuente> <comando...>" >&2
    exit 2
fi
fuente="$1"
shift
if ! [[ "$fuente" =~ ^[a-z][a-z0-9_]*$ ]]; then
    echo "fuente no válida" >&2
    exit 2
fi

lock_dir="${TENIS_LOCK_DIR:-/var/lock}"
log_dir="${TENIS_LOG_DIR:-/var/log/tenis}"
log="$log_dir/$fuente.log"
mkdir -p "$log_dir" 2>/dev/null
registrar() {
    printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >> "$log" 2>/dev/null
}

if ! exec 9>"$lock_dir/tenis-$fuente.lock"; then
    echo "no se puede abrir el candado de $fuente" >&2
    exit 2
fi
if ! flock -n 9; then
    echo "colector $fuente ocupado: se omite esta pasada"
    registrar "fuente=$fuente ocupado"
    exit 0
fi

registrar "fuente=$fuente inicio"
"$@"
codigo=$?
registrar "fuente=$fuente fin codigo=$codigo"
exit "$codigo"
