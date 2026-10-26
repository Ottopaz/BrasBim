# SPDX-License-Identifier: LGPL-3.0-or-later
"""Vistas salvas (spec/ui 25): o que mostrar (planta de um pavimento, corte/fachada ou
câmera do 3D) e como (escala, camadas, opções, recorte), para abrir de novo na janela e
para pôr nas pranchas. Sem Qt.

Operações: ``saved_view.create`` / ``.delete`` (data: estado completo) e
``saved_view.edit`` (before/after: campos alterados).

Vista salva = ``IfcAnnotation`` "VistaSalva" na edificação, sem representação, com o
estado em JSON no Pset ``BrasBim_VistaSalva``::

    {"name": "Térreo 1:50", "kind": "plan", "storey": "<GlobalId>", "view": None,
     "scale": 50, "layers": {"<camada>": [visível, bloqueada], ...},
     "options": {"detail": "simple", "show_above": True, ...},
     "crop": [x0, y0, x1, y1] | None, "camera": None, "pens": None}

``kind``: ``plan`` (``storey``), ``section`` (``view``: corte ou fachada) ou ``3d``
(``camera``: ``target``, ``distance``, ``yaw``, ``pitch``, ``aspect``). As camadas são uma
cópia do estado da hora de salvar (§2); ``None`` = como estiver a janela.
"""

from __future__ import annotations

import contextlib
import copy
import json

import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.util.element

from brasbim.core import display_layers, guid, props, storeys
from brasbim.core.document import Document, OpError, local_placement
from brasbim.core.ops import Transaction
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair

PSET = "BrasBim_VistaSalva"
OBJECT_TYPE = "VistaSalva"
KINDS = ("plan", "section", "3d")
KIND_LABEL = {"plan": "Planta", "section": "Corte/fachada", "3d": "3D"}
STATE_KEYS = ("name", "kind", "storey", "view", "scale", "layers", "options", "crop",
              "camera", "pens")
# Opções de desenho da planta guardadas na vista (§2) e o valor quando faltam.
PLAN_OPTIONS = {"detail": "simple", "show_above": True, "show_tags": True,
                "show_tag_size": False, "show_structure_tags": True,
                "show_object_tags": False, "show_space_numbers": False,
                "show_weights": True, "show_view_symbols": True}
CAMERA_KEYS = ("target", "distance", "yaw", "pitch", "aspect")
WIDTH_3D = 160.0  # mm: largura padrão da vista 3D no papel (§5)


def default_state() -> dict:
    return {"name": "", "kind": "plan", "storey": None, "view": None,
            "scale": storeys.DEFAULT_SCALE, "layers": None, "options": {}, "crop": None,
            "camera": None, "pens": None}


def is_saved_view(entity) -> bool:
    return (entity is not None and entity.is_a("IfcAnnotation")
            and entity.ObjectType == OBJECT_TYPE)


def all_saved_views(doc: Document) -> list:
    return sorted((e for e in doc.ifc.by_type("IfcAnnotation") if is_saved_view(e)),
                  key=lambda e: (read_state(e)["name"].lower(), e.GlobalId))


def read_state(entity) -> dict:
    values = ifcopenshell.util.element.get_pset(entity, PSET, should_inherit=False) or {}
    if "Parametros" not in values:
        raise OpError(f"vista salva {entity.GlobalId} sem os parâmetros do BrasBim")
    return {**default_state(), **json.loads(values["Parametros"])}


def options(state: dict) -> dict:
    """Opções da planta, com os valores padrão nas que faltam."""
    return {**PLAN_OPTIONS, **(state.get("options") or {})}


def source(state: dict) -> str | None:
    """GlobalId de que a vista depende (pavimento ou corte); ``None`` no 3D."""
    return {"plan": state.get("storey"), "section": state.get("view")}.get(state["kind"])


def suggest_name(doc: Document, kind: str, source_name: str = "",
                 scale: int | None = None) -> str:
    """"Térreo 1:50", "Corte A 1:50", "3D 1"… sem repetir um nome que já existe."""
    used = {read_state(v)["name"] for v in all_saved_views(doc)}
    if kind == "3d":
        n = 1
        while f"3D {n}" in used:
            n += 1
        return f"3D {n}"
    base = f"{source_name} 1:{scale}".strip()
    name, n = base, 2
    while name in used:
        name, n = f"{base} ({n})", n + 1
    return name


# --- desenho ---------------------------------------------------------------------------


@contextlib.contextmanager
def drawing(doc: Document, state: dict):
    """Camadas e escala da vista valendo enquanto se desenha (prancha, §5)."""
    with contextlib.ExitStack() as stack:
        if state.get("layers") is not None:
            stack.enter_context(display_layers.using(
                doc, display_layers.display_of(state["layers"])))
        if state["kind"] == "plan" and state.get("storey"):
            stack.enter_context(storeys.using_scale(state["storey"], state["scale"]))
        yield


def plan_of(doc: Document, state: dict):
    """Planta (``core.plan.Plan``) do pavimento da vista, com as opções dela; chamar
    dentro de ``drawing``."""
    from brasbim.core import plan

    storey = doc.find(state["storey"])
    if storey is None:
        return None
    opts = options(state)
    return plan.storey_plan(doc, storey, detail=opts["detail"],
                            show_above=opts["show_above"])


