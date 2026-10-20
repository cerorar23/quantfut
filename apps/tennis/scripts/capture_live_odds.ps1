# Twice daily: h2h odds snapshot (owner authorization 2026-10-19: one region, 400 credits/month),
# then automatic intake (API-Tennis fixtures, 2 requests) -> sealed forecasts with the current engine -> evaluation.
$ErrorActionPreference = 'Continue'
$workspace = 'C:\Users\huye\Documents\apuesta proyec'
$env:PYTHONPATH = 'C:\Users\huye\.codex\worktrees\tennis-engine\apuesta proyec\apps\tennis'
Set-Location $workspace
$python = "$workspace\.venv\Scripts\python.exe"
& $python -m tennis_odds_live_v1 --root data\tennis\live_odds_v1 --workspace $workspace *>> data\tennis\live_odds_v1\scheduler.log
& $python -m tennis_intake_v1 --root data\tennis\intake_v1 --credential-file "$workspace\.env.api-tennis.local" *>> data\tennis\intake_v1\scheduler.log
