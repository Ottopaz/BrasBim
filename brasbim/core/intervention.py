# SPDX-License-Identifier: LGPL-3.0-or-later
"""Situação de cada elemento no projeto legal (``spec/ui/31-projeto-legal.md`` §2–§3),
sem Qt.

- A situação fica no Pset próprio ``BrasBim_Intervencao`` (``Situacao``), que vale para
  todo elemento e anotação. Sem o Pset, a situação vem do ``Status`` do Pset comum (IFC de
  outra origem) ou é *A construir*.
- O ``Status`` do ``Pset_<Classe>Common`` é escrito junto quando a classe tem esse Pset
  no esquema (para outros programas lerem): "a regularizar" e "a transformar" viram
  ``EXISTING``. Ambientes e anotações ficam só com o Pset próprio.
- Operação ``situation.set`` (before/after ``{"situation": código | None}``, mais o
  ``status`` anterior no ``before`` de quem já existia): ``None`` apaga o Pset; sem
  ``status``, grava-se o da situação.
- ``Document.element_situations`` lembra a situação de cada elemento já visto, inclusive
  dos excluídos: desfazer a exclusão devolve a situação (derivação ``sync``), como as
  camadas (spec/ui 18).
- **Vista por situação** (§3): ``Document.situation_view`` (``project``, ``before``,
  ``after``, ``plain``) diz o que some e o que é pintado; ``hidden_ids`` entra nas
  ocultas das camadas (``display_layers.hidden_ids``).
"""

from __future__ import annotations

import contextlib

import ifcopenshell.api.pset
import ifcopenshell.util.element

from brasbim.core import display_layers, props
from brasbim.core.document import Document, OpError
from brasbim.core.ops.base import Op, invert_swap, register, register_derive

PSET = "BrasBim_Intervencao"
PROPERTY = "Situacao"
DEFAULT = "A_CONSTRUIR"
# (código, rótulo, Status do IFC 4.3)
SITUATIONS = (
    ("A_CONSTRUIR", "A construir", "NEW"),
    ("EXISTENTE", "Existente (manter)", "EXISTING"),
    ("A_DEMOLIR", "A demolir", "DEMOLISH"),
    ("A_REGULARIZAR", "A regularizar", "EXISTING"),
    ("A_TRANSFORMAR", "A transformar (adequar)", "EXISTING"),
    ("TEMPORARIO", "Temporário", "TEMPORARY"),
)
CODES = tuple(code for code, _, _ in SITUATIONS)
LABEL = {code: label for code, label, _ in SITUATIONS}
STATUS = {code: status for code, _, status in SITUATIONS}
FROM_STATUS = {"NEW": "A_CONSTRUIR", "EXISTING": "EXISTENTE", "DEMOLISH": "A_DEMOLIR",
               "TEMPORARY": "TEMPORARIO"}

# Filtro de vista (§3): modo → situações que aparecem (None = todas).
VIEWS = (("project", "Projeto"), ("before", "Antes da obra"),
         ("after", "Depois da obra"), ("plain", "Sem cores"))
VIEW_LABEL = dict(VIEWS)
DEFAULT_VIEW = "project"
SHOWN = {"project": None, "plain": None,
         "before": frozenset({"EXISTENTE", "A_DEMOLIR", "A_REGULARIZAR", "A_TRANSFORMAR"}),
         "after": frozenset(set(CODES) - {"A_DEMOLIR"})}
# Cores do perfil Genérico (§4), para quem não tem o documento à mão; as que valem vêm do
# perfil municipal do projeto (``municipal.mark``). Temporário: sem cor.
GENERIC_COLORS = {"A_CONSTRUIR": "#D62828", "EXISTENTE": "#000000",
                  "A_DEMOLIR": "#E0A800", "A_REGULARIZAR": "#1F5FBF",
                  "A_TRANSFORMAR": "#2E9E44"}


def check_code(code: str) -> str:
    if code not in CODES:
        raise OpError(f"situação desconhecida: {code!r}")
    return code


# --- elemento → situação ----------------------------------------------------------------


def situable(element) -> bool:
    """Tem situação: os mesmos que ficam numa camada (elementos, ambientes e anotações;
    não pranchas, tabelas nem vistas salvas), respondendo pelo dono."""
    return display_layers.layerable(element)


# Classes cujo ``Pset_<Classe>Common`` tem ``Status`` no esquema IFC 4.3 (conferido no
# ``ifcopenshell.util.pset`` em 2026‑10‑27), entre as que o BrasBim cria. Objetos ficam
# de fora: o Pset comum deles é o do tipo (``Pset_*TypeCommon``).
STATUS_PSETS = {cls: f"Pset_{cls[3:]}Common" for cls in (
    "IfcWall", "IfcDoor", "IfcWindow", "IfcSlab", "IfcColumn", "IfcBeam", "IfcRoof",
    "IfcStair", "IfcRailing", "IfcCovering", "IfcBuildingElementProxy")}


