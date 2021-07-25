from django.core.management.base import BaseCommand
from os import system

class Command(BaseCommand):
    help = "Scan i18n messages without going into externals."
    #option_list = MakeMessagesCommand.option_list

    def handle(self, *args, **options):
        #Si en github se peridera el enlace enlazar con vuecomponents desde templates
        system("python manage.py makemessages -d djangojs -all --symlinks --extension html,js -i *node_modules*")
