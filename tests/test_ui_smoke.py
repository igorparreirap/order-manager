"""Smoke tests for the Qt interface, running without a display (offscreen)."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt5.QtWidgets")

from PyQt5.QtWidgets import QApplication

from order_manager.demo import seed_demo_data


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(qapp, ctx):
    from order_manager.ui.main_window import MainWindow

    seed_demo_data(ctx)
    win = MainWindow(ctx)
    yield win
    win.close()


def test_pages_load_data(window):
    assert window.history_page.table.rowCount() == 5
    assert window.products_page.table.rowCount() == 15


def test_create_order_through_the_form(window, ctx):
    page = window.order_page
    page.customer_input.setText("Cliente Teste")
    page.add_item_row()
    code = page.table.cellWidget(0, 0)
    code.setText("1")
    page._on_code_entered(code)
    page.table.cellWidget(0, 2).setValue(2)
    assert page.total_label.text() == "R$ 37,80"

    page.save_order()
    assert len(ctx.orders.search("Cliente Teste")) == 1
    assert window.history_page.table.rowCount() == 6


def test_quantity_change_after_removing_a_row_updates_the_right_row(window):
    """Regression: v1 captured the row index in a lambda and updated the wrong row."""
    page = window.order_page
    for code in ("1", "2"):
        page.add_item_row()
        widget = page.table.cellWidget(page.table.rowCount() - 1, 0)
        widget.setText(code)
        page._on_code_entered(widget)
    page.table.selectRow(0)
    page.remove_selected_row()
    page.table.cellWidget(0, 2).setValue(3)
    assert page.table.item(0, 4).text() == "R$ 253,50"  # 3 x R$ 84,50 (product 2)
    assert page.total_label.text() == "R$ 253,50"


def test_edit_order_from_history(window, ctx):
    order = ctx.orders.search()[0]
    window._edit_order(order)
    assert window.order_page.editing_id == order.id
    assert window.order_page.table.rowCount() == len(order.items)