def common_pset(element) -> str | None:
    """``Pset_<Classe>Common`` com ``Status``, ou None (ambientes, anotações…)."""
    return STATUS_PSETS.get(element.is_a())


def _own(element) -> str | None:
    values = ifcopenshell.util.element.get_pset(element, PSET, should_inherit=False) or {}
    return values.get(PROPERTY)


def status_of(element) -> str | None:
    """``Status`` do Pset comum do próprio elemento (o primeiro valor), ou None."""
    name = common_pset(element)
    if name is None:
        return None
    values = ifcopenshell.util.element.get_pset(element, name, should_inherit=False) or {}
    status = values.get("Status")
    if isinstance(status, (list, tuple)):
        status = status[0] if status else None
    return status


def _read(element) -> str | None:
    """Situação gravada (Pset próprio ou, sem ele, o ``Status`` comum); None = padrão."""
    own = _own(element)
    if own in CODES:
        return own
    found = FROM_STATUS.get(status_of(element))
    return None if found in (None, DEFAULT) else found


def _map(doc: Document) -> dict[str, str | None]:
    """``Document.element_situations``, montado do IFC na primeira consulta: só os
    elementos com situação diferente da padrão (ou já tocados)."""
    if doc.element_situations is None:
        found: dict[str, str | None] = {}
        for element in doc.ifc.by_type("IfcProduct"):
            if situable(element):
                value = _read(element)
                if value is not None:
                    found[element.GlobalId] = value
        doc.element_situations = found
    return doc.element_situations


def situation_of(doc: Document, element) -> str:
    """Código da situação do elemento (o dono responde pelas peças)."""
    element = display_layers.owner(element)
    if element is None:
        return DEFAULT
    found = _map(doc).get(element.GlobalId)
    return found or DEFAULT


# --- gravação ------------------------------------------------------------------------


def _targets(element) -> list:
    """O elemento e, na cobertura, as águas (``Pset_SlabCommon``)."""
    if element.is_a("IfcRoof"):
        from brasbim.core.structure import roofs

        return [element, *roofs.parts_of(element)]
    return [element]


def _write_status(doc: Document, element, status: str | None) -> None:
    for target in _targets(element):
        name = common_pset(target)
        if name is None:
            continue
        current = ifcopenshell.util.element.get_pset(target, name, should_inherit=False)
        if status is None:
            if current and "Status" in current:
                ifcopenshell.api.pset.edit_pset(
                    doc.ifc, pset=doc.ifc.by_id(current["id"]), properties={"Status": []})
                if len([k for k in current if k != "id"]) == 1:
                    props.remove_pset(doc, target, name)
            continue
        pset = props.ensure_pset(doc, target, name)
        ifcopenshell.api.pset.edit_pset(doc.ifc, pset=pset, properties={"Status": [status]})


def _write(doc: Document, element, code: str | None, status=...) -> None:
    """Grava a situação (``None`` apaga o Pset). ``status``: o ``Status`` comum a gravar;
    sem ele, o da situação (e nada quando ``code`` é None)."""
    if code is None:
        props.remove_pset(doc, element, PSET)
    else:
        props.write_pset(doc, element, PSET, {PROPERTY: code})
    if status is ...:
        if code is None:
            return
        status = STATUS[code]
    _write_status(doc, element, status)


def _set(doc: Document, op: Op) -> set[str]:
    element = doc.get(op.id)
    if not situable(element) or display_layers.owner(element) is not element:
        raise OpError(f"{op.id} não tem situação própria")
    expected = (op.before or {}).get("situation")
    current = _own(element)
    if current != expected:
        raise OpError(f"situation.set {op.id}: situação é {current!r}, esperado {expected!r}")
    after = op.after or {}
    code = after.get("situation")
    if code is not None:
        check_code(code)
    _write(doc, element, code, after.get("status", ...))
    _map(doc)[op.id] = code
    return {op.id}


register("situation.set", _set, invert_swap)


def sync(doc: Document, dirty: set[str]) -> None:
    """Derivação: elemento refeito sem a situação (desfazer a exclusão, corpo refeito que
    regrava o Pset comum) volta a ter a que tinha."""
    if doc.element_situations is None:
        return
    mapping = doc.element_situations
    for gid in sorted(set(dirty) | doc.changed):
        code = mapping.get(gid)
        if code is None:
            continue
        element = doc.find(gid)
        if element is None or not situable(element):
            continue
        if _read(element) != code:
            _write(doc, element, code)
        elif common_pset(element) and status_of(element) is None:
            _write_status(doc, element, STATUS[code])


register_derive(sync, last=True)


# --- comandos ------------------------------------------------------------------------


