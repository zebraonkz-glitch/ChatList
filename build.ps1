pip install -r requirements.txt pyinstaller

if (-not (Test-Path "app.ico")) {
    pip install -r requirements-dev.txt
    python create_icon.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$buildArgs = @(
    "--onefile",
    "--windowed",
    "--name", "ChatList",
    "--icon", "app.ico",
    "--add-data", "app.ico;.",
    "--hidden-import", "PyQt6.sip",
    "--collect-submodules", "PyQt6",
    "main.py"
)

pyinstaller @buildArgs

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Сборка завершена: dist\ChatList.exe" -ForegroundColor Green
} else {
    Write-Host "Ошибка сборки PyInstaller" -ForegroundColor Red
    exit $LASTEXITCODE
}
