from django.core.management.base import BaseCommand 
from tqdm import tqdm
import requests
import math
from moneymoney.reusing.connection_dj import cursor_one_row, execute

def valueornull(value):
    if value=="null" or value is None:
        return None
    return value
class Command(BaseCommand):
    help = 'Sync products table from dolthub'


    def handle(self, *args, **options):
        owner, repo, branch = 'turulomio', 'dolthub_money', 'master'

        res = requests.get('https://dolthub.com/api/v1alpha1/{}/{}/{}/'.format(owner, repo, branch), params={'q': 'select count(id) as count from products'})
        numberjson=int(res.json()["rows"][0]["count"])
        print("Productos en dolthub",  numberjson)
        execute("update products set obsolete=true where id>0")

        #Load all json data in json list
        json=[]
        for i in tqdm(range (math.ceil(numberjson/200))):
            res = requests.get('https://dolthub.com/api/v1alpha1/{}/{}/{}/'.format(owner, repo, branch), params={'q': f'select * from products order by id desc limit 200 offset {i*200}'})
            
            print("Offset", i*200, "Hay",  len(res.json()["rows"]))
            for j in res.json()["rows"]:
                json.append(j)
        print(len(json), "Must be the number before")
        insert, update=0, 0
        for j in tqdm(json):
            row=cursor_one_row("select * from products where id = %s", (j["id"],))
            if row is None:
                insert=insert+1
                execute("""
                    INSERT INTO 
                        PRODUCTS
                    (
                        NAME, 
                        ISIN,
                        CURRENCY,
                        PRODUCTSTYPES_ID,
                        AGRUPATIONS,
                        WEB,
                        ADDRESS,
                        PHONE,
                        MAIL,
                        PERCENTAGE,
                        PCI,
                        LEVERAGES_ID,
                        STOCKMARKETS_ID,
                        COMMENT,
                        OBSOLETE,
                        TICKERS,
                        HIGH_LOW,
                        DECIMALS,
                        ID)
                    VALUES(%s, %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    j["name"],
                    j["isin"],
                    j["currency"],
                    j["productstypes_id"],
                    j["agrupations"],
                    j["web"],
                    j["address"],
                    j["phone"],
                    j["mail"],
                    j["percentage"],
                    j["pci"],
                    j["leverages_id"],
                    j["stockmarkets_id"],
                    j["comment"],
                    j["obsolete"],
                    [valueornull(j["ticker_yahoo"]), valueornull(j["ticker_morningstar"]), valueornull(j["ticker_google"]), valueornull(j["ticker_quefondos"]), valueornull(j["ticker_investincom"])],
                    j["high_low"],
                    j["decimals"],
                    j["id"],
                ))
            else:
                update=update+1
                execute("""
                    UPDATE 
                        PRODUCTS
                    SET
                        NAME=%s,
                        ISIN=%s,
                        CURRENCY=%s,
                        PRODUCTSTYPES_ID=%s,
                        AGRUPATIONS=%s,
                        WEB=%s,
                        ADDRESS=%s,
                        PHONE=%s,
                        MAIL=%s,
                        PERCENTAGE=%s,
                        PCI=%s,
                        LEVERAGES_ID=%s,
                        STOCKMARKETS_ID=%s,
                        COMMENT=%s,
                        OBSOLETE=%s,
                        TICKERS=%s,
                        HIGH_LOW=%s,
                        DECIMALS=%s
                    WHERE 
                        ID = %s
                """, (
                    j["name"],
                    j["isin"],
                    j["currency"],
                    j["productstypes_id"],
                    j["agrupations"],
                    j["web"],
                    j["address"],
                    j["phone"],
                    j["mail"],
                    j["percentage"],
                    j["pci"],
                    j["leverages_id"],
                    j["stockmarkets_id"],
                    j["comment"],
                    j["obsolete"],
                    [valueornull(j["ticker_yahoo"]), valueornull(j["ticker_morningstar"]), valueornull(j["ticker_google"]), valueornull(j["ticker_quefondos"]), valueornull(j["ticker_investincom"])],
                    j["high_low"],
                    j["decimals"],
                    j["id"],
                ))
        print("Updated:",  update,  "Inserted",  insert)
