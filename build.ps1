param(
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"

$version = (& python -c "from version import __version__; print(__version__)").Trim()
if (-not $version) {
    Write-Host "Failed to read __version__ from version.py" -ForegroundColor Red
    exit 1
}

$appName = "ChatList"
$appVersionedName = "${appName}-${version}"

pip install -r requirements.txt pyinstaller

if (-not (Test-Path "app.ico")) {
    pip install -r requirements-dev.txt
    python create_icon.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$buildArgs = @(
    "--onefile",
    "--windowed",
    "--name", $appVersionedName,
    "--icon", "app.ico",
    "--add-data", "app.ico;.",
    "--hidden-import", "PyQt6.sip",
    "--collect-submodules", "PyQt6",
    "main.py"
)

pyinstaller @buildArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller build failed" -ForegroundColor Red
    exit $LASTEXITCODE
}

$exePath = Join-Path "dist" "$appVersionedName.exe"
if (-not (Test-Path $exePath)) {
    Write-Host "Build output not found: $exePath" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Build complete: $exePath" -ForegroundColor Green
Write-Host "Version: $version" -ForegroundColor Green

if (-not $SkipInstaller) {
    & "$PSScriptRoot\build_installer.ps1" -SkipBuild
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
