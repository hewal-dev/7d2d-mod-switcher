"""Shared look for the local image dialogs (dark theme, assets, small helpers)."""

from __future__ import annotations

from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "assets"
CHECK_SVG = (ASSETS / "check.svg").as_posix()
RADIO_OFF = (ASSETS / "radio-off.svg").as_posix()
RADIO_ON = (ASSETS / "radio-on.svg").as_posix()
ARROW_UP = (ASSETS / "arrow-up.svg").as_posix()
ARROW_DOWN = (ASSETS / "arrow-down.svg").as_posix()

QSS = """
QDialog { background: #131418; }
QLabel { color: #e9eaee; }
QLabel#title { font-size: 20px; font-weight: 600; color: #f7f8fa; }
QLabel#subtitle { color: #b8bdc6; font-size: 12px; }
QLabel#caption { color: #aab0b9; font-size: 11px; }
QLabel#result { color: #f7f8fa; font-size: 16px; font-weight: 600; }
QLabel#detail { color: #c2c7d0; font-size: 12px; }
QLabel#warn { color: #ff9d94; font-size: 12px; }
QLabel#preview { background: #0d0e11; border: 1px solid #2c303a; border-radius: 10px; }
QFrame#card { background: #1b1d22; border: 1px solid #2a2e37; border-radius: 12px; }
QFrame#card[aktiv="true"] { background: #1e2230; border: 1px solid #5b8cff; }
QFrame#divider { background: #2a2e37; max-height: 1px; border: none; }
QRadioButton { color: #e9eaee; font-size: 13px; font-weight: 600; spacing: 9px; }
QRadioButton::indicator { width: 16px; height: 16px; image: url(RADIO_OFF); }
QRadioButton::indicator:checked { image: url(RADIO_ON); }
QComboBox {
    background: #16181d; color: #f7f8fa; border: 1px solid #3a4050;
    border-radius: 8px; padding: 6px 10px; min-height: 22px;
}
QComboBox:focus { border: 1px solid #6c98ff; background: #1a1d24; }
QComboBox:disabled { color: #6d737d; border-color: #22252c; background: #121316; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow { image: url(ARROW_DOWN); width: 10px; height: 10px; }
QComboBox QAbstractItemView {
    background: #1b1d22; color: #e9eaee; selection-background-color: #2b3d64;
    border: 1px solid #2a2e37; padding: 4px;
}
QSpinBox {
    background: #16181d; color: #f7f8fa; border: 1px solid #3a4050;
    border-radius: 8px; padding: 7px 10px; min-height: 20px;
    selection-background-color: #4d7cff;
}
QSpinBox:focus { border: 1px solid #6c98ff; background: #1a1d24; }
QSpinBox::up-button, QSpinBox::down-button {
    width: 20px; background: #1d2129;
    border-left: 1px solid #30343d;
}
QSpinBox::up-button { subcontrol-position: top right; border-top-right-radius: 7px; }
QSpinBox::down-button { subcontrol-position: bottom right; border-bottom-right-radius: 7px; }
QSpinBox::up-button:hover, QSpinBox::down-button:hover { background: #262b35; }
QSpinBox::up-arrow { image: url(ARROW_UP); width: 10px; height: 10px; }
QSpinBox::down-arrow { image: url(ARROW_DOWN); width: 10px; height: 10px; }
QSpinBox::up-arrow:disabled, QSpinBox::down-arrow:disabled { image: none; }
QSpinBox:disabled { color: #6d737d; border-color: #22252c; background: #121316; }
QPushButton {
    background: #262932; color: #e9eaee; border: 1px solid #343a45;
    border-radius: 8px; padding: 8px 16px; min-width: 96px;
}
QPushButton:hover { background: #2e323c; }
QPushButton:disabled { color: #6d737d; border-color: #22252c; background: #14161a; }
QPushButton#preset { padding: 9px 0; font-size: 13px; min-width: 0; }
QPushButton#preset[aktiv="true"] {
    background: #2b3d64; border: 1px solid #5b8cff; color: #ffffff; font-weight: 600;
}
QPushButton#preset:disabled { color: #6d737d; border-color: #24262d; background: #17181c; }
QPushButton#primary {
    background: #4d7cff; border: 1px solid #4d7cff; color: #ffffff;
    font-weight: 600; padding: 9px 24px;
}
QPushButton#primary:hover { background: #5b8cff; }
QPushButton#primary:disabled { background: #262932; border-color: #262932; color: #6f7580; }
QCheckBox { color: #c2c7d0; font-size: 12px; spacing: 8px; }
QCheckBox::indicator {
    width: 16px; height: 16px; border-radius: 4px;
    border: 1px solid #454b57; background: #121317;
}
QCheckBox::indicator:checked {
    background: #4d7cff; border: 1px solid #4d7cff; image: url(CHECK_SVG);
}
QCheckBox:disabled { color: #6d737d; }
"""


def styled() -> str:
    """QSS with the asset placeholders resolved to absolute paths."""
    return (
        QSS.replace("CHECK_SVG", CHECK_SVG)
        .replace("RADIO_OFF", RADIO_OFF)
        .replace("RADIO_ON", RADIO_ON)
        .replace("ARROW_UP", ARROW_UP)
        .replace("ARROW_DOWN", ARROW_DOWN)
    )


def human_size(num_bytes: float) -> str:
    text = (
        f"{num_bytes / 1024:.0f} KB"
        if num_bytes < 1024 * 1024
        else f"{num_bytes / 1024 / 1024:.1f} MB"
    )
    return text.replace(".", ",")
