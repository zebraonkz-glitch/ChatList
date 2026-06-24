param(
    [switch]$SkipTests,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$version = (& python -c "from version import __version__; print(__version__)").Trim()
if (-not $version) {
    Write-Host "Failed to read __version__ from version.py" -ForegroundColor Red
    exit 1
}

$appName = "ChatList"
$appVersionedName = "${appName}-${version}"

Write-Host "Preparing release $version" -ForegroundColor Cyan

if (-not $SkipTests) {
    Write-Host "Running tests..." -ForegroundColor Cyan
    python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipBuild) {
    Write-Host "Building artifacts..." -ForegroundColor Cyan
    & (Join-Path $PSScriptRoot "..\build.ps1")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$exePath = Join-Path "dist" "$appVersionedName.exe"
$installerPath = Join-Path "dist" "${appVersionedName}-setup.exe"
$checksumsPath = Join-Path "dist" "SHA256SUMS.txt"

foreach ($path in @($exePath, $installerPath)) {
    if (-not (Test-Path $path)) {
        Write-Host "Missing artifact: $path" -ForegroundColor Red
        exit 1
    }
}

$lines = @()
foreach ($path in @($installerPath, $exePath)) {
    $hash = (Get-FileHash $path -Algorithm SHA256).Hash.ToLower()
    $name = Split-Path $path -Leaf
    $lines += "$hash  $name"
}
$lines | Set-Content -Path $checksumsPath -Encoding UTF8

$notesPath = Join-Path "docs" "release-notes" "v$version.md"
Write-Host ""
Write-Host "Release $version is ready." -ForegroundColor Green
Write-Host "Artifacts:" -ForegroundColor Green
Write-Host "  $exePath"
Write-Host "  $installerPath"
Write-Host "  $checksumsPath"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Edit release notes: docs\release-notes\v$version.md"
if (-not (Test-Path $notesPath)) {
    Write-Host "     Copy-Item docs\release-notes\TEMPLATE.md $notesPath"
}
Write-Host "  2. git add version.py docs/release-notes/v$version.md"
Write-Host "  3. git commit -m ""Release $version"""
Write-Host "  4. git tag -a v$version -m ""ChatList $version"""
Write-Host "  5. git push origin main --tags"
Write-Host ""
Write-Host "See docs\PUBLISHING.md for full instructions." -ForegroundColor Cyan
