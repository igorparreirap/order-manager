from decimal import Decimal

import pytest

from order_manager.domain.formatting import (
    digits_only,
    format_brl,
    format_phone,
    format_zip_code,
    from_cents,
    normalize_text,
    to_cents,
    to_money,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0.1, "0.10"), ("12,5", "12.50"), (Decimal("2.675"), "2.68"), (3, "3.00")],
)
def test_to_money_rounds_to_cents(value, expected):
    assert to_money(value) == Decimal(expected)


def test_to_money_rejects_garbage():
    with pytest.raises(ValueError):
        to_money("abc")


def test_float_sum_problem_does_not_happen():
    assert to_money(0.1) + to_money(0.2) == Decimal("0.30")


def test_cents_roundtrip():
    assert to_cents(Decimal("19.99")) == 1999
    assert from_cents(1999) == Decimal("19.99")


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, "R$ 0,00"), (Decimal("1234.5"), "R$ 1.234,50"), (1_000_000, "R$ 1.000.000,00")],
)
def test_format_brl(value, expected):
    assert format_brl(value) == expected


def test_phone_and_zip_formatting():
    assert digits_only("(62) 9 9999-0000") == "62999990000"
    assert format_phone("62999990000") == "(62) 99999-0000"
    assert format_phone("6233330000") == "(62) 3333-0000"
    assert format_zip_code("74000000") == "74000-000"


def test_normalize_text_ignores_accents_and_case():
    assert normalize_text("  PÃO de Queijo ") == "pao de queijo"
