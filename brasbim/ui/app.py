# SPDX-License-Identifier: GPL-3.0-or-later
"""Ponto de entrada do aplicativo.

Uso: ``brasbim [arquivo.ifc]`` ou ``python -m brasbim.ui.app [arquivo.ifc]``.
"""

import sys


def verify(folder=None) -> int:
    """Teste de fumaça do programa montado (spec/ui 49 §4): sem janela, cria um projeto
    com uma parede, exporta IFC 2x3 e GLB e confere. 0 se tudo deu certo."""
    import os
    import tempfile
    from pathlib import Path

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from brasbim.core import ifc_export, model_export
    from brasbim.core.walls import commands as wc
    from brasbim.ui import theme
    from brasbim.ui.main_window import MainWindow
    from brasbim.ui.session import Session

    # Com a aplicação já criada (os testes), o tema e as preferências são de quem a criou.
    own = QApplication.instance() is None
    app = QApplication.instance() or QApplication(sys.argv[:1])
    if own:
        theme.apply(app)
    app.setWindowIcon(theme.app_icon())  # confere a logo empacotada
    checks = {}
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(folder or tmp)
        if own:  # preferências num lugar à parte: não mexe nas do usuário (painéis, barras)
            from PySide6.QtCore import QSettings

            QSettings.setDefaultFormat(QSettings.IniFormat)
            QSettings.setPath(QSettings.IniFormat, QSettings.UserScope,
                              str(Path(tmp) / "prefs"))
        session = Session(journal_dir=out / "diarios")
        window = MainWindow(session)
        window.quiet_dialogs = True
        doc = session.doc
        wall_type = doc.ifc.by_type("IfcWallType")[0]
        checks["parede"] = session.run(lambda: wc.create_rectangle(
            doc, wall_type, session.storey, (0, 0), (4, 3)))
        checks["ifc 2x3"] = ifc_export.export(doc, str(out / "verificar.ifc")).elements >= 4
        checks["glb"] = model_export.export(doc, str(out / "verificar.glb")).elements >= 4
        checks["logo"] = not app.windowIcon().isNull()
        checks["ícones"] = not window.windowIcon().isNull() or bool(window.actions())
        session.modified = False  # projeto de teste: fechar sem perguntar se salva
        window.close()
        session.close()
    passed = all(checks.values())
    if sys.stdout is not None:  # o .exe sem console não tem saída
        failed = [k for k, v in checks.items() if not v]
        print("BrasBim: verificação ok" if passed else f"BrasBim: falhou {failed}")
    return 0 if passed else 1


def main() -> int:
    if "--verificar" in sys.argv[1:]:
        return verify()
    from pathlib import Path

    from PySide6.QtCore import QStandardPaths
    from PySide6.QtWidgets import QApplication

    from brasbim.ui import theme
    from brasbim.ui.main_window import MainWindow
    from brasbim.ui.session import Session, feedback_dir

    if sys.platform == "win32":  # barra de tarefas com o ícone do BrasBim, não o do Python
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("BrasBim.BrasBim")
    app = QApplication(sys.argv)
    app.setApplicationName("BrasBim")
    theme.apply(app)
    app.setWindowIcon(theme.app_icon())
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
