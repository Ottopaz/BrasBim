# SPDX-License-Identifier: GPL-3.0-or-later
"""Ponto de entrada do aplicativo."""

import sys

from brasbim import __version__


def main() -> int:
    from PySide6.QtWidgets import QApplication, QLabel, QMainWindow

    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle(f"BrasBim {__version__}")
    window.setCentralWidget(QLabel("BrasBim: em construção."))
    window.resize(1024, 768)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
