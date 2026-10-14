# SPDX-License-Identifier: LGPL-3.0-or-later
"""Parâmetros das esquadrias (``spec/elementos/porta.md`` §2, §3 e §6.1).

Só cálculos e tabelas, sem IFC: operações de porta, folhas padrão de cada operação,
Psets próprios e a posição do marco na espessura da parede.
"""

from __future__ import annotations

OPENS_TO = ("left", "right")
ALIGNS = ("left_face", "axis", "right_face")

# Psets próprios (porta §3.4).
PSET = "BrasBim_Esquadria"
TYPE_PSET = "BrasBim_EsquadriaTipo"
_PSET_ALIGN = {"left_face": "FACE_ESQUERDA", "axis": "EIXO", "right_face": "FACE_DIREITA"}

DOOR_PREDEFINED_TYPES = ("DOOR",)

# Operações oferecidas no MVP (porta §2.1): operação → [(PanelOperation, PanelPosition)].
_SWING, _ACT, _SLIDE, _FOLD = "SWINGING", "DOUBLE_ACTING", "SLIDING", "FOLDING"
DOOR_OPERATIONS = {
    "SINGLE_SWING_LEFT": [(_SWING, "MIDDLE")],
    "SINGLE_SWING_RIGHT": [(_SWING, "MIDDLE")],
    "DOUBLE_DOOR_SINGLE_SWING": [(_SWING, "LEFT"), (_SWING, "RIGHT")],
    "SWING_FIXED_LEFT": [(_SWING, "LEFT"), ("FIXEDPANEL", "RIGHT")],
    "SWING_FIXED_RIGHT": [("FIXEDPANEL", "LEFT"), (_SWING, "RIGHT")],
    "DOUBLE_SWING_LEFT": [(_ACT, "MIDDLE")],
    "DOUBLE_SWING_RIGHT": [(_ACT, "MIDDLE")],
    "DOUBLE_DOOR_DOUBLE_SWING": [(_ACT, "LEFT"), (_ACT, "RIGHT")],
    "SLIDING_TO_LEFT": [(_SLIDE, "MIDDLE")],
    "SLIDING_TO_RIGHT": [(_SLIDE, "MIDDLE")],
    "DOUBLE_DOOR_SLIDING": [(_SLIDE, "LEFT"), (_SLIDE, "RIGHT")],
    "FOLDING_TO_LEFT": [(_FOLD, "MIDDLE")],
    "FOLDING_TO_RIGHT": [(_FOLD, "MIDDLE")],
    "DOUBLE_DOOR_FOLDING": [(_FOLD, "LEFT"), (_FOLD, "RIGHT")],
    "ROLLINGUP": [("ROLLINGUP", "MIDDLE")],
    "NOTDEFINED": [],
}
PANEL_POSITIONS = ("LEFT", "MIDDLE", "RIGHT")

# Padrões do tipo de porta (porta §3.2, CG a revisar).
DEFAULT_LINING = {
    "thickness": 0.03,
    "depth": None,  # vazio = acompanha a espessura da parede
    "casing_thickness": 0.05,
    "casing_depth": 0.01,
    "threshold_thickness": None,
}
DEFAULT_PANEL_DEPTH = 0.035
DEFAULT_DOOR_SIZE = {"width": 0.86, "height": 2.13, "base": 0.0}


def default_panels(operation_type: str, depth: float = DEFAULT_PANEL_DEPTH) -> list[dict]:
    """Folhas de mesma largura, conforme a operação."""
    layout = DOOR_OPERATIONS[operation_type]
    return [{"operation": op, "position": pos, "width": 1 / len(layout), "depth": depth}
            for op, pos in layout]


def align_to_pset(align: str) -> str:
    return _PSET_ALIGN[align]


def align_from_pset(value: str) -> str:
    return {v: k for k, v in _PSET_ALIGN.items()}[value]


def lining_band(align: str, offset: float, depth: float, ymin: float, ymax: float):
    """Faixa ``(a, a + depth)`` do marco no y da parede (porta §6.1, passo 1)."""
    if align == "left_face":
        a = ymax - offset - depth
    elif align == "axis":
        a = (ymin + ymax - depth) / 2 + offset
    elif align == "right_face":
        a = ymin + offset
    else:
        raise ValueError(f"alinhamento inválido: {align!r}")
    return a, a + depth
