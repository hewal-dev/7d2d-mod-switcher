#!/usr/bin/env python3
"""7D2D Mod Switcher als kleine Anwendung (PySide6, dunkle Oberfläche).

Aufgabe: der Ordner `<Spiel>/7 Days To Die/Mods` ist ein Symlink auf einen der
Mod-Sätze im eigenen Mod-Ordner. Die Anwendung zeigt alle Sätze, markiert den
aktiven und schaltet den Symlink um. Sie verweigert den Eingriff, wenn `Mods`
ein echtes Verzeichnis ist (dann würde gelöscht, was nicht gelöscht werden darf).

Beide Pfade sind einstellbar und werden gemerkt:
  * Spielordner  — Standard: automatisch gefundene Steam-Installation
  * Mod-Ordner   — Standard: `~/7 Days`, sonst frei wählbar
Gespeichert in `~/.config/7d2d-mod-switcher/config.json`.

Für Tests und Sonderfälle überschreiben Umgebungsvariablen alles:
MODSWITCH_GAME_DIR, MODSWITCH_MOD_BASE, MODSWITCH_CONFIG, MODSWITCH_UI_KIT.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

try:
    from PySide6.QtCore import QTimer, Qt, Signal
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import (
        QApplication,
        QButtonGroup,
        QDialog,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QRadioButton,
        QScrollArea,
        QVBoxLayout,
        QWidget,
    )
except ImportError:  # pragma: no cover - only hits a machine without PySide6
    print(
        "PySide6 fehlt. Installieren mit:  sudo pacman -S pyside6\n"
        "(oder: python3 -m pip install --user PySide6)",
        file=sys.stderr,
    )
    raise SystemExit(2)

APP_DIR = Path(__file__).resolve().parent
APP_NAME = "7D2D Mod Switcher"
LOGO = APP_DIR / "assets" / "mod-switcher-logo.png"
CONFIG_PATH = Path(
    os.environ.get(
        "MODSWITCH_CONFIG", Path.home() / ".config" / "7d2d-mod-switcher" / "config.json"
    )
)
GAME_FOLDER_NAME = "7 Days To Die"


def _ui_kit_dir() -> Path | None:
    """Find the shared widget style: env, bundled copy next to the app, home copy."""
    candidates = [
        os.environ.get("MODSWITCH_UI_KIT"),
        APP_DIR / "ui_kit",
        Path.home() / "AI" / "ui-kit",
    ]
    for candidate in candidates:
        if candidate and (Path(candidate) / "ui_style.py").is_file():
            return Path(candidate)
    return None


UI_KIT = _ui_kit_dir()
if UI_KIT is not None and str(UI_KIT) not in sys.path:
    sys.path.insert(0, str(UI_KIT))

from ui_style import ASSETS, styled  # noqa: E402


# --------------------------------------------------------------------- paths
def default_steam_roots() -> list[Path]:
    return [
        Path.home() / ".local" / "share" / "Steam",
        Path.home() / ".steam" / "steam",
        Path.home() / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam",
    ]


def steam_libraries(roots: list[Path] | None = None) -> list[Path]:
    """Steam roots and every library folder listed in libraryfolders.vdf."""
    roots = default_steam_roots() if roots is None else roots
    found: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        found.append(root)
        vdf = root / "steamapps" / "libraryfolders.vdf"
        if not vdf.is_file():
            continue
        try:
            text = vdf.read_text(errors="ignore")
        except OSError:
            continue
        for line in text.splitlines():
            match = re.search(r'"path"\s+"([^"]+)"', line)
            if match:
                found.append(Path(match.group(1)))
                continue
            match = re.search(r'"\d+"\s+"(/[^"]+)"', line)  # older VDF layout
            if match:
                found.append(Path(match.group(1)))
    unique: list[Path] = []
    for path in found:
        if path not in unique:
            unique.append(path)
    return unique


def detect_game_dir(libraries: list[Path] | None = None) -> Path | None:
    """First existing `7 Days To Die` install inside a known Steam library."""
    for library in (steam_libraries() if libraries is None else libraries):
        candidate = library / "steamapps" / "common" / GAME_FOLDER_NAME
        if candidate.is_dir():
            return candidate
    return None


def default_mod_base() -> Path:
    return Path.home() / "7 Days"


def read_config() -> dict:
    if not CONFIG_PATH.is_file():
        return {}
    try:
        data = json.loads(CONFIG_PATH.read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def write_config(game_dir: Path, mod_base: Path) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps({"game_dir": str(game_dir), "mod_base": str(mod_base)}, indent=2) + "\n"
    )


GAME_DIR = Path()
MOD_BASE = Path()
MOD_LINK = Path()


def apply_paths(game_dir: Path, mod_base: Path) -> None:
    global GAME_DIR, MOD_BASE, MOD_LINK
    GAME_DIR = Path(game_dir).expanduser()
    MOD_BASE = Path(mod_base).expanduser()
    MOD_LINK = GAME_DIR / "Mods"


def resolve_paths() -> tuple[Path, Path]:
    """Environment beats config file, config beats detection, detection beats default."""
    config = read_config()
    game_env = os.environ.get("MODSWITCH_GAME_DIR")
    base_env = os.environ.get("MODSWITCH_MOD_BASE")
    game = Path(game_env) if game_env else Path(config.get("game_dir") or "")
    base = Path(base_env) if base_env else Path(config.get("mod_base") or "")
    if not game.name:
        game = detect_game_dir() or (
            Path.home() / ".local" / "share" / "Steam" / "steamapps" / "common" / GAME_FOLDER_NAME
        )
    if not base.name:
        base = Path(config.get("mod_base") or default_mod_base())
    return game, base


apply_paths(*resolve_paths())


# --------------------------------------------------------------------- logic
def active_target() -> Path | None:
    """Resolved target of the Mods symlink, or None when nothing is linked."""
    if not MOD_LINK.is_symlink():
        return None
    try:
        return Path(os.path.realpath(MOD_LINK))
    except OSError:
        return None


def mod_sets() -> list[Path]:
    if not MOD_BASE.is_dir():
        return []
    return sorted((p for p in MOD_BASE.iterdir() if p.is_dir()), key=lambda p: p.name.lower())


def mod_count(path: Path) -> int:
    """Number of mod folders inside a set (each subfolder is one mod)."""
    try:
        return sum(1 for p in path.iterdir() if p.is_dir())
    except OSError:
        return 0


def check_state() -> str | None:
    """Blocking problems, same checks as the original shell script."""
    if not GAME_DIR.is_dir():
        return (
            "Spielordner nicht gefunden:\n"
            f"{GAME_DIR}\n\n"
            "Über „Pfade…" + '"' + " den Ordner „7 Days To Die" + '"' + " auswählen."
        )
    if not MOD_BASE.is_dir():
        return (
            "Mod-Ordner nicht gefunden:\n"
            f"{MOD_BASE}\n\n"
            "Über „Pfade…" + '"' + " den Ordner mit den eigenen Mod-Sätzen auswählen."
        )
    if mods_state() == "directory":
        return (
            "Der Ordner Mods im Spiel ist ein echtes Verzeichnis.\n"
            "Über „Symlink anlegen“ (oder beim Start) wird er gesichert und umgestellt; "
            "von Hand wird dabei nichts gelöscht."
        )
    if not mod_sets():
        return f"Keine Mod-Ordner gefunden unter:\n{MOD_BASE}"
    return None


def mods_state() -> str:
    """'symlink', 'directory' (real folder) or 'missing'."""
    if MOD_LINK.is_symlink():
        return "symlink"
    if MOD_LINK.exists():
        return "directory"
    return "missing"


def backup_mods() -> Path | None:
    """Move a real Mods folder aside; nothing in it is ever deleted."""
    if MOD_LINK.is_symlink() or not MOD_LINK.exists():
        return None
    stamp = time.strftime("%Y%m%d-%H%M")
    backup = MOD_LINK.with_name(f"Mods-Original-{stamp}")
    counter = 2
    while backup.exists():
        backup = MOD_LINK.with_name(f"Mods-Original-{stamp}-{counter}")
        counter += 1
    MOD_LINK.rename(backup)
    return backup


def install_symlink(target_name: str | None = None) -> tuple[Path, Path | None]:
    """Create the Mods symlink; a real Mods folder is preserved as a backup."""
    sets = mod_sets()
    if not sets:
        raise FileNotFoundError(f"Keine Mod-Ordner gefunden unter: {MOD_BASE}")
    name = target_name or sets[0].name
    target = MOD_BASE / name
    if not target.is_dir():
        raise FileNotFoundError(f"Zielordner existiert nicht: {target}")
    backup = backup_mods()
    if MOD_LINK.is_symlink():
        MOD_LINK.unlink()
    MOD_LINK.symlink_to(target)
    return target, backup


def remove_symlink() -> bool:
    """Drop the Mods symlink (only a symlink, never a real folder)."""
    if MOD_LINK.is_symlink():
        MOD_LINK.unlink()
        return True
    return False


def activate(name: str) -> None:
    """Point the Mods symlink at MOD_BASE/name, exactly like the shell script."""
    target = MOD_BASE / name
    if not target.is_dir():
        raise FileNotFoundError(f"Zielordner existiert nicht: {target}")
    if MOD_LINK.exists() and not MOD_LINK.is_symlink():
        raise IsADirectoryError(
            "Der Ordner Mods ist ein echtes Verzeichnis. Über „Symlink anlegen“ "
            "wird er gesichert und durch einen Symlink ersetzt."
        )
    if MOD_LINK.is_symlink():
        MOD_LINK.unlink()
    MOD_LINK.symlink_to(target)


EXTRA_QSS = """
QLabel#badge {
    background: #1f5c3c; color: #eafff2; border: 1px solid #34d17b;
    border-radius: 9px; padding: 1px 9px; font-size: 11px; font-weight: 600;
}
QFrame#row { background: #1b1d22; border: 1px solid #2a2e37; border-radius: 10px; }
QFrame#row:hover { background: #23262d; border: 1px solid #3a4050; }
QFrame#row[aktiv="true"] { background: #16251d; border: 1px solid #34d17b; }
QRadioButton#mod { font-weight: 600; font-size: 13px; }
QRadioButton#mod::indicator:checked { image: url(RADIO_GREEN); }
QLabel#count { color: #aab0b9; font-size: 11px; }
QLabel#status { color: #c2c7d0; font-size: 12px; }
QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; }
QLabel#pfad { color: #8f959d; font-size: 11px; }
QLabel#feld { color: #c2c7d0; font-size: 12px; }
QLabel#hinweis { color: #8f959d; font-size: 11px; }
QLabel#banner {
    background: #3a1f22; border: 1px solid #7a3a3f; border-radius: 10px;
    color: #ffb4ab; font-size: 12px; padding: 10px 12px;
}
QLineEdit {
    background: #16181d; color: #f7f8fa; border: 1px solid #3a4050;
    border-radius: 8px; padding: 7px 10px; min-height: 20px;
}
QLineEdit:focus { border: 1px solid #6c98ff; background: #1a1d24; }
QLabel#warn { color: #ffbd66; font-size: 11px; }
QLabel#ok { color: #4fd39a; font-size: 11px; }
"""

if UI_KIT is not None:
    EXTRA_QSS = EXTRA_QSS.replace("RADIO_GREEN", (ASSETS / "radio-on-green.svg").as_posix())
else:  # style without assets still has to start
    EXTRA_QSS = EXTRA_QSS.replace("image: url(RADIO_GREEN);", "")


class ClickableRow(QFrame):
    """A mod row that reacts to a click anywhere on its bar, not just the label."""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class PathsDialog(QDialog):
    """Choose game folder and own mod folder; both must exist to be saved."""

    def __init__(self, game_dir: Path, mod_base: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pfade einstellen")
        self.setStyleSheet(styled() + EXTRA_QSS)
        self.setMinimumWidth(620)
        self.paths_changed = False
        self.status_text = ""
        self.game_edit = QLineEdit(str(game_dir))
        self.base_edit = QLineEdit(str(mod_base))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 20, 22, 16)
        outer.setSpacing(14)
        title = QLabel("Pfade einstellen")
        title.setObjectName("title")
        outer.addWidget(title)

        outer.addLayout(
            self._path_row(
                "Spielordner",
                "Der Ordner „7 Days To Die" + '"' + " aus der Steam-Installation.",
                self.game_edit,
            )
        )
        outer.addLayout(
            self._path_row(
                "Eigener Mod-Ordner",
                "Jeder Unterordner dieses Ordners gilt als eigener Mod-Satz.",
                self.base_edit,
            )
        )

        link_row = QHBoxLayout()
        link_row.setSpacing(8)
        link_label = QLabel("Ordner „Mods" + '"' + " im Spiel:")
        link_label.setObjectName("feld")
        self.create_link_button = QPushButton("Symlink anlegen")
        self.create_link_button.setCursor(Qt.PointingHandCursor)
        self.create_link_button.setToolTip(
            "Ersetzt den Ordner Mods durch einen Symlink auf den gewählten Mod-Satz. "
            "Ein vorhandener Ordner wird vorher als Sicherung umbenannt."
        )
        self.create_link_button.clicked.connect(lambda: self._on_link(True))
        self.remove_link_button = QPushButton("Symlink entfernen")
        self.remove_link_button.setCursor(Qt.PointingHandCursor)
        self.remove_link_button.setToolTip(
            "Entfernt nur den Symlink; das Spiel startet danach ohne Mods. "
            "Ein gesicherter Original-Ordner bleibt liegen."
        )
        self.remove_link_button.clicked.connect(lambda: self._on_link(False))
        link_row.addWidget(link_label)
        link_row.addStretch(1)
        link_row.addWidget(self.create_link_button)
        link_row.addWidget(self.remove_link_button)
        outer.addLayout(link_row)

        self.hint = QLabel()
        self.hint.setObjectName("hinweis")
        self.hint.setWordWrap(True)
        outer.addWidget(self.hint)

        outer.addWidget(self._make_divider())
        row = QHBoxLayout()
        row.addStretch(1)
        cancel = QPushButton("Abbrechen")
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        self.save_button = QPushButton("Speichern")
        self.save_button.setObjectName("primary")
        self.save_button.setCursor(Qt.PointingHandCursor)
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self.accept)
        row.addWidget(cancel)
        row.addWidget(self.save_button)
        outer.addLayout(row)

        self.game_edit.textChanged.connect(self._validate)
        self.base_edit.textChanged.connect(self._validate)
        self._validate()

    def _path_row(self, label: str, hint: str, edit: QLineEdit) -> QVBoxLayout:
        box = QVBoxLayout()
        box.setSpacing(4)
        name = QLabel(label)
        name.setObjectName("feld")
        line = QHBoxLayout()
        line.setSpacing(8)
        browse = QPushButton("Durchsuchen…")
        browse.setCursor(Qt.PointingHandCursor)
        browse.clicked.connect(lambda: self._browse(edit))
        line.addWidget(edit, 1)
        line.addWidget(browse)
        note = QLabel(hint)
        note.setObjectName("hinweis")
        note.setWordWrap(True)
        box.addWidget(name)
        box.addLayout(line)
        box.addWidget(note)
        return box

    def _confirm(self, title: str, text: str, ok: str) -> bool:
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setIcon(QMessageBox.Question)
        box.setText(text)
        yes = box.addButton(ok, QMessageBox.AcceptRole)
        box.addButton("Nein", QMessageBox.RejectRole)
        box.exec()
        return box.clickedButton() is yes

    def _on_link(self, create: bool) -> None:
        game = Path(self.game_edit.text()).expanduser()
        base = Path(self.base_edit.text()).expanduser()
        if not game.is_dir() or not base.is_dir():
            return
        apply_paths(game, base)
        write_config(game, base)
        try:
            if create:
                sets = mod_sets()
                if not sets:
                    raise FileNotFoundError(f"Keine Mod-Ordner gefunden unter: {base}")
                if not self._confirm(
                    "Symlink für Mods anlegen?",
                    "Symlink für Mods anlegen?\nKann jederzeit in der App rückgängig "
                    "gemacht werden.\n\nEin vorhandener Ordner wird vorher als "
                    "„Mods-Original-<Datum>" + '"' + " gesichert.",
                    "Ja",
                ):
                    return
                target, backup = install_symlink()
                message = f"Symlink auf „{target.name}" + '"' + " angelegt."
                if backup:
                    message += f" Original gesichert als „{backup.name}" + '"' + "."
            else:
                if not self._confirm(
                    "Symlink entfernen?",
                    "Symlink für Mods entfernen?\nDas Spiel startet danach ohne Mods. "
                    "Kann jederzeit wieder angelegt werden.",
                    "Ja",
                ):
                    return
                message = (
                    "Symlink entfernt." if remove_symlink() else "Es war kein Symlink vorhanden."
                )
        except Exception as exc:
            self.hint.setObjectName("banner")
            self.hint.setText(str(exc))
            self.hint.style().unpolish(self.hint)
            self.hint.style().polish(self.hint)
            return
        self.paths_changed = True
        self.status_text = message
        self._validate()

    def _browse(self, edit: QLineEdit) -> None:
        start = edit.text() or str(Path.home())
        chosen = QFileDialog.getExistingDirectory(self, "Ordner auswählen", start)
        if chosen:
            edit.setText(chosen)

    def _validate(self) -> None:
        game = Path(self.game_edit.text()).expanduser()
        base = Path(self.base_edit.text()).expanduser()
        problems = []
        if not game.is_dir():
            problems.append("Spielordner existiert nicht.")
        if not base.is_dir():
            problems.append("Mod-Ordner existiert nicht.")
        link = game / "Mods"
        is_link = link.is_symlink()
        is_dir = link.exists() and not is_link
        warning = ""
        if is_dir:
            warning = (
                "„Mods" + '"' + " ist ein echtes Verzeichnis — über „Symlink anlegen" + '"'
                + " wird es gesichert und umgestellt."
            )
        if hasattr(self, "create_link_button"):
            self.create_link_button.setEnabled(game.is_dir() and base.is_dir() and not is_link)
            self.remove_link_button.setEnabled(is_link)
        if problems:
            self.hint.setObjectName("banner")
            self.hint.setText(" ".join(problems))
        elif warning:
            self.hint.setObjectName("warn")
            self.hint.setText(warning)
        else:
            self.hint.setObjectName("ok")
            self.hint.setText("Beide Ordner gefunden.")
        self.hint.style().unpolish(self.hint)
        self.hint.style().polish(self.hint)
        self.save_button.setEnabled(not problems)

    def values(self) -> tuple[Path, Path]:
        return (
            Path(self.game_edit.text()).expanduser(),
            Path(self.base_edit.text()).expanduser(),
        )

    @staticmethod
    def _make_divider() -> QFrame:
        line = QFrame()
        line.setObjectName("divider")
        line.setFixedHeight(1)
        return line


class SwitcherWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(APP_NAME)
        if LOGO.is_file():
            self.setWindowIcon(QIcon(str(LOGO)))
        self.setStyleSheet(styled() + EXTRA_QSS)
        self.setMinimumSize(600, 460)
        self.setWindowModality(Qt.NonModal)
        self.error = check_state()
        self.radios: dict[str, QRadioButton] = {}
        self.rows: dict[str, QFrame] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 20, 22, 16)
        outer.setSpacing(12)
        outer.addLayout(self._build_header())

        self.banner = QLabel()
        self.banner.setObjectName("banner")
        self.banner.setWordWrap(True)
        self.banner.setVisible(False)
        outer.addWidget(self.banner)

        outer.addWidget(self._build_list(), 1)

        self.path_label = QLabel()
        self.path_label.setObjectName("pfad")
        outer.addWidget(self.path_label)

        self.status = QLabel()
        self.status.setObjectName("status")
        outer.addWidget(self.status)

        outer.addWidget(self._make_divider())
        outer.addLayout(self._build_footer())

        self.reload()
        if mods_state() == "directory" and os.environ.get("MODSWITCH_NO_ASK") != "1":
            QTimer.singleShot(0, self.offer_symlink)

    # ---------------------------------------------------------------- layout
    def _build_header(self) -> QVBoxLayout:
        box = QVBoxLayout()
        box.setSpacing(3)
        title = QLabel(APP_NAME)
        title.setObjectName("title")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("subtitle")
        box.addWidget(title)
        box.addWidget(self.subtitle)
        return box

    def _build_list(self) -> QScrollArea:
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.NoFrame)
        self.list_host = QWidget()
        self.list_layout = QVBoxLayout(self.list_host)
        self.list_layout.setContentsMargins(0, 0, 6, 0)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch(1)
        area.setWidget(self.list_host)
        return area

    def _build_footer(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self.reload_button = QPushButton("Neu einlesen")
        self.reload_button.setCursor(Qt.PointingHandCursor)
        self.reload_button.clicked.connect(self.reload)
        self.paths_button = QPushButton("Pfade…")
        self.paths_button.setCursor(Qt.PointingHandCursor)
        self.paths_button.setToolTip("Spielordner und eigenen Mod-Ordner einstellen.")
        self.paths_button.clicked.connect(self.edit_paths)
        close = QPushButton("Schließen")
        close.setCursor(Qt.PointingHandCursor)
        close.clicked.connect(self.reject)
        self.apply_button = QPushButton("Aktivieren")
        self.apply_button.setObjectName("primary")
        self.apply_button.setCursor(Qt.PointingHandCursor)
        self.apply_button.setDefault(True)
        self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self.apply)
        row.addWidget(self.reload_button)
        row.addWidget(self.paths_button)
        row.addStretch(1)
        row.addWidget(close)
        row.addWidget(self.apply_button)
        return row

    @staticmethod
    def _make_divider() -> QFrame:
        line = QFrame()
        line.setObjectName("divider")
        line.setFixedHeight(1)
        return line

    # ------------------------------------------------------------- behaviour
    def offer_symlink(self) -> bool:
        """Offer to replace a real Mods folder with the symlink (never deletes data)."""
        if mods_state() != "directory":
            return False
        box = QMessageBox(self)
        box.setWindowTitle("Symlink für Mods anlegen?")
        box.setIcon(QMessageBox.Question)
        box.setText(
            "Symlink für Mods anlegen?\n"
            "Kann jederzeit in der App rückgängig gemacht werden."
        )
        box.setInformativeText(
            "Der vorhandene Ordner bleibt erhalten und wird vorher als "
            "„Mods-Original-<Datum>" + '"' + " gesichert."
        )
        yes = box.addButton("Ja", QMessageBox.AcceptRole)
        box.addButton("Nein", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is not yes:
            self.status.setText("Unverändert — der Ordner Mods bleibt, wie er ist.")
            return False
        try:
            target, backup = install_symlink()
        except Exception as exc:
            self.banner.setText(str(exc))
            self.banner.setVisible(True)
            return False
        self.reload()
        message = f"Symlink angelegt auf „{target.name}" + '"' + "."
        if backup:
            message += f" Original gesichert als „{backup.name}" + '"' + "."
        self.status.setText(message)
        return True

    def edit_paths(self) -> bool:
        """Open the path dialog; on save remember the choice and reload."""
        dialog = PathsDialog(GAME_DIR, MOD_BASE, self)
        accepted = dialog.exec() == QDialog.Accepted
        if dialog.paths_changed:
            self.reload()
            if dialog.status_text:
                self.status.setText(dialog.status_text)
        if not accepted:
            return False
        game, base = dialog.values()
        apply_paths(game, base)
        write_config(game, base)
        self.reload()
        if not dialog.paths_changed:
            self.status.setText("Pfade gespeichert.")
        return True

    def reload(self) -> None:
        self.error = check_state()
        sets = mod_sets() if MOD_BASE.is_dir() else []
        active = active_target()
        active_name = active.name if active else ""

        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.radios.clear()
        self.rows.clear()
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.group.buttonToggled.connect(self._on_selection)

        for folder in sets:
            card = ClickableRow()
            card.setObjectName("row")
            is_active = folder.name == active_name
            card.setProperty("aktiv", "true" if is_active else "false")
            inner = QHBoxLayout(card)
            inner.setContentsMargins(14, 10, 14, 10)
            inner.setSpacing(10)

            radio = QRadioButton(folder.name)
            radio.setObjectName("mod")
            radio.setCursor(Qt.PointingHandCursor)
            radio.setChecked(is_active)
            self.group.addButton(radio)
            card.clicked.connect(lambda r=radio: r.setChecked(True))
            self.radios[folder.name] = radio
            self.rows[folder.name] = card

            count = QLabel(f"{mod_count(folder)} Mods")
            count.setObjectName("count")

            inner.addWidget(radio)
            inner.addStretch(1)
            if is_active:
                badge = QLabel("AKTIV")
                badge.setObjectName("badge")
                inner.addWidget(badge)
            inner.addWidget(count)
            self.list_layout.insertWidget(self.list_layout.count() - 1, card)

        self.apply_button.setEnabled(False)
        self.apply_button.setText("Aktivieren")
        self.banner.setVisible(bool(self.error))
        if self.error:
            self.banner.setText(self.error)
        elif active_name:
            self.subtitle.setText(f"Aktiv: {active_name} · {len(sets)} Mod-Ordner")
        else:
            self.subtitle.setText(f"Kein Mod-Ordner aktiv · {len(sets)} verfügbar")

        self.path_label.setText(f"Mod-Ordner: {MOD_BASE}")
        self.path_label.setToolTip(f"Spiel: {GAME_DIR}\nMod-Sätze: {MOD_BASE}")

    def selected(self) -> str | None:
        checked = self.group.checkedButton() if hasattr(self, "group") else None
        return checked.text() if checked else None

    def _on_selection(self, _button=None, checked: bool = True) -> None:
        if not checked or self.error:
            return
        aktive = active_target()
        name = self.selected()
        schon_aktiv = bool(name) and name == (aktive.name if aktive else "")
        self.apply_button.setEnabled(bool(name) and not schon_aktiv)
        self.apply_button.setText("Bereits aktiv" if schon_aktiv else "Aktivieren")
        self.apply_button.setToolTip(
            "Der ausgewählte Mod-Ordner ist bereits aktiv."
            if schon_aktiv
            else "Diesen Mod-Ordner für das Spiel aktivieren."
        )

    def apply(self) -> None:
        name = self.selected()
        if not name or self.error:
            return
        try:
            activate(name)
        except Exception as exc:  # surface the real reason instead of a silent no-op
            self.error = str(exc)
            self.banner.setText(str(exc))
            self.banner.setVisible(True)
            self.status.setText("Nicht umgestellt.")
            self.apply_button.setEnabled(False)
            return
        self.reload()
        self.apply_button.setText("Bereits aktiv")
        self.status.setText(f"Aktiviert: {name}")

    def select(self, name: str) -> None:
        for folder, radio in self.radios.items():
            if folder == name:
                radio.setChecked(True)
                break


def main(argv: list[str]) -> int:
    app = QApplication.instance() or QApplication(argv[:1])
    app.setApplicationName(APP_NAME)
    if LOGO.is_file():
        app.setWindowIcon(QIcon(str(LOGO)))
    window = SwitcherWindow()
    auto = os.environ.get("MODSWITCH_AUTO")  # test hook: select and activate, then quit
    if auto == "__close__":
        # Test hook: show the window, then close it through the normal event loop.
        QTimer.singleShot(0, window.reject)
        window.show()
        code = app.exec()
        os._exit(code)
    if auto:
        window.select(auto)
        window.apply()
        print(window.status.text() or "keine Aktion")
        app.processEvents()
        print("aktiv jetzt:", (active_target() or Path("-")))
        window.deleteLater()
        app.processEvents()
        os._exit(0)
    window.show()
    # PySide6 crashes while destroying widgets during interpreter shutdown; the
    # window is gone at this point, so exit the process directly.
    code = app.exec()
    os._exit(code)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
