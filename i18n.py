"""Übersetzungen / translations for the 7D2D Mod Switcher.

English is the default language; the app remembers the user's choice in its
config file. Every user-visible string lives here.
"""

from __future__ import annotations

import os

LANGUAGES = ("en", "de")
LANGUAGE_NAMES = {"en": "English", "de": "Deutsch"}

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "badge": "ACTIVE",
        "count": "{count} mods",
        "header.active": "Active: {name} · {count} mod folders",
        "header.none": "No mod folder active · {count} available",
        "path.base": "Mod folder: {path}",
        "path.tooltip": "Game: {game}\nMod sets: {base}",
        "button.reload": "Reload",
        "button.paths": "Paths…",
        "button.close": "Close",
        "button.activate": "Activate",
        "button.already_active": "Already active",
        "tip.reload": "Read the mod folder again.",
        "tip.paths": "Choose the game folder and your own mod folder.",
        "tip.activate": "Make this mod folder the active one.",
        "tip.already_active": "This mod folder is already active.",
        "lang.tip": "Switch the language.",
        "status.activated": "Activated: {name}",
        "status.paths_saved": "Paths saved.",
        "status.not_switched": "Not switched.",
        "status.unchanged": "Unchanged — the Mods folder stays as it is.",
        "status.link_created": "Symlink created to “{name}”.",
        "status.backup": " Original saved as “{name}”.",
        "err.game_missing": "Game folder not found:\n{path}\n\nPick the “7 Days To Die” folder via “Paths…”.",
        "err.base_missing": "Mod folder not found:\n{path}\n\nPick the folder with your mod sets via “Paths…”.",
        "err.real_dir": "The Mods folder in the game is a real directory.\nUse “Create symlink” (or the question at startup) to back it up and switch; nothing is deleted by hand.",
        "err.no_sets": "No mod folders found under:\n{path}",
        "err.is_directory": "The Mods folder is a real directory. “Create symlink” backs it up and replaces it with a symlink.",
        "err.target_missing": "Target folder does not exist: {path}",
        "ask.create.title": "Create a symlink for Mods?",
        "ask.create.text": "Create a symlink for Mods?\nYou can undo this in the app at any time.",
        "ask.create.info": "The existing folder is kept and renamed to “Mods-Original-<date>” first.",
        "ask.remove.title": "Remove the symlink?",
        "ask.remove.text": "Remove the symlink for Mods?\nThe game will start without mods. You can recreate it at any time.",
        "ask.yes": "Yes",
        "ask.no": "No",
        "paths.title": "Paths",
        "paths.game": "Game folder",
        "paths.game_hint": "The “7 Days To Die” folder from your Steam installation.",
        "paths.base": "Your mod folder",
        "paths.base_hint": "Every subfolder of this folder counts as one mod set.",
        "paths.link_row": "“Mods” folder in the game:",
        "paths.create": "Create symlink",
        "paths.remove": "Remove symlink",
        "paths.create_tip": "Replaces the Mods folder with a symlink to the chosen mod set. An existing folder is renamed as a backup first.",
        "paths.remove_tip": "Removes only the symlink; the game then starts without mods. A saved original folder stays where it is.",
        "paths.browse": "Browse…",
        "paths.cancel": "Cancel",
        "paths.save": "Save",
        "paths.found": "Both folders found.",
        "paths.missing_game": "Game folder does not exist.",
        "paths.missing_base": "Mod folder does not exist.",
        "paths.warn_real_dir": "“Mods” is a real directory — “Create symlink” backs it up and switches.",
        "paths.msg.created": "Symlink created to “{name}”.",
        "paths.msg.created_backup": "Symlink created to “{name}”. Original saved as “{backup}”.",
        "paths.msg.removed": "Symlink removed.",
        "paths.msg.no_link": "There was no symlink.",
        "dialog.choose_folder": "Select folder",
    },
    "de": {
        "badge": "AKTIV",
        "count": "{count} Mods",
        "header.active": "Aktiv: {name} · {count} Mod-Ordner",
        "header.none": "Kein Mod-Ordner aktiv · {count} verfügbar",
        "path.base": "Mod-Ordner: {path}",
        "path.tooltip": "Spiel: {game}\nMod-Sätze: {base}",
        "button.reload": "Neu einlesen",
        "button.paths": "Pfade…",
        "button.close": "Schließen",
        "button.activate": "Aktivieren",
        "button.already_active": "Bereits aktiv",
        "tip.reload": "Den Mod-Ordner neu einlesen.",
        "tip.paths": "Spielordner und eigenen Mod-Ordner einstellen.",
        "tip.activate": "Diesen Mod-Ordner für das Spiel aktivieren.",
        "tip.already_active": "Der ausgewählte Mod-Ordner ist bereits aktiv.",
        "lang.tip": "Sprache umschalten.",
        "status.activated": "Aktiviert: {name}",
        "status.paths_saved": "Pfade gespeichert.",
        "status.not_switched": "Nicht umgestellt.",
        "status.unchanged": "Unverändert — der Ordner Mods bleibt, wie er ist.",
        "status.link_created": "Symlink auf „{name}“ angelegt.",
        "status.backup": " Original gesichert als „{name}“.",
        "err.game_missing": "Spielordner nicht gefunden:\n{path}\n\nÜber „Pfade…“ den Ordner „7 Days To Die“ auswählen.",
        "err.base_missing": "Mod-Ordner nicht gefunden:\n{path}\n\nÜber „Pfade…“ den Ordner mit den eigenen Mod-Sätzen auswählen.",
        "err.real_dir": "Der Ordner Mods im Spiel ist ein echtes Verzeichnis.\nÜber „Symlink anlegen“ (oder beim Start) wird er gesichert und umgestellt; von Hand wird dabei nichts gelöscht.",
        "err.no_sets": "Keine Mod-Ordner gefunden unter:\n{path}",
        "err.is_directory": "Der Ordner Mods ist ein echtes Verzeichnis. Über „Symlink anlegen“ wird er gesichert und durch einen Symlink ersetzt.",
        "err.target_missing": "Zielordner existiert nicht: {path}",
        "ask.create.title": "Symlink für Mods anlegen?",
        "ask.create.text": "Symlink für Mods anlegen?\nKann jederzeit in der App rückgängig gemacht werden.",
        "ask.create.info": "Der vorhandene Ordner bleibt erhalten und wird vorher als „Mods-Original-<Datum>“ gesichert.",
        "ask.remove.title": "Symlink entfernen?",
        "ask.remove.text": "Symlink für Mods entfernen?\nDas Spiel startet danach ohne Mods. Kann jederzeit wieder angelegt werden.",
        "ask.yes": "Ja",
        "ask.no": "Nein",
        "paths.title": "Pfade einstellen",
        "paths.game": "Spielordner",
        "paths.game_hint": "Der Ordner „7 Days To Die“ aus der Steam-Installation.",
        "paths.base": "Eigener Mod-Ordner",
        "paths.base_hint": "Jeder Unterordner dieses Ordners gilt als eigener Mod-Satz.",
        "paths.link_row": "Ordner „Mods“ im Spiel:",
        "paths.create": "Symlink anlegen",
        "paths.remove": "Symlink entfernen",
        "paths.create_tip": "Ersetzt den Ordner Mods durch einen Symlink auf den gewählten Mod-Satz. Ein vorhandener Ordner wird vorher als Sicherung umbenannt.",
        "paths.remove_tip": "Entfernt nur den Symlink; das Spiel startet danach ohne Mods. Ein gesicherter Original-Ordner bleibt liegen.",
        "paths.browse": "Durchsuchen…",
        "paths.cancel": "Abbrechen",
        "paths.save": "Speichern",
        "paths.found": "Beide Ordner gefunden.",
        "paths.missing_game": "Spielordner existiert nicht.",
        "paths.missing_base": "Mod-Ordner existiert nicht.",
        "paths.warn_real_dir": "„Mods“ ist ein echtes Verzeichnis — über „Symlink anlegen“ wird es gesichert und umgestellt.",
        "paths.msg.created": "Symlink auf „{name}“ angelegt.",
        "paths.msg.created_backup": "Symlink auf „{name}“ angelegt. Original gesichert als „{backup}“.",
        "paths.msg.removed": "Symlink entfernt.",
        "paths.msg.no_link": "Es war kein Symlink vorhanden.",
        "dialog.choose_folder": "Ordner auswählen",
    },
}


def detect_language(saved: str | None = None, env: str | None = None) -> str:
    """Saved choice wins, then MODSWITCH_LANG, then the system locale (default: English)."""
    for candidate in (saved, env if env is not None else os.environ.get("MODSWITCH_LANG")):
        if candidate and candidate.lower()[:2] in LANGUAGES:
            return candidate.lower()[:2]
    locale_name = (
        os.environ.get("LC_ALL")
        or os.environ.get("LC_MESSAGES")
        or os.environ.get("LANG")
        or ""
    ).lower()
    return "de" if locale_name.startswith("de") else "en"


class Translator:
    def __init__(self, language: str = "en"):
        self.language = language if language in LANGUAGES else "en"

    def __call__(self, key: str, **values) -> str:
        text = STRINGS[self.language].get(key) or STRINGS["en"].get(key, key)
        return text.format(**values) if values else text
