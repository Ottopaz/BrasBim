# SPDX-License-Identifier: GPL-3.0-or-later
"""Ponto de entrada do aplicativo.

Uso: ``brasbim [arquivo.ifc]`` ou ``python -m brasbim.ui.app [arquivo.ifc]``.
"""

import sys


def main() -> int:
    from pathlib import Path

    from PySide6.QtCore import QStandardPaths
    from PySide6.QtWidgets import QApplication

    from brasbim.ui import theme
    from brasbim.ui.main_window import MainWindow
    from brasbim.ui.session import Session, feedback_dir

    app = QApplication(sys.argv)
    app.setApplicationName("BrasBim")
    theme.apply(app)
    data = QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)
    recovery_dir = Path(data) / "recuperacao" if data else Path.home() / "BrasBim" / "recuperacao"
    session = Session(journal_dir=feedback_dir() / "diarios", recovery_dir=recovery_dir)
    window = MainWindow(session)
    window.install_excepthook()
    if len(sys.argv) > 1:
        session.open(sys.argv[1])
    window.show()
    window.offer_recovery()  # cópia de uma sessão que não fechou (spec/ui 21 §4)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
