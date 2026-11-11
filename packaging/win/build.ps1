# Baut die Windows-Fassung (7D2D-Mod-Switcher.exe) mit PyInstaller.
#
# Voraussetzung: Windows mit Python 3.10+ und PySide6
#   winget install --id Python.Python.3.12 -e
#   python -m pip install PySide6 pyinstaller
#
# Aufruf (im Repo-Wurzelverzeichnis):  powershell -ExecutionPolicy Bypass -File packaging\win\build.ps1
#
# Ergebnis: dist\7D2D-Mod-Switcher.exe (eine Datei, Python und PySide6 enthalten).
# Hinweis: Die App legt unter Windows eine Junction an (mklink /J) statt eines
# Symlinks, weil Junctions keine Sonderrechte brauchen.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Push-Location $root
try {
    python -m PyInstaller --noconfirm --clean --windowed --onefile `
        --name "7D2D-Mod-Switcher" `
        --add-data "assets;assets" `
        --add-data "ui_kit;ui_kit" `
        mod_switcher.py
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }
    Get-ChildItem "dist\7D2D-Mod-Switcher.exe" | Select-Object Name, Length
} finally {
    Pop-Location
}
