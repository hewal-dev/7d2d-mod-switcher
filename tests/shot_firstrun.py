#!/usr/bin/env python3
"""Render the three first-run states for review (offscreen Qt).

Usage:  DEMO_ROOT=/home/user python3 tests/shot_firstrun.py /out
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["MODSWITCH_NO_ASK"] = "1"

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

DEMO = Path(os.environ["DEMO_ROOT"])
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else APP_DIR / "docs" / "screenshots")
GAME = DEMO / "Steam" / "steamapps" / "common" / "7 Days To Die"
BASE = DEMO / "7 Days"
CONFIG = DEMO / "config-firstrun.json"

os.environ["MODSWITCH_CONFIG"] = str(CONFIG)
os.environ["MODSWITCH_LANG"] = "de"

from PySide6.QtWidgets import QApplication  # noqa: E402

import mod_switcher as mod  # noqa: E402


def shot(app, name: str, game: Path, base: Path) -> None:
    mod.apply_paths(game, base)
    window = mod.SwitcherWindow()
    window.resize(660, 480)
    window.show()
    app.processEvents()
    window.grab().save(str(OUT / name))
    state = mod.setup_state()
    print(
        f"{name}: game={state['game']} base={state['base']} sets={state['sets']} "
        f"checklist={window.setup_frame.isVisibleTo(window)!r} "
        f"subtitle={window.subtitle.text()!r}"
    )
    window.deleteLater()
    app.processEvents()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    app = QApplication(["shot"])

    # A: nothing there at all
    shot(app, "firstrun-a-ohne-alles.png", DEMO / "Steam/steamapps/common/7 Days To Die", DEMO / "7 Days")

    # B: game installed, own mod folder missing (the usual case)
    GAME.mkdir(parents=True, exist_ok=True)
    shot(app, "firstrun-b-modordner-fehlt.png", GAME, BASE)

    # C: mod folder exists but is empty
    BASE.mkdir(parents=True, exist_ok=True)
    shot(app, "firstrun-c-modordner-leer.png", GAME, BASE)

    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    raise SystemExit(main())
