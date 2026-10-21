#!/usr/bin/env bash
# Productor diario de cohortes v1.3 (cron cada 10 min; ver docs/nba_v13_prospectivo_20261021.md). Un solo proceso a la vez.
set -euo pipefail
L=$HOME/nba-isolated/live13
exec 9>"$L/producer.lock"
flock -n 9 || exit 0
exec docker run --rm --name nba-live13-producer --user 1001:1001 --read-only --tmpfs /tmp:rw,nosuid,noexec,size=64m \
  --cap-drop ALL --security-opt no-new-privileges --pids-limit 64 --memory 512m \
  -v "$L/data":/live13/data:ro -v "$L/model":/live13/model:ro -v "$L/cohorts":/live13/cohorts \
  nba-live13-producer:20261021
