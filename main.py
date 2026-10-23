"""KLineDeck 入口。"""

from __future__ import annotations

import sys

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from klinedeck.theme import apply_theme
from klinedeck.window import MainWindow


def main() -> int:
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QCoreApplication.setOrganizationName("KLineDeck")
    QCoreApplication.setApplicationName("KLineDeck")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    apply_theme(app)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
