# SPDX-License-Identifier: LGPL-3.0-or-later
"""Regiões por camada e prioridade nas junções (``spec/ui/06-planta-por-camadas.md``
§2.3; UI52, UI53 no núcleo)."""

import pytest

from brasbim.core import clip, geom2d, layers
from brasbim.core.walls import commands as cmd
from brasbim.core.walls import rebuild
from brasbim.core.walls.wall import read_state


def _regions(model, walls):
    pieces = {}
    for w in walls:
        band = rebuild.band(model.doc, read_state(model.doc, w))
        seg = rebuild.profile(model.doc, w, band)
        pieces[w.GlobalId] = [[band.frame.to_global(p) for p in geom2d.polygon(seg)]]
    return layers.regions(model.doc, walls, pieces), pieces


def _walls(model, tx):
    return [model.doc.get(op.id) for op in tx.ops if op.op == "wall.create"]


def _inside(rings, p):
    return clip.area(clip.intersection(rings, [[(p[0] - 1e-4, p[1] - 1e-4),
                                                (p[0] + 1e-4, p[1] - 1e-4),
                                                (p[0] + 1e-4, p[1] + 1e-4),
                                                (p[0] - 1e-4, p[1] + 1e-4)]])) > 3e-8


def test_ui52_l_entre_alvenarias(model):
    # Face esquerda na referência: a parede fica à direita do caminho (y de -0,14 a 0).
    tx = model.commit(cmd.create_chain(model.doc, model.type14, model.terreo,
                                       [(0, 0), (4, 0), (4, -3)]))
    walls = _walls(model, tx)
    found, pieces = _regions(model, walls)
    total = sum(clip.area(p) for p in pieces.values())
    assert sum(clip.area(r.rings) for r in found) == pytest.approx(total)
    groups = layers.by_material(found)
    assert len(groups["Bloco cerâmico"]) == 1  # os blocos se encontram no canto
    assert len(groups["Reboco"]) == 2  # externo em L, contínuo; interno
    # Canto externo em (4, 0): uma faixa só dá a volta.
    outer = next(r for r in groups["Reboco"] if _inside([r], (3.99, -0.01)))
    assert _inside([outer], (3.0, -0.01)) and _inside([outer], (3.99, -1.0))
    # Canto interno em (3,86; −0,14): o reboco das duas para no bloco, cujo canto fica em
    # (3,885; −0,115).
    assert _inside(groups["Bloco cerâmico"], (3.9, -0.1))
    assert _inside(groups["Reboco"], (3.87, -0.13))


def _own(found):
    out = {}
    for r in found:
        out.setdefault((r.owner, r.material), []).extend(r.rings)
    return out


def _t(model):
    a = model.wall((0, 0), (6, 0), ref_line="axis")
    b = model.wall((3, -3), (3, 0), ref_line="axis")
    return a, b


def test_ui53_t_bloco_atravessa_o_reboco(model):
    a, b = _t(model)
    found, _ = _regions(model, [a, b])
    blocks = layers.by_material(found)["Bloco cerâmico"]
    assert len(blocks) == 1  # o bloco da que chega encosta no da contínua
    own = _own(found)
    assert _inside(own[(b.GlobalId, "Bloco cerâmico")], (3.0, -0.06))
    # Reboco da contínua interrompido no encontro.
    assert not _inside(own[(a.GlobalId, "Reboco")], (3.0, -0.06))


def test_ui53_prioridades_invertidas(model):
    a, b = _t(model)
    layers_ = [{"material": "Reboco", "thickness": 0.025, "priority": 90},
               {"material": "Bloco cerâmico", "thickness": 0.09, "priority": 80},
               {"material": "Reboco", "thickness": 0.025, "priority": 90}]
    model.commit(cmd.edit_wall_type(model.doc, model.type14, layers=layers_))
    found, _ = _regions(model, [a, b])
    assert len(layers.by_material(found)["Bloco cerâmico"]) == 2  # reboco contínuo separa
    own = _own(found)
    assert _inside(own[(a.GlobalId, "Reboco")], (3.0, -0.06))
