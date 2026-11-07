"""SQLite connection management and schema migrations.

A single :class:`Database` instance is shared by the whole application, so every
screen reads and writes the same data and no screen can overwrite another's changes.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from order_manager.domain.formatting import normalize_text

logger = logging.getLogger(__name__)

# Each entry upgrades the schema by one version. Never edit a released migration:
# append a new one instead, so existing databases can be upgraded in place.
MIGRATIONS: tuple[str, ...] = (
    """
    CREATE TABLE products (
        code        TEXT PRIMARY KEY,
        name        TEXT NOT NULL,
        price_cents INTEGER NOT NULL CHECK (price_cents >= 0)
    );

    CREATE TABLE customers (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        name     TEXT NOT NULL,
        name_key TEXT NOT NULL UNIQUE,
        contact  TEXT NOT NULL DEFAULT '',
        phone    TEXT NOT NULL DEFAULT '',
        zip_code TEXT NOT NULL DEFAULT '',
        street   TEXT NOT NULL DEFAULT '',
        number   TEXT NOT NULL DEFAULT '',
        district TEXT NOT NULL DEFAULT '',
        city     TEXT NOT NULL DEFAULT '',
        state    TEXT NOT NULL DEFAULT ''
    );

    CREATE TABLE orders (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name  TEXT NOT NULL,
        order_date     TEXT NOT NULL,
        payment_method TEXT NOT NULL,
        contact        TEXT NOT NULL DEFAULT '',
        phone          TEXT NOT NULL DEFAULT '',
        zip_code       TEXT NOT NULL DEFAULT '',
        street         TEXT NOT NULL DEFAULT '',
        number         TEXT NOT NULL DEFAULT '',
        district       TEXT NOT NULL DEFAULT '',
        city           TEXT NOT NULL DEFAULT '',
        state          TEXT NOT NULL DEFAULT '',
        created_at     TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        updated_at     TEXT
    );

    CREATE TABLE order_items (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id         INTEGER NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
        position         INTEGER NOT NULL,
        product_code     TEXT NOT NULL,
        product_name     TEXT NOT NULL,
        quantity         INTEGER NOT NULL CHECK (quantity > 0),
        unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents >= 0)
    );

    CREATE INDEX idx_orders_date ON orders (order_date);
    CREATE INDEX idx_order_items_order ON order_items (order_id);
    """,
)


class Database:
    """Thin wrapper around a SQLite connection that applies pending migrations."""

    def __init__(self, path: Path | str = ":memory:") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        # Lets SQL do accent-insensitive search: normalize('Pão') == 'pao'.
        self.connection.create_function("normalize", 1, normalize_text, deterministic=True)
        self._migrate()

    @property
    def schema_version(self) -> int:
        return int(self.connection.execute("PRAGMA user_version").fetchone()[0])

    def _migrate(self) -> None:
        current = self.schema_version
        for version, script in enumerate(MIGRATIONS[current:], start=current + 1):
            logger.info("Applying database migration %d", version)
            with self.connection:
                self.connection.executescript(f"BEGIN; {script} PRAGMA user_version = {version};")

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Commit on success, roll back on any exception."""
        with self.connection:
            yield self.connection

    def backup_to(self, destination: Path | str) -> None:
        """Write a consistent copy of the database using SQLite's online backup API."""
        target = sqlite3.connect(str(destination))
        try:
            self.connection.backup(target)
        finally:
            target.close()

    def close(self) -> None:
        self.connection.close()
