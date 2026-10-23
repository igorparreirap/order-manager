from decimal import Decimal

import pytest

from order_manager.services.product_import import import_products_csv, parse_products_csv
from order_manager.storage import ProductRepository


def test_import_utf8(tmp_path, db):
    csv_file = tmp_path / "p.csv"
    csv_file.write_text("codigo;nome;preco\n1;Pão;10,50\n2;Bolo;7.00\n", encoding="utf-8")
    result = import_products_csv(csv_file, ProductRepository(db))
    assert result.imported == 2
    assert ProductRepository(db).get("1").price == Decimal("10.50")


def test_import_windows_encoding(tmp_path):
    csv_file = tmp_path / "p.csv"
    csv_file.write_bytes("codigo;nome;preco\n1;Pão de queijo;10\n".encode("cp1252"))
    products, errors = parse_products_csv(csv_file)
    assert products[0].name == "PÃO DE QUEIJO"
    assert errors == []


def test_invalid_rows_are_reported(tmp_path):
    csv_file = tmp_path / "p.csv"
    csv_file.write_text("codigo;nome;preco\n1;A;abc\n;B;1\n3;C;2\n", encoding="utf-8")
    products, errors = parse_products_csv(csv_file)
    assert [p.code for p in products] == ["3"]
    assert len(errors) == 2
    assert errors[0].startswith("Linha 2")


def test_custom_columns(tmp_path):
    csv_file = tmp_path / "p.csv"
    csv_file.write_text("cod,produto,valor\n1,A,1.5\n", encoding="utf-8")
    products, _ = parse_products_csv(
        csv_file, code_column="cod", name_column="produto", price_column="valor", delimiter=","
    )
    assert products[0].price == Decimal("1.50")


def test_missing_columns(tmp_path):
    csv_file = tmp_path / "p.csv"
    csv_file.write_text("x;y\n1;2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Colunas ausentes"):
        parse_products_csv(csv_file)
