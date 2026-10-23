"""Repositories translate between domain entities and database rows."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime

from order_manager.domain.formatting import from_cents, normalize_text, to_cents
from order_manager.domain.models import (
    Address,
    Customer,
    Order,
    OrderItem,
    PaymentMethod,
    Product,
)
from order_manager.storage.database import Database

_ADDRESS_COLUMNS = ("zip_code", "street", "number", "district", "city", "state")


def _address_values(address: Address) -> tuple[str, ...]:
    return tuple(getattr(address, column) for column in _ADDRESS_COLUMNS)


def _address_from_row(row: sqlite3.Row) -> Address:
    return Address(**{column: row[column] for column in _ADDRESS_COLUMNS})


def _like(text: str) -> str:
    """Build an accent/case-insensitive LIKE pattern, escaping wildcards."""
    escaped = normalize_text(text).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


class ProductRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def list(self, search: str = "") -> list[Product]:
        rows = self._db.connection.execute(
            """
            SELECT code, name, price_cents FROM products
            WHERE ? = '' OR normalize(code) LIKE ? ESCAPE '\\' OR normalize(name) LIKE ? ESCAPE '\\'
            -- numeric codes first, in numeric order; then the others alphabetically
            ORDER BY code GLOB '*[^0-9]*', CAST(code AS INTEGER), code
            """,
            (search.strip(), _like(search), _like(search)),
        ).fetchall()
        return [self._from_row(row) for row in rows]

    def get(self, code: str) -> Product | None:
        row = self._db.connection.execute(
            "SELECT code, name, price_cents FROM products WHERE code = ?", (code.strip(),)
        ).fetchone()
        return self._from_row(row) if row else None

    def find_by_name(self, name: str) -> Product | None:
        row = self._db.connection.execute(
            "SELECT code, name, price_cents FROM products WHERE normalize(name) = ?",
            (normalize_text(name),),
        ).fetchone()
        return self._from_row(row) if row else None

    def save(self, product: Product, original_code: str | None = None) -> None:
        """Insert or update ``product``. Pass ``original_code`` when the code was changed."""
        with self._db.transaction() as conn:
            if original_code and original_code != product.code:
                conn.execute("DELETE FROM products WHERE code = ?", (original_code,))
            conn.execute(
                """
                INSERT INTO products (code, name, price_cents) VALUES (?, ?, ?)
                ON CONFLICT (code) DO UPDATE SET name = excluded.name,
                                                 price_cents = excluded.price_cents
                """,
                (product.code, product.name, to_cents(product.price)),
            )

    def save_many(self, products: list[Product]) -> int:
        with self._db.transaction() as conn:
            conn.executemany(
                """
                INSERT INTO products (code, name, price_cents) VALUES (?, ?, ?)
                ON CONFLICT (code) DO UPDATE SET name = excluded.name,
                                                 price_cents = excluded.price_cents
                """,
                [(p.code, p.name, to_cents(p.price)) for p in products],
            )
        return len(products)

    def delete(self, code: str) -> None:
        with self._db.transaction() as conn:
            conn.execute("DELETE FROM products WHERE code = ?", (code,))

    def next_code(self) -> str:
        row = self._db.connection.execute(
            "SELECT MAX(CAST(code AS INTEGER)) FROM products WHERE code NOT GLOB '*[^0-9]*'"
        ).fetchone()
        return str((row[0] or 0) + 1)

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Product:
        return Product(row["code"], row["name"], from_cents(row["price_cents"]))


class CustomerRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def list_names(self) -> list[str]:
        rows = self._db.connection.execute("SELECT name FROM customers ORDER BY name_key")
        return [row["name"] for row in rows]

    def get_by_name(self, name: str) -> Customer | None:
        row = self._db.connection.execute(
            "SELECT * FROM customers WHERE name_key = ?", (normalize_text(name),)
        ).fetchone()
        if row is None:
            return None
        return Customer(
            id=row["id"],
            name=row["name"],
            contact=row["contact"],
            phone=row["phone"],
            address=_address_from_row(row),
        )

    def save(self, customer: Customer) -> Customer:
        """Insert or update a customer, matching by (accent-insensitive) name."""
        with self._db.transaction() as conn:
            conn.execute(
                f"""
                INSERT INTO customers (name, name_key, contact, phone, {", ".join(_ADDRESS_COLUMNS)})
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (name_key) DO UPDATE SET
                    name = excluded.name, contact = excluded.contact, phone = excluded.phone,
                    {", ".join(f"{c} = excluded.{c}" for c in _ADDRESS_COLUMNS)}
                """,
                (
                    customer.name,
                    normalize_text(customer.name),
                    customer.contact,
                    customer.phone,
                    *_address_values(customer.address),
                ),
            )
        saved = self.get_by_name(customer.name)
        assert saved is not None
        return saved


class OrderRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def save(self, order: Order) -> Order:
        """Insert a new order or replace an existing one (including its items)."""
        order.validate()
        header = (
            order.customer_name,
            order.order_date.isoformat(),
            order.payment_method.value,
            order.contact,
            order.phone,
            *_address_values(order.address),
        )
        with self._db.transaction() as conn:
            if order.is_new:
                cursor = conn.execute(
                    f"""
                    INSERT INTO orders (customer_name, order_date, payment_method, contact, phone,
                                        {", ".join(_ADDRESS_COLUMNS)})
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    header,
                )
                order.id = cursor.lastrowid
            else:
                cursor = conn.execute(
                    f"""
                    UPDATE orders SET customer_name = ?, order_date = ?, payment_method = ?,
                        contact = ?, phone = ?, {", ".join(f"{c} = ?" for c in _ADDRESS_COLUMNS)},
                        updated_at = datetime('now', 'localtime')
                    WHERE id = ?
                    """,
                    (*header, order.id),
                )
                if cursor.rowcount == 0:
                    raise LookupError(f"Pedido #{order.id} não existe mais.")
                conn.execute("DELETE FROM order_items WHERE order_id = ?", (order.id,))
            conn.executemany(
                """
                INSERT INTO order_items (order_id, position, product_code, product_name,
                                         quantity, unit_price_cents)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (order.id, pos, i.product_code, i.product_name, i.quantity, to_cents(i.unit_price))
                    for pos, i in enumerate(order.items)
                ],
            )
        saved = self.get(order.id)  # type: ignore[arg-type]
        assert saved is not None
        return saved

    def get(self, order_id: int) -> Order | None:
        row = self._db.connection.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        return self._hydrate([row])[0] if row else None

    def delete(self, order_id: int) -> None:
        with self._db.transaction() as conn:
            conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))

    def search(
        self,
        text: str = "",
        start: date | None = None,
        end: date | None = None,
    ) -> list[Order]:
        """Search by customer, product name or product code, optionally within a date range.

        Results are ordered from the most recent to the oldest.
        """
        pattern = _like(text)
        rows = self._db.connection.execute(
            """
            SELECT o.* FROM orders o
            WHERE (:text = '' OR normalize(o.customer_name) LIKE :pattern ESCAPE '\\'
                   OR EXISTS (SELECT 1 FROM order_items i
                              WHERE i.order_id = o.id
                                AND (normalize(i.product_name) LIKE :pattern ESCAPE '\\'
                                     OR normalize(i.product_code) LIKE :pattern ESCAPE '\\')))
              AND (:start IS NULL OR o.order_date >= :start)
              AND (:end IS NULL OR o.order_date <= :end)
            ORDER BY o.order_date DESC, o.id DESC
            """,
            {
                "text": text.strip(),
                "pattern": pattern,
                "start": start.isoformat() if start else None,
                "end": end.isoformat() if end else None,
            },
        ).fetchall()
        return self._hydrate(rows)

    def _hydrate(self, rows: list[sqlite3.Row]) -> list[Order]:
        if not rows:
            return []
        ids = [row["id"] for row in rows]
        placeholders = ", ".join("?" for _ in ids)
        items_by_order: dict[int, list[OrderItem]] = {order_id: [] for order_id in ids}
        for item in self._db.connection.execute(
            f"SELECT * FROM order_items WHERE order_id IN ({placeholders}) ORDER BY position",
            ids,
        ):
            items_by_order[item["order_id"]].append(
                OrderItem(
                    product_code=item["product_code"],
                    product_name=item["product_name"],
                    quantity=item["quantity"],
                    unit_price=from_cents(item["unit_price_cents"]),
                )
            )
        return [
            Order(
                id=row["id"],
                customer_name=row["customer_name"],
                order_date=date.fromisoformat(row["order_date"]),
                payment_method=PaymentMethod.from_label(row["payment_method"]),
                contact=row["contact"],
                phone=row["phone"],
                address=_address_from_row(row),
                items=items_by_order[row["id"]],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]
