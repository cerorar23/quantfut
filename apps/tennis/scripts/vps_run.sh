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
  hourly)
    # Cron at minute 25 of every hour (server clock is Europe/Berlin; minutes do not move with daylight saving).
    # API-Tennis fixtures (2 requests) only in the 00 and 12 UTC runs; the other runs seal from the archived fixtures
    # so each match is sealed 1.5-2.5 h before its start with the freshest hourly PropLine observation.
    case "$(date -u +%H)" in 00|12) capture="" ;; *) capture="--no-capture" ;; esac
    exec 9>"$BASE/data/intake_v1/hourly.lock"; flock -n 9 || exit 0
    run python -m tennis_intake_v1 --root /data/intake_v1 --credential-file /secrets/.env.api-tennis.local $capture >> "$BASE/data/intake_v1/scheduler.log" 2>&1 ;;
  twice-daily)
    run python -m tennis_intake_v1 --root /data/intake_v1 --credential-file /secrets/.env.api-tennis.local >> "$BASE/data/intake_v1/scheduler.log" 2>&1 ;;
  weekly)
    run python -m tennis_refresh_v1 run --weekly-root /data/weekly --config /data/motor_config.json >> "$BASE/data/weekly/scheduler.log" 2>&1 ;;
  *) echo "usage: vps_run.sh hourly|twice-daily|weekly" >&2; exit 2 ;;
esac
