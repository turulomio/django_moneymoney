"""
Docker-specific Django settings for django_moneymoney.
Inherits from the base settings and allows environment variable overrides for container environments.
"""
from .settings import *
import os

# Database configuration from environment variables (defaults match standard Docker setup)
DATABASES['default']['HOST'] = os.environ.get('POSTGRES_HOST', os.environ.get('DB_HOST', 'db'))
DATABASES['default']['PORT'] = int(os.environ.get('POSTGRES_PORT', os.environ.get('DB_PORT', '5432')))
DATABASES['default']['NAME'] = os.environ.get('POSTGRES_DB', os.environ.get('DB_NAME', 'xulpymoney'))
DATABASES['default']['USER'] = os.environ.get('POSTGRES_USER', os.environ.get('DB_USER', 'postgres'))
DATABASES['default']['PASSWORD'] = os.environ.get('POSTGRES_PASSWORD', os.environ.get('DB_PASSWORD', 'postgres'))

# Allow additional hosts from environment variable if provided
if os.environ.get('ALLOWED_HOSTS'):
    ALLOWED_HOSTS.extend([h.strip() for h in os.environ.get('ALLOWED_HOSTS').split(',') if h.strip()])
