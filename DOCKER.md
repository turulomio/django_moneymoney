# Docker & Environment Variables

[![Docker Hub](https://img.shields.io/badge/docker-turulomio%2Fdjango__moneymoney-blue.svg?logo=docker&logoColor=white)](https://hub.docker.com/r/turulomio/django_moneymoney)

The official Docker images are available at [Docker Hub: turulomio/django_moneymoney](https://hub.docker.com/r/turulomio/django_moneymoney).

Two tags are published:
1. **`turulomio/django_moneymoney:latest`**: Standard / Production-ready image. Lightweight, requires an external PostgreSQL database configured via environment variables.
2. **`turulomio/django_moneymoney:e2e`**: Dedicated End-to-End (E2E) testing image. Contains an embedded PostgreSQL 16 server with the `plpython3u` extension, all Django migrations pre-applied, and catalog/test fixtures (`all.json`, `test_users.json`) already pre-loaded into the database during image build. Starts instantly in standalone mode.

---

## 1. Production Image (`turulomio/django_moneymoney:latest`)

The standard Docker image uses [settings_docker.py](file:///home/worky/Proyectos/django_moneymoney/django_moneymoney/settings_docker.py), which inherits from the base `settings.py` and allows configuring the database connection and server port via environment variables without altering the local development configuration.

### Available Variables

| Variable | Description | Default Value |
| :--- | :--- | :--- |
| `PORT` | Port where Gunicorn listens | `8000` |
| `POSTGRES_DB` / `DB_NAME` | Database name | `xulpymoney` |
| `POSTGRES_USER` / `DB_USER` | PostgreSQL user | `postgres` |
| `POSTGRES_PASSWORD` / `DB_PASSWORD` | PostgreSQL password | `postgres` |
| `POSTGRES_HOST` / `DB_HOST` | PostgreSQL host address | `db` |
| `POSTGRES_PORT` / `DB_PORT` | PostgreSQL port | `5432` |
| `ALLOWED_HOSTS` | Extra allowed hostnames (comma-separated) | *(none)* |

### Build the image
```bash
docker build -t turulomio/django_moneymoney:latest -f Dockerfile .
```

### Run container with custom database and port
```bash
docker run -d \
  -p 8080:8080 \
  -e PORT=8080 \
  -e POSTGRES_HOST=my-postgres-host \
  -e POSTGRES_PORT=5432 \
  -e POSTGRES_DB=xulpymoney \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=mysecretpassword \
  turulomio/django_moneymoney:latest
```

---

## 2. E2E Testing Image (`turulomio/django_moneymoney:e2e`)

> [!NOTE]
> **Use Case**: This image is exclusively intended for testing and CI pipelines (such as frontend E2E tests, Playwright, Cypress, Vue test suites). It allows running tests against a fully configured and populated Django MoneyMoney API without needing to deploy or configure a separate database container, install extensions, run migrations, or load fixture files.

### Key Features
- **Embedded PostgreSQL 16** with `plpython3u` enabled.
- **Pre-applied migrations**: Database schema is completely migrated during build.
- **Pre-loaded Fixtures**:
  - `moneymoney/fixtures/all.json` (Currencies, countries, asset classes, tags, products, concepts, banks, accounts, etc.).
  - `moneymoney/fixtures/test_users.json` (Pre-configured test users and permissions).
- **Fast Startup**: Starts in ~1–2 seconds.

### Pre-loaded Test Users

| Username | Password | Role / Groups |
| :--- | :--- | :--- |
| `authorized_1` | `authorized_1` | Standard Active User |
| `authorized_2` | `authorized_2` | Standard Active User |
| `catalog_manager` | `catalog_manager` | CatalogManager Group Member |

### Build the E2E image
```bash
docker build -t turulomio/django_moneymoney:e2e -f Dockerfile.e2e .
```

### Run E2E container
```bash
docker run -d \
  --name moneymoney-e2e \
  -p 8000:8000 \
  turulomio/django_moneymoney:e2e
```

The API will be immediately accessible at `http://localhost:8000/`.
