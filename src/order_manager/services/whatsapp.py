"""Builds a WhatsApp message with the order summary."""

from __future__ import annotations

from urllib.parse import quote

from order_manager.domain.formatting import digits_only, format_brl
from order_manager.domain.models import Order

BRAZIL_COUNTRY_CODE = "55"


def build_order_message(order: Order, company_name: str = "") -> str:
    lines = []
    if company_name:
        lines.append(f"*{company_name}*")
    lines += [
        f"*PEDIDO{f' #{order.id}' if order.id else ''} - {order.customer_name}*",
        f"Data: {order.order_date:%d/%m/%Y}",
        "",
        "*ITENS:*",
    ]
    lines += [f"- {item.quantity}x {item.product_name} ({format_brl(item.total)})" for item in order.items]
    lines += [
        "",
        f"*TOTAL: {format_brl(order.total)}*",
        f"Pagamento: {order.payment_method.value}",
    ]
    return "\n".join(lines)


def normalize_whatsapp_phone(phone: str) -> str:
    """Return the phone in international format (``55`` + DDD + number)."""
    digits = digits_only(phone)
    if len(digits) in (10, 11):  # DDD + number, without country code
        digits = BRAZIL_COUNTRY_CODE + digits
    if len(digits) not in (12, 13):
        raise ValueError("Telefone inválido para WhatsApp. Use DDD + número.")
    return digits


def build_whatsapp_url(phone: str, message: str) -> str:
    return f"https://wa.me/{normalize_whatsapp_phone(phone)}?text={quote(message)}"
