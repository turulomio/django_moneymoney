from django.core.management.base import BaseCommand
from os import system


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
        
    def handle(self, *args, **options):
        if options["settings"] is None: #Settings camesfrom basecommand
            str_settings=""
        else:
            str_settings=f" --settings {options['settings']}"
        system(f"coverage run --omit=moneymoney/reusing/*.py,moneymoney/migrations/*.py,/usr/lib64/libreoffice/program/uno.py,manage.py manage.py test {str_settings}; coverage report;coverage html")
        print("Now you can open htmlcov/index.html")
    
