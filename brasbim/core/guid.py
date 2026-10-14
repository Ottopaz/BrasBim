# SPDX-License-Identifier: LGPL-3.0-or-later
"""GlobalIds do IFC.

Entidades criadas por uma operação recebem o GlobalId registrado na operação.
Entidades derivadas (Psets, quantidades, relações) recebem um GlobalId determinístico,
calculado a partir do dono e do papel, para que refazer ou reaplicar operações em
outra máquina produza o mesmo IFC.
"""

import uuid

import ifcopenshell.guid

_NAMESPACE = uuid.UUID("6f1d3c2a-8b4e-5a7f-9c0d-b5a5b1b0a001")


def new() -> str:
    return ifcopenshell.guid.new()


def derived(owner: str, role: str) -> str:
    return ifcopenshell.guid.compress(uuid.uuid5(_NAMESPACE, f"{owner}/{role}").hex)


def stamp(entity, owner: str, role: str) -> None:
    """Atribui a ``entity`` o GlobalId derivado de ``owner`` e ``role``."""
    if entity is not None:
        entity.GlobalId = derived(owner, role)
