from django.conf import settings
from django.core.management.base import BaseCommand 
from moneymoney.reusing.connection_pg import Connection
from moneymoney.database_update import  database_update
from moneymoney import __versiondatetime__
class Command(BaseCommand):
    help = 'Sync quotes table to other databases'
    
    def handle(self, *args, **options):
        con=Connection()
        con.db=settings.DATABASES['default']['NAME']
        con.password=settings.DATABASES['default']['PASSWORD']
        con.port=settings.DATABASES['default']['PORT']
        con.server=settings.DATABASES['default']['HOST']
        con.user=settings.DATABASES['default']['USER']
        con.connect()
        database_update(con, 'moneymoney', __versiondatetime__,"Console")

#        con.commit()
