"""Screenshots von Pfad-Dialog und Symlink-Rückfrage (offscreen)."""

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# a sandbox where Mods is a real folder, so both dialog buttons make sense
tmp = Path(tempfile.mkdtemp(prefix="modswitch-shot-"))
game = tmp / "7 Days To Die"
base = tmp / "Meine Mods"
(game / "Mods").mkdir(parents=True)
(game / "Mods" / "BeispielMod").mkdir()
for name in ("Vanilla", "Hardcore"):
    (base / name).mkdir(parents=True)

os.environ["MODSWITCH_GAME_DIR"] = str(game)
os.environ["MODSWITCH_MOD_BASE"] = str(base)
os.environ["MODSWITCH_CONFIG"] = str(tmp / "config.json")
os.environ["MODSWITCH_NO_ASK"] = "1"  # no blocking popup while taking the shots

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

import mod_switcher as ms  # noqa: E402

app = QApplication(["shot"])

dialog = ms.PathsDialog(ms.GAME_DIR, ms.MOD_BASE)
dialog.resize(700, 380)
dialog.show()
app.processEvents()
dialog.grab().save("/tmp/dialog-pfade.png")
print("Dialog: Anlegen aktiv =", dialog.create_link_button.isEnabled(),
      "| Entfernen aktiv =", dialog.remove_link_button.isEnabled())

window = ms.SwitcherWindow()
window.resize(640, 470)
window.show()
app.processEvents()
window.grab().save("/tmp/fenster-mit-ordner.png")

box = QMessageBox()
box.setWindowTitle("Symlink für Mods anlegen?")
box.setIcon(QMessageBox.Question)
box.setText(
    "Symlink für Mods anlegen?\nKann jederzeit in der App rückgängig gemacht werden."
)
box.setInformativeText(
    "Der vorhandene Ordner bleibt erhalten und wird vorher als "
    "„Mods-Original-<Datum>“ gesichert."
)
box.addButton("Ja", QMessageBox.AcceptRole)
box.addButton("Nein", QMessageBox.RejectRole)
box.show()
app.processEvents()
box.grab().save("/tmp/popup-symlink.png")

sys.stdout.flush()
os._exit(0)
