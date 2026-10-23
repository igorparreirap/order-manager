"""User settings persisted as JSON."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from order_manager.paths import DEFAULT_LOGO

logger = logging.getLogger(__name__)


@dataclass
class Settings:
    theme: str = "light"  # "light" | "dark"
    printer_port: str = ""
    printer_baudrate: int = 9600
    print_copies: int = 1
    open_pdf_after_save: bool = True
    company_name: str = "Minha Empresa"
    company_footer: str = "Obrigado pela preferência!"
    logo_path: str = ""

    @property
    def logo(self) -> Path | None:
        """The configured logo, falling back to the bundled one."""
        custom = Path(self.logo_path) if self.logo_path else None
        if custom and custom.is_file():
            return custom
        return DEFAULT_LOGO if DEFAULT_LOGO.is_file() else None


class SettingsStore:
    """Loads and saves :class:`Settings`, tolerating missing or corrupted files."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.settings = self._load()

    def _load(self) -> Settings:
        if not self.path.exists():
            return Settings()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.exception("Could not read %s; using default settings", self.path)
            return Settings()
        known = {f.name for f in fields(Settings)}
        return Settings(**{key: value for key, value in data.items() if key in known})

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self.settings), indent=2, ensure_ascii=False), "utf-8")
        tmp.replace(self.path)  # atomic: never leaves a half-written file behind

    def update(self, **changes: object) -> None:
        for key, value in changes.items():
            if not hasattr(self.settings, key):
                raise AttributeError(f"Unknown setting: {key}")
            setattr(self.settings, key, value)
        self.save()
