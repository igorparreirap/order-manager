"""Product catalogue management."""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
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
    CardWidget,
    DoubleSpinBox,
    LineEdit,
    MessageBox,
    PrimaryPushButton,
    PushButton,
    SearchLineEdit,
    StrongBodyLabel,
    SubtitleLabel,
    TableWidget,
)
from qfluentwidgets import FluentIcon as FIF

from order_manager.context import AppContext
from order_manager.domain.formatting import format_brl
from order_manager.domain.models import Product, ValidationError
from order_manager.services.product_import import import_products_csv
from order_manager.ui.helpers import notify_error, notify_success, notify_warning


class ProductsPage(QWidget):
    products_changed = pyqtSignal()

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("productsPage")
        self.ctx = ctx
        self.original_code: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header.addWidget(SubtitleLabel("Produtos", self))
        header.addStretch()
        import_button = PushButton(FIF.DOWNLOAD, "Importar CSV")
        import_button.clicked.connect(self.import_csv)
        header.addWidget(import_button)
        layout.addLayout(header)

        card = CardWidget(self)
        form = QVBoxLayout(card)
        form.addWidget(StrongBodyLabel("Cadastro"))
        fields = QHBoxLayout()
        self.code_input = LineEdit()
        self.code_input.setPlaceholderText("Código (automático)")
        self.code_input.setFixedWidth(170)
        self.name_input = LineEdit()
        self.name_input.setPlaceholderText("Nome do produto")
        self.price_input = DoubleSpinBox()
        self.price_input.setPrefix("R$ ")
        self.price_input.setRange(0, 999_999.99)
        self.price_input.setDecimals(2)
        self.price_input.setFixedWidth(170)
        fields.addWidget(self.code_input)
        fields.addWidget(self.name_input, 1)
        fields.addWidget(self.price_input)
        form.addLayout(fields)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.delete_button = PushButton(FIF.DELETE, "Excluir")
        self.delete_button.clicked.connect(self.delete_selected)
        self.delete_button.setEnabled(False)
        clear = PushButton(FIF.CANCEL, "Limpar")
        clear.clicked.connect(self.clear_form)
        save = PrimaryPushButton(FIF.SAVE, "Salvar")
        save.clicked.connect(self.save)
        for button in (self.delete_button, clear, save):
            buttons.addWidget(button)
        form.addLayout(buttons)
        layout.addWidget(card)

        self.search_input = SearchLineEdit()
        self.search_input.setPlaceholderText("Buscar por código ou nome")
        self.search_input.textChanged.connect(self.reload)
        layout.addWidget(self.search_input)

        self.table = TableWidget(self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Código", "Nome", "Preço"])
        self.table.verticalHeader().hide()
        self.table.setBorderVisible(True)
        self.table.setBorderRadius(8)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 110)
        self.table.setColumnWidth(2, 140)
        self.table.cellClicked.connect(self._on_row_clicked)
        layout.addWidget(self.table, 1)
        self.reload()

    def reload(self) -> None:
        products = self.ctx.products.list(self.search_input.text())
        self.table.setRowCount(len(products))
        for row, product in enumerate(products):
            price = QTableWidgetItem(format_brl(product.price))
            price.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            code = QTableWidgetItem(product.code)
            code.setData(Qt.UserRole, product)
            self.table.setItem(row, 0, code)
            self.table.setItem(row, 1, QTableWidgetItem(product.name))
            self.table.setItem(row, 2, price)

    def _on_row_clicked(self, row: int, _column: int) -> None:
        product: Product = self.table.item(row, 0).data(Qt.UserRole)
        self.original_code = product.code
        self.code_input.setText(product.code)
        self.name_input.setText(product.name)
        self.price_input.setValue(float(product.price))
        self.delete_button.setEnabled(True)

    def clear_form(self) -> None:
        self.original_code = None
        self.code_input.clear()
        self.name_input.clear()
        self.price_input.setValue(0)
        self.delete_button.setEnabled(False)
        self.table.clearSelection()

    def save(self) -> None:
        code = self.code_input.text().strip() or self.ctx.products.next_code()
        if code != self.original_code and self.ctx.products.get(code):
            notify_warning(self, f"Já existe um produto com o código {code}.")
            return
        try:
            product = Product(code, self.name_input.text(), f"{self.price_input.value():.2f}")
        except ValidationError as exc:
            notify_warning(self, str(exc))
            return
        self.ctx.products.save(product, original_code=self.original_code)
        self._after_change(f"Produto {product.code} salvo.")

    def delete_selected(self) -> None:
        if not self.original_code:
            return
        box = MessageBox(
            "Excluir produto",
            f"Excluir o produto {self.original_code}? Pedidos antigos não são afetados.",
            self.window(),
        )
        if box.exec():
            self.ctx.products.delete(self.original_code)
            self._after_change("Produto excluído.")

    def import_csv(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Importar produtos", "", "CSV (*.csv)")
        if not filename:
            return
        try:
            result = import_products_csv(filename, self.ctx.products)
        except (OSError, ValueError) as exc:
            notify_error(self, str(exc))
            return
        message = f"{result.imported} produtos importados."
        if result.errors:
            message += f" {len(result.errors)} linhas ignoradas."
        self._after_change(message)

    def _after_change(self, message: str) -> None:
        self.clear_form()
        self.reload()
        self.products_changed.emit()
        notify_success(self, message)
