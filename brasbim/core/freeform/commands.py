# SPDX-License-Identifier: LGPL-3.0-or-later
"""Comandos da forma livre (``spec/elementos/forma-livre.md`` §4 e §5): cada um devolve a
transação, que quem chama aplica pelo histórico."""

from __future__ import annotations

import copy
import math

import numpy as np

from brasbim.core import guid
from brasbim.core.document import Document, OpError
from brasbim.core.freeform import elements, mesh, shapes
from brasbim.core.objects import commands as oc
from brasbim.core.ops import Op, Transaction

MIN_SIZE = 0.001  # m: medida mínima ao esticar


def _gid(x) -> str:
    return x if isinstance(x, str) else x.GlobalId


def _element(doc: Document, element):
    entity = doc.get(_gid(element))
    if not elements.is_freeform(entity):
        raise OpError(f"{entity.GlobalId} não é forma livre")
    return entity


def free_name(doc: Document, name: str) -> str:
    used = {(e.Name or "").casefold() for e in elements.all_freeforms(doc)}
    if name.casefold() not in used:
        return name
    n = 2
    while f"{name} ({n})".casefold() in used:
        n += 1
    return f"{name} ({n})"


def create(doc: Document, storey, parts: list, point=(0.0, 0.0), *, name: str | None = None,
           category: str = "proxy", object_type: str = "", angle: float = 0.0,
           elevation: float = 0.0, source: str = "", description: str = "",
           recipe: list | None = None, gid: str | None = None) -> Transaction:
    """Forma livre nova com a malha ``parts`` (simplificada antes por quem chama, se
    preciso)."""
    state = {**elements.default_state(),
             "name": free_name(doc, (name or "").strip() or elements.DEFAULT_NAME),
             "category": category, "object_type": object_type.strip(),
             "storey": _gid(storey), "point": [float(point[0]), float(point[1])],
             "elevation": float(elevation), "angle": float(angle),
             "parts": copy.deepcopy(parts), "source": source, "description": description,
             "recipe": copy.deepcopy(recipe)}
    elements.validate(state)
    if mesh.triangle_count(state["parts"]) > shapes.MAX_TRIANGLES:
        raise OpError(f"a malha tem {mesh.triangle_count(state['parts'])} triângulos: o "
                      f"limite é {shapes.MAX_TRIANGLES}")
    ops = oc.layer_ops(doc, category)
    ops.append(Op("freeform.create", gid or guid.new(), data=state))
    return Transaction(f"Criar forma livre {state['name']}", ops)


def from_recipe(doc: Document, storey, recipe: list, point=(0.0, 0.0), **options) -> Transaction:
    """Forma livre feita de formas (§4.1); a receita fica guardada para corrigir depois."""
    return create(doc, storey, shapes.build(recipe), point, recipe=recipe, **options)


def edit(doc: Document, element, **changes) -> Transaction:
    """Campos do estado. Mudar ``parts`` sem dar ``recipe`` apaga a receita (ela não
    descreve mais a malha)."""
    element = _element(doc, element)
    state = elements.read_state(doc, element)
    if "parts" in changes and "recipe" not in changes:
        changes = {**changes, "recipe": None}
    after = {}
    for key, value in changes.items():
        if key not in elements.STATE_KEYS:
            raise OpError(f"campo desconhecido: {key}")
        if value != state[key]:
            after[key] = copy.deepcopy(value)
    if not after:
        return Transaction("Editar forma livre", [])
    elements.validate({**state, **after})
    ops = oc.layer_ops(doc, after["category"]) if "category" in after else []
    ops.append(Op("freeform.edit", element.GlobalId,
                  before={k: copy.deepcopy(state[k]) for k in after}, after=after))
    return Transaction(f"Editar forma livre {state['name']}", ops)


def set_recipe(doc: Document, element, recipe: list) -> Transaction:
    """Refaz a malha a partir de uma receita nova (§4.1, ``edit_freeform``)."""
    return edit(doc, element, parts=shapes.build(recipe), recipe=recipe)


def resize(doc: Document, element, width: float | None = None, depth: float | None = None,
           height: float | None = None, proportional: bool = True) -> Transaction:
    """Estica a malha para a medida dada (§3). ``proportional``: as outras medidas
    acompanham a primeira que foi dada. O centro da base fica no lugar."""
    element = _element(doc, element)
    state = elements.read_state(doc, element)
    current = mesh.size(state["parts"])
    wanted = (width, depth, height)
    if all(w is None for w in wanted):
        return Transaction("Esticar forma livre", [])
    factors = []
    for now, new in zip(current, wanted, strict=True):
        if new is None:
            factors.append(None)
            continue
        if float(new) < MIN_SIZE:
            raise OpError("medida pequena demais")
        if now < 1e-9:
            raise OpError("a peça não tem medida nesse eixo para esticar")
        factors.append(float(new) / now)
    if proportional:
        first = next(f for f in factors if f is not None)
        factors = [first, first, first]
    else:
        factors = [1.0 if f is None else f for f in factors]
    b = mesh.bounds(state["parts"])
    anchor = np.array([(b[0] + b[1]) / 2, (b[2] + b[3]) / 2, b[4]])
    scale = np.array(factors)
    parts = mesh.transformed(state["parts"], scale=scale, offset=anchor - anchor * scale)
    return edit(doc, element, parts=parts)


