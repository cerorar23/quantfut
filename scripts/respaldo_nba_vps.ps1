# Trae al PC los respaldos de nba_datos y los originales capturados (copia FUERA del VPS).
# Uso:  powershell -File scripts/respaldo_nba_vps.ps1 [-Destino D:\respaldos_nba]
param([string]$Destino = "$HOME\Documents\respaldos_nba")
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force "$Destino\respaldos", "$Destino\datos" | Out-Null
# Solo agrega lo nuevo: no borra nada del destino.
scp -q -r "quantfut:nba-isolated/nba-captura/respaldos/*" "$Destino\respaldos\"
scp -q -r "quantfut:nba-isolated/nba-captura/datos/*" "$Destino\datos\"
Get-ChildItem "$Destino\respaldos" | Sort-Object LastWriteTime -Descending | Select-Object -First 3 Name, Length, LastWriteTime
