# Mondays: download only changed TennisMyLife files (owner authorization 2026-10-19), rebuild identities, promote if checks pass.
$ErrorActionPreference = 'Continue'
$workspace = 'C:\Users\huye\Documents\apuesta proyec'
$engine = 'C:\Users\huye\.codex\worktrees\tennis-engine\apuesta proyec\apps\tennis'
$env:PYTHONPATH = $engine
Set-Location $workspace
& "$workspace\.venv\Scripts\python.exe" -m tennis_refresh_v1 run --weekly-root data\tennis\weekly --config "$engine\config\motor.json" *>> data\tennis\weekly\scheduler.log
