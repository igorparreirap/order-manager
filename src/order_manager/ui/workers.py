"""Background workers, so network calls never freeze the interface."""

from __future__ import annotations

from PyQt5.QtCore import QThread, pyqtSignal

from order_manager.services.zip_code import ZipCodeError, lookup_zip_code


class ZipCodeWorker(QThread):
    found = pyqtSignal(object)  # Address
    failed = pyqtSignal(str)

    def __init__(self, zip_code: str, parent=None) -> None:
        super().__init__(parent)
        self.zip_code = zip_code

    def run(self) -> None:
        try:
            self.found.emit(lookup_zip_code(self.zip_code))
        except ZipCodeError as exc:
            self.failed.emit(str(exc))
