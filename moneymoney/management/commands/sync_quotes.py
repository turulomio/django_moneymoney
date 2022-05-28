from django.conf import settings
from django.core.management.base import BaseCommand 
from logging import critical, info
from sys import exit
from tqdm import tqdm
from moneymoney.connection_pg import Connection

class Command(BaseCommand):
    help = 'Sync quotes table to other databases'

    def add_arguments(self, parser):
        parser.add_argument('--db_target', required=True)
        parser.add_argument('--port_target',  default='5432', required=False)
        parser.add_argument('--server_target',  default='127.0.0.1', required=False)
        parser.add_argument('--user_target',  default='postgres', required=False)
        
    def handle(self, *args, **options):
        con_source=Connection()
        con_source.db=settings.DATABASES['default']['NAME']
        con_source.password=settings.DATABASES['default']['PASSWORD']
        con_source.port=settings.DATABASES['default']['PORT']
        con_source.server=settings.DATABASES['default']['HOST']
        con_source.user=settings.DATABASES['default']['USER']
        con_source.connect()

        con_target=Connection()
        con_target.db=options['db_target']
        con_target.port=options['port_target']
        con_target.server=options['server_target']
        con_target.user=options['user_target']
        con_target.get_password()
        con_target.connect()
        
        #Checks if database has same version
        source_version=con_source.cursor_one_field("select value from globals where global='Version'")
        target_version=con_target.cursor_one_field("select value from globals where global='Version'")
        if source_version!=target_version:
            critical ("Databases has diferent versions, please update them")
            exit(0)

        quotes=0#Number of quotes synced
        estimation_dps=0#Number of estimation_dps synced
        estimation_eps=0#Number of estimation_eps synced
        dps=0
        splits=0 #Number of splits synced
        products=0#Number of products synced

        #Iterate all products
        rows_target=con_target.cursor_rows("select id,name from products where id>0 order by name")
        info ("Syncing {} products".format (len(rows_target)))
        for i_target, row in tqdm(enumerate(rows_target), total=len(rows_target)):
            output="Syncing {}: ".format(row['name'])
            ## QUOTES #####################################################################
            #Search last datetime
            max=con_target.cursor_one_field("select max(datetime) as max from quotes where products_id=%s", (row['id'], ))
            #Ask for quotes in source with last datetime
            if max==None:#No hay ningun registro y selecciona todos
                rows_source=con_source.cursor_rows("select * from quotes where products_id=%s", (row['id'], ))
            else:#Hay registro y selecciona los posteriores a el
                rows_source=con_source.cursor_rows("select * from quotes where products_id=%s and datetime>%s", (row['id'], max))
            if len(rows_source)>0:
                for  row_source in rows_source: #Inserts them 
                    con_target.execute("insert into quotes (products_id, datetime, quote) values (%s,%s,%s)", ( row_source['products_id'], row_source['datetime'], row_source['quote']))
                    quotes=quotes+1
                    output=output+"."

            ## DPS ################################################################################
            #Search last datetime
            max=con_target.cursor_one_field("select max(date) as max from dps where id=%s", (row['id'], ))
            #Ask for quotes in source with last datetime
            if max==None:#No hay ningun registro y selecciona todos
                rows_source=con_source.cursor_rows("select * from dps where id=%s", (row['id'], ))
            else:#Hay registro y selecciona los posteriores a el
                rows_source=con_source.cursor_rows("select * from dps where id=%s and date>%s", (row['id'], max))
            if len(rows_source)>0:
                for row_source in rows_source: #Inserts them 
                    con_target.execute("insert into dps (date, gross, id) values (%s,%s,%s)", ( row_source['date'], row_source['gross'], row_source['id']))
                    dps=dps+1
                    output=output+"-"

            ## DPS ESTIMATIONS #####################################################################
            #Search last datetime
            max=con_target.cursor_one_field("select max(year) as max from estimations_dps where products_id=%s", (row['id'], ))
            #Ask for quotes in source with last datetime
            if max==None:#No hay ningun registro y selecciona todos
                rows_source=con_source.cursor_rows("select * from estimations_dps where products_id=%s", (row['id'], ))
            else:#Hay registro y selecciona los posteriores a el
                rows_source=con_source.cursor_rows("select * from estimations_dps where products_id=%s and year>%s", (row['id'], max))
            if len(rows_source)>0:
                for row_source in rows_source: #Inserts them 
                    con_target.execute("insert into estimations_dps (year, estimation, date_estimation, source, manual, products_id) values (%s,%s,%s,%s,%s,%s)", ( row_source['year'], row_source['estimation'], row_source['date_estimation'], row_source['source'], row_source['manual'],  row_source['products_id']))
                    estimation_dps=estimation_dps+1
                    output=output+"+"

            ## EPS ESTIMATIONS #####################################################################
            #Search last datetime
            max=con_target.cursor_one_field("select max(year) as max from estimations_eps where products_id=%s", (row['id'], ))
            #Ask for quotes in source with last datetime
            if max==None:#No hay ningun registro y selecciona todos
                rows_source=con_source.cursor_rows("select * from estimations_eps where products_id=%s", (row['id'], ))
            else:#Hay registro y selecciona los posteriores a el
                rows_source=con_source.cursor_rows("select * from estimations_eps where products_id=%s and year>%s", (row['id'], max))
            if len(rows_source)>0:
                for row_source in rows_source: #Inserts them 
                    con_target.execute("insert into estimations_eps (year, estimation, date_estimation, source, manual, products_id) values (%s,%s,%s,%s,%s,%s)", ( row_source['year'], row_source['estimation'], row_source['date_estimation'], row_source['source'], row_source['manual'],  row_source['products_id']))
                    estimation_eps=estimation_eps+1
                    output=output+"*"

            ## SPLITS  #####################################################################
            #Search last datetime
            max=con_target.cursor_one_field("select max(datetime) as max from splits where products_id=%s", (row['id'], ))
            #Ask for quotes in source with last datetime
            if max==None:#No hay ningun registro y selecciona todos
                rows_source=con_source.cursor_rows("select * from splits where products_id=%s", (row['id'], ))
            else:#Hay registro y selecciona los posteriores a el
                rows_source=con_source.cursor_rows("select * from splits where products_id=%s and datetime>%s", (row['id'], max))
            if len(rows_source)>0:
                for row_source in rows_source: #Inserts them 
                    con_target.execute("insert into splits (datetime, products_id, before, after, comment) values (%s,%s,%s,%s,%s)", ( row_source['datetime'], row_source['products_id'], row_source['before'], row_source['after'], row_source['comment']))
                    splits=splits+1
                    output=output+"s"

            if output!="Syncing {}: ".format(row['name']):
                products=products+1
                print(output)
                con_target.commit()
                
        print("""From {} desynchronized products added:
        - {} quotes
        - {} dividends per share
        - {} dividend per share estimations
        - {} earnings per share estimations
        - {} splits / contrasplits""".format(  products,  quotes, dps, estimation_dps,  estimation_eps, splits))
