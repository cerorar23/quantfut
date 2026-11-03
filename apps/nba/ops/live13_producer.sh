#!/usr/bin/env bash
# Productor de cohortes v1.3 (cron cada 10 min; sella cada partido 65-90 min antes de su salto). Un solo proceso a la vez.
# $L/cache (escribible por 1001) guarda los box scores finales y el calendario del día entre pasadas.
# El archivo horario común de PropLine (volumen quantfut_artifacts, subcarpeta propline_shared) se monta de solo lectura:
# líneas de puntos, rebotes y asistencias por jugador.
set -euo pipefail
L=$HOME/nba-isolated/live13
exec 9>"$L/producer.lock"
flock -n 9 || exit 0
exec docker run --rm --name nba-live13-producer --user 1001:1001 --read-only --tmpfs /tmp:rw,nosuid,noexec,size=64m \
  --cap-drop ALL --security-opt no-new-privileges --pids-limit 64 --memory 1g \
  -v "$L/data":/live13/data:ro -v "$L/model":/live13/model:ro -v "$L/cohorts":/live13/cohorts -v "$L/cache":/live13/cache \
  --mount type=volume,src=quantfut_artifacts,dst=/live13/propline,volume-subpath=propline_shared,readonly \
  nba-live13-producer:20261025b
