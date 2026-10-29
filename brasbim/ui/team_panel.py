# SPDX-License-Identifier: GPL-3.0-or-later
"""Painel Equipe e diálogos do projeto compartilhado (``spec/ui/33-projeto-compartilhado.md``
§3–§4): pessoas conectadas, pedidos de liberação e eventos; compartilhar e entrar."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from brasbim.core.collab import protocol


def _dot(color: str, size: int = 12) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(color))
    return QIcon(pixmap)


class TeamPanel(QWidget):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        layout.addWidget(QLabel("Pessoas"))
        self.users = QListWidget()
        self.users.setMaximumHeight(120)
        layout.addWidget(self.users)
        self.requests_box = QFrame()
        self.requests_layout = QVBoxLayout(self.requests_box)
        self.requests_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.requests_box)
        self.release_button = QPushButton("Liberar minhas reservas")
        self.release_button.clicked.connect(lambda: self.session.release())
        layout.addWidget(self.release_button)
        layout.addWidget(QLabel("Eventos"))
        self.events = QListWidget()
        self.events.setWordWrap(True)
        layout.addWidget(self.events, 1)
        session.listeners.append(self._on_session)
        self.refresh()

    def _on_session(self, event: str) -> None:
        if event in ("team", "document"):
            self.refresh()

    def refresh(self) -> None:
        s = self.session
        client = s.collab if s.shared else None
        self.users.clear()
        self.events.clear()
        while self.requests_layout.count():
            item = self.requests_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self.release_button.setEnabled(client is not None and bool(client.mine()))
        if client is None:
            self.status.setText("Projeto não compartilhado. Use Equipe > Compartilhar este "
                                "projeto na rede ou Entrar num projeto da rede")
        else:
            role = "compartilhado por você" if s.server is not None \
                else f"de {client.host}"
            self.status.setText(f"<b>{client.project}</b> · {role}")
            counts: dict[str, int] = {}
            for uid in client.reservations.values():
                counts[uid] = counts.get(uid, 0) + 1
            for uid, user in client.users.items():
                you = " (você)" if uid == client.me else ""
                n = counts.get(uid, 0)
                text = f"{user['name']}{you} · {n} reserva{'s' if n != 1 else ''}"
                self.users.addItem(QListWidgetItem(_dot(user["color"]), text))
        for request in list(s.requests):
            self.requests_layout.addWidget(self._request_row(request))
        for text in reversed(s.team_events):
            self.events.addItem(text)

    def _request_row(self, request: dict) -> QWidget:
        row = QFrame()
        row.setFrameShape(QFrame.StyledPanel)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(6, 4, 6, 4)
        label = QLabel(f"{request['name']} pede {len(request['ids'])} elemento(s)")
        label.setWordWrap(True)
        layout.addWidget(label, 1)
        grant = QPushButton("Liberar")
        grant.clicked.connect(lambda: self.session.answer_request(request, True))
        deny = QPushButton("Recusar")
        deny.clicked.connect(lambda: self.session.answer_request(request, False))
        layout.addWidget(grant)
        layout.addWidget(deny)
        return row


def parse_address(text: str) -> tuple[str, int]:
    """``nome``, ``nome:porta``, ``192.168.0.10`` ou ``192.168.0.10:47815``."""
    text = text.strip()
    host, sep, port = text.rpartition(":")
    if sep and port.isdigit() and host:
        return host, int(port)
    return text, protocol.TCP_PORT


class JoinDialog(QDialog):
    """Equipe > Entrar num projeto da rede… (§4). ``discover``: troca a busca (testes)."""

    def __init__(self, name: str, parent=None, discover=protocol.discover):
        super().__init__(parent)
        self.setWindowTitle("Entrar num projeto da rede")
        self._discover = discover
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name = QLineEdit(name)
        form.addRow("Seu nome", self.name)
        layout.addLayout(form)
        layout.addWidget(QLabel("Projetos achados na rede"))
        self.found = QListWidget()
        self.found.itemSelectionChanged.connect(self._picked)
        self.found.itemDoubleClicked.connect(lambda _: self.accept())
        layout.addWidget(self.found)
        search = QPushButton("Procurar de novo")
        search.clicked.connect(self.search)
        layout.addWidget(search, 0, Qt.AlignLeft)
        form2 = QFormLayout()
        self.address = QLineEdit()
        self.address.setPlaceholderText("nome-do-computador ou 192.168.0.10")
        form2.addRow("Endereço", self.address)
        layout.addLayout(form2)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Entrar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(420, 360)

    def search(self) -> None:
        self.found.clear()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            results = self._discover()
        finally:
            QApplication.restoreOverrideCursor()
        for r in results:
            item = QListWidgetItem(f"{r['project']} · {r['host']} ({r['address']})")
            item.setData(Qt.UserRole, f"{r['address']}:{r['port']}")
            self.found.addItem(item)
        if not results:
            item = QListWidgetItem("Nenhum projeto achado. Digite o endereço que aparece "
                                   "no computador que compartilha.")
            item.setFlags(Qt.NoItemFlags)
            self.found.addItem(item)
        elif len(results) == 1:
            self.found.setCurrentRow(0)

    def _picked(self) -> None:
        item = self.found.currentItem()
        if item is not None and item.data(Qt.UserRole):
            self.address.setText(item.data(Qt.UserRole))

    def result_value(self) -> tuple[str, int, str]:
        host, port = parse_address(self.address.text())
        return host, port, self.name.text().strip() or "Sem nome"
