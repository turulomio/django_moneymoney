from moneymoney.reusing.connection_dj import cursor_rows
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Command to dump database translatable string to hardcoded_strings.py'

    def handle(self, *args, **options):
        strings=[]
        for row in cursor_rows("select name from concepts where editable is false order by name"):
            strings.append("_('{}')".format(row["name"]))
        for row in cursor_rows("select name from leverages order by name"):
            strings.append("_('{}')".format(row["name"]))
        for row in cursor_rows("select name from productstypes order by name"):
            strings.append("_('{}')".format(row["name"]))
        for row in cursor_rows("select name from operationstypes order by name"):
            strings.append("_('{}')".format(row["name"]))
        for row in cursor_rows("select name from stockmarkets order by name"):
            strings.append("_('{}')".format(row["name"]))
        for row in cursor_rows("select name from banks where id=3"):
            strings.append("_('{}')".format(row["name"]))
        for row in cursor_rows("select name from accounts where id=4"):
            strings.append("_('{}')".format(row["name"]))
            
        strings.sort()
        f=open("moneymoney/hardcoded_strings.py", "w")
        f.write("from django.utils.translation import gettext_lazy as _\n")
        for s in strings:
            f.write(f"{s}\n")
        f.close()

