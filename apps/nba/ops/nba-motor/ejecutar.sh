#!/bin/sh
# Lanza el motor una vez (sella los partidos que entran en su hora previa). Cron sugerido, cada 5 minutos:
#   */5 * * * * $HOME/nba-isolated/nba-captura/ejecutar_motor.sh >> $HOME/.local/share/quantfut/nba_motor.log 2>&1
# Un solo proceso (flock); sin puertos; solo red `nba-red`; usuario de base `nba_motor` (lee todo, solo inserta). Para ver sin sellar:
#   ejecutar_motor.sh --simulacro [--ahora 2026-11-03T02:30:00+00:00]
set -eu
BASE="$HOME/nba-isolated/nba-captura"
IMAGEN="$(cat "$BASE/imagen_motor")"
exec flock -n "$BASE/motor.lock" docker run --rm --network nba-red --user "$(id -u):$(id -g)" \
  --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges --memory 1g --pids-limit 64 \
  --env-file "$BASE/motor.env" "$IMAGEN" python -m nba.v2.motor "$@"
