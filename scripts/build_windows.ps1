$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path ".venv")) {
    py -3 -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
& .\.venv\Scripts\python.exe -m pytest
& .\.venv\Scripts\pyinstaller.exe `
    --noconfirm `
    --clean `
    --windowed `
    --onedir `
    --name Purrse `
    --add-data "src\purrse\qml;purrse\qml" `
    --add-data "src\purrse\assets;purrse\assets" `
    --collect-all PySide6 `
    --collect-all matplotlib `
    --collect-all reportlab `
    launcher.py

Write-Host "Purrse application built at dist\Purrse\Purrse.exe"
Write-Host "Open installer\Purrse.iss in Inno Setup to create the installer."
