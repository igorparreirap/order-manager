# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [2.0.0] - 2026-10-23

Complete rewrite of version 1, which was used in production by a frozen-food distributor.

### Added
- SQLite database with versioned migrations (previously JSON files).
- Order search by date range, ignoring accents ("pao" finds "Pão").
- Deleting products and orders, with confirmation.
- Product CSV import from the UI and the command line, reporting invalid lines.
- `seed-demo` command that creates fictitious demo data.
- Configurable company name, footer, logo and number of receipt copies.
- PDF with automatic pagination, repeated table header and page numbers.
- Consistent database backups using SQLite's online backup API.
- Rotating log file.
- Automated tests (pytest), linting (ruff) and CI on GitHub Actions.

### Fixed
- Orders could be overwritten because each screen kept its own in-memory copy of the data.
- Save errors were silently ignored (`except: pass`).
- Changing a quantity after removing a row recalculated the wrong row.
- Money stored as `float` caused rounding errors. It now uses `Decimal`, stored as cents.
- Timestamp-based order IDs could collide.
- The app depended on the working directory to find its files.
- Bold receipt text used an argument removed in python-escpos 3.

## [1.0.0] - 2025

- First version: order entry, product and customer records, PDF, thermal printing and WhatsApp.
