# SPDX-License-Identifier: LGPL-3.0-or-later
"""Transações e histórico de desfazer/refazer."""

from __future__ import annotations

from collections.abc import Callable
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

    def to_dict(self, copy_: bool = True) -> dict:
        return {"label": self.label, "ops": [op.to_dict(copy_) for op in self.ops]}

    @classmethod
    def from_dict(cls, d: dict) -> Transaction:
        return cls(d["label"], [Op.from_dict(o) for o in d["ops"]])


def run(doc: Document, tx: Transaction) -> set[str]:
    """Aplica a transação inteira ou nada (desfaz o que já foi aplicado em caso de erro).

    Devolve os GlobalIds criados, alterados ou excluídos, inclusive os recalculados
    (vizinhas de uma parede, portas de uma parede alterada).
    """
    applied: list[Op] = []
    dirty: set[str] = set()
    doc.changed.clear()
    try:
        for op in tx.ops:
            dirty |= apply_op(doc, op)
            applied.append(op)
        derive(doc, dirty)
    except Exception:
        for op in reversed(applied):
            apply_op(doc, invert_op(op))
        derive(doc, dirty)
        doc.changed.clear()
        raise
    changed = dirty | {op.id for op in tx.ops} | doc.changed
    doc.changed.clear()
    return changed


def combine(doc: Document, label: str, builders) -> Transaction:
    """Junta várias ações numa transação só (ex.: edição em lote).

    Cada ``builder`` (função sem argumentos que devolve uma ``Transaction``) é montado
    sobre o resultado dos anteriores, aplicados provisoriamente; no fim tudo é desfeito e
    o modelo volta ao estado inicial. Assim uma ação vê o que a anterior criou (ex.: a
    variante de mão de um tipo de porta) e não a cria de novo.
    """
    applied: list[Transaction] = []
    ops: list[Op] = []
    try:
        for build in builders:
            tx = build()
            run(doc, tx)
            applied.append(tx)
            ops += tx.ops
    finally:
        for tx in reversed(applied):
            run(doc, tx.inverse())
    return Transaction(label, ops)


class History:
    """Pilhas de desfazer/refazer e diário de tudo o que foi aplicado.

    O diário (``journal``) inclui desfazer/refazer como transações comuns; reaplicá-lo
    em outro documento com os mesmos pavimentos reproduz o mesmo IFC.

    ``listeners`` são chamados depois de cada transação aplicada, com o tipo
    (``commit``, ``undo``, ``redo``), a transação e os GlobalIds alterados (``run``).
    """

    def __init__(self, doc: Document):
        self.doc = doc
        self.undo_stack: list[Transaction] = []
        self.redo_stack: list[Transaction] = []
        self.journal: list[Transaction] = []
        self.listeners: list[Callable[[str, Transaction, set[str]], None]] = []

    def _notify(self, kind: str, tx: Transaction, changed: set[str]) -> None:
        for listener in list(self.listeners):
            listener(kind, tx, changed)

    def commit(self, tx: Transaction) -> None:
        changed = run(self.doc, tx)
        self.undo_stack.append(tx)
        self.redo_stack.clear()
        self.journal.append(tx)
        self._notify("commit", tx, changed)

    def squash(self, count: int, label: str) -> Transaction | None:
        """Junta as ``count`` últimas transações da pilha num passo só de desfazer (o
        pedido inteiro do assistente). O diário continua com cada uma."""
        if count < 2 or count > len(self.undo_stack):
            return None
        txs = self.undo_stack[-count:]
        del self.undo_stack[-count:]
        tx = Transaction(label, [op for t in txs for op in t.ops])
        self.undo_stack.append(tx)
        return tx

    def undo(self) -> Transaction | None:
        if not self.undo_stack:
            return None
        tx = self.undo_stack.pop()
        inverse = tx.inverse()
        changed = run(self.doc, inverse)
        self.redo_stack.append(tx)
        self.journal.append(inverse)
        self._notify("undo", tx, changed)
        return tx

    def redo(self) -> Transaction | None:
        if not self.redo_stack:
            return None
        tx = self.redo_stack.pop()
        changed = run(self.doc, tx)
        self.undo_stack.append(tx)
        self.journal.append(tx)
        self._notify("redo", tx, changed)
        return tx
