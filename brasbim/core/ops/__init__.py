# SPDX-License-Identifier: LGPL-3.0-or-later
"""Operações serializáveis (RF-NUC-02) e histórico de desfazer/refazer (RF-NUC-01)."""

from brasbim.core.ops.base import Op, apply_op, invert_op, register, register_inverse_pair
from brasbim.core.ops.history import History, Transaction

__all__ = [
    "History",
    "Op",
    "Transaction",
    "apply_op",
    "invert_op",
    "register",
    "register_inverse_pair",
]
