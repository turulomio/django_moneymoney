from django.core.management.base import BaseCommand
from moneymoney.__init__ import __version__, __versiondatetime__
from os import system

class Command(BaseCommand):
    help = 'New release procedure'

    def handle(self, *args, **options):
        print(f"""To release a new version:
DJANGO_MONEYMONEY
  * Create issue and a branch associated to that issue, and paste code
  * Change version and version datetime in moneymoney/__init__.py
  * python manage.py procedure
  * python manage.py makedbmessages
  * python manage.py makemessages --all
  * mcedit moneymoney/locale/es/LC_MESSAGES/django.po
  * python manage.py compilemessages
  * git commit -a -m 'django_moneymoney-{__version__}'
  * git push
  * Hacer un pull request y comprobar que no hay fallos
  * Hacer un nuevo tag en GitHub de django_moneymoney

OJO: Poner la misma versión {__version__} y hora en {__versiondatetime__} moneymoney y seguir sus instrucciones con npm run release
""")

