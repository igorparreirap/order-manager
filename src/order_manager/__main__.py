"""Command-line entry point.

order-manager                         # opens the desktop app
order-manager import-products x.csv   # imports a product catalogue
order-manager seed-demo               # fills the database with fictitious demo data
"""

from __future__ import annotations

import argparse
import contextlib
import logging
import sys
from logging.handlers import RotatingFileHandler

from order_manager import __version__, paths


def configure_logging(verbose: bool = False) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    with contextlib.suppress(OSError):  # logging to file is best-effort
        handlers.append(
            RotatingFileHandler(paths.log_path(), maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        )
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def run_gui() -> int:
    from PyQt5.QtCore import QLocale, Qt
    from PyQt5.QtWidgets import QApplication

    from order_manager.context import AppContext
    from order_manager.ui.main_window import MainWindow

    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    QLocale.setDefault(QLocale(QLocale.Portuguese, QLocale.Brazil))

    app = QApplication(sys.argv)
    app.setApplicationName(paths.APP_NAME)
    ctx = AppContext.create()
    window = MainWindow(ctx)
    window.show()
    try:
        return app.exec_()
    finally:
        ctx.close()


def run_import(args: argparse.Namespace) -> int:
    from order_manager.context import AppContext
    from order_manager.services.product_import import import_products_csv

    ctx = AppContext.create()
    try:
        result = import_products_csv(
            args.file,
            ctx.products,
            code_column=args.code_column,
            name_column=args.name_column,
            price_column=args.price_column,
            delimiter=args.delimiter,
        )
    finally:
        ctx.close()
    print(f"{result.imported} produtos importados.")
    for error in result.errors:
        print(f"  ignorado: {error}", file=sys.stderr)
    return 0


def run_seed(_args: argparse.Namespace) -> int:
    from order_manager.context import AppContext
    from order_manager.demo import seed_demo_data

    ctx = AppContext.create()
    try:
        seed_demo_data(ctx)
    finally:
        ctx.close()
    print(f"Dados de demonstração criados em {paths.database_path()}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="order-manager", description=__doc__.splitlines()[0])
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="logs detalhados")
    sub = parser.add_subparsers(dest="command")

    imp = sub.add_parser("import-products", help="importa produtos de um CSV")
    imp.add_argument("file")
    imp.add_argument("--code-column", default="codigo")
    imp.add_argument("--name-column", default="nome")
    imp.add_argument("--price-column", default="preco")
    imp.add_argument("--delimiter", default=";")
    imp.set_defaults(func=run_import)

    seed = sub.add_parser("seed-demo", help="cria dados fictícios para demonstração")
    seed.set_defaults(func=run_seed)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(args.verbose)
    if getattr(args, "func", None):
        return args.func(args)
    return run_gui()


if __name__ == "__main__":
    sys.exit(main())
