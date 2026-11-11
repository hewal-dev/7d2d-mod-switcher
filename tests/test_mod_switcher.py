"""Headless checks for the mod switcher (offscreen Qt) using a throwaway sandbox.

Never touches the real Steam folder: GAME_DIR/MOD_BASE are redirected through
MODSWITCH_GAME_DIR / MODSWITCH_MOD_BASE before the module is imported.
"""

import importlib
import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["MODSWITCH_NO_ASK"] = "1"  # no blocking popup during tests
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

failures: list[str] = []


def check(name: str, got, want) -> None:
    flag = "ok " if got == want else "FAIL"
    print(f"{flag} {name}: {got!r} (erwartet {want!r})")
    if got != want:
        failures.append(name)


def load(tmp: Path):
    os.environ["MODSWITCH_GAME_DIR"] = str(tmp / "game")
    os.environ["MODSWITCH_MOD_BASE"] = str(tmp / "mods")
    for name in ("mod_switcher",):
        sys.modules.pop(name, None)
    return importlib.import_module("mod_switcher")


def load_from_config_only():
    """Import the module with no path env vars, so the config file decides."""
    for name in ("MODSWITCH_GAME_DIR", "MODSWITCH_MOD_BASE"):
        os.environ.pop(name, None)
    sys.modules.pop("mod_switcher", None)
    return importlib.import_module("mod_switcher")


def build_sandbox(tmp: Path) -> None:
    game = tmp / "game"
    base = tmp / "mods"
    game.mkdir(parents=True)
    for folder, count in (("01 Vanilla", 3), ("02 Overhaul", 2), ("03 Test", 4)):
        target = base / folder
        target.mkdir(parents=True)
        for i in range(count):
            (target / f"Mod{i}").mkdir()



def test_paths(tmp: Path) -> None:
    """Config file, Steam detection and the path dialog."""
    print("--- Pfade und Einstellungen ---")
    cfg = tmp / "config" / "config.json"
    os.environ["MODSWITCH_CONFIG"] = str(cfg)
    os.environ["MODSWITCH_GAME_DIR"] = str(tmp / "game")
    os.environ["MODSWITCH_MOD_BASE"] = str(tmp / "mods")
    mod = load(tmp)
    check("Konfigdatei zunächst leer", mod.read_config(), {})

    other = tmp / "andere mods"
    other.mkdir()
    (other / "Set A").mkdir()
    mod.write_config(tmp / "game", other)
    check("Konfig geschrieben", mod.read_config(), {
        "game_dir": str(tmp / "game"), "mod_base": str(other)})

    # without env overrides the config wins over detection
    fresh = load_from_config_only()
    check("Spielpfad aus Konfig", fresh.GAME_DIR, tmp / "game")
    check("Mod-Pfad aus Konfig", fresh.MOD_BASE, other)

    # environment beats the config file
    os.environ["MODSWITCH_MOD_BASE"] = str(tmp / "mods")
    fresh = load(tmp)
    check("Umgebung schlägt Konfig", fresh.MOD_BASE, tmp / "mods")

    # Steam detection from a fake library with libraryfolders.vdf
    steam_root = tmp / "steam"
    (steam_root / "steamapps").mkdir(parents=True)
    library = tmp / "library2"
    (library / "steamapps" / "common" / "7 Days To Die").mkdir(parents=True)
    (steam_root / "steamapps" / "libraryfolders.vdf").write_text(
        '"libraryfolders"\n{\n\t"0"\n\t{\n\t\t"path"\t\"%s"\n\t}\n}\n' % library
    )
    libs = fresh.steam_libraries([steam_root])
    check("Bibliothek aus VDF gelesen", library in libs, True)
    check("Spielordner erkannt", fresh.detect_game_dir(libs), library / "steamapps" / "common" / "7 Days To Die")
    check("Nichts erfunden ohne Treffer", fresh.detect_game_dir([tmp / "leer"]), None)

    # path dialog: invalid paths block saving, valid ones allow it
    dialog = fresh.PathsDialog(tmp / "gibtsnicht", tmp / "mods")
    check("Ungültig blockiert Speichern", dialog.save_button.isEnabled(), False)
    dialog.game_edit.setText(str(tmp / "game"))
    check("Gültig erlaubt Speichern", dialog.save_button.isEnabled(), True)
    check("Werte übernommen", dialog.values(), (tmp / "game", tmp / "mods"))

    # applying new paths switches the list content
    window = fresh.SwitcherWindow()
    before = sorted(window.radios)
    fresh.apply_paths(tmp / "game", other)
    window.reload()
    check("Liste folgt neuen Pfaden", sorted(window.radios), ["Set A"])
    check("Vorher andere Liste", before != sorted(window.radios), True)


