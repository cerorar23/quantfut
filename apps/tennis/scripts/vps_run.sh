#!/bin/sh
# Cron entry point on the VPS (user qf): intake, or the weekly refresh.
# Data in ~/quantfut-tenis/data (/data), keys in ~/quantfut-tenis/secrets (/secrets, read-only).
# Odds: the shared hourly PropLine archive (volume quantfut_artifacts, subfolder propline_shared), mounted read-only at
# /propline; the engine never requests odds itself (owner decision 2026-10-23, no The Odds API capture or fallback).
set -u
BASE="$HOME/quantfut-tenis"
IMAGE="$(cat "$BASE/IMAGE")"
run() { docker run --rm --name "tenis-$$-$(date +%s)" --user "$(id -u):$(id -g)" -v "$BASE/data:/data" -v "$BASE/secrets:/secrets:ro" \
  --mount type=volume,src=quantfut_artifacts,dst=/propline,volume-subpath=propline_shared,readonly "$IMAGE" "$@"; }
case "${1:-}" in
  twice-daily)
    run python -m tennis_intake_v1 --root /data/intake_v1 --credential-file /secrets/.env.api-tennis.local >> "$BASE/data/intake_v1/scheduler.log" 2>&1 ;;
  weekly)
    run python -m tennis_refresh_v1 run --weekly-root /data/weekly --config /data/motor_config.json >> "$BASE/data/weekly/scheduler.log" 2>&1 ;;
  *) echo "usage: vps_run.sh twice-daily|weekly" >&2; exit 2 ;;
esac
