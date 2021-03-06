"""
ASGI config for django_money project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/howto/deployment/asgi/
"""

import os

from django.conf import settings
from moneymoney.connection_pg import Connection
from moneymoney.database_update import  database_update
from moneymoney import __versiondatetime__
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_moneymoney.settings')
print("Checking database version")
con=Connection()
con.db=settings.DATABASES['default']['NAME']
con.password=settings.DATABASES['default']['PASSWORD']
con.port=settings.DATABASES['default']['PORT']
con.server=settings.DATABASES['default']['HOST']
con.user=settings.DATABASES['default']['USER']
con.connect()
database_update(con, 'moneymoney', __versiondatetime__)
con.disconnect()
application = get_asgi_application()
