"""
WSGI config for django_money project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/howto/deployment/wsgi/
"""

import os
from django.conf import settings
from moneymoney.reusing.connection_pg import Connection
from moneymoney.database_update import  database_update
from moneymoney import __versiondatetime__
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_moneymoney.settings')


application = get_wsgi_application()
