from django.conf import settings
from django.core.management.base import BaseCommand

from django.core.management import call_command
from requests import get



class Command(BaseCommand):
    help = 'Load two fixtures data'
        #Generate fixtures
    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument('--internet', action='store_true', help='Load data from internet', default=False)
                
    def handle(self, *args,**options):
        if options["internet"]:
            r=get("https://github.com/turulomio/django_moneymoney/raw/main/moneymoney/fixtures/all.json")
            filename=f"{settings.TMPDIR}/all.json"
            with open(filename, "wb") as f:
                f.write(r.content)
        else:
            filename="moneymoney/fixtures/all.json"
        call_command("loaddata", filename )
        
