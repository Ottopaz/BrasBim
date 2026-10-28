# SPDX-License-Identifier: GPL-3.0-or-later
"""Projeto > Perfil municipal… (``spec/ui/31-projeto-legal.md`` §4 e §13): escolhe um
perfil pronto ou edita a cópia do projeto (cores e hachuras por situação, escalas, planta,
notas e PDF), mostrando a fonte. Trabalha numa cópia; OK grava numa transação."""

from __future__ import annotations

import copy

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from brasbim.core import intervention, municipal, storeys
from brasbim.ui.pens_dialog import swatch

HATCHES = [("Sem hachura", "none"), ("Cheia", "solid"), ("Linhas", "lines"),
           ("Cruzada", "cross")]
ANGLES = [("45°", 45.0), ("135°", 135.0), ("0°", 0.0), ("90°", 90.0)]
SCALES = sorted(set(storeys.SCALES) | {100, 200, 250})
PROJECT = "__projeto__"


class MunicipalDialog(QDialog):
    def __init__(self, doc, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Perfil municipal")
        self.resize(600, 600)
        self.builtin = municipal.builtin()
        self.saved = municipal.read(doc)
        self.profile = copy.deepcopy(self.saved or self.builtin[0])
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel("Perfil"))
        self.choice = QComboBox()
        if self.saved is not None:
            self.choice.addItem(f"Do projeto: {self.saved['nome']}", PROJECT)
        for p in self.builtin:
            self.choice.addItem(p["nome"], p["id"])
        self.choice.currentIndexChanged.connect(self._chosen)
        top.addWidget(self.choice, 1)
        layout.addLayout(top)
        self.source = QLabel()
        self.source.setWordWrap(True)
        self.source.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.source)
        self.tabs = QTabWidget()
        self.color_grid = QTableWidget(0, 4)
        self.color_grid.setHorizontalHeaderLabels(["Situação", "Cor", "Hachura em preto",
                                                   "Ângulo"])
        self.color_grid.verticalHeader().hide()
        header = self.color_grid.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        self.color_grid.setSelectionMode(QAbstractItemView.NoSelection)
        self._build_colors()
        self.tabs.addTab(self.color_grid, "Cores e hachuras")
        page = QWidget()
        form = QFormLayout(page)
        self.scales = {}
        for key, label in municipal.SCALE_KEYS:
            combo = QComboBox()
            for value in SCALES:
                combo.addItem(f"1:{value}", value)
            combo.currentIndexChanged.connect(
                lambda i, k=key, c=combo: self.profile["escalas"].__setitem__(k, c.itemData(i)))
            form.addRow(label, combo)
            self.scales[key] = combo
        self.plan = QComboBox()
        for value, text in municipal.PLANS:
            self.plan.addItem(text, value)
        self.plan.currentIndexChanged.connect(
            lambda i: self.profile.__setitem__("planta", self.plan.itemData(i)))
        form.addRow("Planta", self.plan)
        self.pdf_size = QDoubleSpinBox()
        self.pdf_size.setRange(0.0, 1000.0)
        self.pdf_size.setDecimals(1)
        self.pdf_size.setSuffix(" MB")
        self.pdf_size.setSpecialValueText("sem limite")
        self.pdf_size.valueChanged.connect(
            lambda v: self.profile["pdf"].__setitem__("max_mb", v or None))
        form.addRow("PDF até", self.pdf_size)
        self.stamp = QCheckBox("Deixar espaço para o carimbo de aprovação na última prancha")
        self.stamp.toggled.connect(
            lambda v: self.profile["pdf"].__setitem__("carimbo_ultima_prancha", bool(v)))
        form.addRow("", self.stamp)
        self.tabs.addTab(page, "Escalas e entrega")
        page = QWidget()
        box = QVBoxLayout(page)
        box.addWidget(QLabel("Notas obrigatórias (uma por linha)"))
        self.notes = QPlainTextEdit()
        self.notes.textChanged.connect(self._notes_changed)
        box.addWidget(self.notes, 1)
        box.addWidget(QLabel("Campos do selo"))
        self.seal = QLabel()
        self.seal.setWordWrap(True)
        box.addWidget(self.seal)
        self.tabs.addTab(page, "Notas e selo")
        layout.addWidget(self.tabs, 1)
        self.apply_scales = QCheckBox("Aplicar as escalas do perfil às plantas, cortes e "
                                      "fachadas do projeto")
        self.apply_scales.setChecked(True)
        layout.addWidget(self.apply_scales)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._fill()

    def _build_colors(self) -> None:
        """Uma linha por situação; ``_fill`` só troca os valores."""
        self.color_grid.setRowCount(len(intervention.CODES))
        for row, code in enumerate(intervention.CODES):
            self.color_grid.setCellWidget(row, 0, QLabel(intervention.LABEL[code]))
            color = QPushButton()
            color.clicked.connect(lambda _=False, c=code: self.choose_color(c))
            self.color_grid.setCellWidget(row, 1, color)
            for column, options, field_ in ((2, HATCHES, "hachura"), (3, ANGLES, "angulo")):
                combo = QComboBox()
                for label, value in options:
                    combo.addItem(label, value)
                combo.currentIndexChanged.connect(
                    lambda i, c=code, f=field_, w=combo: self.set_mark(c, **{f: w.itemData(i)}))
                self.color_grid.setCellWidget(row, column, combo)

    # --- perfil escolhido ----------------------------------------------------------------

    def choose(self, profile_id: str) -> None:
        """Troca a cópia de trabalho por um perfil pronto (ou pela do projeto)."""
        self.choice.setCurrentIndex(max(0, self.choice.findData(profile_id)))

    def _chosen(self, index: int) -> None:
        key = self.choice.itemData(index)
        found = self.saved if key == PROJECT else \
            next(p for p in self.builtin if p["id"] == key)
        self.profile = copy.deepcopy(found)
        self._fill()

    def _fill(self) -> None:
        p = self.profile
        fonte = p.get("fonte") or {}
        text = f"Fonte: {fonte.get('documento') or '—'}"
        if fonte.get("acesso"):
            text += f" (acesso em {fonte['acesso']})"
        if p.get("herdado"):
            text += "<br>Vêm do perfil Genérico, sem fonte da prefeitura: " + ", ".join(
                intervention.LABEL[c] for c in p["herdado"]) + "."
        self.source.setText(text)
        for row, code in enumerate(intervention.CODES):
            data = p["cores"][code]
            color = self.color_grid.cellWidget(row, 1)
            color.setText(data["cor"].upper() if data.get("cor") else "Sem cor")
            color.setIcon(swatch(data["cor"]) if data.get("cor") else QIcon())
            for column, field_, default in ((2, "hachura", "none"), (3, "angulo", 45.0)):
                combo = self.color_grid.cellWidget(row, column)
                combo.blockSignals(True)
                combo.setCurrentIndex(max(0, combo.findData(data.get(field_, default))))
                combo.blockSignals(False)
        for key, combo in self.scales.items():
            value = p["escalas"].get(key) or storeys.DEFAULT_SCALE
            if combo.findData(value) < 0:
                combo.addItem(f"1:{value}", value)
            combo.blockSignals(True)
            combo.setCurrentIndex(combo.findData(value))
            combo.blockSignals(False)
        for widget, setter in ((self.plan, lambda: self.plan.setCurrentIndex(
                                    max(0, self.plan.findData(p.get("planta", "completa"))))),
                               (self.pdf_size, lambda: self.pdf_size.setValue(
                                    float(p["pdf"].get("max_mb") or 0))),
                               (self.stamp, lambda: self.stamp.setChecked(
                                    bool(p["pdf"].get("carimbo_ultima_prancha")))),
                               (self.notes, lambda: self.notes.setPlainText(
                                    "\n".join(p.get("notas") or [])))):
            widget.blockSignals(True)
            setter()
            widget.blockSignals(False)
        self.seal.setText("; ".join(p.get("selo") or []) or "—")

    # --- edição --------------------------------------------------------------------------

    def set_mark(self, code: str, **values) -> None:
        self.profile["cores"][code].update(values)
        self._own(code)

    def choose_color(self, code: str, color: str | None = "") -> None:
        """Cor da situação; ``None`` tira a cor (a situação não é pintada)."""
        if color == "":
            current = self.profile["cores"][code].get("cor") or "#000000"
            chosen = QColorDialog.getColor(QColor(current), self,
                                           f"Cor de {intervention.LABEL[code]}")
            if not chosen.isValid():
                return
            color = chosen.name()
        self.profile["cores"][code]["cor"] = color.upper() if color else None
        self._own(code)
        self._fill()

    def _own(self, code: str) -> None:
        """A cor editada deixa de ser "herdada do Genérico"."""
        if code in self.profile.get("herdado", []):
            self.profile["herdado"].remove(code)

    def _notes_changed(self) -> None:
        lines = [t.strip() for t in self.notes.toPlainText().splitlines()]
        self.profile["notas"] = [t for t in lines if t]
