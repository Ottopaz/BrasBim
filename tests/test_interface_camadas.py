# SPDX-License-Identifier: GPL-3.0-or-later
"""Interface da planta por camadas (``spec/ui/06-planta-por-camadas.md``): Exibir >
Detalhe da planta, Exibir > Elementos acima do plano de corte, coluna Plano de corte."""

import ifcopenshell.util.element as ue
import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication
from test_interface import _rectangle

from brasbim.core import storeys
from brasbim.core.walls import commands as cmd


def test_detalhe_da_planta_no_menu(window, tmp_path):
    _rectangle(window)
    assert {r.fill["source"] for r in window.ctx.plan.regions} == {"type"}
    window.detail_actions["layers"].trigger()
    assert window.ctx.detail == "layers"
    assert {r.key for r in window.ctx.plan.regions} == {"Bloco cerâmico", "Reboco"}
    window.plan.repaint()
    window.plan.grab().save(str(tmp_path / "camadas.png"))
    window.detail_actions["simple"].trigger()
    assert {r.fill["source"] for r in window.ctx.plan.regions} == {"type"}


def test_acima_do_plano_no_menu(window):
    s = window.session
    s.run(lambda: cmd.create_wall(s.doc, window.toolbox.tools["wall"].options.type, s.storey,
                                  (0, 2), (4, 2), base_offset=1.8))
    gid = s.doc.ifc.by_type("IfcWall")[0].GlobalId
    assert [sh.role for sh in window.ctx.plan.shapes if sh.owner == gid] == ["wall_above"]
    window.above_action.trigger()
    assert not window.ctx.show_above
    assert [sh.role for sh in window.ctx.plan.shapes if sh.owner == gid] == []
    window.above_action.trigger()
    assert window.ctx.show_above


def test_coluna_plano_de_corte(window):
    s = window.session
    panel = window.storeys
    table = panel.table
    assert table.horizontalHeaderItem(2).text() == "Plano de corte"
    row = next(r for r in range(table.rowCount())
               if panel.storey_at(r).GlobalId == s.storey.GlobalId)
    assert table.item(row, 2).text() == "1,50"
    table.item(row, 2).setText("1,00")
    QApplication.processEvents()
    assert ue.get_pset(s.storey, storeys.PSET)["AlturaPlanoCorte"] == pytest.approx(1.0)
    row = next(r for r in range(table.rowCount())
               if panel.storey_at(r).GlobalId == s.storey.GlobalId)
    table.item(row, 2).setText("")  # vazio: volta ao padrão
    assert ue.get_pset(s.storey, storeys.PSET) is None
    window.undo()
    assert storeys.cut_height(s.storey) == pytest.approx(1.0)


def test_ui56_dialogo_de_materiais(window):
    from brasbim.core import materials
    from brasbim.ui.materials_dialog import MaterialsDialog

    s = window.session
    _rectangle(window)
    dialog = MaterialsDialog(s, window, select="Bloco cerâmico")
    assert dialog.current == "Bloco cerâmico"
    names = [dialog.list.item(i).text() for i in range(dialog.list.count())]
    assert "Bloco cerâmico" in names  # biblioteca: estilo gravado, sem "(padrão)"
    dialog.pattern.setCurrentIndex(dialog.pattern.findData("cross"))
    dialog.angle.setText("30")
    dialog.spacing.setText("0,04")
    dialog.set_color(dialog.color, "#aa5533")
    assert dialog.sample.pixmap() is not None
    assert dialog.apply()
    tx = s.history.undo_stack[-1]
    assert [op.op for op in tx.ops] == ["material.edit"]
    style = materials.style(s.doc, "Bloco cerâmico")
    assert style["color"] == "#AA5533" and style["cut"]["pattern"] == "cross"
    assert style["cut"]["angle"] == pytest.approx(30)
    assert window.scene.meshes  # 3D recarregado com a cor nova
    dialog.close()
    window.undo()
    assert materials.style(s.doc, "Bloco cerâmico")["color"] == \
        materials.LIBRARY["Bloco cerâmico"]["color"]
