#!/bin/sh
# Cron entry point on the VPS (user qf): odds snapshot + intake, or the weekly refresh.
# Data in ~/quantfut-tenis/data (/data), keys in ~/quantfut-tenis/secrets (/secrets, read-only).
set -u
BASE="$HOME/quantfut-tenis"
IMAGE="$(cat "$BASE/IMAGE")"
run() { docker run --rm --name "tenis-$1-$$" -v "$BASE/data:/data" -v "$BASE/secrets:/secrets:ro" "$IMAGE" "$@"; }
case "${1:-}" in
  twice-daily)
    run python -m tennis_odds_live_v1 --root /data/live_odds_v1 --workspace /secrets >> "$BASE/data/live_odds_v1/scheduler.log" 2>&1
    run python -m tennis_intake_v1 --root /data/intake_v1 --credential-file /secrets/.env.api-tennis.local >> "$BASE/data/intake_v1/scheduler.log" 2>&1 ;;
  weekly)
    run python -m tennis_refresh_v1 run --weekly-root /data/weekly --config /data/motor_config.json >> "$BASE/data/weekly/scheduler.log" 2>&1 ;;
  *) echo "usage: vps_run.sh twice-daily|weekly" >&2; exit 2 ;;
esac
