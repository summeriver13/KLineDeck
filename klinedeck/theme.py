"""配色与 Qt 样式表。"""

from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

BG = "#0f131a"
PANEL = "#11161e"
PANEL_ALT = "#151b25"
BORDER = "#232b38"
TEXT = "#dbe3ee"
MUTED = "#8b97a8"
FAINT = "#5d6878"
ACCENT = "#3b82f6"
UP = "#f0545a"
DOWN = "#22b573"
GRID = "#2a3444"

MA_COLORS = {5: "#f5c542", 10: "#4cc9f0", 20: "#b388ff", 60: "#ff8a65"}
BOLL_COLORS = {"UPPER": "#5aa9e6", "MID": "#c9d1d9", "LOWER": "#b388ff"}

QSS = """
QMainWindow { background: #0f131a; }
QWidget { color: #dbe3ee; font-family: "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", sans-serif; font-size: 13px; }
QFrame#sidebar { background: #11161e; border-right: 1px solid #1f2734; }
QFrame#header { background: #0f131a; border-bottom: 1px solid #1c2431; }
QToolBar { background: #121821; border-bottom: 1px solid #1f2734; spacing: 4px; padding: 5px 10px; }
QToolBar::separator { background: #232b38; width: 1px; margin: 6px 8px; }
QToolButton { color: #aab6c6; padding: 5px 8px; border-radius: 5px; }
QToolButton:hover { background: #1a2230; color: #ffffff; }
QToolButton:checked { background: #233048; color: #ffffff; }
QToolButton:pressed { background: #2a3a55; }
QToolButton#watch { color: #8b97a8; border: 1px solid #263040; border-radius: 5px; padding: 4px 9px; }
QToolButton#watch:hover { color: #f5c542; border-color: #5a4a1a; background: #1c1a12; }
QToolButton#watch[watched="true"] { color: #f5c542; border-color: #5a4a1a; background: #211d12; }
QLineEdit { background: #151b25; border: 1px solid #232b38; border-radius: 6px; padding: 8px 10px; selection-background-color: #2f6feb; }
QLineEdit:focus { border-color: #3b82f6; }
QListWidget { background: transparent; border: none; outline: 0; }
QListWidget::item { padding: 7px 8px; border-radius: 5px; }
QListWidget::item:hover { background: #182030; }
QListWidget::item:selected { background: #1f2d44; color: #ffffff; }
QLabel#brand { font-size: 22px; font-weight: 700; letter-spacing: 1px; }
QLabel#subtitle { color: #6f7b8c; font-size: 11px; letter-spacing: 1px; }
QLabel#section { color: #8b97a8; font-size: 11px; font-weight: 600; letter-spacing: 1px; }
QLabel#hint { color: #5d6878; font-size: 11px; }
QLabel#title { font-size: 20px; font-weight: 600; }
QLabel#code { color: #8b97a8; font-size: 12px; }
QLabel#price { font-size: 32px; font-weight: 700; }
QLabel#change { font-size: 14px; }
QFrame#infoPanel { background: #11161e; border: 1px solid #1c2431; border-radius: 6px; }
QLabel#info { color: #aab6c6; font-family: Consolas, "Cascadia Mono", monospace; font-size: 12px; background: transparent; border: none; }
QLabel#detail { color: #7d8798; font-family: Consolas, "Cascadia Mono", monospace; font-size: 11px; background: transparent; border: none; }
QComboBox { background: #151b25; border: 1px solid #232b38; border-radius: 5px; color: #aab6c6; padding: 4px 7px; min-width: 64px; }
QComboBox:hover { border-color: #2f3d52; }
QComboBox::drop-down { border: none; width: 16px; }
QComboBox QAbstractItemView { background: #151b25; border: 1px solid #2a3444; color: #dbe3ee; selection-background-color: #233048; outline: 0; }
QLabel#footer { color: #5d6878; font-size: 11px; }
QLabel#empty { color: #5d6878; font-size: 12px; border: 1px dashed #232b38; border-radius: 6px; padding: 20px; }
QSplitter::handle { background: #1a212c; }
QStatusBar { background: #0f131a; border-top: 1px solid #1c2431; color: #7d8798; }
QStatusBar::item { border: none; }
QProgressBar { background: #1a2230; border: none; border-radius: 3px; }
QProgressBar::chunk { background: #3b82f6; border-radius: 3px; }
QPushButton { background: #1a2230; border: 1px solid #263040; border-radius: 5px; padding: 4px 10px; }
QPushButton:hover { background: #223047; }
QPushButton:disabled { color: #5d6878; }
QScrollBar:vertical { background: transparent; width: 8px; }
QScrollBar::handle:vertical { background: #2a3444; border-radius: 4px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip { background: #1a2230; color: #dbe3ee; border: 1px solid #2a3444; padding: 4px 6px; }
"""


def apply_theme(app: QApplication) -> None:
    app.setStyleSheet(QSS)
    palette = app.palette()
    palette.setColor(palette.ColorRole.Window, QColor(BG))
    palette.setColor(palette.ColorRole.Base, QColor(PANEL))
    palette.setColor(palette.ColorRole.Text, QColor(TEXT))
    palette.setColor(palette.ColorRole.WindowText, QColor(TEXT))
    app.setPalette(palette)
