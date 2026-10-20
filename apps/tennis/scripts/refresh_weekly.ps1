# Mondays: download only changed TennisMyLife files (owner authorization 2026-10-19), rebuild identities, promote if checks pass.
$ErrorActionPreference = 'Continue'
$workspace = 'C:\Users\huye\Documents\apuesta proyec'
$engine = 'C:\Users\huye\Documents\quantfut-tenis\apps\tennis'
$env:PYTHONPATH = $engine
$env:TENNIS_MOTOR_CONFIG = "$workspace\data\tennis\motor_config.json"
Set-Location $workspace
& "$workspace\.venv\Scripts\python.exe" -m tennis_refresh_v1 run --weekly-root data\tennis\weekly --config $env:TENNIS_MOTOR_CONFIG *>> data\tennis\weekly\scheduler.log
