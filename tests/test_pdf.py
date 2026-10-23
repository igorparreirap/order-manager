import re

from order_manager.domain.models import OrderItem
from order_manager.paths import DEFAULT_LOGO
from order_manager.services.company import CompanyInfo
from order_manager.services.pdf import render_order_pdf


def _page_count(data: bytes) -> int:
    return len(re.findall(rb"/Type /Page\b", data))


def test_pdf_is_generated(tmp_path, order):
    output = render_order_pdf(order, tmp_path / "pedido.pdf", CompanyInfo("Empresa", "Rodapé", DEFAULT_LOGO))
    data = output.read_bytes()
    assert data.startswith(b"%PDF")
    assert _page_count(data) == 1


def test_long_orders_span_multiple_pages(tmp_path, order):
    order.items = [
        OrderItem(str(i), f"PRODUTO COM UM NOME BEM COMPRIDO NÚMERO {i}", 1, 1) for i in range(120)
    ]
    output = render_order_pdf(order, tmp_path / "longo.pdf", CompanyInfo("Empresa"))
    assert _page_count(output.read_bytes()) > 1
