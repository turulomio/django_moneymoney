from datetime import datetime
from django.conf import settings
from django.core.management.base import BaseCommand
from subprocess import run
from os import environ


class Command(BaseCommand):
    help = 'Command to dump postgres database'

    def handle(self, *args, **options):
        dt=datetime.now()
        dts="{}{}{}{}{}".format(dt.year, str(dt.month).zfill(2), str(dt.day).zfill(2), str(dt.hour).zfill(2), str(dt.minute).zfill(2))
        environ["PGPASSWORD"]= settings.DATABASES['default']['PASSWORD']
        run("pg_dump -U {0} -h {1} --port {2} {3} > {3}-{4}.sql".format(
                    settings.DATABASES['default']['USER'], 
                    settings.DATABASES['default']['HOST'], 
                    settings.DATABASES['default']['PORT'], 
                    settings.DATABASES['default']['NAME'], 
                    dts), 
                shell=True, 
                env=environ)

