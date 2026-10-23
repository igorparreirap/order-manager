"""Creates timestamped backups of the database and settings."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from order_manager.storage.database import Database


def create_backup(db: Database, settings_file: Path | None, destination_dir: Path | str) -> Path:
    target = Path(destination_dir) / f"backup-pedidos-{datetime.now():%Y-%m-%d_%H%M%S}"
    target.mkdir(parents=True, exist_ok=False)
    db.backup_to(target / "orders.db")
    if settings_file and settings_file.exists():
        shutil.copy2(settings_file, target / settings_file.name)
    return target
