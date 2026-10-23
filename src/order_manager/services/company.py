"""Company information printed on receipts and PDFs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CompanyInfo:
    name: str
    footer: str = ""
    logo: Path | None = None
