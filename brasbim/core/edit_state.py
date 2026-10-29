# SPDX-License-Identifier: LGPL-3.0-or-later
"""Estado de edição de um elemento (spec/ui 39 §5–§6): travar e ordem de desenho.

Gravado no Pset próprio ``BrasBim_Edicao`` da ocorrência: ``Travado`` (booleano, só
quando verdadeiro) e ``Ordem`` (inteiro, só fora da ordem padrão). Sem nenhuma das duas, o
Pset sai.

Operação: ``edit_state.set`` com ``before``/``after`` = {"locked": bool} e/ou
{"order": int | None}. A transação (``ops.history.run``) chama ``ensure_unlocked`` antes
de cada operação: a que mexe num elemento travado é recusada inteira, venha da interface,
do assistente ou da equipe. O que é derivado (junções, ambientes) não passa por operação
sobre o travado e continua valendo.
"""

from __future__ import annotations

import ifcopenshell.util.element

from brasbim.core import props
from brasbim.core.document import Document, OpError
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_check
from brasbim.core.ops.history import Transaction

PSET = "BrasBim_Edicao"
LOCKED = "Travado"
ORDER = "Ordem"
OP = "edit_state.set"
# Operações que não editam o elemento travado (a própria trava, a ordem de desenho).
_FREE = frozenset({OP})


def _read(element) -> dict:
    found = ifcopenshell.util.element.get_pset(element, PSET, should_inherit=False) or {}
    order = found.get(ORDER)
    return {"locked": bool(found.get(LOCKED)),
            "order": int(order) if order is not None else None}


def read(element) -> dict:
    """{"locked": bool, "order": int | None} do elemento."""
    return _read(element)


def _locked_map(doc: Document) -> set[str]:
    cached = getattr(doc, "locked_elements", None)
    if cached is None:
        cached = set()
        for rel in doc.ifc.by_type("IfcRelDefinesByProperties"):
            pset = rel.RelatingPropertyDefinition
            if not pset.is_a("IfcPropertySet") or pset.Name != PSET:
                continue
            if any(p.Name == LOCKED and p.NominalValue and p.NominalValue.wrappedValue
                   for p in pset.HasProperties or []):
                cached |= {o.GlobalId for o in rel.RelatedObjects}
        doc.locked_elements = cached
    return cached


def is_locked(doc: Document, element_or_id) -> bool:
    gid = element_or_id if isinstance(element_or_id, str) else element_or_id.GlobalId
    return gid in _locked_map(doc)


def locked_ids(doc: Document) -> set[str]:
    return set(_locked_map(doc))


def name_of(element) -> str:
    return element.Name or element.is_a()[3:]


def ensure_unlocked(doc: Document, gids) -> None:
    """``OpError("elemento travado: <nome>")`` se algum dos elementos estiver travado."""
    locked = _locked_map(doc)
    if not locked:
        return
    for gid in gids:
        if gid in locked:
            element = doc.find(gid)
            raise OpError(f"elemento travado: {name_of(element) if element else gid}")


def check_op(doc: Document, op: Op) -> None:
    """Chamado por ``run`` antes de aplicar cada operação."""
    if op.op not in _FREE:
        ensure_unlocked(doc, (op.id,))


def lockable(element) -> bool:
    return element is not None and element.is_a("IfcProduct") and not element.is_a(
        "IfcSpatialStructureElement")


# --- operação ---------------------------------------------------------------------------


def _set(doc: Document, op: Op) -> set[str]:
    element = doc.get(op.id)
    if not lockable(element):
        raise OpError(f"{op.id} não tem estado de edição")
    current = _read(element)
    check_before(op, current)
    state = {**current, **(op.after or {})}
    values = {}
    if state["locked"]:
        values[LOCKED] = True
    if state["order"] is not None:
        values[ORDER] = int(state["order"])
    if values:
        props.write_pset(doc, element, PSET, values)
    else:
        props.remove_pset(doc, element, PSET)
    locked = _locked_map(doc)
    (locked.add if state["locked"] else locked.discard)(op.id)
    # Só o estado de edição muda: nada a refazer na geometria.
    return set()


register(OP, _set, invert_swap)
register_check(check_op)


# --- comandos ---------------------------------------------------------------------------


def _ops(doc: Document, gids, key: str, value) -> list[Op]:
    out = []
    for gid in sorted(gids):
        element = doc.find(gid)
        if not lockable(element):
            continue
        current = _read(element)[key]
        if current != value:
            out.append(Op(OP, gid, before={key: current}, after={key: value}))
    return out