def test_symlink(tmp: Path) -> None:
    """Real Mods folder -> backup + symlink, and the way back."""
    print("--- Symlink anlegen und entfernen ---")
    os.environ["MODSWITCH_CONFIG"] = str(tmp / "config" / "config.json")
    os.environ["MODSWITCH_GAME_DIR"] = str(tmp / "game")
    os.environ["MODSWITCH_MOD_BASE"] = str(tmp / "mods")
    mod = load(tmp)

    real = tmp / "game" / "Mods"
    if real.is_symlink():
        real.unlink()
    real.mkdir(parents=True, exist_ok=True)
    (real / "keep.txt").write_text("nicht löschen")

    check("Zustand ist Verzeichnis", mod.mods_state(), "directory")
    check("Hinweis nennt echtes Verzeichnis", "echtes Verzeichnis" in (mod.check_state() or ""), True)

    target, backup = mod.install_symlink()
    check("Symlink zeigt auf ersten Satz", target, tmp / "mods" / "01 Vanilla")
    check("Mods ist jetzt Symlink", mod.mods_state(), "symlink")
    check("Sicherung angelegt", backup is not None and backup.is_dir(), True)
    check("Inhalt der Sicherung erhalten", (backup / "keep.txt").read_text(), "nicht löschen")
    check("Kein Fehler mehr", mod.check_state(), None)

    check("Entfernen klappt", mod.remove_symlink(), True)
    check("Mods fehlt jetzt", mod.mods_state(), "missing")
    check("Sicherung bleibt liegen", backup.is_dir(), True)
    check("Zweites Entfernen ohne Wirkung", mod.remove_symlink(), False)

    real.mkdir()
    refused = False
    try:
        mod.activate("01 Vanilla")
    except IsADirectoryError:
        refused = True
    check("activate verweigert echtes Verzeichnis", refused, True)
    check("Verzeichnis blieb erhalten", real.is_dir(), True)

    dialog = mod.PathsDialog(tmp / "game", tmp / "mods")
    check("Anlegen moeglich ohne Symlink", dialog.create_link_button.isEnabled(), True)
    check("Entfernen gesperrt ohne Symlink", dialog.remove_link_button.isEnabled(), False)

    mod.install_symlink()
    dialog2 = mod.PathsDialog(tmp / "game", tmp / "mods")
    check("Anlegen gesperrt bei Symlink", dialog2.create_link_button.isEnabled(), False)
    check("Entfernen moeglich bei Symlink", dialog2.remove_link_button.isEnabled(), True)

def main() -> int:
    app = QApplication.instance() or QApplication(["test"])
    tmp = Path(tempfile.mkdtemp(prefix="modswitch-"))
    try:
        build_sandbox(tmp)
        mod = load(tmp)

        check("Startzustand ohne Link", mod.check_state(), None)
        check("Erkannte Mod-Ordner", [p.name for p in mod.mod_sets()],
              ["01 Vanilla", "02 Overhaul", "03 Test"])
        check("Nichts aktiv", mod.active_target(), None)

        window = mod.SwitcherWindow()
        window.resize(600, 470)
        app.processEvents()
        check("Aktivieren gesperrt ohne Auswahl", window.apply_button.isEnabled(), False)
        check("Untertitel", "3 verfügbar" in window.subtitle.text(), True)

        # a click anywhere on the bar must select the row, not only the label
        window.rows["02 Overhaul"].clicked.emit()
        check("Klick auf die Zeile wählt aus", window.selected(), "02 Overhaul")
        QTest.mouseClick(window.rows["02 Overhaul"], Qt.LeftButton)
        check("Echter Mausklick auf die Zeile", window.selected(), "02 Overhaul")
        window.select("02 Overhaul")
        check("Auswahl aktiviert Knopf", window.apply_button.isEnabled(), True)
        window.apply()
        check("Symlink gesetzt", os.path.realpath(mod.MOD_LINK),
              str(tmp / "mods" / "02 Overhaul"))
        check("Statusmeldung", window.status.text(), "Aktiviert: 02 Overhaul")
        check("Aktiver Eintrag erkannt", mod.active_target().name, "02 Overhaul")
        check("Kein zweiter Klick nötig", window.apply_button.isEnabled(), False)

        window.show()
        app.processEvents()
        out = Path("/tmp/modswitch-fenster.png")
        window.grab().save(str(out))
        print(f"ok  Screenshot {out}")

        # switching again to another set replaces the link instead of adding one
        window.select("02 Overhaul")
        window.apply()
        check("Zweiter Wechsel", mod.active_target().name, "02 Overhaul")
        check("Nur ein Link", mod.MOD_LINK.is_symlink(), True)

        # safety: a real directory named Mods must block everything
        (tmp / "game" / "Mods").unlink()
        (tmp / "game" / "Mods").mkdir()
        real = Path(tmp / "game" / "Mods" / "keep.txt")
        real.write_text("nicht löschen")
        guard = mod.SwitcherWindow()
        app.processEvents()
        check("Echtes Verzeichnis erkannt", "echtes Verzeichnis" in (guard.error or ""), True)
        check("Banner sichtbar", guard.banner.isVisibleTo(guard), True)
        check("Aktivieren bleibt gesperrt", guard.apply_button.isEnabled(), False)
        check("Nichts gelöscht", real.exists(), True)

        missing = load(tmp / "nichtda")
        check("Fehlender Spielordner", "Spielordner nicht gefunden" in (missing.check_state() or ""), True)

        test_paths(tmp)
        test_symlink(tmp)
        print("FEHLGESCHLAGEN: " + ", ".join(failures) if failures else "Alle Prüfungen grün")
        # PySide6 crashes while destroying widgets at interpreter shutdown; exit directly
        # so the test result is not masked by a teardown segfault.
        sys.stdout.flush()
        os._exit(1 if failures else 0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
