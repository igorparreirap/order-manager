"""Application context: the single set of shared services injected into every screen."""

from __future__ import annotations

from dataclasses import dataclass

from order_manager import paths
from order_manager.config import SettingsStore
from order_manager.services.company import CompanyInfo
from order_manager.storage import CustomerRepository, Database, OrderRepository, ProductRepository


@dataclass
class AppContext:
    db: Database
    settings: SettingsStore
    products: ProductRepository
    customers: CustomerRepository
    orders: OrderRepository

    @classmethod
    def create(cls, db: Database | None = None, settings: SettingsStore | None = None) -> AppContext:
        db = db or Database(paths.database_path())
        return cls(
            db=db,
            settings=settings or SettingsStore(paths.settings_path()),
            products=ProductRepository(db),
            customers=CustomerRepository(db),
            orders=OrderRepository(db),
        )

    def close(self) -> None:
        self.db.close()

    @property
    def company(self) -> CompanyInfo:
        s = self.settings.settings
        return CompanyInfo(name=s.company_name, footer=s.company_footer, logo=s.logo)
