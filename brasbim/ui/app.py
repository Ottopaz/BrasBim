# SPDX-License-Identifier: GPL-3.0-or-later
"""Ponto de entrada do aplicativo.

Uso: ``brasbim [arquivo.ifc]`` ou ``python -m brasbim.ui.app [arquivo.ifc]``.
"""

import sys


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from brasbim.ui.main_window import MainWindow
    from brasbim.ui.session import Session, feedback_dir

    app = QApplication(sys.argv)
    app.setApplicationName("BrasBim")
    session = Session(journal_dir=feedback_dir() / "diarios")
    window = MainWindow(session)
    window.install_excepthook()
    if len(sys.argv) > 1:
        session.open(sys.argv[1])
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
