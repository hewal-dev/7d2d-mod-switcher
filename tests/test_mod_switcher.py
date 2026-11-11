"""Headless checks for the mod switcher (offscreen Qt) using a throwaway sandbox.

Never touches the real Steam folder: GAME_DIR/MOD_BASE are redirected through
MODSWITCH_GAME_DIR / MODSWITCH_MOD_BASE before the module is imported.
"""

import importlib
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

# Qt's offscreen backend crashes at exit on Windows (PySide6 6.12), the normal
# plugin works there without a visible desktop, so only force offscreen elsewhere.
if sys.platform != "win32":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["MODSWITCH_NO_ASK"] = "1"  # no blocking popup during tests
os.environ["MODSWITCH_NO_OPEN"] = "1"  # never launch a file manager from the tests
os.environ.setdefault("MODSWITCH_LANG", "de")  # the checks below assert German texts
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import i18n as i18n_mod  # noqa: E402

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
    # never read the real user config: a saved language there would silently
    # change every expected text below
    os.environ["MODSWITCH_CONFIG"] = str(tmp / "config" / "config.json")
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
    mod.remove_symlink()
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

def test_first_run(tmp: Path) -> None:
    """Erststart ohne Mod-Ordner: Checkliste statt Fehlermeldung, Ordner anlegen."""
    print("--- Erststart ---")
    root = tmp / "erststart"
    (root / "game").mkdir(parents=True)
    mod = load(root)
    state = mod.setup_state()
    check("Spielordner vorhanden", state["game"], True)
    check("Mod-Ordner fehlt", state["base"], False)
    check("Noch nicht bereit", state["ready"], False)
    check("Kein Fehlerblocker", mod.check_state(), None)

    window = mod.SwitcherWindow()
    check("Checkliste sichtbar", window.setup_frame.isVisibleTo(window), True)

    window.on_create_folder()
    check("Ordner per Knopf angelegt", mod.MOD_BASE.is_dir(), True)
    check("Meldung nennt angelegten Ordner", "Ordner angelegt" in window.status.text(), True)
    check("Ohne Paket weiter nicht bereit", mod.setup_state()["ready"], False)
    check("Checkliste bleibt sichtbar", window.setup_frame.isVisibleTo(window), True)

    (mod.MOD_BASE / "01 Vanilla").mkdir()
    window.reload()
    check("Bereit nach erstem Paket", mod.setup_state()["ready"], True)
    check("Checkliste verschwindet", window.setup_frame.isVisibleTo(window), False)
    check("Umschalten jetzt moeglich", mod.can_switch(), True)

    mod.apply_paths(root / "kein spiel", mod.MOD_BASE)
    window.reload()
    check("Ohne Spiel kein Umschalten", mod.can_switch(), False)
    check("Checkliste zeigt den Spielordner", window.setup_frame.isVisibleTo(window), True)
    check("Untertitel nennt den Spielordner", "Spielordner fehlt" in window.subtitle.text(), True)
    window.select("01 Vanilla")
    check("Aktivieren bleibt gesperrt", window.apply_button.isEnabled(), False)
    check("Hinweis nennt den Spielordner", "Spielordner" in window.apply_button.toolTip(), True)
    check("Dateimanager im Test abgeschaltet", mod.open_in_file_manager(mod.MOD_BASE), False)

    # Pfad-Dialog: fehlender Mod-Ordner laesst sich direkt anlegen
    dialog = mod.PathsDialog(root / "game", root / "neuer ordner")
    check("Anlegen-Knopf aktiv", dialog.base_create_button.isEnabled(), True)
    check("Speichern noch gesperrt", dialog.save_button.isEnabled(), False)
    dialog.on_create_base()
    check("Ordner aus dem Dialog angelegt", (root / "neuer ordner").is_dir(), True)
    check("Speichern danach erlaubt", dialog.save_button.isEnabled(), True)
    check("Anlegen-Knopf danach aus", dialog.base_create_button.isEnabled(), False)


