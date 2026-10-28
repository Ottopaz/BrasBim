# SPDX-License-Identifier: LGPL-3.0-or-later
"""Projeto compartilhado na rede local (``spec/ui/33-projeto-compartilhado.md``).

O servidor guarda uma cópia do projeto, numera as transações e guarda as reservas; o
cliente liga o histórico ao servidor. Sem Qt: a interface chama ``Client.poll`` no
laço de eventos.
"""

from brasbim.core.collab.client import Client
from brasbim.core.collab.protocol import TCP_PORT, UDP_PORT, discover
from brasbim.core.collab.server import Server

__all__ = ["TCP_PORT", "UDP_PORT", "Client", "Server", "discover"]
