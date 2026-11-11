# 7D2D Mod Switcher

Kleine Linux-Anwendung, die den Mod-Ordner von **7 Days to Die** umschaltet.

Das Spiel lädt seine Mods aus `<Spielordner>/7 Days To Die/Mods`. Die Anwendung legt dort
einen Symlink an, der auf einen von mehreren vorbereiteten Mod-Sätzen zeigt — so lässt sich
zwischen Mod-Paketen wechseln, ohne Dateien hin und her zu kopieren.

## Download

Fertige **AppImage** für x86_64 gibt es unter [Releases](../../releases/latest): herunterladen,
`chmod +x` setzen, doppelklicken. Enthalten sind Python und PySide6 — es muss nichts
installiert werden. Auf Systemen ohne FUSE2 hilft
`./7D2D-Mod-Switcher-x86_64.AppImage --appimage-extract-and-run`.

## Aus dem Quellcode starten

Voraussetzungen: Linux, Python 3.10+ und **PySide6**

```bash
sudo pacman -S pyside6                    # Arch/CachyOS
python3 -m pip install --user PySide6     # andere Distributionen

python3 mod_switcher.py
```

Wahlweise als Starter: `packaging/7d2d-mod-switcher.desktop` nach
`~/.local/share/applications/` kopieren und den Pfad in `Exec=` anpassen.

## Pfade

Beim ersten Start wird der Spielordner automatisch gesucht: alle Steam-Bibliotheken aus
`~/.local/share/Steam/steamapps/libraryfolders.vdf` (auch Flatpak-Steam). Wird nichts
gefunden, lässt er sich über **Pfade…** auswählen. Der eigene Mod-Ordner ist voreingestellt
auf `~/7 Days`.

Beide Pfade werden in `~/.config/7d2d-mod-switcher/config.json` gemerkt:

```json
{ "game_dir": "/pfad/zu/7 Days To Die", "mod_base": "/pfad/zu/eigenen/mods" }
```

Im Mod-Ordner ist **jeder Unterordner ein Mod-Satz** (z. B. `Vanilla`, `Overhaul`). Die
Anwendung zeigt alle Sätze mit der Anzahl enthaltener Mods; der aktive ist grün markiert.

## Sicherheit

Die Anwendung löscht keine Dateien. Sie ersetzt ausschließlich den Symlink `Mods` im
Spielordner.

Ist `Mods` noch ein **echter Ordner**, fragt die Anwendung beim Start:

> **Symlink für Mods anlegen?** Kann jederzeit in der App rückgängig gemacht werden.

Mit „Ja" wird der vorhandene Ordner zuerst nach `Mods-Original-<Datum>` umbenannt (nichts
darin geht verloren) und dann der Symlink auf den ersten Mod-Satz angelegt. Mit „Nein"
bleibt alles, wie es ist; die Frage lässt sich über **Pfade… → Symlink anlegen** jederzeit
nachholen.

Im Dialog **Pfade…** stehen dafür zwei Knöpfe:

- **Symlink anlegen** — sichert einen echten Ordner und legt den Symlink an.
- **Symlink entfernen** — entfernt nur den Symlink; das Spiel startet danach ohne Mods.
  Eine vorhandene Sicherung `Mods-Original-<Datum>` bleibt liegen.

## Bedienung

- Klick irgendwo auf einen Balken wählt den Mod-Satz aus.
- **Aktivieren** schaltet um; ist der Satz schon aktiv, heißt der Knopf „Bereits aktiv".
- **Neu einlesen** liest den Mod-Ordner neu (nach dem Anlegen eines Satzes).
- **Pfade…** ändert Spielordner und Mod-Ordner.

## Umgebungsvariablen (Tests, Sonderfälle)

`MODSWITCH_GAME_DIR`, `MODSWITCH_MOD_BASE`, `MODSWITCH_CONFIG`, `MODSWITCH_UI_KIT`
überschreiben die Einstellungen. `MODSWITCH_AUTO=<name>` aktiviert einen Satz und beendet die
Anwendung sofort, `MODSWITCH_AUTO=__close__` öffnet und schließt sie nur,
`MODSWITCH_NO_ASK=1` unterdrückt die Start-Rückfrage.

## Aufbau

| Pfad | Zweck |
|---|---|
| `mod_switcher.py` | die Anwendung |
| `assets/` | Logo (Fenster/Starter) |
| `ui_kit/` | gemeinsames Aussehen (Farben, Radiobuttons, Häkchen) |
| `tests/` | Prüfläufe gegen einen Wegwerf-Ordner |
| `packaging/appimage/` | Rezept und Baulauf für das AppImage |
| `packaging/7d2d-mod-switcher.desktop` | Starterdatei für lokale Installation |

## Prüfen

```bash
QT_QPA_PLATFORM=offscreen python3 tests/test_mod_switcher.py
```

Die Prüfungen laufen in einem temporären Verzeichnis und fassen den echten Spielordner
nicht an.

## AppImage bauen

```bash
cd packaging/appimage
./build.sh
```

Nötig sind `python-appimage` und `appimagetool` (das Skript legt beides in einer eigenen
venv im Build-Ordner ab).

## Lizenz

MIT — siehe [LICENSE](LICENSE).
