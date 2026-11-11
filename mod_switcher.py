#!/usr/bin/env python3
"""7D2D Mod Switcher — small desktop app (PySide6, dark UI, English/German).

Task: `<game>/Mods` is a symlink pointing at one of the mod sets in your own mod
folder. The app lists the sets, marks the active one and switches the symlink.
It never deletes anything: a real `Mods` folder is renamed as a backup first.

Both paths and the language are remembered in
`~/.config/7d2d-mod-switcher/config.json` (Windows: `%APPDATA%\\7d2d-mod-switcher\\config.json`).

Environment overrides (tests, special cases):
MODSWITCH_GAME_DIR, MODSWITCH_MOD_BASE, MODSWITCH_CONFIG, MODSWITCH_UI_KIT, MODSWITCH_LANG.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
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
        "PySide6 fehlt / PySide6 is missing.\n"
        "  Arch/CachyOS:  sudo pacman -S pyside6\n"
        "  otherwise:     python3 -m pip install --user PySide6",
        file=sys.stderr,
    )
    raise SystemExit(2)

APP_DIR = Path(__file__).resolve().parent
APP_NAME = "7D2D Mod Switcher"
LOGO = APP_DIR / "assets" / "mod-switcher-logo.png"
GAME_FOLDER_NAME = "7 Days To Die"


def _config_path() -> Path:
    override = os.environ.get("MODSWITCH_CONFIG")
    if override:
        return Path(override)
    appdata = os.environ.get("APPDATA")  # Windows
    if appdata:
        return Path(appdata) / "7d2d-mod-switcher" / "config.json"
    return Path.home() / ".config" / "7d2d-mod-switcher" / "config.json"


CONFIG_PATH = _config_path()


def _ui_kit_dir() -> Path | None:
    """Find the shared widget style: env, bundled copy next to the app, home copy."""
    for candidate in (
        os.environ.get("MODSWITCH_UI_KIT"),
        APP_DIR / "ui_kit",
        Path.home() / "AI" / "ui-kit",
    ):
        if candidate and (Path(candidate) / "ui_style.py").is_file():
            return Path(candidate)
    return None


UI_KIT = _ui_kit_dir()
if UI_KIT is not None and str(UI_KIT) not in sys.path:
    sys.path.insert(0, str(UI_KIT))
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from ui_style import ASSETS, styled  # noqa: E402

from i18n import LANGUAGES, Translator, detect_language  # noqa: E402


# ------------------------------------------------------------------- settings
def read_config() -> dict:
    if not CONFIG_PATH.is_file():
        return {}
    try:
        data = json.loads(CONFIG_PATH.read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def write_config(game_dir: Path, mod_base: Path, language: str | None = None) -> None:
    data = {"game_dir": str(game_dir), "mod_base": str(mod_base)}
    if language:
        data["language"] = language
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, indent=2) + "\n")


T = Translator(detect_language(read_config().get("language")))


# ---------------------------------------------------------------------- paths
def default_steam_roots() -> list[Path]:
    home = Path.home()
    if sys.platform.startswith("win"):
        return [
            Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")) / "Steam",
            Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "Steam",
        ]
    return [
        home / ".local" / "share" / "Steam",
        home / ".steam" / "steam",
        home / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam",
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
            match = re.search(r'"\d+"\s+"([A-Za-z]:[^"]+)"', line)  # older VDF layout
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
            default_steam_roots()[0] / "steamapps" / "common" / GAME_FOLDER_NAME
        )
    if not base.name:
        base = Path(config.get("mod_base") or default_mod_base())
    return game, base


apply_paths(*resolve_paths())




# ------------------------------------------------------------------ links
IS_WINDOWS = sys.platform.startswith("win")


def is_link(path: Path) -> bool:
    """True for a symlink (Linux, Windows with Developer Mode) or a junction.

    Junctions need no special rights on Windows, symlinks do — which is why the
    app creates junctions there instead.
    """
    if path.is_symlink():
        return True
    isjunction = getattr(os.path, "isjunction", None)
    return bool(isjunction and isjunction(path))


def create_link(target: Path, link: Path) -> None:
    """Point `link` at `target` (junction on Windows, symlink elsewhere)."""
    if IS_WINDOWS:
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            text=True,
            errors="replace",
        )
        if result.returncode != 0:
            raise OSError((result.stdout + result.stderr).strip() or "mklink /J failed")
        return
    link.symlink_to(target, target_is_directory=True)


def remove_link(link: Path) -> bool:
    """Remove the link itself; the folder behind it is never touched."""
    if link.is_symlink():
        link.unlink()
        return True
    if is_link(link):
        os.rmdir(link)  # a junction is a reparse point directory
        return True
    return False


# ---------------------------------------------------------------------- logic
def active_target() -> Path | None:
    """Resolved target of the Mods symlink, or None when nothing is linked."""
    if not is_link(MOD_LINK):
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


def mods_state() -> str:
    """'symlink' (link or junction), 'directory' (real folder) or 'missing'."""
    if is_link(MOD_LINK):
        return "symlink"
    if MOD_LINK.exists():
        return "directory"
    return "missing"


def setup_state() -> dict:
    """What is still missing for a working first run.

    A missing game folder is not an error: mod sets can be collected before the
    game is installed. Only a real `Mods` folder in the way needs a decision.
    """
    base_ok = MOD_BASE.is_dir()
    sets = mod_sets() if base_ok else []
    return {
        "game": GAME_DIR.is_dir(),
        "base": base_ok,
        "sets": len(sets),
        "ready": GAME_DIR.is_dir() and base_ok and bool(sets),
    }


def can_switch() -> bool:
    """Everything needed to flip the link is in place."""
    return GAME_DIR.is_dir() and bool(mod_sets()) and mods_state() != "directory"


def check_state() -> str | None:
    """Problem that needs a decision (a real Mods folder), or None."""
    if mods_state() == "directory":
        return T("err.real_dir")
    return None


def create_mod_folder() -> Path:
    """Create the configured mod folder; the empty state offers this as a button."""
    MOD_BASE.mkdir(parents=True, exist_ok=True)
    return MOD_BASE


def open_in_file_manager(path: Path) -> bool:
    """Show a folder in the desktop file manager; False when that is not possible."""
    target = Path(path)
    if os.environ.get("MODSWITCH_NO_OPEN") == "1" or not target.is_dir():
        return False
    try:
        if IS_WINDOWS:
            os.startfile(str(target))  # type: ignore[attr-defined]  # Windows only
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target)])
    except OSError:
        return False
    return True


def backup_mods() -> Path | None:
    """Move a real Mods folder aside; nothing in it is ever deleted."""
    if is_link(MOD_LINK) or not MOD_LINK.exists():
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
        raise FileNotFoundError(T("err.no_sets", path=MOD_BASE))
    name = target_name or sets[0].name
    target = MOD_BASE / name
    if not target.is_dir():
        raise FileNotFoundError(T("err.target_missing", path=target))
    backup = backup_mods()
    remove_link(MOD_LINK)
    create_link(target, MOD_LINK)
    return target, backup


def remove_symlink() -> bool:
    """Drop the Mods link (only the link, never a real folder)."""
    return remove_link(MOD_LINK)


def activate(name: str) -> None:
    """Point the Mods symlink at MOD_BASE/name."""
    target = MOD_BASE / name
    if not target.is_dir():
        raise FileNotFoundError(T("err.target_missing", path=target))
    if MOD_LINK.exists() and not is_link(MOD_LINK):
        raise IsADirectoryError(T("err.is_directory"))
    remove_link(MOD_LINK)
    create_link(target, MOD_LINK)


# ------------------------------------------------------------------------ UI
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
QFrame#setup {
    background: #191b21; border: 1px solid #2a2e37; border-radius: 10px;
}
QPushButton#klein { min-width: 0px; padding: 4px 10px; font-size: 12px; }
QPushButton#lang { min-width: 40px; padding: 4px 10px; font-size: 12px; }
QPushButton#lang[aktiv="true"] {
    background: #2b3d64; border: 1px solid #5b8cff; color: #ffffff; font-weight: 600;
}
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
        self.paths_changed = False
        self.status_text = ""
        self.setWindowTitle(T("paths.title"))
        self.setStyleSheet(styled() + EXTRA_QSS)
        self.setMinimumWidth(660)
        self.game_edit = QLineEdit(str(game_dir))
        self.base_edit = QLineEdit(str(mod_base))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 20, 22, 16)
        outer.setSpacing(14)
        title = QLabel(T("paths.title"))
        title.setObjectName("title")
        outer.addWidget(title)

        outer.addLayout(self._path_row(T("paths.game"), T("paths.game_hint"), self.game_edit))
        outer.addLayout(
            self._path_row(T("paths.base"), T("paths.base_hint"), self.base_edit, with_create=True)
        )

        link_row = QHBoxLayout()
        link_row.setSpacing(8)
        link_label = QLabel(T("paths.link_row"))
        link_label.setObjectName("feld")
        self.create_link_button = QPushButton(T("paths.create"))
        self.create_link_button.setCursor(Qt.PointingHandCursor)
        self.create_link_button.setToolTip(T("paths.create_tip"))
        self.create_link_button.clicked.connect(lambda: self._on_link(True))
        self.remove_link_button = QPushButton(T("paths.remove"))
        self.remove_link_button.setCursor(Qt.PointingHandCursor)
        self.remove_link_button.setToolTip(T("paths.remove_tip"))
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
        cancel = QPushButton(T("paths.cancel"))
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        self.save_button = QPushButton(T("paths.save"))
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

    def _path_row(
        self, label: str, hint: str, edit: QLineEdit, with_create: bool = False
    ) -> QVBoxLayout:
        box = QVBoxLayout()
        box.setSpacing(4)
        name = QLabel(label)
        name.setObjectName("feld")
        line = QHBoxLayout()
        line.setSpacing(8)
        browse = QPushButton(T("paths.browse"))
        browse.setCursor(Qt.PointingHandCursor)
        browse.clicked.connect(lambda: self._browse(edit))
        line.addWidget(edit, 1)
        if with_create:
            self.base_create_button = QPushButton(T("button.create_folder"))
            self.base_create_button.setObjectName("klein")
            self.base_create_button.setCursor(Qt.PointingHandCursor)
            self.base_create_button.clicked.connect(self.on_create_base)
            line.addWidget(self.base_create_button)
        line.addWidget(browse)
        note = QLabel(hint)
        note.setObjectName("hinweis")
        note.setWordWrap(True)
        box.addWidget(name)
        box.addLayout(line)
        box.addWidget(note)
        return box

    def _browse(self, edit: QLineEdit) -> None:
        start = edit.text() or str(Path.home())
        chosen = QFileDialog.getExistingDirectory(self, T("dialog.choose_folder"), start)
        if chosen:
            edit.setText(chosen)

    def _confirm(self, title: str, text: str, informative: str = "") -> bool:
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setIcon(QMessageBox.Question)
        box.setText(text)
        if informative:
            box.setInformativeText(informative)
        yes = box.addButton(T("ask.yes"), QMessageBox.AcceptRole)
        box.addButton(T("ask.no"), QMessageBox.RejectRole)
        box.exec()
        return box.clickedButton() is yes

    def _set_hint(self, style: str, text: str) -> None:
        self.hint.setObjectName(style)
        self.hint.setText(text)
        self.hint.style().unpolish(self.hint)
        self.hint.style().polish(self.hint)

    def _on_link(self, create: bool) -> None:
        game = Path(self.game_edit.text()).expanduser()
        base = Path(self.base_edit.text()).expanduser()
        if not game.is_dir() or not base.is_dir():
            return
        apply_paths(game, base)
        write_config(game, base, T.language)
        try:
            if create:
                if not mod_sets():
                    raise FileNotFoundError(T("err.no_sets", path=base))
                if not self._confirm(
                    T("ask.create.title"), T("ask.create.text"), T("ask.create.info")
                ):
                    return
                target, backup = install_symlink()
                message = (
                    T("paths.msg.created_backup", name=target.name, backup=backup.name)
                    if backup
                    else T("paths.msg.created", name=target.name)
                )
            else:
                if not self._confirm(T("ask.remove.title"), T("ask.remove.text")):
                    return
                message = T("paths.msg.removed") if remove_symlink() else T("paths.msg.no_link")
        except Exception as exc:
            self._set_hint("banner", str(exc))
            return
        self.paths_changed = True
        self.status_text = message
        self._validate()

    def on_create_base(self) -> None:
        """Create the mod folder right here instead of sending the user away."""
        target = Path(self.base_edit.text()).expanduser()
        try:
            target.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._set_hint("banner", T("status.create_failed", msg=exc))
            return
        self._validate()

    def _validate(self) -> None:
        game = Path(self.game_edit.text()).expanduser()
        base = Path(self.base_edit.text()).expanduser()
        problems = []
        if not game.is_dir():
            problems.append(T("paths.missing_game"))
        if not base.is_dir():
            problems.append(T("paths.missing_base"))

        link = game / "Mods"
        linked = is_link(link)
        warning = ""
        if game.is_dir() and link.exists() and not linked:
            warning = T("paths.warn_real_dir")
        if hasattr(self, "base_create_button"):
            self.base_create_button.setEnabled(
                bool(str(self.base_edit.text()).strip()) and not base.is_dir()
            )
        if hasattr(self, "create_link_button"):
            self.create_link_button.setEnabled(game.is_dir() and base.is_dir() and not linked)
            self.remove_link_button.setEnabled(linked)

        if problems:
            self._set_hint("banner", " ".join(problems))
        elif warning:
            self._set_hint("warn", warning)
        else:
            self._set_hint("ok", T("paths.found"))
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
        if LOGO.is_file():
            self.setWindowIcon(QIcon(str(LOGO)))
        self.setStyleSheet(styled() + EXTRA_QSS)
        self.setMinimumSize(640, 490)
        self.setWindowModality(Qt.NonModal)
        self.error = check_state()
        self.radios: dict[str, QRadioButton] = {}
        self.rows: dict[str, QFrame] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 20, 22, 16)
        outer.setSpacing(12)
        outer.addLayout(self._build_header())

        self.setup_frame = QFrame()
        self.setup_frame.setObjectName("setup")
        self.setup_layout = QVBoxLayout(self.setup_frame)
        self.setup_layout.setContentsMargins(14, 12, 14, 12)
        self.setup_layout.setSpacing(8)
        outer.addWidget(self.setup_frame)

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

        self.retranslate()
        if mods_state() == "directory" and os.environ.get("MODSWITCH_NO_ASK") != "1":
            QTimer.singleShot(0, self.offer_symlink)

    # ---------------------------------------------------------------- layout
    def _build_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        box = QVBoxLayout()
        box.setSpacing(3)
        self.title_label = QLabel(APP_NAME)
        self.title_label.setObjectName("title")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("subtitle")
        box.addWidget(self.title_label)
        box.addWidget(self.subtitle)
        row.addLayout(box, 1)

        self.lang_buttons: dict[str, QPushButton] = {}
        for code in LANGUAGES:
            button = QPushButton(code.upper())
            button.setObjectName("lang")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setToolTip(T("lang.tip"))
            button.clicked.connect(lambda _=False, c=code: self.set_language(c))
            self.lang_buttons[code] = button
            row.addWidget(button)
        return row

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
        self.reload_button = QPushButton()
        self.reload_button.setCursor(Qt.PointingHandCursor)
        self.reload_button.clicked.connect(self.reload)
        self.paths_button = QPushButton()
        self.paths_button.setCursor(Qt.PointingHandCursor)
        self.paths_button.clicked.connect(self.edit_paths)
        self.close_button = QPushButton()
        self.close_button.setCursor(Qt.PointingHandCursor)
        self.close_button.clicked.connect(self.reject)
        self.apply_button = QPushButton()
        self.apply_button.setObjectName("primary")
        self.apply_button.setCursor(Qt.PointingHandCursor)
        self.apply_button.setDefault(True)
        self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self.apply)
        row.addWidget(self.reload_button)
        row.addWidget(self.paths_button)
        row.addStretch(1)
        row.addWidget(self.close_button)
        row.addWidget(self.apply_button)
        return row

    @staticmethod
    def _make_divider() -> QFrame:
        line = QFrame()
        line.setObjectName("divider")
        line.setFixedHeight(1)
        return line

    # ------------------------------------------------------------- language
    def set_language(self, code: str) -> None:
        if code == T.language:
            self._sync_language_buttons()
            return
        T.language = code
        write_config(GAME_DIR, MOD_BASE, T.language)
        for button in self.lang_buttons.values():
            button.setToolTip(T("lang.tip"))
        self.retranslate()

    def _sync_language_buttons(self) -> None:
        for code, button in self.lang_buttons.items():
            active = code == T.language
            button.setChecked(active)
            button.setProperty("aktiv", "true" if active else "false")
            button.style().unpolish(button)
            button.style().polish(button)

    def retranslate(self) -> None:
        self.setWindowTitle(APP_NAME)
        self.reload_button.setText(T("button.reload"))
        self.reload_button.setToolTip(T("tip.reload"))
        self.paths_button.setText(T("button.paths"))
        self.paths_button.setToolTip(T("tip.paths"))
        self.close_button.setText(T("button.close"))
        self.apply_button.setText(T("button.activate"))
        self._sync_language_buttons()
        self.reload()

    # ------------------------------------------------------------- behaviour
    def offer_symlink(self) -> bool:
        """Offer to replace a real Mods folder with the symlink (never deletes data)."""
        if mods_state() != "directory":
            return False
        box = QMessageBox(self)
        box.setWindowTitle(T("ask.create.title"))
        box.setIcon(QMessageBox.Question)
        box.setText(T("ask.create.text"))
        box.setInformativeText(T("ask.create.info"))
        yes = box.addButton(T("ask.yes"), QMessageBox.AcceptRole)
        box.addButton(T("ask.no"), QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is not yes:
            self.status.setText(T("status.unchanged"))
            return False
        try:
            target, backup = install_symlink()
        except Exception as exc:
            self.banner.setText(str(exc))
            self.banner.setVisible(True)
            return False
        self.reload()
        message = T("status.link_created", name=target.name)
        if backup:
            message += T("status.backup", name=backup.name)
        self.status.setText(message)
        return True

    # ---------------------------------------------------------- first run
    @staticmethod
    def _clear_layout(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            elif item.layout() is not None:
                SwitcherWindow._clear_layout(item.layout())

    def _setup_row(self, ok: bool, text: str, buttons=()) -> QWidget:
        """One checklist line: state dot, text and the buttons that fix it."""
        row = QWidget()
        line = QHBoxLayout(row)
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(8)

        dot = QLabel("●" if ok else "○")
        dot.setObjectName("ok" if ok else "warn")
        label = QLabel(text)
        label.setObjectName("feld" if ok else "warn")
        label.setWordWrap(True)
        line.addWidget(dot)
        line.addWidget(label, 1)

        for caption, handler in buttons:
            button = QPushButton(caption)
            button.setObjectName("klein")
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(handler)
            line.addWidget(button)
        return row

    def _refresh_setup(self) -> None:
        """Show the getting-started checklist while anything is still missing."""
        self._clear_layout(self.setup_layout)
        state = setup_state()
        self.setup_frame.setVisible(not state["ready"])
        if state["ready"]:
            return

        title = QLabel(T("setup.title"))
        title.setObjectName("subtitle")
        self.setup_layout.addWidget(title)

        if state["game"]:
            self.setup_layout.addWidget(
                self._setup_row(True, T("setup.game.ok", path=GAME_DIR))
            )
        else:
            self.setup_layout.addWidget(
                self._setup_row(
                    False,
                    T("setup.game.missing"),
                    [(T("button.choose_folder"), lambda: self.choose_folder("game"))],
                )
            )

        if state["base"]:
            self.setup_layout.addWidget(
                self._setup_row(
                    True,
                    T("setup.base.ok", path=MOD_BASE),
                    [(T("button.open_folder"), lambda: open_in_file_manager(MOD_BASE))],
                )
            )
        else:
            self.setup_layout.addWidget(
                self._setup_row(
                    False,
                    T("setup.base.missing", path=MOD_BASE),
                    [
                        (T("button.create_folder"), self.on_create_folder),
                        (T("button.choose_folder"), lambda: self.choose_folder("base")),
                    ],
                )
            )

        if state["base"]:
            if state["sets"]:
                self.setup_layout.addWidget(
                    self._setup_row(True, T("setup.sets.count", count=state["sets"]))
                )
            else:
                self.setup_layout.addWidget(
                    self._setup_row(
                        False,
                        T("setup.sets.none"),
                        [
                            (T("button.open_folder"), lambda: open_in_file_manager(MOD_BASE)),
                            (T("button.reload"), self.reload),
                        ],
                    )
                )

    def choose_folder(self, which: str) -> None:
        """Pick the game folder or the mod folder straight from the checklist."""
        start = MOD_BASE if which == "base" else GAME_DIR
        if not start.is_dir():
            start = Path.home()
        chosen = QFileDialog.getExistingDirectory(self, T("dialog.choose_folder"), str(start))
        if not chosen:
            return
        path = Path(chosen)
        if which == "base":
            apply_paths(GAME_DIR, path)
        else:
            apply_paths(path, MOD_BASE)
        write_config(GAME_DIR, MOD_BASE, T.language)
        self.reload()
        self.status.setText(T("status.folder_chosen", path=path))

    def on_create_folder(self) -> None:
        """Create the mod folder so the user does not have to leave the app."""
        try:
            created = create_mod_folder()
        except OSError as exc:
            self.status.setText(T("status.create_failed", msg=exc))
            return
        self.reload()
        self.status.setText(T("status.folder_created", path=created))

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
        write_config(game, base, T.language)
        self.reload()
        if not dialog.paths_changed:
            self.status.setText(T("status.paths_saved"))
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

            count = QLabel(T("count", count=mod_count(folder)))
            count.setObjectName("count")

            inner.addWidget(radio)
            inner.addStretch(1)
            if is_active:
                badge = QLabel(T("badge"))
                badge.setObjectName("badge")
                inner.addWidget(badge)
            inner.addWidget(count)
            self.list_layout.insertWidget(self.list_layout.count() - 1, card)

        self.apply_button.setEnabled(False)
        self.apply_button.setText(T("button.activate"))
        self.banner.setVisible(bool(self.error))
        if self.error:
            self.banner.setText(self.error)
        if active_name:
            self.subtitle.setText(T("header.active", name=active_name, count=len(sets)))
        elif sets:
            self.subtitle.setText(T("header.none", count=len(sets)))
        else:
            self.subtitle.setText(T("header.empty"))
        if not GAME_DIR.is_dir():
            self.subtitle.setText(
                self.subtitle.text() + " · " + T("header.game_missing")
            )
        self._refresh_setup()

        self.path_label.setText(T("path.base", path=MOD_BASE))
        self.path_label.setToolTip(T("path.tooltip", game=GAME_DIR, base=MOD_BASE))

    def selected(self) -> str | None:
        checked = self.group.checkedButton() if hasattr(self, "group") else None
        return checked.text() if checked else None

    def _on_selection(self, _button=None, checked: bool = True) -> None:
        if not checked or self.error:
            return
        aktive = active_target()
        name = self.selected()
        schon_aktiv = bool(name) and name == (aktive.name if aktive else "")
        state = setup_state()
        self.apply_button.setEnabled(bool(name) and not schon_aktiv and can_switch())
        self.apply_button.setText(
            T("button.already_active") if schon_aktiv else T("button.activate")
        )
        if schon_aktiv:
            tip = T("tip.already_active")
        elif not state["game"]:
            tip = T("tip.needs_game")
        elif not state["sets"]:
            tip = T("tip.needs_sets")
        else:
            tip = T("tip.activate")
        self.apply_button.setToolTip(tip)

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
            self.status.setText(T("status.not_switched"))
            self.apply_button.setEnabled(False)
            return
        self.reload()
        self.apply_button.setText(T("button.already_active"))
        self.status.setText(T("status.activated", name=name))

    def select(self, name: str) -> None:
        for folder, radio in self.radios.items():
            if folder == name:
                radio.setChecked(True)
                break


def language_from_argv(argv: list[str]) -> str | None:
    """Read --lang=de / --lang de; the Windows installer passes its own choice."""
    for index, arg in enumerate(argv):
        value = None
        if arg.startswith("--lang="):
            value = arg.split("=", 1)[1]
        elif arg == "--lang" and index + 1 < len(argv):
            value = argv[index + 1]
        if value and value.lower()[:2] in LANGUAGES:
            return value.lower()[:2]
    return None


def use_language(code: str) -> None:
    """Switch the interface language and remember it in the config file."""
    T.language = code
    write_config(GAME_DIR, MOD_BASE, code)


def _say(text: str) -> None:
    """Report for the test hooks; a windowed build has no stdout at all."""
    if sys.stdout is None:
        return
    print(text)
    sys.stdout.flush()


def main(argv: list[str]) -> int:
    forced = language_from_argv(argv)
    if forced:
        use_language(forced)
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
        os._exit(app.exec())
    if auto:
        window.select(auto)
        window.apply()
        _say(window.status.text() or "no action")
        app.processEvents()
        _say("active now: %s" % (active_target() or Path("-")))
        window.deleteLater()
        app.processEvents()
        os._exit(0)
    window.show()
    # PySide6 crashes while destroying widgets during interpreter shutdown; the
    # window is gone at this point, so exit the process directly.
    os._exit(app.exec())


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