def test_language(tmp: Path) -> None:
    """English/German switcher, and the remembered choice."""
    print("--- Sprache ---")
    cfg = tmp / "config" / "config.json"
    os.environ["MODSWITCH_CONFIG"] = str(cfg)
    os.environ["MODSWITCH_GAME_DIR"] = str(tmp / "game")
    os.environ["MODSWITCH_MOD_BASE"] = str(tmp / "mods")

    # detect_language: saved choice > env > locale
    sample = load(tmp)
    check("Umgebung wählt Englisch", i18n_mod.detect_language(None, "en"), "en")
    check("Umgebung wählt Deutsch", i18n_mod.detect_language(None, "de_DE.UTF-8"), "de")
    check("Gespeicherte Wahl schlägt Umgebung", i18n_mod.detect_language("en", "de"), "en")
    check("Unbekannte Angabe fällt auf Systemsprache",
          i18n_mod.detect_language("xx", "yy") in i18n_mod.LANGUAGES, True)

    # start in English, switch to German, both are remembered
    os.environ["MODSWITCH_LANG"] = "en"
    mod = load(tmp)
    check("Startsprache Englisch", mod.T.language, "en")
    window = mod.SwitcherWindow()
    check("Knopf englisch", window.apply_button.text(), "Activate")
    check("Sprachknopf aktiv", window.lang_buttons["en"].property("aktiv"), "true")
    window.set_language("de")
    check("Sprache umgeschaltet", mod.T.language, "de")
    check("Knopf deutsch", window.apply_button.text(), "Aktivieren")
    check("Englisch nicht mehr aktiv", window.lang_buttons["en"].property("aktiv"), "false")
    check("Sprache in Konfig gespeichert", mod.read_config().get("language"), "de")
    check("Spielpfad blieb erhalten", mod.read_config().get("game_dir"), str(tmp / "game"))

    # a restart without the env override picks the saved language up again
    os.environ.pop("MODSWITCH_LANG", None)
    again = load(tmp)
    check("Sprache beim Neustart gemerkt", again.T.language, "de")
    check("Texte beim Neustart deutsch", again.SwitcherWindow().apply_button.text(), "Aktivieren")

    # English strings really are English (nothing left in German)
    again.T.language = "en"
    german = re.compile(r"[äöüÄÖÜß]|\bOrdner\b|\baktiv\b|Spiel")
    for key, values in (
        ("header.none", {"count": 3}),
        ("header.active", {"name": "02 Overhaul", "count": 3}),
        ("button.already_active", {}),
        ("paths.found", {}),
        ("badge", {}),
        ("err.real_dir", {}),
    ):
        english = again.T(key, **values)
        again.T.language = "de"
        german_text = again.T(key, **values)
        again.T.language = "en"
        check(f"Englischer Text {key}", bool(german.search(english)), False)
        check(f"Deutsch weicht ab {key}", german_text != english, True)
    check("Englischer Text Beispiel", again.T("header.none", count=3),
          "No mod folder active · 3 available")
    os.environ["MODSWITCH_LANG"] = "de"


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
        check("Symlink gesetzt", mod.active_target(), tmp / "mods" / "02 Overhaul")
        check("Statusmeldung", window.status.text(), "Aktiviert: 02 Overhaul")
        check("Aktiver Eintrag erkannt", mod.active_target().name, "02 Overhaul")
        check("Kein zweiter Klick nötig", window.apply_button.isEnabled(), False)

        if os.environ.get("MODSWITCH_NO_SHOT") != "1":
            # grab() is the one call that crashes Qt's offscreen backend on
            # Windows at exit; MODSWITCH_NO_SHOT=1 skips it for CI runs there.
            window.show()
            app.processEvents()
            out = Path(tempfile.gettempdir()) / "modswitch-fenster.png"
            window.grab().save(str(out))
            print(f"ok  Screenshot {out}")

        # switching again to another set replaces the link instead of adding one
        window.select("02 Overhaul")
        window.apply()
        check("Zweiter Wechsel", mod.active_target().name, "02 Overhaul")
        check("Nur ein Link", mod.is_link(mod.MOD_LINK), True)

        # safety: a real directory named Mods must block everything
        mod.remove_symlink()
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
        mstate = missing.setup_state()
        check("Fehlender Spielordner blockiert nicht", missing.check_state(), None)
        check("Spielordner als fehlend erkannt", mstate["game"], False)
        check("Mod-Ordner als fehlend erkannt", mstate["base"], False)
        check("Nicht bereit ohne Ordner", mstate["ready"], False)
        check("Umschalten gesperrt ohne Ordner", missing.can_switch(), False)

        test_paths(tmp)
        test_symlink(tmp)
        test_first_run(tmp)
        test_language(tmp)
        print("FEHLGESCHLAGEN: " + ", ".join(failures) if failures else "Alle Prüfungen grün")
        # PySide6 crashes while destroying widgets at interpreter shutdown; exit directly
        # so the test result is not masked by a teardown segfault.
        sys.stdout.flush()
        os._exit(1 if failures else 0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
