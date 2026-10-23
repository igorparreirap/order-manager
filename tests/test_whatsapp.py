from urllib.parse import unquote

import pytest

from order_manager.services.whatsapp import (
    build_order_message,
    build_whatsapp_url,
    normalize_whatsapp_phone,
)


def test_message_contains_items_and_total(order):
    order.id = 42
    message = build_order_message(order, "Minha Empresa")
    assert "*PEDIDO #42 - Padaria Exemplo*" in message
    assert "- 3x PÃO DE QUEIJO 1KG (R$ 56,70)" in message
    assert "*TOTAL: R$ 81,50*" in message
    assert "Pagamento: PIX" in message


@pytest.mark.parametrize(
    ("phone", "expected"),
    [
        ("(62) 99999-0000", "5562999990000"),
        ("6233330000", "556233330000"),
        ("5562999990000", "5562999990000"),
    ],
)
def test_phone_gets_country_code(phone, expected):
    assert normalize_whatsapp_phone(phone) == expected


@pytest.mark.parametrize("phone", ["", "123", "62999999999999999"])
def test_invalid_phone(phone):
    with pytest.raises(ValueError):
        normalize_whatsapp_phone(phone)


def test_url_is_encoded():
    url = build_whatsapp_url("62999990000", "Olá & tchau")
    assert url.startswith("https://wa.me/5562999990000?text=")
    assert unquote(url.split("text=")[1]) == "Olá & tchau"
