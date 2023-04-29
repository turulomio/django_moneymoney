from django.core.management.base import BaseCommand

from django.core.management import call_command
from moneymoney.reusing.file_functions import replace_in_file
from moneymoney import models
from json import load, dumps
from os import remove

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

from os import chdir, system
class Command(BaseCommand):
    help = 'Dumpdata command for catalog models only'
        #Generate fixtures
                
    def remove_items_with_condition(self, filename, condition):
        """
            Public method Condition is a lambda
        """        
        ## Loads json
        dict_=load(open(filename, "r"))
        remove(filename)
        print("Before remove", len(dict_))
        to_remove=[]
        for p in dict_:
            if condition(p) is True:
                to_remove.append(p)
        
        for o in to_remove:
            dict_.remove(o)
        print("After remove",  len(dict_))
        #Rewrites file
        j = dumps(dict_, indent=4)
        with open(filename, 'w') as f:
            print(j, file=f)
                
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
        
        # Due to ids are negative I made a total dump but I must delete positive ids
        filename="moneymoney/fixtures/products.json"
        call_command(
            "dumpdata",
            "moneymoney.products", 
            "--indent",  "4", 
            "-o", filename
        )
        self.remove_items_with_condition(filename, lambda x: x["pk"]>10000000)

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
        
        # Banks
        call_command(
            "dumpdata",
            "moneymoney.banks", 
            "--indent",  "4", 
            "--pks",  "3", 
            "-o", "moneymoney/fixtures/banks.json"
        )        
        # Accounts
        call_command(
            "dumpdata",
            "moneymoney.accounts", 
            "--indent",  "4", 
            "--pks",  "4", 
            "-o", "moneymoney/fixtures/accounts.json"
        )


        ## JOINS ALL FILES IN all.json
        chdir("moneymoney/fixtures/")
        files="other.json products.json concepts.json banks.json accounts.json"
        system(f"cat {files} > all.json")
        replace_in_file("all.json",  "\n]\n[", ",")
        system(f"rm {files}")
