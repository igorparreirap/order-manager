"""Generates an A4 PDF for an order using ReportLab's Platypus layout engine.

Platypus handles pagination automatically: long orders flow onto extra pages and the
item table header is repeated on each one.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from order_manager.domain.formatting import format_brl, format_phone
from order_manager.domain.models import Order
from order_manager.services.company import CompanyInfo

LOGO_WIDTH = 45 * mm


def render_order_pdf(order: Order, output: Path | str, company: CompanyInfo) -> Path:
    output = Path(output)
    styles = getSampleStyleSheet()
    centered = ParagraphStyle("centered", parent=styles["Title"], alignment=TA_CENTER)
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=9, leading=11)

    story = []
    if company.logo and company.logo.is_file():
        width, height = ImageReader(str(company.logo)).getSize()
        story.append(Image(str(company.logo), LOGO_WIDTH, LOGO_WIDTH * height / width))
    story += [
        Paragraph(company.name, centered),
        Paragraph(f"PEDIDO DE VENDA{f' Nº {order.id}' if order.id else ''}", styles["Heading2"]),
        Spacer(1, 2 * mm),
    ]

    customer_lines = [
        f"<b>Data:</b> {order.order_date:%d/%m/%Y}",
        f"<b>Cliente:</b> {order.customer_name}",
    ]
    contact = " - ".join(p for p in (order.contact, format_phone(order.phone)) if p)
    if contact:
        customer_lines.append(f"<b>Contato:</b> {contact}")
    if not order.address.is_empty():
        customer_lines.append(f"<b>Endereço:</b> {order.address.street_line()}")
        customer_lines.append(order.address.city_line())
    story += [Paragraph(line, styles["Normal"]) for line in customer_lines]
    story.append(Spacer(1, 6 * mm))

    rows = [["Cód.", "Produto", "Qtd.", "Unitário", "Total"]]
    rows += [
        [
            item.product_code,
            Paragraph(item.product_name, small),  # wraps long names instead of cutting them
            str(item.quantity),
            format_brl(item.unit_price),
            format_brl(item.total),
        ]
        for item in order.items
    ]
    rows.append(["", "", "", "TOTAL", format_brl(order.total)])

    table = Table(rows, colWidths=[18 * mm, 87 * mm, 15 * mm, 25 * mm, 25 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F3F4F6")]),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#1F2937")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story += [
        table,
        Spacer(1, 6 * mm),
        Paragraph(f"<b>Forma de pagamento:</b> {order.payment_method.value}", styles["Normal"]),
    ]

    def draw_footer(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica-Oblique", 8)
        canvas.drawString(doc.leftMargin, 10 * mm, company.footer)
        canvas.drawRightString(A4[0] - doc.rightMargin, 10 * mm, f"Página {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=12 * mm,
        bottomMargin=18 * mm,
        title=f"Pedido {order.id or ''} - {order.customer_name}",
        author=company.name,
    )
    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    return output
