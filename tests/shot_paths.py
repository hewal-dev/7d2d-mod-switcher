"""Screenshots der Pfad-Einstellungen für die Sichtprüfung (offscreen)."""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication  # noqa: E402

import mod_switcher as ms  # noqa: E402

app = QApplication(["shot"])
window = ms.SwitcherWindow()
window.resize(640, 500)
window.show()
app.processEvents()
window.grab().save("/tmp/modswitch-pfade.png")

dialog = ms.PathsDialog(ms.GAME_DIR, ms.MOD_BASE)
dialog.resize(680, 340)
dialog.show()
app.processEvents()
dialog.grab().save("/tmp/modswitch-pfaddialog.png")
print("gültig, Speichern aktiv:", dialog.save_button.isEnabled())

dialog.game_edit.setText("/tmp/gibtsnicht")
app.processEvents()
dialog.grab().save("/tmp/modswitch-pfaddialog-fehler.png")
print("ungültig, Speichern aktiv:", dialog.save_button.isEnabled())
sys.stdout.flush()
os._exit(0)
