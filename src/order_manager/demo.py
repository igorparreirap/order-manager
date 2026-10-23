"""Fictitious demo data, used for screenshots and to try the app quickly.

Every name, phone number and address here is invented.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from order_manager.context import AppContext
from order_manager.domain.models import Address, Customer, Order, OrderItem, PaymentMethod
from order_manager.paths import ASSETS_DIR
from order_manager.services.product_import import import_products_csv

SAMPLE_CSV = ASSETS_DIR / "produtos_exemplo.csv"

CUSTOMERS = [
    Customer(
        "Padaria Sol Nascente",
        contact="Ana Ribeiro",
        phone="11900000001",
        address=Address("01001000", "Praça da Sé", "100", "Sé", "São Paulo", "SP"),
    ),
    Customer(
        "Lanchonete Bom Sabor",
        contact="Carlos Mendes",
        phone="21900000002",
        address=Address("20040020", "Avenida Rio Branco", "45", "Centro", "Rio de Janeiro", "RJ"),
    ),
    Customer(
        "Mercadinho Esquina Feliz",
        contact="Juliana Costa",
        phone="31900000003",
        address=Address("30130010", "Avenida Afonso Pena", "1500", "Centro", "Belo Horizonte", "MG"),
    ),
    Customer(
        "Café da Praça",
        contact="Roberto Lima",
        phone="61900000004",
        address=Address("70040010", "Eixo Monumental", "10", "Asa Norte", "Brasília", "DF"),
    ),
]

ORDERS = [  # (customer index, days ago, payment, [(product code, quantity)])
    (0, 0, PaymentMethod.PIX, [("2", 3), ("5", 2), ("11", 1)]),
    (1, 1, PaymentMethod.ON_DELIVERY, [("12", 4), ("13", 4), ("14", 10)]),
    (2, 3, PaymentMethod.CARD, [("1", 12), ("4", 20)]),
    (3, 6, PaymentMethod.CASH, [("8", 5), ("9", 5), ("10", 3)]),
    (0, 9, PaymentMethod.PIX, [("2", 2), ("6", 2)]),
]


def seed_demo_data(ctx: AppContext, csv_path: Path = SAMPLE_CSV) -> None:
    if csv_path.exists():
        import_products_csv(csv_path, ctx.products)
    for customer in CUSTOMERS:
        ctx.customers.save(customer)
    for customer_index, days_ago, payment, lines in ORDERS:
        customer = CUSTOMERS[customer_index]
        items = []
        for code, quantity in lines:
            product = ctx.products.get(code)
            if product:
                items.append(OrderItem.from_product(product, quantity))
        if items:
            ctx.orders.save(
                Order(
                    customer_name=customer.name,
                    order_date=date.today() - timedelta(days=days_ago),
                    payment_method=payment,
                    contact=customer.contact,
                    phone=customer.phone,
                    address=customer.address,
                    items=items,
                )
            )