def lock(doc: Document, gids) -> Transaction:
    ops = _ops(doc, gids, "locked", True)
    if not ops:
        raise OpError("nada a travar")
    return Transaction("Travar", ops)


def unlock(doc: Document, gids) -> Transaction:
    ops = _ops(doc, gids, "locked", False)
    if not ops:
        raise OpError("nada a destravar")
    return Transaction("Destravar", ops)


def unlock_all(doc: Document) -> Transaction:
    ops = _ops(doc, _locked_map(doc), "locked", False)
    if not ops:
        raise OpError("nenhum elemento travado")
    return Transaction("Destravar tudo", ops)


# --- ordem de desenho (§6) --------------------------------------------------------------

# Ordem padrão por tipo de anotação: hachuras embaixo, depois linhas, depois textos e cotas.
DEFAULT_ORDER = {"hatch": 0, "figure": 0, "line": 100, "text": 200}


# Tipo de anotação (prefixo) → grupo da ordem padrão.
_ORDER_GROUP = {"hatch": "hatch", "text": "text", "label": "text", "dimension": "text",
                "angle_dim": "text", "radius_dim": "text", "level_mark": "text",
                "revision": "text"}


def order_group(prefix: str) -> str:
    return _ORDER_GROUP.get(prefix, "line")


def annotation_order(element) -> int | None:
    """Ordem efetiva de uma anotação da planta, ou ``None`` se não for anotação."""
    from brasbim.core.annotations import base

    kind = base.kind_of(element)
    return None if kind is None else order_of(element, order_group(kind.prefix))


def default_order(kind: str) -> int:
    return DEFAULT_ORDER.get(kind, 100)


def order_of(element, kind: str) -> int:
    order = _read(element)["order"]
    return default_order(kind) if order is None else order


def set_order(doc: Document, changes: dict, label: str) -> Transaction:
    """``changes`` = {GlobalId: ordem ou None}; uma transação."""
    ops = []
    for gid, value in sorted(changes.items()):
        element = doc.get(gid)
        current = _read(element)["order"]
        if current != value:
            ops.append(Op(OP, gid, before={"order": current}, after={"order": value}))
    if not ops:
        raise OpError("a ordem já é essa")
    return Transaction(label, ops)


def reorder(doc: Document, items: list[tuple[str, int]], gids, mode: str,
            overlaps=None) -> Transaction:
    """Nova ordem para ``gids`` entre as anotações ``items`` (``[(GlobalId, ordem)]``, todas
    as do pavimento, com a ordem efetiva).

    ``mode``: ``front`` (acima da maior), ``back`` (abaixo da menor), ``forward``/``backward``
    (troca com a anotação seguinte/anterior que se sobrepõe, ``overlaps(a, b)``) ou
    ``default`` (remove a propriedade).
    """
    gids = set(gids)
    labels = {"front": "Trazer para a frente", "back": "Mandar para trás",
              "forward": "Um passo à frente", "backward": "Um passo atrás",
              "default": "Ordem padrão"}
    if mode not in labels:
        raise OpError(f"ordem de desenho desconhecida: {mode!r}")
    if mode == "default":
        return set_order(doc, {g: None for g in gids}, labels[mode])
    order = dict(items)
    chosen = sorted((g for g in gids if g in order), key=lambda g: (order[g], g))
    if not chosen:
        raise OpError("nenhuma anotação escolhida")
    others = [(o, g) for g, o in items if g not in gids]
    changes: dict = {}
    if mode == "front":
        top = max([o for o, _ in others] + [order[g] for g in chosen])
        for i, g in enumerate(chosen, 1):
            changes[g] = top + i
    elif mode == "back":
        low = min([o for o, _ in others] + [order[g] for g in chosen])
        for i, g in enumerate(reversed(chosen), 1):
            changes[g] = low - i
    else:
        forward = mode == "forward"
        for g in (reversed(chosen) if forward else chosen):
            mine = changes.get(g, order[g])
            candidates = [(o, h) for o, h in others
                          if (o > mine if forward else o < mine)
                          or (o == mine and (h > g if forward else h < g))]
            if overlaps is not None:
                candidates = [(o, h) for o, h in candidates if overlaps(g, h)]
            if not candidates:
                continue
            o, h = min(candidates) if forward else max(candidates)
            # Troca as posições; com ordem igual, desempata por um passo.
            changes[g] = o + (1 if forward else -1) if o == mine else o
            if o != mine:
                changes[h] = mine
    if not changes:
        raise OpError("a ordem já é essa")
    return set_order(doc, changes, labels[mode])
