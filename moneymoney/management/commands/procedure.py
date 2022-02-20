from django.core.management.base import BaseCommand
from moneymoney.__init__ import __version__, __versiondatetime__
from os import system

class Command(BaseCommand):
    help = 'New release procedure'

    def handle(self, *args, **options):
        print(f"Updating versions of moneymoney frontend project to {__version__} and {__versiondatetime__}")
        d=__versiondatetime__
        system (f"""sed -i '3s/.*/  "version": "{__version__}",/' ../moneymoney/package.json""")
        system (f"""sed -i '13s/.*/        version: "{__version__}",/' ../moneymoney/src/store.js""")
        system (f"""sed -i '14s/.*/        versiondate: new Date({d.year}, {d.month-1}, {d.day}, {d.hour}, {d.minute}),/' ../moneymoney/src/store.js""")

        print()
        print(f"""To release a new version:
DJANGO_MONEYMONEY
  * Change version and version datetime in moneymoney/__init__.py
  * python manage.py procedure
  * python manage.py makemessages --all
  * mcedit moneymoney/locale/es/LC_MESSAGES/django.po
  * python manage.py compilemessages
  * python manage.py doxygen
  * git commit -a -m 'django_moneymoney-{__version__}'
  * git push
  * Hacer un nuevo tag en GitHub de django_moneymoney

MONEYMONEY
  * Cambiar a moneymoney project
  * Add release changelog in README.md
  * npm run i18n:report
  * mcedit src/locales/es.json
  * git commit -a -m 'moneymoney-{__version__}'
  * git push
  * Hacer un nuevo tag en GitHub de moneymoney
""")

