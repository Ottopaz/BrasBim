# SPDX-License-Identifier: LGPL-3.0-or-later
"""Transações e histórico de desfazer/refazer."""

from __future__ import annotations

from dataclasses import dataclass, field

from brasbim.core.document import Document
from brasbim.core.ops.base import Op, apply_op, derive, invert_op


@dataclass
class Transaction:
    """Uma ação do usuário: lista ordenada de operações aplicadas juntas."""

    label: str
    ops: list[Op] = field(default_factory=list)

    def inverse(self) -> Transaction:
        return Transaction(self.label, [invert_op(op) for op in reversed(self.ops)])

    def to_dict(self) -> dict:
        return {"label": self.label, "ops": [op.to_dict() for op in self.ops]}

    @classmethod
    def from_dict(cls, d: dict) -> Transaction:
        return cls(d["label"], [Op.from_dict(o) for o in d["ops"]])


def run(doc: Document, tx: Transaction) -> None:
    """Aplica a transação inteira ou nada (desfaz o que já foi aplicado em caso de erro)."""
    applied: list[Op] = []
    dirty: set[str] = set()
    try:
        for op in tx.ops:
            dirty |= apply_op(doc, op)
            applied.append(op)
        derive(doc, dirty)
    except Exception:
        for op in reversed(applied):
            apply_op(doc, invert_op(op))
        derive(doc, dirty)
        raise


class History:
    """Pilhas de desfazer/refazer e diário de tudo o que foi aplicado.

    O diário (``journal``) inclui desfazer/refazer como transações comuns; reaplicá-lo
    em outro documento com os mesmos pavimentos reproduz o mesmo IFC.
    """

    def __init__(self, doc: Document):
        self.doc = doc
        self.undo_stack: list[Transaction] = []
        self.redo_stack: list[Transaction] = []
        self.journal: list[Transaction] = []

    def commit(self, tx: Transaction) -> None:
        run(self.doc, tx)
        self.undo_stack.append(tx)
        self.redo_stack.clear()
        self.journal.append(tx)

    def undo(self) -> Transaction | None:
        if not self.undo_stack:
            return None
        tx = self.undo_stack.pop()
        inverse = tx.inverse()
        run(self.doc, inverse)
        self.redo_stack.append(tx)
        self.journal.append(inverse)
        return tx

    def redo(self) -> Transaction | None:
        if not self.redo_stack:
            return None
        tx = self.redo_stack.pop()
        run(self.doc, tx)
        self.undo_stack.append(tx)
        self.journal.append(tx)
        return tx
