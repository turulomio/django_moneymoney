from django.core.management.base import BaseCommand
from moneymoney.models import Stockmarkets, Leverages, Productstypes, Products
from tqdm import tqdm
#from moneymoney.reusing.listdict_functions import listdict2json

## qs models must hava json method to convert object to string
def qs_to_json(qs, root_tab=1, end_coma=True):
    r="[\n"
    for o in tqdm(qs):
        r=r+" "*4*(root_tab+1)+o.json() +",\n"
        
    r=r[:-2]+"\n"+" "*4+ "],"
    if end_coma is True:
        return r
    else:
        return r[:-1]
    


class Command(BaseCommand):
    help = 'Export catalogs to json to allow internet update in Github'

    def handle(self, *args, **options):
        qs_sm=Stockmarkets.objects.all().order_by("id")
        qs_leverages=Leverages.objects.all().order_by("id")
        qs_products_types=Productstypes.objects.all().order_by("id")
        qs_products=Products.objects.filter(id__gt=0).order_by("id")
        
        s=f"""{{
    "stock_markets": {qs_to_json(qs_sm)}
    "leverages": {qs_to_json(qs_leverages)}
    "products_types": {qs_to_json(qs_products_types)}
    "products": {qs_to_json(qs_products, end_coma=False)}
}}
"""
        with open("moneymoney/data/catalogs.json", "w") as f:
            f.write(s)
        

