# SPDX-License-Identifier: GPL-3.0-or-later
"""Aparência (spec/ui 11): tema claro próprio, fonte Archivo, cores num só lugar."""

import re
from pathlib import Path

from PySide6.QtGui import QPalette

from brasbim.ui import theme

UI = Path(theme.__file__).parent


def test_ap01_tema_claro_e_fonte(app):
    old_palette, old_font, old_sheet = app.palette(), app.font(), app.styleSheet()
    try:
        theme.apply(app)
        assert app.font().family() == "Archivo"
        palette = app.palette()
        # claro mesmo com o sistema em modo escuro
        assert palette.color(QPalette.Window).lightness() > 200
        assert palette.color(QPalette.WindowText).lightness() < 60
        assert palette.color(QPalette.Highlight).name().upper() == theme.ACCENT.upper()
        assert theme.ACCENT in app.styleSheet()
    finally:
        app.setPalette(old_palette)
        app.setFont(old_font)
        app.setStyleSheet(old_sheet)


def test_ap02_cores_de_interface_so_no_tema():
    """Nenhuma cor de interface fixa fora de theme.py (as cores de materiais e da
    representação dos tipos são dados do modelo e ficam onde estão)."""
    allowed = {"theme.py", "plan_view.py", "materials_dialog.py", "types_dialog.py",
               "icons.py", "scene3d.py", "view3d.py", "handles3d.py"}
    found = []
    for path in UI.glob("*.py"):
        if path.name in allowed:
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"setStyleSheet\(.*#[0-9a-fA-F]{3,6}", line):
                found.append(f"{path.name}:{n}")
    assert not found, found


def test_ap03_fonte_distribuida_com_licenca():
    assert (theme.FONT_DIR / "Archivo.ttf").is_file()
    assert "SIL Open Font License" in (theme.FONT_DIR / "OFL.txt").read_text(encoding="utf-8")


def test_ap04_marca(app):
    """Logo e símbolo gerados (spec/ui 11 §8): ícone em vários tamanhos, .ico válido."""
    import struct

    sizes = {s.width() for s in theme.app_icon().availableSizes()}
    assert {16, 32, 48, 256} <= sizes
    assert theme.logo(150).width() == 150
    ico = (theme.LOGO_DIR / "brasbim.ico").read_bytes()
    reserved, kind, count = struct.unpack("<HHH", ico[:6])
    assert (reserved, kind) == (0, 1) and count >= 5
