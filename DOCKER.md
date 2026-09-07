# Docker & Environment Variables

The Docker image uses [settings_docker.py](file:///home/worky/Proyectos/django_moneymoney/django_moneymoney/settings_docker.py), which inherits from the base `settings.py` and allows configuring the database connection and server port via environment variables without altering the local development configuration.

## Available Variables

| Variable | Description | Default Value |
| :--- | :--- | :--- |
| `PORT` | Port where Gunicorn listens | `8000` |
| `POSTGRES_DB` / `DB_NAME` | Database name | `xulpymoney` |
| `POSTGRES_USER` / `DB_USER` | PostgreSQL user | `postgres` |
| `POSTGRES_PASSWORD` / `DB_PASSWORD` | PostgreSQL password | `postgres` |
| `POSTGRES_HOST` / `DB_HOST` | PostgreSQL host address | `db` |
| `POSTGRES_PORT` / `DB_PORT` | PostgreSQL port | `5432` |
| `ALLOWED_HOSTS` | Extra allowed hostnames (comma-separated) | *(none)* |

## Example Usage

### Build the image
```bash
docker build -t django_moneymoney .
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
  django_moneymoney
```
