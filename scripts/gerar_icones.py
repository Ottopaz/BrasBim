# SPDX-License-Identifier: GPL-3.0-or-later
"""Gera os ícones próprios do BrasBim (spec/ui 03 §3): traço 1,5 em 24 × 24.

Uso, na raiz do repositório: python scripts/gerar_icones.py
"""
from pathlib import Path

HEAD = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.5" stroke-linecap="square" '
        'stroke-linejoin="miter">\n'
        '<!-- SPDX-License-Identifier: GPL-3.0-or-later. Ícone próprio do BrasBim. -->\n')

ICONS = {
    # cursor de seleção
    "select": '<path d="M6 3 V18 L9.6 14.6 L12.2 20.4 L14.4 19.4 L11.8 13.6 H16.6 Z"/>',
    # parede em planta: faixa com hachura
    "wall": '<rect x="2.75" y="8.75" width="18.5" height="6.5"/>'
            '<path d="M7 9 L5 15 M11 9 L9 15 M15 9 L13 15 M19 9 L17 15" stroke-width="1"/>',
    "wall_line": '<rect x="4.75" y="9.75" width="14.5" height="4.5"/>'
                 '<circle cx="3" cy="12" r="1.25" fill="currentColor"/>'
                 '<circle cx="21" cy="12" r="1.25" fill="currentColor"/>',
    "wall_arc": '<path d="M3.75 19 A8.25 8.25 0 0 1 20.25 19"/>'
                '<path d="M7.75 19 A4.25 4.25 0 0 1 16.25 19"/>'
                '<path d="M3.75 19 H7.75 M16.25 19 H20.25"/>',
    "wall_rect": '<rect x="3.75" y="4.75" width="16.5" height="14.5"/>'
                 '<rect x="7.25" y="8.25" width="9.5" height="7.5"/>',
    # porta em planta: trechos de parede, folha e arco de giro
    "door": '<path d="M2 19.25 H5.75 M18.25 19.25 H22"/>'
            '<path d="M5.75 19.25 V6.75"/>'
            '<path d="M5.75 6.75 A12.5 12.5 0 0 1 18.25 19.25" stroke-width="1" '
            'stroke-dasharray="2 1.5"/>',
    # janela em planta: trechos de parede, marco e dois caixilhos de correr
    "window": '<path d="M2 8.75 H5.75 V15.25 H2 M22 8.75 H18.25 V15.25 H22"/>'
              '<path d="M5.75 11 H13.5 M10.5 13 H18.25" stroke-width="1"/>',
    "undo": '<path d="M8.5 6.5 L4.5 10.5 L8.5 14.5"/>'
            '<path d="M4.5 10.5 H14.5 A4.75 4.75 0 0 1 14.5 20 H10"/>',
    "redo": '<path d="M15.5 6.5 L19.5 10.5 L15.5 14.5"/>'
            '<path d="M19.5 10.5 H9.5 A4.75 4.75 0 0 0 9.5 20 H14"/>',
    "move": '<path d="M12 3 V21 M3 12 H21"/>'
            '<path d="M9.5 5.5 L12 3 L14.5 5.5 M9.5 18.5 L12 21 L14.5 18.5"/>'
            '<path d="M5.5 9.5 L3 12 L5.5 14.5 M18.5 9.5 L21 12 L18.5 14.5"/>',
    "copy": '<rect x="3.75" y="8.75" width="11.5" height="11.5"/>'
            '<path d="M8.75 8.75 V3.75 H20.25 V15.25 H15.25"/>',
    "rotate": '<path d="M19.5 12 A7.5 7.5 0 1 1 15.75 5.5"/>'
              '<path d="M15.75 2 V5.75 H19.5"/>'
              '<circle cx="12" cy="12" r="1.25" fill="currentColor"/>',
    "split": '<rect x="2.75" y="9.25" width="7" height="5.5"/>'
             '<rect x="14.25" y="9.25" width="7" height="5.5"/>'
             '<path d="M12 4 V20" stroke-dasharray="2 2"/>',
    "delete": '<path d="M5.5 5.5 L18.5 18.5 M18.5 5.5 L5.5 18.5"/>',
    "flip_opening": '<path d="M3 12 H21" stroke-width="2.5"/>'
                    '<path d="M12 4 V9 M12 15 V20"/>'
                    '<path d="M9.5 6.5 L12 4 L14.5 6.5 M9.5 17.5 L12 20 L14.5 17.5"/>',
    "flip_hinges": '<path d="M4 16 H20"/>'
                   '<circle cx="4" cy="16" r="1.5" fill="currentColor"/>'
                   '<path d="M7 8 H17 M7 8 L9.5 5.5 M7 8 L9.5 10.5 M17 8 L14.5 5.5 '
                   'M17 8 L14.5 10.5"/>',
    "ref_left": '<rect x="3.75" y="7.75" width="16.5" height="8.5" stroke-width="1"/>'
                '<path d="M2 7.75 H22" stroke-width="2.5"/>',
    "ref_axis": '<rect x="3.75" y="7.75" width="16.5" height="8.5" stroke-width="1"/>'
                '<path d="M2 12 H22" stroke-width="2.5"/>',
    "ref_right": '<rect x="3.75" y="7.75" width="16.5" height="8.5" stroke-width="1"/>'
                 '<path d="M2 16.25 H22" stroke-width="2.5"/>',
    "hinge_left": '<path d="M5 19 V7"/><path d="M5 7 A12 12 0 0 1 17 19" stroke-width="1"/>'
                  '<circle cx="5" cy="19" r="1.75" fill="currentColor"/>',
    "hinge_right": '<path d="M19 19 V7"/><path d="M19 7 A12 12 0 0 0 7 19" stroke-width="1"/>'
                   '<circle cx="19" cy="19" r="1.75" fill="currentColor"/>',
    "mirror": '<path d="M12 2.5 V21.5" stroke-dasharray="2 2"/>'
              '<path d="M9.5 6 L3.5 18 H9.5 Z"/><path d="M14.5 6 L20.5 18 H14.5 Z"/>',
    "join": '<path d="M4 20.25 V3.75 H20.25 M8 20.25 V7.75 H20.25"/>'
            '<path d="M4 20.25 H8 M20.25 3.75 V7.75"/>',
    "unjoin": '<path d="M4 20.25 V9.5 H8 V20.25 Z"/><path d="M11.5 3.75 H20.25 V7.75 H11.5 Z"/>',
    "swap": '<path d="M2.5 9.75 H21.5 M2.5 14.25 H21.5"/>'
            '<path d="M9.75 2.5 V9.75 M14.25 2.5 V9.75 M9.75 14.25 V21.5 M14.25 14.25 V21.5" '
            'stroke-width="1"/>',
    "edit_type": '<path d="M4.5 19.5 L5.5 15.5 L15.5 5.5 L18.5 8.5 L8.5 18.5 Z"/>'
                 '<path d="M13.5 7.5 L16.5 10.5"/>',
}

out = Path("brasbim/ui/icons")
out.mkdir(exist_ok=True)
for name, body in ICONS.items():
    (out / f"{name}.svg").write_text(HEAD + body + "\n</svg>\n", encoding="utf-8")
print(len(ICONS), "ícones")
