from datetime import date
from decimal import Decimal

import pytest

from order_manager.domain.models import Customer, OrderItem, Product, ValidationError
from order_manager.storage import CustomerRepository, Database, OrderRepository, ProductRepository
from order_manager.storage.database import MIGRATIONS


def test_migrations_are_applied_once(tmp_path):
    path = tmp_path / "orders.db"
    Database(path).close()
    db = Database(path)  # reopening must not fail or re-run migrations
    assert db.schema_version == len(MIGRATIONS)
    db.close()


class TestProductRepository:
    def test_save_and_list_in_numeric_order(self, db, products):
        repo = ProductRepository(db)
        for product in products:
            repo.save(product)
        assert [p.code for p in repo.list()] == ["1", "2", "10"]

    def test_search_is_accent_insensitive(self, db, products):
        repo = ProductRepository(db)
        repo.save_many(products)
        assert [p.code for p in repo.list("pao")] == ["1"]
        assert [p.code for p in repo.list("10")] == ["10"]

    def test_search_escapes_like_wildcards(self, db, products):
        repo = ProductRepository(db)
        repo.save_many(products)
        assert repo.list("%") == []

    def test_update_and_rename(self, db):
        repo = ProductRepository(db)
        repo.save(Product("1", "A", 1))
        repo.save(Product("5", "A renamed", 2), original_code="1")
        assert repo.get("1") is None
        assert repo.get("5").price == Decimal("2.00")

    def test_find_by_name(self, db, products):
        repo = ProductRepository(db)
        repo.save_many(products)
        assert repo.find_by_name("pao de queijo 1kg").code == "1"

    def test_next_code_ignores_non_numeric(self, db):
        repo = ProductRepository(db)
        assert repo.next_code() == "1"
        repo.save_many([Product("9", "A", 1), Product("ABC", "B", 1)])
        assert repo.next_code() == "10"

    def test_delete(self, db, products):
        repo = ProductRepository(db)
        repo.save_many(products)
        repo.delete("1")
        assert repo.get("1") is None


class TestCustomerRepository:
    def test_upsert_by_name(self, db):
        repo = CustomerRepository(db)
        repo.save(Customer("José Souza", phone="11 90000-0000"))
        repo.save(Customer("JOSE SOUZA", contact="Zé"))
        assert repo.list_names() == ["JOSE SOUZA"]
        assert repo.get_by_name("josé souza").contact == "Zé"

    def test_unknown_customer(self, db):
        assert CustomerRepository(db).get_by_name("ninguém") is None


class TestOrderRepository:
    def test_save_assigns_id_and_roundtrips(self, db, order):
        repo = OrderRepository(db)
        saved = repo.save(order)
        assert saved.id == 1
        loaded = repo.get(saved.id)
        assert loaded.items == order.items
        assert loaded.total == Decimal("81.50")
        assert loaded.address == order.address

    def test_update_replaces_items(self, db, order):
        repo = OrderRepository(db)
        saved = repo.save(order)
        saved.items = [OrderItem("9", "OUTRO", 1, "5")]
        repo.save(saved)
        assert [i.product_code for i in repo.get(saved.id).items] == ["9"]
        assert len(repo.search()) == 1

    def test_update_of_deleted_order_fails(self, db, order):
        repo = OrderRepository(db)
        saved = repo.save(order)
        repo.delete(saved.id)
        with pytest.raises(LookupError):
            repo.save(saved)

    def test_invalid_order_is_not_saved(self, db, order):
        order.items = []
        with pytest.raises(ValidationError):
            OrderRepository(db).save(order)
        assert OrderRepository(db).search() == []

    def test_failed_transaction_rolls_back(self, db, order, monkeypatch):
        repo = OrderRepository(db)
        order.items.append(OrderItem("3", "X", 1, 1))
        # Corrupt the last item after validation so the INSERT violates a CHECK constraint.
        monkeypatch.setattr(order.items[-1], "quantity", -1)
        with pytest.raises(Exception):  # noqa: B017
            repo.save(order)
        assert repo.search() == []

    def test_search_by_customer_product_and_code(self, db, order):
        repo = OrderRepository(db)
        repo.save(order)
        assert len(repo.search("padaria")) == 1
        assert len(repo.search("pao de queijo")) == 1
        assert len(repo.search("2")) == 1
        assert repo.search("inexistente") == []

    def test_search_by_date_range_newest_first(self, db, order):
        repo = OrderRepository(db)
        for day in (10, 20, 15):
            order.id = None
            order.order_date = date(2026, 1, day)
            repo.save(order)
        result = repo.search(start=date(2026, 1, 12), end=date(2026, 1, 31))
        assert [o.order_date.day for o in result] == [20, 15]

    def test_deleting_order_deletes_items(self, db, order):
        repo = OrderRepository(db)
        saved = repo.save(order)
        repo.delete(saved.id)
        count = db.connection.execute("SELECT COUNT(*) FROM order_items").fetchone()[0]
        assert count == 0
