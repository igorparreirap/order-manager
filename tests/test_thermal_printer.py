import pytest
from escpos.printer import Dummy

from order_manager.services.company import CompanyInfo
from order_manager.services.thermal_printer import PrinterError, print_order_on_serial, print_receipt


def test_receipt_contains_order_data(order):
    order.id = 7
    printer = Dummy()
    print_receipt(printer, order, CompanyInfo("Minha Empresa", "Volte sempre"))
    output = printer.output
    for expected in (b"Minha Empresa", b"PEDIDO DE VENDA #7", b"Padaria Exemplo", b"81,50", b"Volte sempre"):
        assert expected in output
    assert output.endswith(b"\x1dV\x00") or b"\x1dV" in output  # paper cut command


def test_long_lines_are_wrapped(order):
    order.customer_name = "CLIENTE " * 20
    printer = Dummy()
    print_receipt(printer, order, CompanyInfo("X"))
    text = printer.output.decode("cp437", errors="ignore")
    assert all(len(line) <= 60 for line in text.splitlines())


def test_missing_port_raises(order):
    with pytest.raises(PrinterError):
        print_order_on_serial("", order, CompanyInfo("X"))
