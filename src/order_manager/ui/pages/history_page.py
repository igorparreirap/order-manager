"""Order history with search, date filter, edit, PDF and delete."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from PyQt5.QtCore import QDate, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CalendarPicker,
    CardWidget,
    MessageBox,
    PrimaryPushButton,
    PushButton,
    SearchLineEdit,
    SubtitleLabel,
    TableWidget,
)
from qfluentwidgets import FluentIcon as FIF

from order_manager.context import AppContext
from order_manager.domain.formatting import format_brl
from order_manager.domain.models import Order
from order_manager.services.pdf import render_order_pdf
from order_manager.ui.helpers import notify_error, notify_success, notify_warning, open_file


def _to_date(qdate: QDate) -> date | None:
    return date(qdate.year(), qdate.month(), qdate.day()) if qdate.isValid() else None


class HistoryPage(QWidget):
    edit_requested = pyqtSignal(object)  # Order

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("historyPage")
        self.ctx = ctx

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(16)
        layout.addWidget(SubtitleLabel("Histórico de pedidos", self))

        filters = CardWidget(self)
        f = QHBoxLayout(filters)
        self.search_input = SearchLineEdit()
        self.search_input.setPlaceholderText("Cliente, produto ou código")
        self.search_input.searchSignal.connect(lambda _: self.reload())
        self.search_input.returnPressed.connect(self.reload)
        self.start_input = CalendarPicker(self)
        self.start_input.setDateFormat("dd/MM/yyyy")
        self.start_input.setText("Data inicial")
        self.end_input = CalendarPicker(self)
        self.end_input.setDateFormat("dd/MM/yyyy")
        self.end_input.setText("Data final")
        search = PrimaryPushButton(FIF.SEARCH, "Filtrar")
        search.clicked.connect(self.reload)
        reset = PushButton(FIF.SYNC, "Limpar filtros")
        reset.clicked.connect(self.reset_filters)
        f.addWidget(self.search_input, 1)
        f.addWidget(self.start_input)
        f.addWidget(self.end_input)
        f.addWidget(search)
        f.addWidget(reset)
        layout.addWidget(filters)

        self.table = TableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Nº", "Data", "Cliente", "Itens", "Total", "Pagamento"])
        self.table.verticalHeader().hide()
        self.table.setBorderVisible(True)
        self.table.setBorderRadius(8)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        for col, width in ((0, 70), (1, 110), (3, 70), (4, 130), (5, 130)):
            self.table.setColumnWidth(col, width)
        self.table.cellDoubleClicked.connect(lambda *_: self.edit_selected())
        layout.addWidget(self.table, 1)

        bottom = QHBoxLayout()
        self.summary_label = BodyLabel()
        bottom.addWidget(self.summary_label)
        bottom.addStretch()
        for icon, text, slot in (
            (FIF.DELETE, "Excluir", self.delete_selected),
            (FIF.DOCUMENT, "PDF", self.export_selected),
            (FIF.EDIT, "Editar", self.edit_selected),
        ):
            button = PushButton(icon, text)
            button.clicked.connect(slot)
            bottom.addWidget(button)
        layout.addLayout(bottom)
        self.reload()

    def reset_filters(self) -> None:
        self.search_input.clear()
        for picker, label in ((self.start_input, "Data inicial"), (self.end_input, "Data final")):
            picker.setDate(QDate())
            picker.setText(label)
        self.reload()

    def reload(self) -> None:
        orders = self.ctx.orders.search(
            self.search_input.text(),
            _to_date(self.start_input.getDate()),
            _to_date(self.end_input.getDate()),
        )
        self.table.setRowCount(len(orders))
        for row, order in enumerate(orders):
            cells = (
                str(order.id),
                f"{order.order_date:%d/%m/%Y}",
                order.customer_name,
                str(len(order.items)),
                format_brl(order.total),
                order.payment_method.value,
            )
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if col in (0, 3, 4):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, col, item)
            self.table.item(row, 0).setData(Qt.UserRole, order.id)
        total = sum((o.total for o in orders), Decimal(0))
        self.summary_label.setText(f"{len(orders)} pedido(s) • {format_brl(total)}")

    def _selected_order(self) -> Order | None:
        row = self.table.currentRow()
        if row < 0:
            notify_warning(self, "Selecione um pedido.")
            return None
        return self.ctx.orders.get(self.table.item(row, 0).data(Qt.UserRole))

    def edit_selected(self) -> None:
        if order := self._selected_order():
            self.edit_requested.emit(order)

    def export_selected(self) -> None:
        order = self._selected_order()
        if not order:
            return
        suggested = Path.home() / "Downloads" / f"Pedido_{order.id}_{order.customer_name}.pdf"
        filename, _ = QFileDialog.getSaveFileName(self, "Salvar PDF", str(suggested), "PDF (*.pdf)")
        if not filename:
            return
        try:
            render_order_pdf(order, filename, self.ctx.company)
        except OSError as exc:
            notify_error(self, f"Não foi possível salvar o PDF: {exc}")
            return
        notify_success(self, "PDF gerado.")
        if self.ctx.settings.settings.open_pdf_after_save:
            open_file(filename)

    def delete_selected(self) -> None:
        order = self._selected_order()
        if not order:
            return
        box = MessageBox(
            "Excluir pedido",
            f"Excluir o pedido #{order.id} de {order.customer_name}? Esta ação não pode ser desfeita.",
            self.window(),
        )
        if box.exec():
            self.ctx.orders.delete(order.id)
            self.reload()
            notify_success(self, f"Pedido #{order.id} excluído.")
