"""Domain entities.

Money is always represented as :class:`decimal.Decimal` rounded to cents. Using floats
for money leads to rounding errors (``0.1 + 0.2 != 0.3``), which is unacceptable in
an order total.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from order_manager.domain.formatting import digits_only, format_zip_code, to_money


class ValidationError(ValueError):
    """Raised when an entity violates a business rule."""


class PaymentMethod(str, Enum):
    """Accepted payment methods. The value is the label shown to the user."""

    ON_DELIVERY = "Na entrega"
    PIX = "PIX"
    CARD = "Cartão"
    CASH = "Dinheiro"

    @classmethod
    def from_label(cls, label: str) -> PaymentMethod:
        for method in cls:
            if method.value == label:
                return method
        raise ValidationError(f"Forma de pagamento inválida: {label!r}")


@dataclass
class Address:
    zip_code: str = ""
    street: str = ""
    number: str = ""
    district: str = ""
    city: str = ""
    state: str = ""

    def __post_init__(self) -> None:
        self.zip_code = digits_only(self.zip_code)
        self.state = self.state.strip().upper()

    def street_line(self) -> str:
        """``Rua X, 123 - Bairro`` (empty parts are skipped)."""
        street = ", ".join(part for part in (self.street, self.number) if part)
        return " - ".join(part for part in (street, self.district) if part)

    def city_line(self) -> str:
        """``Cidade/UF - CEP: 00000-000`` (empty parts are skipped)."""
        city = "/".join(part for part in (self.city, self.state) if part)
        zip_part = f"CEP: {format_zip_code(self.zip_code)}" if self.zip_code else ""
        return " - ".join(part for part in (city, zip_part) if part)

    def is_empty(self) -> bool:
        return not any((self.zip_code, self.street, self.number, self.district, self.city, self.state))


@dataclass
class Customer:
    name: str
    contact: str = ""
    phone: str = ""
    address: Address = field(default_factory=Address)
    id: int | None = None

    def __post_init__(self) -> None:
        self.name = " ".join(self.name.split())
        if not self.name:
            raise ValidationError("O nome do cliente é obrigatório.")
        self.phone = digits_only(self.phone)


@dataclass
class Product:
    code: str
    name: str
    price: Decimal

    def __post_init__(self) -> None:
        self.code = self.code.strip()
        self.name = " ".join(self.name.split()).upper()
        if not self.code:
            raise ValidationError("O código do produto é obrigatório.")
        if not self.name:
            raise ValidationError("O nome do produto é obrigatório.")
        self.price = to_money(self.price)
        if self.price < 0:
            raise ValidationError("O preço não pode ser negativo.")


@dataclass
class OrderItem:
    product_code: str
    product_name: str
    quantity: int
    unit_price: Decimal

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValidationError(f"Quantidade inválida para {self.product_name!r}.")
        self.unit_price = to_money(self.unit_price)
        if self.unit_price < 0:
            raise ValidationError(f"Preço inválido para {self.product_name!r}.")

    @property
    def total(self) -> Decimal:
        return to_money(self.unit_price * self.quantity)

    @classmethod
    def from_product(cls, product: Product, quantity: int) -> OrderItem:
        return cls(product.code, product.name, quantity, product.price)


@dataclass
class Order:
    customer_name: str
    order_date: date
    payment_method: PaymentMethod
    items: list[OrderItem] = field(default_factory=list)
    contact: str = ""
    phone: str = ""
    address: Address = field(default_factory=Address)
    id: int | None = None
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        self.customer_name = " ".join(self.customer_name.split())
        self.phone = digits_only(self.phone)

    @property
    def total(self) -> Decimal:
        return to_money(sum((item.total for item in self.items), Decimal("0")))

    @property
    def is_new(self) -> bool:
        return self.id is None

    def validate(self) -> None:
        """Raise :class:`ValidationError` if the order cannot be saved."""
        if not self.customer_name:
            raise ValidationError("Informe o cliente.")
        if not self.items:
            raise ValidationError("Adicione ao menos um produto ao pedido.")
