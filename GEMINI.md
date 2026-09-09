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

- Avoid bypassing ORM querysets directly when updating unless necessary, but make sure to call `cache.clear()` when altering quotes/splits historical data.

---

## 6. Listing without Splits (`list_without_splits`)
All models in `moneymoney/models.py` have a classmethod `list_without_splits(cls)` which returns a list of dictionaries representing all database entries as if splits had never occurred.
- For models unaffected by splits, it returns all records directly converted to standard Python dictionaries.
- For models affected by splits (`Quotes`, `Investmentsoperations`, `Investments`, `Dividends`, `Orders`, `Dps`, `EstimationsDps`), it determines all split factors that affect each item based on product and date/datetime ranges, and applies the reverse calculations to the values before returning them.

---

## 7. AI Assistant Guidelines & Rules
- **Documentation Maintenance**: Every time a codebase edit is made, the AI assistant **MUST** update:
  - The documentation / docstrings of the modified methods/classes.
  - The project's main [README.md](file:///home/keko/Proyectos/django_moneymoney/README.md).
  - This [GEMINI.md](file:///home/keko/Proyectos/django_moneymoney/GEMINI.md) file, to keep the project knowledge and design history completely fresh and accurate.

---

## 8. Accounts Balance Endpoint (`/api/accounts/{id}/balance/`)
- **Detail Action**: Added to `AccountsViewSet` (`@action(detail=True, methods=['get'])`).
- **Query Parameters**:
  - `year` & `month`: Calculates balance at the end of the specified month (`casts.dtaware_month_end`). Solves the frontend issue when an account has 0 operations in a given month.
  - `year` only: Calculates balance at the end of that year (`casts.dtaware_year_end`).
  - `datetime`: Calculates balance at an explicit ISO datetime.
  - *No parameters*: Defaults to current balance (`timezone.now()`).
- **Response Format**:
  Includes `id`, `name`, `datetime`, `balance_account`, `balance_user`, `balance_account_currency`, `balance_user_currency`, and `currency`.
- **Validation & Error Responses (HTTP 400 Bad Request)**:
  - Both `datetime` and `year`/`month` specified in query params.
  - `month` provided without `year`.
  - `month` is not an integer between 1 and 12.
  - `year` is not an integer between 1 and 9999.
  - `datetime` cannot be parsed as a valid ISO datetime string.

---

## 9. Alerts Endpoint (`/alerts/`)
- Returns system alerts for:
  - `orders_expired`: Limit orders that have expired.
  - `banks_inactive_with_balance`: Inactive banks with non-zero total balance.
  - `accounts_inactive_with_balance`: Inactive accounts with non-zero balance.
  - `investments_inactive_with_balance`: Inactive investments with non-zero balance.
  - `investments_transfers_unfinished`: Transfers without destination datetime set.
  - `products_without_quotes_before_operations`: Returns a list of objects containing `{"url": "<product_url>", "datetime": "<earliest_operation_datetime>"}` for products that have investment operations where no quote exists with `datetime <= operation.datetime`. Because missing quotes default to 0 in portfolio calculations (`ios.py`), this alert provides the product reference URL and the earliest operation date needing a quote so the frontend knows what quote to add.

---

## 10. Docker Deployment & Configuration
- **Official Docker Hub Images**: [`turulomio/django_moneymoney`](https://hub.docker.com/r/turulomio/django_moneymoney)
  - **`turulomio/django_moneymoney:latest`**: Standard production-ready image. Requires external PostgreSQL database configured via environment variables.
  - **`turulomio/django_moneymoney:e2e`**: Standalone testing image containing embedded PostgreSQL 16 with the `plpython3u` extension, pre-applied migrations, and pre-loaded fixtures (`all.json`, `test_users.json`). Built to accelerate frontend E2E and CI test suites without needing external database provisioning.
- **Container Settings**: Configured in `django_moneymoney/settings_docker.py` (inherits from `settings.py` without modifying development configuration).
- **Environment Variables**:
  - `PORT`: Web server listen port (default `8000`).
  - `POSTGRES_DB` / `DB_NAME`: Database name (default `xulpymoney`).
  - `POSTGRES_USER` / `DB_USER`: PostgreSQL username (default `postgres`).
  - `POSTGRES_PASSWORD` / `DB_PASSWORD`: PostgreSQL password (default `postgres`).
  - `POSTGRES_HOST` / `DB_HOST`: PostgreSQL host (default `db` for `:latest`, `127.0.0.1` for `:e2e`).
  - `POSTGRES_PORT` / `DB_PORT`: PostgreSQL port (default `5432`).
  - `ALLOWED_HOSTS`: Extra allowed hosts (comma-separated).
- **CI / Publishing**: Handled via a unified container-first workflow in `.github/workflows/django.yml`. It builds the Docker image with GitHub Actions caching, runs the full Django test suite hermetically inside the container, and automatically publishes both `:latest` and `:e2e` images to Docker Hub on push to `main`.




