"""Formatting and normalisation helpers for Brazilian money, phones and ZIP codes."""

from __future__ import annotations

import unicodedata
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")


def to_money(value: Decimal | int | float | str) -> Decimal:
    """Convert ``value`` to a Decimal rounded to cents.

    Floats are converted through ``str`` so that ``0.1`` becomes ``Decimal("0.10")``
    instead of ``Decimal("0.1000000000000000055511151231257827")``.
    Accepts Brazilian decimal commas (``"12,50"``).
    """
    if isinstance(value, str):
        value = value.strip().replace(",", ".")
    try:
        return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid monetary value: {value!r}") from exc


def to_cents(value: Decimal) -> int:
    """Convert a money value to an integer number of cents (for storage)."""
    return int(to_money(value) * 100)


def from_cents(cents: int) -> Decimal:
    """Convert an integer number of cents back to a Decimal money value."""
    return to_money(Decimal(cents) / 100)


def format_brl(value: Decimal | int | float) -> str:
    """Format a value as Brazilian Real, e.g. ``R$ 1.234,50``."""
    text = f"{to_money(value):,.2f}"
    return "R$ " + text.replace(",", "_").replace(".", ",").replace("_", ".")


def digits_only(text: str | None) -> str:
    """Return only the digits contained in ``text``."""
    return "".join(ch for ch in (text or "") if ch.isdigit())


def format_phone(phone: str | None) -> str:
    """Format a Brazilian phone number: ``(62) 99999-0000`` or ``(62) 3333-0000``."""
    digits = digits_only(phone)
    if len(digits) == 11:
        return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    if len(digits) == 10:
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    return digits


def format_zip_code(zip_code: str | None) -> str:
    """Format a Brazilian ZIP code (CEP) as ``00000-000``."""
    digits = digits_only(zip_code)
    return f"{digits[:5]}-{digits[5:]}" if len(digits) == 8 else digits


def normalize_text(text: str | None) -> str:
    """Lower-case and strip accents, for accent-insensitive search (``Pão`` == ``pao``)."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).casefold().strip()
