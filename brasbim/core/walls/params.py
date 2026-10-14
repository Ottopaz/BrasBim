# SPDX-License-Identifier: LGPL-3.0-or-later
"""Parâmetros da parede (spec §3.1) e linha de referência (spec §3.2)."""

from __future__ import annotations

REF_LINES = ("axis", "left_face", "right_face")
TOP_MODES = ("storey", "fixed")
DEFAULT_FIXED_HEIGHT = 2.80

# Pset próprio com os vínculos que não têm atributo IFC (spec §3.1).
PSET = "BrasBim_Parede"
_PSET_REF = {"axis": "EIXO", "left_face": "FACE_ESQUERDA", "right_face": "FACE_DIREITA"}
_PSET_TOP = {"storey": "PAVIMENTO", "fixed": "ALTURA_FIXA"}

# Campos do estado de uma parede (``data`` de wall.create; chaves de wall.edit).
STATE_KEYS = (
    "name",
    "type",
    "storey",
    "path",
    "ref_line",
    "flip_layers",
    "base_offset",
    "top_mode",
    "top_storey",
    "top_offset",
    "fixed_height",
    "common",
)


def default_state() -> dict:
    return {
        "name": None,
        "ref_line": "left_face",
        "flip_layers": False,
        "base_offset": 0.0,
        "top_mode": "fixed",
        "top_storey": None,
        "top_offset": 0.0,
        "fixed_height": DEFAULT_FIXED_HEIGHT,
        "common": {},
    }


def layer_usage(ref_line: str, flip: bool, thickness: float) -> tuple[str, float]:
    """(DirectionSense, OffsetFromReferenceLine) conforme a tabela da spec §3.2."""
    t = thickness
    if not flip:
        offset = {"right_face": 0.0, "axis": -t / 2, "left_face": -t}[ref_line]
        return "POSITIVE", offset
    offset = {"right_face": t, "axis": t / 2, "left_face": 0.0}[ref_line]
    return "NEGATIVE", offset


def ref_line_from_usage(sense: str, offset: float, thickness: float) -> tuple[str, bool] | None:
    """Inverso de ``layer_usage``; None se a combinação não está na tabela."""
    for flip in (False, True):
        for ref in REF_LINES:
            s, o = layer_usage(ref, flip, thickness)
            if s == sense and abs(o - offset) < 1e-6:
                return ref, flip
    return None


def band(sense: str, offset: float, thickness: float) -> tuple[float, float]:
    """Faixa (ymin, ymax) ocupada pela parede no sistema local do caminho."""
    if sense == "POSITIVE":
        return offset, offset + thickness
    return offset - thickness, offset


def pset_values(state: dict) -> dict:
    return {
        "LinhaReferencia": _PSET_REF[state["ref_line"]],
        "CamadasInvertidas": bool(state["flip_layers"]),
        "PavimentoBase": state["storey"],
        "DeslocamentoBase": float(state["base_offset"]),
        "TipoTopo": _PSET_TOP[state["top_mode"]],
        "PavimentoTopo": state["top_storey"] if state["top_mode"] == "storey" else None,
        "DeslocamentoTopo": float(state["top_offset"]),
        "AlturaFixa": float(state["fixed_height"]),
    }


def state_from_pset(values: dict) -> dict:
    """Estado a partir do Pset. O pavimento base vem da contenção espacial, não daqui."""
    ref = {v: k for k, v in _PSET_REF.items()}
    top = {v: k for k, v in _PSET_TOP.items()}
    return {
        "ref_line": ref[values["LinhaReferencia"]],
        "flip_layers": bool(values["CamadasInvertidas"]),
        "base_offset": float(values["DeslocamentoBase"]),
        "top_mode": top[values["TipoTopo"]],
        "top_storey": values.get("PavimentoTopo"),
        "top_offset": float(values["DeslocamentoTopo"]),
        "fixed_height": float(values["AlturaFixa"]),
    }


def validate(state: dict) -> None:
    if state["ref_line"] not in REF_LINES:
        raise ValueError(f"linha de referência inválida: {state['ref_line']!r}")
    if state["top_mode"] not in TOP_MODES:
        raise ValueError(f"tipo de topo inválido: {state['top_mode']!r}")
    if state["top_mode"] == "storey" and not state["top_storey"]:
        raise ValueError("topo ligado a pavimento exige o pavimento do topo")
    if state["top_mode"] == "fixed" and state["fixed_height"] <= 0:
        raise ValueError("altura fixa deve ser maior que zero")
