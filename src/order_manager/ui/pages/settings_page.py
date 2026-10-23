"""Application settings: appearance, printing, company data and backups."""

from __future__ import annotations

import serial.tools.list_ports
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QFileDialog, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    ComboBox,
    LineEdit,
    PushButton,
    ScrollArea,
    SpinBox,
    StrongBodyLabel,
    SubtitleLabel,
    SwitchButton,
)
from qfluentwidgets import FluentIcon as FIF

from order_manager import paths
from order_manager.context import AppContext
from order_manager.services.backup import create_backup
from order_manager.ui.helpers import notify_error, notify_success, open_file

THEMES = {"Claro": "light", "Escuro": "dark"}


class SettingsPage(ScrollArea):
    theme_changed = pyqtSignal(str)

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsPage")
        self.ctx = ctx
        self.store = ctx.settings
        s = self.store.settings

        container = QWidget()
        container.setObjectName("settingsContainer")
        self.body = QVBoxLayout(container)
        self.body.setContentsMargins(30, 24, 30, 24)
        self.body.setSpacing(16)
        self.setWidget(container)
        self.setWidgetResizable(True)
        self.enableTransparentBackground()

        self.body.addWidget(SubtitleLabel("Configurações", self))

        # Appearance
        self.theme_input = ComboBox()
        self.theme_input.addItems(list(THEMES))
        self.theme_input.setCurrentText(next(k for k, v in THEMES.items() if v == s.theme))
        self.theme_input.currentTextChanged.connect(self._on_theme_changed)
        self._card("Aparência", [("Tema", self.theme_input)])

        # Printing
        self.port_input = ComboBox()
        self._fill_ports()
        self.port_input.currentTextChanged.connect(
            lambda text: self.store.update(printer_port="" if text == "Nenhuma" else text)
        )
        refresh = PushButton(FIF.SYNC, "Atualizar")
        refresh.clicked.connect(self._fill_ports)
        port_row = QHBoxLayout()
        port_row.addWidget(self.port_input, 1)
        port_row.addWidget(refresh)
        self.copies_input = SpinBox()
        self.copies_input.setRange(1, 5)
        self.copies_input.setValue(s.print_copies)
        self.copies_input.valueChanged.connect(lambda v: self.store.update(print_copies=v))
        self.open_pdf_input = SwitchButton()
        self.open_pdf_input.setOnText("Sim")
        self.open_pdf_input.setOffText("Não")
        self.open_pdf_input.setChecked(s.open_pdf_after_save)
        self.open_pdf_input.checkedChanged.connect(lambda v: self.store.update(open_pdf_after_save=v))
        self._card(
            "Impressão",
            [
                ("Impressora térmica (porta serial)", port_row),
                ("Vias por pedido", self.copies_input),
                ("Abrir o PDF depois de salvar", self.open_pdf_input),
            ],
        )

        # Company
        self.company_input = LineEdit()
        self.company_input.setText(s.company_name)
        self.company_input.editingFinished.connect(
            lambda: self.store.update(company_name=self.company_input.text().strip())
        )
        self.footer_input = LineEdit()
        self.footer_input.setText(s.company_footer)
        self.footer_input.editingFinished.connect(
            lambda: self.store.update(company_footer=self.footer_input.text().strip())
        )
        self.logo_label = CaptionLabel(s.logo_path or "Logo padrão")
        choose_logo = PushButton(FIF.PHOTO, "Escolher logo")
        choose_logo.clicked.connect(self._choose_logo)
        logo_row = QHBoxLayout()
        logo_row.addWidget(self.logo_label, 1)
        logo_row.addWidget(choose_logo)
        self._card(
            "Empresa (aparece no PDF e no cupom)",
            [("Nome", self.company_input), ("Rodapé", self.footer_input), ("Logo", logo_row)],
        )

        # Data
        backup = PushButton(FIF.SAVE, "Fazer backup")
        backup.clicked.connect(self._backup)
        open_folder = PushButton(FIF.FOLDER, "Abrir pasta de dados")
        open_folder.clicked.connect(lambda: open_file(paths.app_home()))
        data_row = QHBoxLayout()
        data_row.addWidget(backup)
        data_row.addWidget(open_folder)
        data_row.addStretch()
        self._card("Dados", [(f"Banco de dados: {self.ctx.db.path}", data_row)])
        self.body.addStretch()

    def _card(self, title: str, rows: list[tuple[str, object]]) -> None:
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.addWidget(StrongBodyLabel(title))
        for label, widget in rows:
            layout.addWidget(BodyLabel(label))
            if isinstance(widget, QHBoxLayout):
                layout.addLayout(widget)
            else:
                layout.addWidget(widget)
        self.body.addWidget(card)

    def _fill_ports(self) -> None:
        self.port_input.blockSignals(True)
        self.port_input.clear()
        self.port_input.addItem("Nenhuma")
        for port in serial.tools.list_ports.comports():
            self.port_input.addItem(port.device)
        saved = self.store.settings.printer_port
        if saved and saved not in [self.port_input.itemText(i) for i in range(self.port_input.count())]:
            self.port_input.addItem(saved)  # keep the saved port visible even if unplugged
        self.port_input.setCurrentText(saved or "Nenhuma")
        self.port_input.blockSignals(False)

    def _on_theme_changed(self, label: str) -> None:
        self.store.update(theme=THEMES[label])
        self.theme_changed.emit(THEMES[label])

    def _choose_logo(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Escolher logo", "", "Imagens (*.png *.jpg)")
        if filename:
            self.store.update(logo_path=filename)
            self.logo_label.setText(filename)

    def _backup(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Pasta para o backup")
        if not folder:
            return
        try:
            target = create_backup(self.ctx.db, self.store.path, folder)
        except OSError as exc:
            notify_error(self, f"Falha no backup: {exc}")
            return
        notify_success(self, f"Backup salvo em {target}")
