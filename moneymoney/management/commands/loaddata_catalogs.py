from django.core.management.base import BaseCommand

from django.core.management import call_command



class Command(BaseCommand):
    help = 'Load two fixtures data'
        #Generate fixtures
                
    def handle(self, *args,**options):

        call_command(
            "loaddata",
            "moneymoney/fixtures/other.json", 
            "moneymoney/fixtures/products.json"
        )
        
