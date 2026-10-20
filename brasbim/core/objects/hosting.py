# SPDX-License-Identifier: LGPL-3.0-or-later
"""Objetos presos à parede (``spec/elementos/objeto-parametrico.md`` §6.3)."""

from __future__ import annotations

from brasbim.core.document import Document, OpError


def place(doc: Document, state: dict, built) -> dict:
    """Estado com ``point`` e ``angle`` calculados pela parede."""
    raise OpError("objeto preso à parede ainda não suportado")


def sync(doc: Document, element, state: dict, built) -> None:
    """Relação com a parede e o vão."""


def release(doc: Document, element) -> None:
    """Desfaz a relação com a parede e apaga o vão."""


def hosted_by(doc: Document, wall) -> list:
    """Objetos presos à parede."""
    return []


def slid(doc: Document, state: dict, vector) -> dict:
    """Hospedagem depois de mover o objeto sozinho: desliza ao longo da parede."""
    raise OpError("objeto preso à parede ainda não suportado")


def copied_ops(doc: Document, tx, found, vector) -> list:
    return []
