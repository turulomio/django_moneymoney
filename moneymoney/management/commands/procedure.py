from django.core.management.base import BaseCommand
from books.__init__ import __version__

class Command(BaseCommand):
    help = 'New release procedure'

    def handle(self, *args, **options):
        print("""To release a new version:
  * Change version and version date in books.__init__.py
  * Add release changelog en README.md
  * python manage.py makemessages
  * linguist
  * python manage.py compilemessages
  * python manage.py doxygen
  * git commit -a -m 'dj_books-{}'
  * git push
  * Hacer un nuevo tag en GitHub
  * Crea un nuevo ebuild de Gentoo con la nueva versión
  * Subelo al repositorio del portage
""".format(__version__))

