"""Main window with side navigation."""

from __future__ import annotations

from PyQt5.QtGui import QIcon
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import FluentWindow, NavigationItemPosition, Theme, setTheme

from order_manager import __version__, paths
from order_manager.context import AppContext
from order_manager.domain.models import Order
from order_manager.ui.pages.history_page import HistoryPage
from order_manager.ui.pages.order_page import OrderPage
from order_manager.ui.pages.products_page import ProductsPage
from order_manager.ui.pages.settings_page import SettingsPage


def apply_theme(theme: str) -> None:
    setTheme(Theme.DARK if theme == "dark" else Theme.LIGHT)


class MainWindow(FluentWindow):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle(f"Order Manager {__version__}")
        if paths.DEFAULT_LOGO.is_file():
            self.setWindowIcon(QIcon(str(paths.DEFAULT_LOGO)))
        self.resize(1200, 780)
        apply_theme(ctx.settings.settings.theme)

        self.order_page = OrderPage(ctx, self)
        self.products_page = ProductsPage(ctx, self)
        self.history_page = HistoryPage(ctx, self)
        self.settings_page = SettingsPage(ctx, self)

        self.addSubInterface(self.order_page, FIF.SHOPPING_CART, "Novo pedido")
        self.addSubInterface(self.history_page, FIF.HISTORY, "Histórico")
        self.addSubInterface(self.products_page, FIF.TAG, "Produtos")
        self.addSubInterface(
            self.settings_page, FIF.SETTING, "Configurações", position=NavigationItemPosition.BOTTOM
        )

        # Pages communicate through signals, never by reaching into each other.
        self.order_page.order_saved.connect(lambda _: self.history_page.reload())
        self.products_page.products_changed.connect(self.order_page.refresh_completers)
        self.history_page.edit_requested.connect(self._edit_order)
        self.settings_page.theme_changed.connect(apply_theme)

    def _edit_order(self, order: Order) -> None:
        self.order_page.load_order(order)
        self.switchTo(self.order_page)
