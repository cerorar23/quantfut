# Twice-daily h2h snapshot (owner authorization 2026-10-19: one region, 400 credits/month).
$ErrorActionPreference = 'Stop'
$workspace = 'C:\Users\huye\Documents\apuesta proyec'
$env:PYTHONPATH = 'C:\Users\huye\.codex\worktrees\tennis-engine\apuesta proyec\apps\tennis'
Set-Location $workspace
& "$workspace\.venv\Scripts\python.exe" -m tennis_odds_live_v1 --root data\tennis\live_odds_v1 --workspace $workspace *>> data\tennis\live_odds_v1\scheduler.log
