"""Where the application stores its data.

Data lives in the user's data directory (e.g. ``%LOCALAPPDATA%\\OrderManager`` on
Windows) instead of the current working directory, so the program behaves the same no
matter where it is started from. Set ``ORDER_MANAGER_HOME`` to override it (useful for
portable installs and tests).
"""

from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_data_dir

APP_NAME = "OrderManager"
ASSETS_DIR = Path(__file__).parent / "assets"
DEFAULT_LOGO = ASSETS_DIR / "logo.png"


def app_home() -> Path:
    override = os.environ.get("ORDER_MANAGER_HOME")
    home = Path(override) if override else Path(user_data_dir(APP_NAME, appauthor=False))
    home.mkdir(parents=True, exist_ok=True)
    return home


def database_path() -> Path:
    return app_home() / "orders.db"


def settings_path() -> Path:
    return app_home() / "settings.json"


def log_path() -> Path:
    return app_home() / "order-manager.log"
