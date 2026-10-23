import json
import sqlite3

import pytest

from order_manager.config import Settings, SettingsStore
from order_manager.demo import seed_demo_data
from order_manager.paths import DEFAULT_LOGO
from order_manager.services.backup import create_backup


def test_settings_roundtrip(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    store.update(theme="dark", print_copies=2)
    assert SettingsStore(tmp_path / "settings.json").settings.print_copies == 2


def test_corrupted_settings_fall_back_to_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{not json", encoding="utf-8")
    assert SettingsStore(path).settings == Settings()


def test_unknown_keys_are_ignored(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"theme": "dark", "old_key": 1}), encoding="utf-8")
    assert SettingsStore(path).settings.theme == "dark"


def test_unknown_setting_cannot_be_set(tmp_path):
    with pytest.raises(AttributeError):
        SettingsStore(tmp_path / "s.json").update(nope=1)


def test_logo_falls_back_to_default(tmp_path):
    assert Settings(logo_path=str(tmp_path / "missing.png")).logo == DEFAULT_LOGO


def test_backup_copies_database(tmp_path, ctx):
    seed_demo_data(ctx)
    ctx.settings.save()
    target = create_backup(ctx.db, ctx.settings.path, tmp_path / "backups")
    copy = sqlite3.connect(target / "orders.db")
    assert copy.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 5
    assert (target / "settings.json").exists()


def test_demo_data(ctx):
    seed_demo_data(ctx)
    assert len(ctx.products.list()) == 15
    assert len(ctx.customers.list_names()) == 4
    assert all(order.items for order in ctx.orders.search())
