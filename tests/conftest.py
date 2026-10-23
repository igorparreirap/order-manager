from __future__ import annotations

import logging
from datetime import date

import pytest

from order_manager.config import SettingsStore
from order_manager.context import AppContext
from order_manager.domain.models import Address, Order, OrderItem, PaymentMethod, Product
from order_manager.storage import Database


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Never touch the real user data directory during tests."""
    monkeypatch.setenv("ORDER_MANAGER_HOME", str(tmp_path / "home"))
    yield
    root = logging.getLogger()  # close log files opened by the CLI entry point
    for handler in root.handlers[:]:
        handler.close()
        root.removeHandler(handler)


@pytest.fixture
def db():
    database = Database(":memory:")
    yield database
    database.close()


@pytest.fixture
def ctx(db, tmp_path):
    return AppContext.create(db=db, settings=SettingsStore(tmp_path / "settings.json"))


@pytest.fixture
def products():
    return [
        Product("1", "Pão de queijo 1kg", "18.90"),
        Product("2", "Biscoito de queijo 500g", "12.40"),
        Product("10", "Croissant folhado 1kg", "32.00"),
    ]


@pytest.fixture
def order():
    return Order(
        customer_name="Padaria Exemplo",
        order_date=date(2026, 1, 15),
        payment_method=PaymentMethod.PIX,
        contact="Maria",
        phone="(11) 90000-0001",
        address=Address("01001-000", "Praça da Sé", "100", "Sé", "São Paulo", "sp"),
        items=[
            OrderItem("1", "PÃO DE QUEIJO 1KG", 3, "18.90"),
            OrderItem("2", "BISCOITO DE QUEIJO 500G", 2, "12.40"),
        ],
    )
