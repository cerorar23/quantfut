[CmdletBinding()]
param(
    [switch]$Login,
    [string]$ProjectId,
    [ValidateSet('android', 'ios')]
    [string[]]$Platforms = @('android', 'ios')
)

$ErrorActionPreference = 'Stop'
$mobileRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = (Resolve-Path (Join-Path $mobileRoot '..\..')).Path
$firebaseBin = Join-Path $repoRoot '.local\firebase-tools\node_modules\.bin'
$flutterfireCache = Join-Path $repoRoot '.local\flutterfire-pub-cache'
$firebaseCommand = Join-Path $firebaseBin 'firebase.cmd'
$flutterfireCommand = Join-Path $flutterfireCache 'bin\flutterfire.bat'

if (!(Test-Path -LiteralPath $firebaseCommand) -or
    !(Test-Path -LiteralPath $flutterfireCommand)) {
    throw 'Faltan herramientas. Consulta docs/FIREBASE_INSTALACION_20261012.md.'
}
$previousPath = $env:PATH
$previousPubCache = $env:PUB_CACHE
if (!(Get-Command dart -CommandType Application -ErrorAction SilentlyContinue)) {
    if (Test-Path -LiteralPath 'C:\flutter\bin\dart.bat') {
        $env:PATH = 'C:\flutter\bin;' + $env:PATH
    } else {
        throw 'Añade el SDK de Flutter a PATH para ejecutar Dart.'
    }
}

try {
    $env:PATH = "$firebaseBin;$env:PATH"
    $env:PUB_CACHE = $flutterfireCache
    if ($Login) {
        & $firebaseCommand login --interactive
        if ($LASTEXITCODE -ne 0) { throw 'No se completó el acceso a Firebase.' }
        return
    }
    if ([string]::IsNullOrWhiteSpace($ProjectId)) {
        throw 'Indica -ProjectId con el proyecto real, o -Login para iniciar sesión.'
    }
    if ($ProjectId -notmatch '^[a-z][a-z0-9-]{4,28}[a-z0-9]$') {
        throw 'ProjectId debe ser el ID de Firebase, no el nombre visible ni una URL.'
    }
    Push-Location $mobileRoot
    try {
        & $flutterfireCommand configure "--project=$ProjectId" `
            "--platforms=$($Platforms -join ',')" `
            --android-package-name=com.saptain.quantfut `
            --ios-bundle-id=com.saptain.quantfut `
            --out=lib/firebase_options.dart --overwrite-firebase-options --yes
        if ($LASTEXITCODE -ne 0) { throw 'La configuración de FlutterFire no terminó.' }
        if ($Platforms -contains 'ios') {
            # FlutterFire on Windows emits Dart options but not the native plist.
            $configuration = Get-Content 'firebase.json' -Raw | ConvertFrom-Json
            $iosAppId = $configuration.flutter.platforms.dart.'lib/firebase_options.dart'.configurations.ios
            if ([string]::IsNullOrWhiteSpace($iosAppId)) {
                throw 'FlutterFire no devolvió una app iOS configurada.'
            }
            $iosConfigDownload = Join-Path $mobileRoot ("ios/Runner/firebase-{0}.tmp" -f [guid]::NewGuid())
            try {
                & $firebaseCommand apps:sdkconfig IOS $iosAppId "--project=$ProjectId" `
                    "--out=$iosConfigDownload" --non-interactive
                if ($LASTEXITCODE -ne 0) { throw 'No se pudo descargar la configuración iOS.' }
                Move-Item -LiteralPath $iosConfigDownload -Destination 'ios/Runner/Google-Service-Info.plist' -Force
                $nativePlist = [xml](Get-Content 'ios/Runner/Google-Service-Info.plist' -Raw)
                $nativeValues = @{}
                $nativeNodes = @($nativePlist.plist.dict.ChildNodes | Where-Object { $_.NodeType -eq 'Element' })
                for ($index = 0; $index -lt $nativeNodes.Count - 1; $index += 2) {
                    $nativeValues[$nativeNodes[$index].InnerText] = $nativeNodes[$index + 1].InnerText
                }
                # Required by the CocoaPods Crashlytics symbol upload phase.
                $symbolConfiguration = @{
                    file_generated_by = 'QuantFut configure_firebase.ps1'
                    purpose = 'Firebase app identifiers used for Crashlytics symbol uploads'
                    GOOGLE_APP_ID = $nativeValues['GOOGLE_APP_ID']
                    FIREBASE_PROJECT_ID = $nativeValues['PROJECT_ID']
                    GCM_SENDER_ID = $nativeValues['GCM_SENDER_ID']
                } | ConvertTo-Json
                [IO.File]::WriteAllText((Join-Path $mobileRoot 'ios/firebase_app_id_file.json'), $symbolConfiguration, [Text.UTF8Encoding]::new($false))
                if ($nativeValues['CLIENT_ID'] -and $nativeValues['REVERSED_CLIENT_ID']) {
                    $runnerInfoPath = Join-Path $mobileRoot 'ios/Runner/Info.plist'
                    $runnerInfoText = [IO.File]::ReadAllText($runnerInfoPath)
                    $runnerInfoText = [regex]::Replace($runnerInfoText,
                        '(<key>GIDClientID</key>\s*<string>)[^<]*(</string>)',
                        { param($match) $match.Groups[1].Value + $nativeValues['CLIENT_ID'] + $match.Groups[2].Value })
                    $runnerInfoText = [regex]::Replace($runnerInfoText,
                        '<string>com\.googleusercontent\.apps\.[^<]+</string>',
                        { param($match) '<string>' + $nativeValues['REVERSED_CLIENT_ID'] + '</string>' })
                    [IO.File]::WriteAllText($runnerInfoPath, $runnerInfoText, [Text.UTF8Encoding]::new($false))
                }
            } finally {
                if (Test-Path -LiteralPath $iosConfigDownload) {
                    Remove-Item -LiteralPath $iosConfigDownload
                }
            }
        }
    } finally {
        Pop-Location
    }
} finally {
    $env:PATH = $previousPath
    $env:PUB_CACHE = $previousPubCache
}
