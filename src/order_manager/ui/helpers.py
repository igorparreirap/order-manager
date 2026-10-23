"""Small UI helpers shared by the pages."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QCompleter, QWidget
from qfluentwidgets import InfoBar, InfoBarPosition

logger = logging.getLogger(__name__)


def open_file(path: Path | str) -> None:
    """Open ``path`` with the operating system's default application."""
    try:
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except OSError:
        logger.exception("Could not open %s", path)


def make_completer(items: list[str], parent: QWidget, contains: bool = True) -> QCompleter:
    completer = QCompleter(items, parent)
    completer.setCaseSensitivity(Qt.CaseInsensitive)
    completer.setFilterMode(Qt.MatchContains if contains else Qt.MatchStartsWith)
    return completer


def _notify(kind: str, parent: QWidget, title: str, content: str) -> None:
    getattr(InfoBar, kind)(
        title=title,
        content=content,
        orient=Qt.Horizontal,
        isClosable=True,
        position=InfoBarPosition.TOP_RIGHT,
        duration=4000 if kind != "error" else -1,
        parent=parent.window(),
    )


def notify_success(parent: QWidget, content: str, title: str = "Pronto") -> None:
    _notify("success", parent, title, content)


def notify_info(parent: QWidget, content: str, title: str = "Info") -> None:
    _notify("info", parent, title, content)


def notify_warning(parent: QWidget, content: str, title: str = "Atenção") -> None:
    _notify("warning", parent, title, content)


def notify_error(parent: QWidget, content: str, title: str = "Erro") -> None:
    _notify("error", parent, title, content)