def set_part_material(doc: Document, element, index: int, material: str | None,
                      name: str | None = None) -> Transaction:
    element = _element(doc, element)
    parts = elements.read_state(doc, element)["parts"]
    if not 0 <= index < len(parts):
        raise OpError("parte inexistente")
    parts[index] = {**parts[index], "material": (material or "").strip() or None,
                    "name": (name or parts[index]["name"]).strip() or parts[index]["name"]}
    state = elements.read_state(doc, element)
    return edit(doc, element, parts=parts, recipe=state["recipe"])


def delete_ops(doc: Document, element) -> list[Op]:
    element = _element(doc, element)
    return [Op("freeform.delete", element.GlobalId, data=elements.read_state(doc, element))]


# --- converter (§4.3) ---------------------------------------------------------------------


def _object_parts(doc: Document, element) -> tuple[list, dict]:
    """Malha de um objeto paramétrico no sistema local dele, por material, e o lugar."""
    from brasbim.core.objects import elements as objects
    from brasbim.core.objects import mesh as object_mesh
    from brasbim.core.objects import types as ot

    state = objects.read_state(doc, element)
    _, tstate, built = objects.resolve(doc, state)

    def resolver(name):
        t = ot.by_name(doc, name)
        return ot.read(t) if t is not None else None

    by_material: dict = {}
    for tri, material, _part in object_mesh.object_mesh(
            tstate["definition"], built.values, resolver, bool(state["mirror"])):
        by_material.setdefault(material or None, []).append(tri)
    parts = []
    for material, tris in by_material.items():
        vertices = np.asarray(tris, dtype=float).reshape(-1, 3)
        faces = np.arange(len(vertices)).reshape(-1, 3)
        parts.append({"name": material or "Corpo", "material": material,
                      "vertices": vertices.tolist(), "faces": faces.tolist()})
    place = {"point": list(state["point"]), "angle": float(state["angle"]),
             "elevation": float(built.values.get("elevacao", 0.0)),
             "storey": state["storey"], "name": element.Name or tstate["name"],
             "category": tstate["definition"]["category"]}
    return mesh.cleaned(parts), place


def _sources(doc: Document, gids) -> list[tuple[object, list, dict]]:
    from brasbim.core.objects import elements as objects

    found = []
    for g in dict.fromkeys(_gid(x) for x in gids):
        e = doc.get(g)
        if objects.is_part(e):
            e = objects.parent_of(e)
        if any(e is f[0] for f in found):
            continue
        if elements.is_freeform(e):
            state = elements.read_state(doc, e)
            found.append((e, state["parts"], {k: state[k] for k in (
                "point", "angle", "elevation", "storey", "name", "category")}))
        elif objects.is_object(e):
            if objects.read_state(doc, e)["host"] is not None:
                raise OpError("objeto preso à parede não vira forma livre: solte-o antes")
            found.append((e, *_object_parts(doc, e)))
        else:
            raise OpError(f"{e.Name or e.is_a()} não vira forma livre: só objetos e formas "
                          "livres")
    return found


def convert(doc: Document, gids, name: str | None = None) -> Transaction:
    """Objetos e formas livres selecionados viram **uma** forma livre, no lugar do
    primeiro; os originais são excluídos na mesma transação."""
    found = _sources(doc, gids)
    if not found:
        raise OpError("selecione objetos ou formas livres para converter")
    if len(found) == 1 and elements.is_freeform(found[0][0]):
        raise OpError("já é uma forma livre")
    base = found[0][2]
    if any(place["storey"] != base["storey"] for _, _, place in found):
        raise OpError("os elementos precisam estar no mesmo pavimento")
    a0 = math.radians(base["angle"])
    parts = []
    for _, source_parts, place in found:
        # do sistema local da origem para o da peça nova (o do primeiro elemento)
        a = math.radians(place["angle"] - base["angle"])
        c, s = math.cos(a), math.sin(a)
        dx, dy = place["point"][0] - base["point"][0], place["point"][1] - base["point"][1]
        offset = (dx * math.cos(a0) + dy * math.sin(a0), -dx * math.sin(a0) + dy * math.cos(a0),
                  place["elevation"] - base["elevation"])
        parts += mesh.transformed(source_parts, offset=offset,
                                  matrix=[[c, -s, 0], [s, c, 0], [0, 0, 1]])
    parts = mesh.merged(parts)
    count = mesh.triangle_count(parts)
    if count > shapes.MAX_TRIANGLES:
        parts = mesh.simplified(parts, shapes.MAX_TRIANGLES)
    tx = create(doc, base["storey"], parts, base["point"], name=name or base["name"],
                category=base["category"], angle=base["angle"], elevation=base["elevation"],
                source=f"convertido de {len(found)} elemento(s)")
    ops = []
    for element, _, _ in found:
        ops += (delete_ops(doc, element) if elements.is_freeform(element)
                else oc.delete_ops(doc, element))
    return Transaction("Converter em forma livre", ops + tx.ops)
