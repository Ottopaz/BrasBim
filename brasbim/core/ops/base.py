# SPDX-License-Identifier: LGPL-3.0-or-later
"""Registro de operações.

Uma operação é um registro com ``op`` (nome), ``id`` (GlobalId do objeto afetado) e
dados em unidades SI: ``data`` (estado completo, para criar/excluir) ou ``before`` e
``after`` (só os campos alterados, para editar). Toda operação é invertível sozinha.

Efeitos derivados (corpo, recortes, quantidades) não são registrados: o handler devolve
os GlobalIds "sujos" e quem aplica recalcula (ver ``derive``).
"""

from __future__ import annotations

import copy
import importlib
from collections.abc import Callable
from dataclasses import dataclass

from brasbim.core.document import Document, OpError


@dataclass
class Op:
    op: str
    id: str
    data: dict | None = None
    before: dict | None = None
    after: dict | None = None

    def to_dict(self, copy_: bool = True) -> dict:
        """``copy_=False``: sem cópia, para quem só vai serializar (o diário)."""
        d = {"op": self.op, "id": self.id}
        for key in ("data", "before", "after"):
            value = getattr(self, key)
            if value is not None:
                d[key] = copy.deepcopy(value) if copy_ else value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Op:
        return cls(
            op=d["op"],
            id=d["id"],
            data=copy.deepcopy(d.get("data")),
            before=copy.deepcopy(d.get("before")),
            after=copy.deepcopy(d.get("after")),
        )


ApplyFn = Callable[[Document, Op], set[str]]
InvertFn = Callable[[Op], Op]
DeriveFn = Callable[[Document, set[str]], None]

_APPLY: dict[str, ApplyFn] = {}
_INVERT: dict[str, InvertFn] = {}
_DERIVE: list[DeriveFn] = []
_DERIVE_LAST: list[DeriveFn] = []  # depois de todos os corpos refeitos (camadas)
_CHECK: list[Callable[[Document, Op], None]] = []  # antes de cada operação (travados)

# Módulos que registram handlers; importados sob demanda para evitar ciclos.
HANDLER_MODULES = (
    "brasbim.core.storeys",
    "brasbim.core.walls.types",
    "brasbim.core.materials",
    "brasbim.core.walls.wall",
    "brasbim.core.walls.connections",
    "brasbim.core.walls.openings",
    "brasbim.core.fillings.door_types",
    "brasbim.core.fillings.window_types",
    "brasbim.core.fillings.doors",
    "brasbim.core.fillings.rebuild",
    "brasbim.core.profile_defs",
    "brasbim.core.structure.types",
    "brasbim.core.structure.columns",
    "brasbim.core.structure.beams",
    "brasbim.core.structure.slabs",
    "brasbim.core.structure.slab_openings",
    "brasbim.core.structure.rebuild",
    "brasbim.core.structure.roofs",
    "brasbim.core.structure.skylights",
    "brasbim.core.structure.railings",
    "brasbim.core.structure.stairs",
    "brasbim.core.terrain",
    "brasbim.core.annotations.spaces",
    "brasbim.core.annotations.drafting",
    "brasbim.core.annotations.dimensions",
    "brasbim.core.annotations.drawing2d",
    "brasbim.core.annotations.reference",
    "brasbim.core.annotations.rebuild",
    "brasbim.core.drawings.views",
    "brasbim.core.grids",
    "brasbim.core.drawings.sheets",
    "brasbim.core.quantities.tables",
    "brasbim.core.quantities.legal_areas",
    "brasbim.core.objects.types",
    "brasbim.core.objects.elements",
    "brasbim.core.objects.rebuild",
    "brasbim.core.intervention",
    "brasbim.core.display_layers",
    "brasbim.core.edit_state",
)
_loaded = False


def _ensure_loaded() -> None:
    global _loaded
    if not _loaded:
        _loaded = True
        for name in HANDLER_MODULES:
            importlib.import_module(name)


def register(name: str, apply: ApplyFn, invert: InvertFn) -> None:
    _APPLY[name] = apply
    _INVERT[name] = invert


def register_inverse_pair(create: str, apply_create: ApplyFn, delete: str, apply_delete: ApplyFn):
    """Registra um par criar/excluir cujo inverso troca só o nome da operação."""
    register(create, apply_create, lambda op: Op(delete, op.id, data=copy.deepcopy(op.data)))
    register(delete, apply_delete, lambda op: Op(create, op.id, data=copy.deepcopy(op.data)))


def invert_swap(op: Op) -> Op:
    """Inverso de uma edição: troca ``before`` e ``after``."""
    return Op(op.op, op.id, data=copy.deepcopy(op.data), before=copy.deepcopy(op.after),
              after=copy.deepcopy(op.before))


def same_value(a, b, tol: float = 1e-6) -> bool:
    """Comparação tolerante de valores de operação (números, listas, dicionários)."""
    if isinstance(a, bool) or isinstance(b, bool) or a is None or b is None:
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= tol
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(same_value(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same_value(a[k], b[k], tol) for k in a)
    return a == b


def check_before(op: Op, current: dict) -> None:
    """Rejeita a edição se o estado atual não for o ``before`` registrado (conflito)."""
    for key, value in (op.before or {}).items():
        if not same_value(current.get(key), value):
            raise OpError(f"{op.op} {op.id}: '{key}' é {current.get(key)!r}, esperado {value!r}")


def register_derive(fn: DeriveFn, last: bool = False) -> None:
    (_DERIVE_LAST if last else _DERIVE).append(fn)


def register_check(fn) -> None:
    """``fn(doc, op)`` recusa a operação com ``OpError`` antes de aplicá-la (só nas
    transações; o desfazer de uma transação que falhou não passa por aqui)."""
    _CHECK.append(fn)


def check_op(doc: Document, op: Op) -> None:
    _ensure_loaded()
    for fn in _CHECK:
        fn(doc, op)


def apply_op(doc: Document, op: Op) -> set[str]:
    _ensure_loaded()
    try:
        fn = _APPLY[op.op]
    except KeyError:
        raise OpError(f"operação desconhecida: {op.op!r}") from None
    return fn(doc, op)


def invert_op(op: Op) -> Op:
    _ensure_loaded()
    return _INVERT[op.op](op)


def derive(doc: Document, dirty: set[str]) -> None:
    _ensure_loaded()
    for fn in (*_DERIVE, *_DERIVE_LAST):
        fn(doc, dirty)
