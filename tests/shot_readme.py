#!/usr/bin/env python3
"""Render the README screenshots from a throwaway demo tree (offscreen Qt).

Usage:  DEMO_ROOT=/tmp/demo python3 tests/shot_readme.py docs/screenshots

The demo root must contain `Steam/steamapps/common/7 Days To Die` and a `7 Days`
folder with a few mod sets; the script links `Mods` to one of them so the active
state is visible. Nothing outside DEMO_ROOT is touched: the config path is
redirected before the app module is imported, so the real config stays untouched.
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["MODSWITCH_NO_ASK"] = "1"
os.environ["MODSWITCH_NO_OPEN"] = "1"

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

DEMO = Path(os.environ["DEMO_ROOT"])
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else APP_DIR / "docs" / "screenshots")
GAME = DEMO / "Steam" / "steamapps" / "common" / "7 Days To Die"
BASE = DEMO / "7 Days"
SETS = (("01 Vanilla", 2), ("02 QoL", 6), ("03 Overhaul", 14))
ACTIVE = "02 QoL"

# Redirect everything before the app module computes its paths and config.
os.environ["MODSWITCH_CONFIG"] = str(DEMO / "config.json")
os.environ["MODSWITCH_GAME_DIR"] = str(GAME)
os.environ["MODSWITCH_MOD_BASE"] = str(BASE)
os.environ["MODSWITCH_LANG"] = "en"

from PySide6.QtWidgets import QApplication  # noqa: E402

import mod_switcher as mod  # noqa: E402


def build_demo() -> None:
    GAME.mkdir(parents=True, exist_ok=True)
    for name, count in SETS:
        folder = BASE / name
        folder.mkdir(parents=True, exist_ok=True)
        for index in range(count):
            (folder / f"Mod{index + 1:02d}").mkdir(exist_ok=True)
    link = GAME / "Mods"
    if mod.is_link(link) or link.exists():
        mod.remove_link(link)
    link.symlink_to(BASE / ACTIVE, target_is_directory=True)


def main() -> int:
    build_demo()
    OUT.mkdir(parents=True, exist_ok=True)

    app = QApplication(["screenshot"])
    mod.apply_paths(GAME, BASE)

    mod.T.language = "en"
    window = mod.SwitcherWindow()
    window.resize(660, 480)
    window.show()
    app.processEvents()
    window.grab().save(str(OUT / "main-en.png"))

    window.set_language("de")
    window.select("03 Overhaul")
    app.processEvents()
    window.grab().save(str(OUT / "main-de.png"))

    mod.T.language = "en"
    dialog = mod.PathsDialog(GAME, BASE)
    dialog.resize(660, 300)
    dialog.show()
    app.processEvents()
    dialog.grab().save(str(OUT / "paths-en.png"))

    # first start: the mod folder does not exist yet
    empty = DEMO / "demo"
    (empty / "game").mkdir(parents=True, exist_ok=True)
    mod.apply_paths(empty / "game", empty / "7 Days")
    first = mod.SwitcherWindow()
    first.resize(660, 480)
    first.show()
    app.processEvents()
    first.grab().save(str(OUT / "firstrun-en.png"))
    first.set_language("de")
    app.processEvents()
    first.grab().save(str(OUT / "firstrun-de.png"))
    first.deleteLater()

    for image in sorted(OUT.glob("*.png")):
        print(f"{image} {image.stat().st_size} bytes")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    raise SystemExit(main())