def size_3d(state: dict, width: float | None = None) -> tuple[float, float]:
    """Largura e altura (mm de papel) da imagem da vista 3D."""
    width = float(width or WIDTH_3D)
    aspect = float((state.get("camera") or {}).get("aspect") or 1.5)
    return width, width / max(aspect, 0.1)


# --- operações ---------------------------------------------------------------------------


def _validate(doc: Document, state: dict) -> None:
    if state["kind"] not in KINDS:
        raise OpError(f"tipo de vista salva inválido: {state['kind']!r}")
    if not (state["name"] or "").strip():
        raise OpError("a vista salva precisa de um nome")
    if state["kind"] == "plan" and not state.get("storey"):
        raise OpError("vista de planta sem pavimento")
    if state["kind"] == "section" and not state.get("view"):
        raise OpError("vista de corte sem o corte ou a fachada")
    if state["kind"] == "3d":
        camera = state.get("camera") or {}
        if set(CAMERA_KEYS) - set(camera):
            raise OpError("vista 3D sem a câmera completa")
    elif int(state["scale"]) not in storeys.SCALES:
        raise OpError(f"escala inválida: 1:{state['scale']}")
    crop = state.get("crop")
    if crop is not None and (len(crop) != 4 or crop[2] <= crop[0] or crop[3] <= crop[1]):
        raise OpError("recorte inválido")
    unknown = set(state.get("options") or {}) - set(PLAN_OPTIONS)
    if unknown:
        raise OpError(f"opções desconhecidas: {sorted(unknown)}")


def _write(doc: Document, entity, state: dict) -> None:
    _validate(doc, state)
    building = doc.building
    entity.ObjectType = OBJECT_TYPE
    entity.Name = state["name"]
    if ifcopenshell.util.element.get_container(entity) != building:
        rel = ifcopenshell.api.spatial.assign_container(doc.ifc, products=[entity],
                                                        relating_structure=building)
        guid.stamp(rel, building.GlobalId, "contains")
    if entity.ObjectPlacement is None:
        entity.ObjectPlacement = local_placement(doc.ifc, building.ObjectPlacement)
    props.write_pset(doc, entity, PSET, {"Parametros": doc.ifc.createIfcText(json.dumps(
        state, sort_keys=True, ensure_ascii=False))})


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    entity = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class="IfcAnnotation")
    entity.GlobalId = op.id
    entity.PredefinedType = "USERDEFINED"
    try:
        _write(doc, entity, {**default_state(), **copy.deepcopy(op.data)})
    except Exception:
        ifcopenshell.api.root.remove_product(doc.ifc, product=entity)
        raise
    return {op.id}


def _delete(doc: Document, op: Op) -> set[str]:
    ifcopenshell.api.root.remove_product(doc.ifc, product=doc.get(op.id, "IfcAnnotation"))
    return {op.id}


def _edit(doc: Document, op: Op) -> set[str]:
    entity = doc.get(op.id, "IfcAnnotation")
    state = read_state(entity)
    check_before(op, state)
    unknown = set(op.after or {}) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"saved_view.edit: campos desconhecidos {sorted(unknown)}")
    state.update(copy.deepcopy(op.after or {}))
    _write(doc, entity, state)
    return {op.id}


register_inverse_pair("saved_view.create", _create, "saved_view.delete", _delete)
register("saved_view.edit", _edit, invert_swap)


def dependents(doc: Document, gid: str) -> list:
    """Vistas salvas que dependem do pavimento ou do corte ``gid``."""
    return [v for v in all_saved_views(doc) if source(read_state(v)) == gid]


# --- comandos ----------------------------------------------------------------------------


def create_saved_view(doc: Document, name: str, kind: str, **fields) -> Transaction:
    unknown = set(fields) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    data = {**default_state(), **copy.deepcopy(fields), "name": name.strip(), "kind": kind}
    _validate(doc, data)
    key = source(data)
    if key is not None and doc.find(key) is None:
        raise OpError("o pavimento ou o corte da vista não existe")
    return Transaction("Salvar vista", [Op("saved_view.create", guid.new(), data=data)])


def edit_saved_view(doc: Document, entity, label: str = "Editar vista salva",
                    **changes) -> Transaction:
    entity = doc.get(entity if isinstance(entity, str) else entity.GlobalId, "IfcAnnotation")
    state = read_state(entity)
    unknown = set(changes) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    if "name" in changes:
        changes["name"] = (changes["name"] or "").strip()
    _validate(doc, {**state, **changes})
    changes = {k: v for k, v in changes.items() if v != state[k]}
    if not changes:
        return Transaction(label, [])
    return Transaction(label, [Op(
        "saved_view.edit", entity.GlobalId,
        before={k: copy.deepcopy(state[k]) for k in changes}, after=copy.deepcopy(changes))])


def delete_ops(doc: Document, entity) -> list[Op]:
    from brasbim.core.drawings import sheets

    return [*sheets.refs_removed_ops(doc, entity.GlobalId, cascade=False),
            Op("saved_view.delete", entity.GlobalId, data=read_state(entity))]


def delete_saved_view(doc: Document, entity) -> Transaction:
    """Exclui a vista e a tira das pranchas em que está (§4)."""
    entity = doc.get(entity if isinstance(entity, str) else entity.GlobalId, "IfcAnnotation")
    return Transaction("Excluir vista salva", delete_ops(doc, entity))
