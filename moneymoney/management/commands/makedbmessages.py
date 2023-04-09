from django.core.management.base import BaseCommand
from moneymoney import models

class Command(BaseCommand):
    help = 'Command to dump database translatable string to hardcoded_strings.py'

    def handle(self, *args, **options):
        strings=set()
        for o in models.Concepts.objects.filter(editable=False):
            strings.add("_('{}')".format(o.name))
        for o in models.Leverages.objects.all():
            strings.add("_('{}')".format(o.name))
        for o in models.Productstypes.objects.all():
            strings.add("_('{}')".format(o.name))
        for o in models.Operationstypes.objects.all():
            strings.add("_('{}')".format(o.name))
        for o in models.Stockmarkets.objects.all():
            strings.add("_('{}')".format(o.name))
        for o in models.Banks.objects.filter(pk=3):
            strings.add("_('{}')".format(o.name))
        for o in models.Accounts.objects.filter(pk=4):
            strings.add("_('{}')".format(o.name))
        strings=list(strings)
        strings.sort()
        with open("moneymoney/hardcoded_strings.py", "w") as f:
            f.write("from django.utils.translation import gettext_lazy as _\n")
            for s in strings:
                f.write(f"{s}\n")
