# Django MoneyMoney - Project Knowledge & Architecture Guide

This document summarizes the core components, design decisions, and learned lessons for the **django_moneymoney** project. Use this as a reference for future updates or development.

---

## 1. Project Stack & Environment
- **Core Framework**: Django with Django REST Framework (DRF)
- **Dependency Management**: Poetry (`poetry.lock`, `pyproject.toml`)
- **Testing**: Django test runner executed via Poetry (`poetry run python manage.py test`)
- **Database**: PostgreSQL (requires setting up a test database; if it exists during test run, answer `yes` when prompted to destroy and recreate it).

---

## 2. Key Models & Relationships

- **Products**: Represents financial instruments (shares, ETFs, CFDs, futures).
  - System products have IDs `< 100,000,000`. Personal products have IDs `>= 100,000,000`.
- **Quotes**: Historical price data for a product. A product must have at least one quote for transaction/investment operations to be successfully created.
- **Investments**: Groups a product with a specific account. Holds metadata like `selling_price`, `selling_expiration`, etc.
- **Investmentsoperations**: Tracks buy/sell operations (shares, price, taxes, commission) for an investment.
- **Orders**: Tracks broker order limits (shares, price, expiration, executed status) linked to an investment.
- **Dividends**: Tracks dividend payments (gross, net, taxes, commission, dps) for an investment. Linked 1-to-1 with `Accountsoperations`.
- **Dps (Dividend Per Share)**: Dividend history for products.
- **EstimationsDps**: Future dividend estimations for a product per year. **Note**: Unique constraint/validation in `save()` permits only *one* `EstimationsDps` record per product-year combination. Trying to create a second one with the same year and product will overwrite the first one.

---

## 3. Stock Splits Logic

The `Splits` model implements database-wide adjustments when a stock split occurs:
- **Save Hook**: When a split is created or updated, the system first calls `revert_adjustments()` on the original split values (if updating), saves the split, and then runs `apply_adjustments()`.
- **Delete Hook**: Deleting a split automatically triggers `revert_adjustments()`.
- **Affected Models**:
  - **Quotes**: Adjusts `quote` values.
  - **Investmentsoperations**: Adjusts `shares` and `price`.
  - **Investments**: Adjusts `selling_price`.
  - **Dividends**: Adjusts `dps`.
  - **Orders**: Adjusts `shares` and `price` (added in the latest update).
  - **Dps**: Adjusts `gross` (added in the latest update).
  - **EstimationsDps**: Adjusts `estimation` (added in the latest update).

### Important Date Filters in Splits
Because models use different date types:
- Models with `datetime` (DateTimeField) use `datetime__lt=self.datetime` (e.g. `Quotes`, `Investmentsoperations`, `Dividends`).
- Models with `date` (DateField) use `date__lt=self.datetime.date()` or `date_estimation__lt=self.datetime.date()` (e.g. `Orders`, `Dps`, `EstimationsDps`).

---

## 4. Testing Guidelines

- **Test Suite Execution**:
  ```bash
  poetry run python manage.py test
  ```
- **Rounding / Precision Issues**:
  SQLite and database dec-fields round values to 6 decimal places. When testing splits with divisions and multiplications (e.g., 2-for-1 and 3-for-1 splits), **always use mock values that are divisible by 6** (such as `12.0`, `24.0`, `120.0`) for price, shares, gross, and estimation values. This avoids assertion failures due to minor floating-point or division remainder discrepancies (e.g. asserting `50.000000` but getting `50.000001`).
- **Unified Tests for Splits**:
  All stock split adjustment logic (Quotes, Investmentsoperations, Investments, Dividends, Orders, Dps, EstimationsDps) is unified within the single integration test case `test_Splits_integration_flow` in `moneymoney/tests/test_splits.py`.

---

## 5. Performance & Caching
- The project implements L1 (Request-level) and L2 (Server-level) caching for Quotes, speeding up queries up to 200x over direct database lookups.
- Avoid bypassing ORM querysets directly when updating unless necessary, but make sure to call `cache.clear()` when altering quotes/splits historical data.
