from django.core.management.base import BaseCommand

from django.core.management import call_command
from moneymoney import models


## Pruebas con dumpdata y load data
## Creo un registro en systemproducts id=342
## Hago un dumpdata y aparece en el json
## Le edito el nombre de REUSEME a REUSEME2
## Hago loaddata y me devuelve a REUSEME


## Borro el registrto 342
## Ejecuto el loaddata y vuelvo a tenerlo en la base de datos

## Teniendolo en base de datos lo borro del all.json

## Si se hubiera borrado algún modelo o campo desde que fue originalmente creado -i lo ignora

## Conclusión las tablas de fixtures no deben borrar nunca objetos sino ponerlos obsoletos, ya que no lo borra por defecto

## Si se necesitara borrar abría que hacer una load_data comand específico


class Command(BaseCommand):
    help = 'Dumpdata command for catalog models only'
        #Generate fixtures
                
    def handle(self, *args,**options):
        
        
        call_command(
            "dumpdata",         
            "moneymoney.stockmarkets", 
            "moneymoney.leverages", 
            "moneymoney.operationstypes", 
            "moneymoney.productstypes", 
            "--indent",  "4", 
            "-o", "moneymoney/fixtures/other.json"
        )
        
        # Personal products are generated with id<0 in products table, so I pass pks as --pks parameter
        products_ids=list(models.Products.objects.filter(id__gt=0).values_list('id', flat=True))
        s=""
        for id in products_ids:
            s=s+f"{id},"
        s=s[:-1]
        
        call_command(
            "dumpdata",
            "moneymoney.products", 
            "--indent",  "4", 
            "--pks",  s, 
            "-o", "moneymoney/fixtures/products.json"
        )
                
        # System concepts are generated with id<100 in concepts table, so I pass pks as --pks parameter
        concepts_ids=list(models.Concepts.objects.filter(id__lt=100).values_list('id', flat=True))
        s=""
        for id in concepts_ids:
            s=s+f"{id},"
        s=s[:-1]
        call_command(
            "dumpdata",
            "moneymoney.concepts", 
            "--indent",  "4", 
            "--pks",  s, 
            "-o", "moneymoney/fixtures/concepts.json"
        )
        
