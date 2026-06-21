pip install -r requirements.txt pyinstaller

$buildArgs = @(
    "--onefile",
    "--windowed",
    "--name", "ChatList",
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
