from django.conf import settings
from django.core.management.base import BaseCommand
from os import system, chdir
from moneymoney.__init__ import __version__

class Command(BaseCommand):
    help = 'Create doxygen documentation'

    def handle(self, *args, **options):
    
    
        system("""sed -i -e "41d" doc/Doxyfile""")#Delete line 41
        system("""sed -i -e "41iPROJECT_NUMBER         = {}" doc/Doxyfile""".format(__version__))#Insert line 41
        chdir("doc")
        system("doxygen Doxyfile")
        db=settings.DATABASES['default']

        chdir("html")
        system("/usr/bin/postgresql_autodoc -d {} -h {} -u {} -p {} --password={} -t html".format(db['NAME'], db['HOST'], db['USER'], db['PORT'], db['PASSWORD']))
        system("/usr/bin/postgresql_autodoc -d {} -h {} -u {} -p {} --password={} -t dot_shortfk".format(db['NAME'], db['HOST'], db['USER'], db['PORT'], db['PASSWORD']))
        system("dot -Tpng {0}.dot_shortfk -o {0}_er.png".format(db['NAME']))
        chdir("..")


        system("rsync -avzP -e 'ssh -l turulomio' html/ frs.sourceforge.net:/home/users/t/tu/turulomio/userweb/htdocs/doxygen/django_money/ --delete-after")

