"""Prints order receipts on ESC/POS thermal printers (80 mm, 48 columns).

Receipt layout is separated from the transport: :func:`print_receipt` works with any
``python-escpos`` printer object, so it can be tested with ``escpos.printer.Dummy``.
"""

from __future__ import annotations

import logging
import textwrap

from escpos.escpos import Escpos

from order_manager.domain.formatting import format_brl, format_phone
from order_manager.domain.models import Order
from order_manager.services.company import CompanyInfo

logger = logging.getLogger(__name__)

COLUMNS = 48


class PrinterError(Exception):
    pass


def _wrap(text: str, width: int = COLUMNS) -> str:
    return "".join(f"{line}\n" for line in textwrap.wrap(text, width=width)) if text else ""


def print_receipt(printer: Escpos, order: Order, company: CompanyInfo, columns: int = COLUMNS) -> None:
    separator = "-" * columns + "\n"

    printer.set(align="center")
    if company.logo and company.logo.is_file():
        try:
            printer.image(str(company.logo))
        except Exception:  # a broken logo must never block the order from printing
            logger.exception("Could not print logo %s", company.logo)
    printer.set(align="center", bold=True, double_height=True)
    printer.text(_wrap(company.name, columns))
    printer.set(align="center", bold=False, normal_textsize=True)
    printer.text(f"PEDIDO DE VENDA{f' #{order.id}' if order.id else ''}\n")
    printer.text(separator)

    printer.set(align="left")
    printer.text(_wrap(f"CLIENTE: {order.customer_name}", columns))
    printer.text(f"DATA:    {order.order_date:%d/%m/%Y}\n")
    if order.contact:
        printer.text(_wrap(f"CONTATO: {order.contact}", columns))
    if order.phone:
        printer.text(f"TEL:     {format_phone(order.phone)}\n")
    if not order.address.is_empty():
        printer.text(_wrap(order.address.street_line(), columns))
        printer.text(_wrap(order.address.city_line(), columns))
    printer.text(separator)

    for item in order.items:
        printer.text(_wrap(f"{item.product_code} - {item.product_name}", columns))
        values = f"{item.quantity} x {format_brl(item.unit_price)} = {format_brl(item.total)}"
        printer.text(values.rjust(columns) + "\n")
    printer.text(separator)

    printer.set(align="right", bold=True)
    printer.text(f"TOTAL: {format_brl(order.total)}\n")
    printer.set(align="left", bold=False)
    printer.text(f"Pagamento: {order.payment_method.value}\n\n")

    if company.footer:
        printer.set(align="center")
        printer.text(_wrap(company.footer, columns))
    printer.text("\n\n")
    printer.cut()


def print_order_on_serial(
    port: str,
    order: Order,
    company: CompanyInfo,
    copies: int = 1,
    baudrate: int = 9600,
) -> None:
    """Open the serial printer on ``port`` and print ``copies`` receipts."""
    if not port:
        raise PrinterError("Nenhuma impressora selecionada.")
    from escpos.printer import Serial  # imported lazily: needs pyserial and a real port

    printer = None
    try:
        printer = Serial(devfile=port, baudrate=baudrate, timeout=1.0, dsrdtr=True)
        for _ in range(max(1, copies)):
            print_receipt(printer, order, company)
    except Exception as exc:
        raise PrinterError(f"Erro na impressora ({port}): {exc}") from exc
    finally:
        if printer is not None:
            printer.close()
