"""Imports a product catalogue from a CSV spreadsheet.

Expected columns (header names are configurable): ``codigo``, ``nome`` and a price
column. Spreadsheets exported from Excel on Windows are usually encoded as cp1252, so
that encoding is tried when the file is not valid UTF-8.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from pathlib import Path

from order_manager.domain.models import Product, ValidationError
from order_manager.storage.repositories import ProductRepository


@dataclass
class ImportResult:
    imported: int = 0
    errors: list[str] = field(default_factory=list)


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def parse_products_csv(
    path: Path | str,
    code_column: str = "codigo",
    name_column: str = "nome",
    price_column: str = "preco",
    delimiter: str = ";",
) -> tuple[list[Product], list[str]]:
    reader = csv.DictReader(io.StringIO(_read_text(Path(path))), delimiter=delimiter)
    missing = {code_column, name_column, price_column} - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"Colunas ausentes no CSV: {', '.join(sorted(missing))}")

    products: list[Product] = []
    errors: list[str] = []
    for line, row in enumerate(reader, start=2):  # line 1 is the header
        try:
            name = row[name_column].replace("�", "").replace("\xa0", " ")
            products.append(Product(row[code_column], name, row[price_column] or "0"))
        except (ValidationError, ValueError) as exc:
            errors.append(f"Linha {line}: {exc}")
    return products, errors


def import_products_csv(path: Path | str, repository: ProductRepository, **options: str) -> ImportResult:
    products, errors = parse_products_csv(path, **options)
    imported = repository.save_many(products)
    return ImportResult(imported=imported, errors=errors)
