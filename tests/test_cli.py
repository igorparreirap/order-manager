from order_manager.__main__ import main
from order_manager.context import AppContext


def test_import_products_command(tmp_path, capsys):
    csv_file = tmp_path / "p.csv"
    csv_file.write_text("codigo;nome;preco\n1;A;1\n", encoding="utf-8")
    assert main(["import-products", str(csv_file)]) == 0
    assert "1 produtos importados" in capsys.readouterr().out
    ctx = AppContext.create()
    assert ctx.products.get("1") is not None
    ctx.close()


def test_seed_demo_command():
    assert main(["seed-demo"]) == 0
    ctx = AppContext.create()
    assert len(ctx.orders.search()) == 5
    ctx.close()
