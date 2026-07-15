# 💰 Django MoneyMoney

[![Build Status](https://img.shields.io/endpoint.svg?url=https%3A%2F%2Factions-badge.atrox.dev%2Fturulomio%2Fdjango_moneymoney%2Fbadge%3Fref%3Dmain&style=flat)](https://actions-badge.atrox.dev/turulomio/django_moneymoney/goto?ref=main)

Django MoneyMoney is a powerful, high-performance financial management backend built with **Django** and **Django REST Framework (DRF)**. It tracks and analyzes bank accounts, investment operations, dividends, orders, and credit card expenses across multiple currencies.

This is the backend of the [MoneyMoney](https://github.com/turulomio/moneymoney) app.

---

## ✨ Core Features

- 🏦 **Multi-Account & Multi-Currency Management**: Manage multiple bank accounts and credit cards with built-in currency conversions and automatic balance updates.
- 📈 **Investment Portfolio Tracking**: Support for diverse financial instruments (Shares, ETFs, CFDs, Futures, Leveraged products) under both System (public) and Personal categories.
- 🔀 **Automated Stock Splits**: Sophisticated stock split engine that updates historical quotes, operations, selling prices, limit orders, and dividend per share estimations, with full reversion capability.
- 💵 **Dividends & Estimations**: Record past dividend distributions, map them to account operations, and create future Dividend-Per-Share (DPS) estimations.
- ⚡ **Multi-Tier Caching System**: Employs Request-level (L1) and Server-level (L2) caching for quotes, boosting retrieval performance by up to 200x.
- 📊 **Advanced Financial Reporting**: API endpoints for generating rich financial reports, including Annual Performance, Asset Revaluations, Concept-based reports, Asset Evolution, Rankings, and Risk assessments.
- 🛠️ **Fully-Documented API**: Integrated with `drf-spectacular` to provide automated OpenAPI schema generation and a Swagger UI dashboard.

---

## 🏗️ Project Architecture & Data Models

- **Accounts**: Standard accounts mapping to specific banks.
- **Investments**: Groups a financial product with a bank account.
- **Investmentsoperations**: Tracks shares purchase/sell operations with price, taxes, and commissions.
- **Quotes**: Historical price points for products.
- **Orders**: Limit orders placed with brokers.
- **Dividends**: Realized dividend payments, linked to `Accountsoperations` for ledger consistency.
- **Dps / EstimationsDps**: Historical and estimated future Dividend-Per-Share figures.
- **Splits**: Triggers automated modifications to quotes and operations upon stock split events.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Poetry (for dependency management)
- PostgreSQL (database backend)

### Setup & Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/turulomio/django_moneymoney.git
   cd django_moneymoney
   ```
2. Install dependencies via Poetry:
   ```bash
   poetry install
   ```
3. Run migrations to set up the database schema:
   ```bash
   poetry run python manage.py migrate
   ```
4. Start the development server:
   ```bash
   poetry run python manage.py runserver
   ```

---

## 🧪 Testing

The project is backed by a comprehensive unit and integration test suite.

To run all tests:
```bash
poetry run python manage.py test
```

### Note on Splits Precision Testing
SQLite and database Decimal fields round values to 6 decimal places. When writing split tests with division/multiplication factors (like 2-for-1 and 3-for-1 splits), **use initial values that are divisible by 6** (e.g., 12.0, 24.0, 120.0) to prevent assertion failures due to minor floating-point or division remainder discrepancies.
