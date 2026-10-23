from decimal import Decimal

import pytest

from order_manager.domain.models import (
    Address,
    Customer,
    OrderItem,
    PaymentMethod,
    Product,
    ValidationError,
)


def test_product_normalizes_fields():
    product = Product(" 7 ", "  pão   francês ", "3,5")
    assert product.code == "7"
    assert product.name == "PÃO FRANCÊS"
    assert product.price == Decimal("3.50")


@pytest.mark.parametrize(("code", "name", "price"), [("", "x", 1), ("1", "  ", 1), ("1", "x", -1)])
def test_product_validation(code, name, price):
    with pytest.raises(ValidationError):
        Product(code, name, price)


def test_order_item_total():
    assert OrderItem("1", "X", 3, "18.90").total == Decimal("56.70")


def test_order_item_rejects_zero_quantity():
    with pytest.raises(ValidationError):
        OrderItem("1", "X", 0, 1)


def test_order_total_and_validation(order):
    assert order.total == Decimal("81.50")
    order.validate()


def test_order_requires_items_and_customer(order):
    order.items = []
    with pytest.raises(ValidationError, match="produto"):
        order.validate()
    order.customer_name = ""
    with pytest.raises(ValidationError, match="cliente"):
        order.validate()


def test_order_stores_phone_digits_only(order):
    assert order.phone == "11900000001"


def test_address_lines():
    address = Address("74000000", "Rua A", "10", "Centro", "Goiânia", "go")
    assert address.street_line() == "Rua A, 10 - Centro"
    assert address.city_line() == "Goiânia/GO - CEP: 74000-000"
    assert Address().is_empty()


def test_customer_requires_name():
    with pytest.raises(ValidationError):
        Customer("   ")


def test_payment_method_from_label():
    assert PaymentMethod.from_label("PIX") is PaymentMethod.PIX
    with pytest.raises(ValidationError):
        PaymentMethod.from_label("Cheque")
