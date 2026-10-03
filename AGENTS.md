# Django MoneyMoney - Architecture & Development Guide

## 1. Stack & Environment
- **Framework**: Django & Django REST Framework (DRF) | **Deps**: Poetry | **DB**: PostgreSQL
- **Testing**: `poetry run python manage.py test` (Answer `yes` if prompted to recreate `test_xulpymoney`).

## 2. Key Models & Constraints
- **Products**: System (`id < 100M`) vs Personal (`id >= 100M`). A product must have at least one quote before creating operations.
- **Investments & Operations**: `Investments` binds a product to an account. `Investmentsoperations` tracks buy/sell/add operations.
- **Associated Ledger Records (`Accountsoperations`)**: `Investmentsoperations.save()` calculates linked `Accountsoperations` via `IOS`.
- **Validation**: `Investmentsoperations.clean()` forbids future datetimes (`self.datetime > timezone.now()`).
- **Dividends & DPS**: `Dividends` links 1-to-1 with `Accountsoperations`. `EstimationsDps` strictly enforces unique `(product, year)`.

## 3. Stock Splits Logic
- **Hooks**: `Splits.save()` reverts previous factors then applies new factors. `Splits.delete()` reverts adjustments.
- **Affected Models**: `Quotes`, `Investmentsoperations`, `Investments`, `Dividends`, `Orders`, `Dps`, `EstimationsDps`.
- **Date Filters**: `DateTimeField` uses `datetime__lt=split.datetime`; `DateField` uses `date__lt=split.datetime.date()`.
- **Listing without Splits**: All models implement `list_without_splits()` classmethod to retrieve pre-split historical dictionaries.
- **Testing Splits**: Use values divisible by 6 (e.g. `12.0`, `24.0`, `120.0`) to avoid 6-decimal rounding assertion diffs. Tests are unified in `moneymoney/tests/test_splits.py`.

## 4. Key Endpoints
- **Accounts Balance (`/api/accounts/{id}/balance/`)**: Supports `year`, `month`, `datetime` filters. Defaults to current balance (`timezone.now()`). Validates mutually exclusive or malformed parameters with HTTP 400.
- **Alerts (`/alerts/`)**: Detects `orders_expired`, `banks_inactive_with_balance`, `accounts_inactive_with_balance`, `investments_inactive_with_balance`, `investments_transfers_unfinished`, and `products_without_quotes_before_operations` (returning URL and earliest operation datetime needing a quote).

## 5. Performance & Caching
- **Indexes (Migration `0067`)**: Composite indexes on `(products, datetime)`, `(investments, datetime)`, `(accounts, datetime)`, `(orders, executed, expiration)`, etc.
- **Cache**: Request-level (L1) and Server-level (L2) for quotes. Call `cache.clear()` when modifying historical data.

## 6. Deployment & Docker
- **Images**: `turulomio/django_moneymoney:latest` (production) and `turulomio/django_moneymoney:e2e` (standalone test environment with embedded PostgreSQL 16, migrations, and fixtures).
- **CI**: `.github/workflows/django.yml` builds, tests hermetically, and publishes on push to `main`.

## 7. Development Rules
- When modifying code, keep docstrings, `README.md`, and this `AGENTS.md` up to date.
