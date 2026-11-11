#!/bin/bash
# Baut das AppImage für den 7D2D Mod Switcher.
#
# Zwei Schritte: python-appimage erzeugt den AppDir (Python + PySide6 + Programm),
# dessen interne Paketierung am Leerzeichen im Anwendungsnamen scheitert — deshalb
# wird appimagetool danach direkt aufgerufen.
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
APP=$(cd "$HERE/../.." && pwd)
WORK="$HERE/work"
OUT="$HERE/7D2D-Mod-Switcher-x86_64.AppImage"

mkdir -p "$WORK"
cd "$WORK"

if [ ! -x "$WORK/.venv/bin/python-appimage" ]; then
    python3 -m venv "$WORK/.venv"
    "$WORK/.venv/bin/pip" install -U pip python-appimage
fi

# 1) AppDir bauen (ohne Paketierung); der App-Ordner wird als Extra-Daten mitgenommen
"$WORK/.venv/bin/python-appimage" build app "$HERE" -x "$APP" --no-packaging

# 2) AppImage packen — appimagetool legt python-appimage beim ersten Lauf in den Cache
TOOL=$(ls -d "$HOME"/.cache/python-appimage/bin/.appimagetool-*/AppRun 2>/dev/null | head -1)
if [ -z "${TOOL:-}" ]; then
    echo "appimagetool fehlt: einmal 'python-appimage build app ...' ohne --no-packaging laufen lassen" >&2
    exit 1
fi

"$TOOL" "7D2D Mod Switcher-x86_64" "$OUT"
chmod +x "$OUT"
ls -lh "$OUT"
