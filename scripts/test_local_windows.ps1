param([string]$PythonPath = "")

# El .venv conserva las dependencias, pero su python.exe puede apuntar a una
# instalación de Python 3.12 retirada. Este arnés usa otro 3.12 compatible sin
# modificar ni borrar el entorno existente.
$qfRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$qfPackages = Join-Path $qfRoot '.venv\Lib\site-packages'
if (-not (Test-Path -LiteralPath $qfPackages -PathType Container)) {
    throw "No se encontraron dependencias en $qfPackages"
}

if (-not $PythonPath) {
    $qfCandidates = @(
        (Join-Path $qfRoot '.venv\Scripts\python.exe'),
        (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe')
    )
    foreach ($qfCandidate in $qfCandidates) {
        if (-not (Test-Path -LiteralPath $qfCandidate -PathType Leaf)) { continue }
        & $qfCandidate -c 'import sys; raise SystemExit(sys.version_info[:2] != (3, 12))' 2>$null
        if ($LASTEXITCODE -eq 0) { $PythonPath = $qfCandidate; break }
    }
    if (-not $PythonPath) {
        throw 'Se necesita Python 3.12. Pasa su ruta con -PythonPath.'
    }
}

$qfTempRoot = Join-Path $qfRoot '.local\pytest-runs'
New-Item -ItemType Directory -Path $qfTempRoot -Force | Out-Null
$qfTemp = Join-Path $qfTempRoot ('run-' + [guid]::NewGuid().ToString('N'))
if (-not $qfTemp.StartsWith($qfRoot + [IO.Path]::DirectorySeparatorChar,
                             [StringComparison]::OrdinalIgnoreCase) -or
    (Test-Path -LiteralPath $qfTemp)) {
    throw 'Ruta temporal de pruebas no válida'
}

$qfBootstrap = @'
import os
import site
import sys

root, packages, temp = sys.argv[1:]
if sys.version_info[:2] != (3, 12):
    raise SystemExit("Se necesita Python 3.12")
site.addsitedir(packages)
if packages in sys.path:
    sys.path.remove(packages)
sys.path.insert(0, packages)
sys.path.insert(0, os.path.join(root, "src"))
import pytest
raise SystemExit(pytest.main(["-p", "no:cacheprovider", "--basetemp", temp,
                              "tests", "-q", "--tb=short"]))
'@

Push-Location $qfRoot
try {
    # Windows PowerShell 5.1 quita las comillas dobles internas de `-c`; el
    # bootstrap va en un archivo para que corra igual en 5.1 y en 7.
    $qfBootstrapFile = $qfTemp + '-bootstrap.py'
    [IO.File]::WriteAllText($qfBootstrapFile, $qfBootstrap, [Text.UTF8Encoding]::new($false))
    & $PythonPath -u $qfBootstrapFile $qfRoot $qfPackages $qfTemp
    $qfExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $qfExitCode