def _op(doc: Document, element, code: str) -> Op:
    """``situation.set`` de um elemento que já existe: o ``before`` guarda o ``Status``
    comum, para o desfazer voltar exatamente ao que era."""
    return Op("situation.set", element.GlobalId,
              before={"situation": _own(element), "status": status_of(element)},
              after={"situation": code})


def set_situation(doc: Document, gids, code: str):
    """Muda a situação dos elementos (o dono responde pelas peças): uma transação."""
    from brasbim.core.ops import Transaction

    check_code(code)
    ops, seen = [], set()
    for gid in gids:
        element = display_layers.owner(doc.get(gid))
        if element is None or element.GlobalId in seen or not situable(element):
            continue
        seen.add(element.GlobalId)
        if situation_of(doc, element) != code:
            ops.append(_op(doc, element, code))
    return Transaction(f"Situação: {LABEL[code]}", ops)


def _created_op(gid: str, code: str) -> Op:
    """``situation.set`` de um elemento que a transação cria: o desfazer apaga o elemento
    logo depois, então o ``before`` não precisa do ``Status``."""
    return Op("situation.set", gid, before={"situation": None}, after={"situation": code})


def inherit(doc: Document, tx, sources):
    """Acrescenta a ``tx`` (cópia, espelho com cópia, dividir) a situação do original
    em cada elemento novo (§2: copiar herda a situação)."""
    from brasbim.core.ops import Transaction

    ops = [_created_op(gid, code)
           for _, gid, code in display_layers.copies(
               doc, tx, sources, lambda e: situation_of(doc, e))
           if code != DEFAULT]
    return Transaction(tx.label, tx.ops + ops) if ops else tx


def stamp_created(doc: Document, tx, code: str):
    """Situação dos novos elementos (opção da ferramenta, §2): acrescenta a ``tx`` a
    situação de cada elemento criado que ainda não a recebeu."""
    from brasbim.core.ops import Transaction

    if code == DEFAULT:
        return tx
    check_code(code)
    done = {op.id for op in tx.ops if op.op == "situation.set"}
    ops = [_created_op(gid, code)
           for _, gid, origin in display_layers.created(tx, doc)
           if origin is None and gid not in done]
    return Transaction(tx.label, tx.ops + ops) if ops else tx


# --- vista por situação (§3) ----------------------------------------------------------


def hidden_ids(doc: Document) -> set[str]:
    """GlobalIds que o filtro de situação da vista tira (as águas junto com a cobertura)."""
    shown = SHOWN.get(doc.situation_view)
    if shown is None:
        return set()
    mapping = _map(doc)
    out = set()
    for element in doc.ifc.by_type("IfcProduct"):
        if not situable(element) or display_layers.owner(element) is not element:
            continue
        if (mapping.get(element.GlobalId) or DEFAULT) in shown:
            continue
        out.add(element.GlobalId)
        if element.is_a("IfcRoof"):
            from brasbim.core.structure import roofs

            out |= {p.GlobalId for p in roofs.parts_of(element)}
    return out


def marks(doc: Document) -> dict[str, tuple[str, dict]]:
    """GlobalId → (cor, hachura) da situação pelo perfil municipal (§4, §13), na vista
    *Projeto*. Projeto sem nenhuma situação além de *A construir* (obra nova) não é
    pintado (§3). Situação sem cor no perfil fica de fora."""
    from brasbim.core import municipal

    if doc.situation_view != "project":
        return {}
    mapping = _map(doc)
    present = {gid for gid, code in mapping.items()
               if code not in (None, DEFAULT) and doc.find(gid) is not None}
    if not present:
        return {}
    profile = municipal.current(doc)
    by_code = {code: municipal.mark(profile, code) for code in CODES}
    out = {}
    for element in doc.ifc.by_type("IfcProduct"):
        if not situable(element) or display_layers.owner(element) is not element:
            continue
        color, hatch = by_code[mapping.get(element.GlobalId) or DEFAULT]
        if color:
            out[element.GlobalId] = (color, hatch)
    return out


def colors(doc: Document) -> dict[str, str]:
    """GlobalId → cor da situação na vista *Projeto* (ver ``marks``)."""
    return {gid: color for gid, (color, _) in marks(doc).items()}


def present(doc: Document) -> list[str]:
    """Situações que aparecem no modelo (para a legenda, §6), na ordem de ``SITUATIONS``."""
    found = {situation_of(doc, e) for e in doc.ifc.by_type("IfcProduct")
             if situable(e) and display_layers.owner(e) is e}
    return [code for code in CODES if code in found]


@contextlib.contextmanager
def using(doc: Document, view: str | None):
    """Desenha com outro filtro de situação (vista salva, §3); ``None`` = o da janela."""
    previous = doc.situation_view
    if view is not None:
        doc.situation_view = view
    try:
        yield
    finally:
        doc.situation_view = previous
