"""Screen for creating and editing orders."""

from __future__ import annotations

import logging
import webbrowser
from datetime import date
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
    ComboBox,
    LineEdit,
    PrimaryPushButton,
    PushButton,
    SpinBox,
    StrongBodyLabel,
    SubtitleLabel,
    TableWidget,
)
from qfluentwidgets import FluentIcon as FIF

from order_manager.context import AppContext
from order_manager.domain.formatting import format_brl, format_phone, format_zip_code, to_money
from order_manager.domain.models import (
    Address,
    Customer,
    Order,
    OrderItem,
    PaymentMethod,
    ValidationError,
)
from order_manager.services.pdf import render_order_pdf
from order_manager.services.thermal_printer import PrinterError, print_order_on_serial
from order_manager.services.whatsapp import build_order_message, build_whatsapp_url
from order_manager.ui.helpers import (
    make_completer,
    notify_error,
    notify_info,
    notify_success,
    notify_warning,
    open_file,
)
from order_manager.ui.workers import ZipCodeWorker

logger = logging.getLogger(__name__)

COL_CODE, COL_NAME, COL_QTY, COL_UNIT, COL_TOTAL = range(5)


class OrderPage(QWidget):
    order_saved = pyqtSignal(int)
    customers_changed = pyqtSignal()

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("orderPage")
        self.ctx = ctx
        self.editing_id: int | None = None
        self._zip_worker: ZipCodeWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(16)
        self.title = SubtitleLabel("Novo pedido", self)
        layout.addWidget(self.title)
        layout.addLayout(self._build_form())
        layout.addWidget(self._build_items(), 1)
        layout.addLayout(self._build_footer())
        self.refresh_completers()

    # ------------------------------------------------------------------ layout
    def _build_form(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(16)

        customer_card = CardWidget(self)
        c = QVBoxLayout(customer_card)
        c.addWidget(StrongBodyLabel("Cliente"))
        self.customer_input = LineEdit()
        self.customer_input.setPlaceholderText("Nome do cliente (digite para buscar)")
        self.customer_input.setClearButtonEnabled(True)
        self.customer_input.editingFinished.connect(self._fill_known_customer)
        c.addWidget(self.customer_input)

        date_payment = QHBoxLayout()
        self.date_input = CalendarPicker(self)
        self.date_input.setDateFormat("dd/MM/yyyy")
        self.date_input.setDate(QDate.currentDate())
        self.payment_input = ComboBox()
        self.payment_input.addItems([method.value for method in PaymentMethod])
        date_payment.addWidget(self.date_input)
        date_payment.addWidget(self.payment_input)
        c.addLayout(date_payment)

        self.contact_input = LineEdit()
        self.contact_input.setPlaceholderText("Responsável")
        self.phone_input = LineEdit()
        self.phone_input.setPlaceholderText("Celular com DDD")
        c.addWidget(self.contact_input)
        c.addWidget(self.phone_input)
        save_customer = PushButton(FIF.PEOPLE, "Salvar cliente")
        save_customer.clicked.connect(self.save_customer)
        c.addWidget(save_customer)
        row.addWidget(customer_card, 1)

        address_card = CardWidget(self)
        a = QVBoxLayout(address_card)
        a.addWidget(StrongBodyLabel("Endereço de entrega"))
        self.zip_input = LineEdit()
        self.zip_input.setPlaceholderText("CEP (preenche o endereço automaticamente)")
        self.zip_input.editingFinished.connect(self._lookup_zip_code)
        self.street_input = LineEdit()
        self.street_input.setPlaceholderText("Rua")
        self.number_input = LineEdit()
        self.number_input.setPlaceholderText("Nº")
        self.district_input = LineEdit()
        self.district_input.setPlaceholderText("Bairro")
        self.city_input = LineEdit()
        self.city_input.setPlaceholderText("Cidade")
        self.state_input = LineEdit()
        self.state_input.setPlaceholderText("UF")
        self.state_input.setMaxLength(2)
        self.state_input.setFixedWidth(70)

        a.addWidget(self.zip_input)
        a.addWidget(self.street_input)
        number_district = QHBoxLayout()
        number_district.addWidget(self.number_input, 1)
        number_district.addWidget(self.district_input, 2)
        a.addLayout(number_district)
        city_state = QHBoxLayout()
        city_state.addWidget(self.city_input)
        city_state.addWidget(self.state_input)
        a.addLayout(city_state)
        a.addStretch()
        row.addWidget(address_card, 1)
        return row

    def _build_items(self) -> CardWidget:
        card = CardWidget(self)
        v = QVBoxLayout(card)
        buttons = QHBoxLayout()
        buttons.addWidget(StrongBodyLabel("Itens"))
        buttons.addStretch()
        add = PushButton(FIF.ADD, "Adicionar produto")
        add.clicked.connect(lambda: self.add_item_row())
        remove = PushButton(FIF.DELETE, "Remover selecionado")
        remove.clicked.connect(self.remove_selected_row)
        buttons.addWidget(add)
        buttons.addWidget(remove)
        v.addLayout(buttons)

        self.table = TableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Cód.", "Produto", "Qtd.", "Unitário", "Total"])
        self.table.verticalHeader().hide()
        self.table.setBorderVisible(True)
        self.table.setBorderRadius(8)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(COL_NAME, QHeaderView.Stretch)
        for col, width in ((COL_CODE, 90), (COL_QTY, 110), (COL_UNIT, 110), (COL_TOTAL, 120)):
            self.table.setColumnWidth(col, width)
        v.addWidget(self.table)
        return card

    def _build_footer(self) -> QHBoxLayout:
        footer = QHBoxLayout()
        self.total_label = SubtitleLabel(format_brl(0))
        footer.addWidget(BodyLabel("Total do pedido:"))
        footer.addWidget(self.total_label)
        footer.addStretch()

        actions = (
            (PushButton, FIF.CANCEL, "Limpar", self.clear_form),
            (PushButton, FIF.SAVE, "Salvar", self.save_order),
            (PushButton, FIF.CHAT, "WhatsApp", self.send_whatsapp),
            (PushButton, FIF.DOCUMENT, "PDF", self.export_pdf),
            (PrimaryPushButton, FIF.PRINT, "Imprimir", self.print_order),
        )
        for cls, icon, text, slot in actions:
            button = cls(icon, text)
            button.clicked.connect(slot)
            footer.addWidget(button)
        return footer

    # ------------------------------------------------------------- completers
    def refresh_completers(self) -> None:
        self.customer_input.setCompleter(make_completer(self.ctx.customers.list_names(), self))
        products = self.ctx.products.list()
        self._codes = [p.code for p in products]
        self._names = [p.name for p in products]

    # ------------------------------------------------------------------ items
    def add_item_row(self, item: OrderItem | None = None) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)

        code = LineEdit()
        code.setPlaceholderText("Cód.")
        code.setCompleter(make_completer(self._codes, code, contains=False))
        code.editingFinished.connect(lambda: self._on_code_entered(code))
        name = LineEdit()
        name.setPlaceholderText("Buscar produto...")
        name.setCompleter(make_completer(self._names, name))
        name.editingFinished.connect(lambda: self._on_name_entered(name))
        qty = SpinBox()
        qty.setRange(1, 99999)
        qty.valueChanged.connect(lambda _: self._recalculate_row(self._row_of(qty)))

        self.table.setCellWidget(row, COL_CODE, code)
        self.table.setCellWidget(row, COL_NAME, name)
        self.table.setCellWidget(row, COL_QTY, qty)
        for col in (COL_UNIT, COL_TOTAL):
            cell = QTableWidgetItem(format_brl(0))
            cell.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, col, cell)
        self._set_unit_price(row, to_money(0))

        if item:
            code.setText(item.product_code)
            name.setText(item.product_name)
            qty.setValue(item.quantity)
            self._set_unit_price(row, item.unit_price)
        else:
            code.setFocus()

    def _row_of(self, widget: QWidget) -> int:
        """Find the current row of a cell widget.

        Rows shift when another row is removed, so the row number must be looked up
        at event time instead of being captured when the widget is created.
        """
        for row in range(self.table.rowCount()):
            for col in (COL_CODE, COL_NAME, COL_QTY):
                if self.table.cellWidget(row, col) is widget:
                    return row
        return -1

    def _on_code_entered(self, widget: LineEdit) -> None:
        row = self._row_of(widget)
        product = self.ctx.products.get(widget.text())
        if row >= 0 and product:
            self.table.cellWidget(row, COL_NAME).setText(product.name)
            self._set_unit_price(row, product.price)

    def _on_name_entered(self, widget: LineEdit) -> None:
        row = self._row_of(widget)
        product = self.ctx.products.find_by_name(widget.text())
        if row >= 0 and product:
            self.table.cellWidget(row, COL_CODE).setText(product.code)
            self._set_unit_price(row, product.price)

    def _set_unit_price(self, row: int, price) -> None:
        cell = self.table.item(row, COL_UNIT)
        cell.setData(Qt.UserRole, str(to_money(price)))
        cell.setText(format_brl(price))
        self._recalculate_row(row)

    def _unit_price(self, row: int):
        return to_money(self.table.item(row, COL_UNIT).data(Qt.UserRole) or 0)

    def _recalculate_row(self, row: int) -> None:
        if row < 0:
            return
        quantity = self.table.cellWidget(row, COL_QTY).value()
        self.table.item(row, COL_TOTAL).setText(format_brl(self._unit_price(row) * quantity))
        self._update_total()

    def remove_selected_row(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self._update_total()

    def _update_total(self) -> None:
        items = self._collect_items(strict=False)
        self.total_label.setText(format_brl(sum((i.total for i in items), to_money(0))))

    def _collect_items(self, strict: bool = True) -> list[OrderItem]:
        items = []
        for row in range(self.table.rowCount()):
            name = self.table.cellWidget(row, COL_NAME).text().strip()
            if not name:
                continue
            code = self.table.cellWidget(row, COL_CODE).text().strip()
            if strict and not self.ctx.products.get(code):
                raise ValidationError(f"Produto da linha {row + 1} não está cadastrado.")
            items.append(
                OrderItem(code, name, self.table.cellWidget(row, COL_QTY).value(), self._unit_price(row))
            )
        return items

    # ------------------------------------------------------------------- form
    def _address(self) -> Address:
        return Address(
            zip_code=self.zip_input.text(),
            street=self.street_input.text().strip(),
            number=self.number_input.text().strip(),
            district=self.district_input.text().strip(),
            city=self.city_input.text().strip(),
            state=self.state_input.text(),
        )

    def _set_address(self, address: Address) -> None:
        self.zip_input.setText(format_zip_code(address.zip_code))
        self.street_input.setText(address.street)
        self.number_input.setText(address.number)
        self.district_input.setText(address.district)
        self.city_input.setText(address.city)
        self.state_input.setText(address.state)

    def build_order(self) -> Order:
        """Build an :class:`Order` from the form. Raises ValidationError if invalid."""
        qdate = self.date_input.getDate()
        order = Order(
            id=self.editing_id,
            customer_name=self.customer_input.text(),
            order_date=date(qdate.year(), qdate.month(), qdate.day()),
            payment_method=PaymentMethod.from_label(self.payment_input.currentText()),
            contact=self.contact_input.text().strip(),
            phone=self.phone_input.text(),
            address=self._address(),
            items=self._collect_items(),
        )
        order.validate()
        return order

    def clear_form(self) -> None:
        self.editing_id = None
        self.title.setText("Novo pedido")
        for field in (
            self.customer_input,
            self.contact_input,
            self.phone_input,
            self.zip_input,
            self.street_input,
            self.number_input,
            self.district_input,
            self.city_input,
            self.state_input,
        ):
            field.clear()
        self.date_input.setDate(QDate.currentDate())
        self.payment_input.setCurrentIndex(0)
        self.table.setRowCount(0)
        self._update_total()

    def load_order(self, order: Order) -> None:
        """Fill the form with an existing order so it can be edited."""
        self.clear_form()
        self.editing_id = order.id
        self.title.setText(f"Editando pedido #{order.id}")
        self.customer_input.setText(order.customer_name)
        self.date_input.setDate(QDate(order.order_date.year, order.order_date.month, order.order_date.day))
        self.payment_input.setCurrentText(order.payment_method.value)
        self.contact_input.setText(order.contact)
        self.phone_input.setText(format_phone(order.phone))
        self._set_address(order.address)
        for item in order.items:
            self.add_item_row(item)
        self._update_total()

    def _fill_known_customer(self) -> None:
        customer = self.ctx.customers.get_by_name(self.customer_input.text())
        if customer and not self.editing_id:
            self.customer_input.setText(customer.name)
            self.contact_input.setText(customer.contact)
            self.phone_input.setText(format_phone(customer.phone))
            self._set_address(customer.address)

    def _lookup_zip_code(self) -> None:
        if len("".join(ch for ch in self.zip_input.text() if ch.isdigit())) != 8:
            return
        self._zip_worker = ZipCodeWorker(self.zip_input.text(), self)
        self._zip_worker.found.connect(self._on_zip_found)
        self._zip_worker.failed.connect(lambda msg: notify_warning(self, msg))
        self._zip_worker.start()

    def _on_zip_found(self, address: Address) -> None:
        address.number = self.number_input.text()
        self._set_address(address)
        self.number_input.setFocus()

    # ---------------------------------------------------------------- actions
    def save_customer(self) -> None:
        try:
            customer = self.ctx.customers.save(
                Customer(
                    name=self.customer_input.text(),
                    contact=self.contact_input.text().strip(),
                    phone=self.phone_input.text(),
                    address=self._address(),
                )
            )
        except ValidationError as exc:
            notify_warning(self, str(exc))
            return
        self.refresh_completers()
        self.customers_changed.emit()
        notify_success(self, f"Cliente {customer.name} salvo.")

    def _persist(self) -> Order | None:
        """Validate and save the current order, keeping the form in edit mode."""
        try:
            order = self.ctx.orders.save(self.build_order())
        except (ValidationError, LookupError) as exc:
            notify_warning(self, str(exc))
            return None
        self.editing_id = order.id
        self.title.setText(f"Editando pedido #{order.id}")
        self.order_saved.emit(order.id)
        return order

    def save_order(self) -> None:
        if order := self._persist():
            notify_success(self, f"Pedido #{order.id} salvo.")
            self.clear_form()

    def export_pdf(self) -> None:
        order = self._persist()
        if not order:
            return
        suggested = Path.home() / "Downloads" / f"Pedido_{order.id}_{order.customer_name}.pdf"
        filename, _ = QFileDialog.getSaveFileName(self, "Salvar PDF", str(suggested), "PDF (*.pdf)")
        if not filename:
            return
        try:
            render_order_pdf(order, filename, self.ctx.company)
        except OSError as exc:
            logger.exception("PDF export failed")
            notify_error(self, f"Não foi possível salvar o PDF: {exc}")
            return
        notify_success(self, f"PDF do pedido #{order.id} gerado.")
        if self.ctx.settings.settings.open_pdf_after_save:
            open_file(filename)
        self.clear_form()

    def print_order(self) -> None:
        order = self._persist()
        if not order:
            return
        s = self.ctx.settings.settings
        try:
            print_order_on_serial(s.printer_port, order, self.ctx.company, s.print_copies, s.printer_baudrate)
        except PrinterError as exc:
            notify_error(self, f"{exc}\nO pedido #{order.id} foi salvo.")
            return
        notify_success(self, f"Pedido #{order.id} enviado para a impressora.")
        self.clear_form()

    def send_whatsapp(self) -> None:
        try:
            order = self.build_order()
            url = build_whatsapp_url(order.phone, build_order_message(order, self.ctx.company.name))
        except ValueError as exc:  # includes ValidationError and invalid phone numbers
            notify_warning(self, str(exc))
            return
        webbrowser.open(url)
        notify_info(self, "Abrindo o WhatsApp...")
