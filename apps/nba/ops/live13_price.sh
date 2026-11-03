#!/usr/bin/env bash
# Pinnacle price step for the live v1.3 cohorts (cron cada 5 min; ver docs/nba_captura_precio_servidor_propuesta_20261022.md).
# Own flock and own container: the producer (producer.sh) is not touched and never sees the key.
# Every tick is idempotent: it asks the provider only when a seal-phase or close-phase price is due, within the shared budget
# kept in $L/ledger (2 requests per UTC day, 70 credits per UTC month, halt file on any failure). Before 2026-11-01 it asks for nothing.
set -euo pipefail
L=$HOME/nba-isolated/live13
exec 8>"$L/price.lock"
flock -n 8 || exit 0
exec docker run --rm --name nba-live13-price --user 1001:1001 --read-only --tmpfs /tmp:rw,nosuid,noexec,size=32m \
  --cap-drop ALL --security-opt no-new-privileges --pids-limit 64 --memory 256m --network nba-price \
  -v "$L/cohorts":/live13/cohorts:ro -v "$L/price":/live13/price -v "$L/ledger":/live13/ledger \
  -v "$L/private/odds_key":/run/secrets/odds_key:ro \
  "nba-live13-price:${NBA_LIVE13_PRICE_TAG:-20261022}" \
  python -m nba.live_market capture-pending --cohorts /live13/cohorts --market-root /live13/price --ledger /live13/ledger \
  --key-file /run/secrets/odds_key
