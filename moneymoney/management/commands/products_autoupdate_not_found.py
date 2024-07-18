from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from pydicts import lod
from subprocess import run
from tempfile import TemporaryDirectory
from moneymoney.investing_com import InvestingCom

class Command(BaseCommand):
    help = "Returns a list of products don't found in products autoupdate"

    def handle(self, *args, **options):
        
        user=User.objects.all()[0]
        
        ### COPIED FROM PRODUCTS UPDATE VIEW
        with TemporaryDirectory() as tmp:
            run(f"""wget --header="Host: es.investing.com" \
                --header="User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:92.0) Gecko/20100101 Firefox/92.0" \
                --header="Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8" \
                --header="Accept-Language: es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3" \
                --header="Accept-Encoding: gzip, deflate, br" \
                --header="Alt-Used: es.investing.com" \
                --header="Connection: keep-alive" \
                --referer="{user.profile.investing_com_referer}" \
                --header="{user.profile.investing_com_cookie}" \
                --header="Upgrade-Insecure-Requests: 1" \
                --header="Sec-Fetch-Dest: document" \
                --header="Sec-Fetch-Mode: navigate" \
                --header="Sec-Fetch-Site: same-origin" \
                --header="Sec-Fetch-User: ?1" \
                --header="Pragma: no-cache" \
                --header="Cache-Control: no-cache" \
                --header="TE: trailers" \
                "{user.profile.investing_com_url}" -O {tmp}/portfolio.csv""", shell=True, capture_output=True)
            ic=InvestingCom.from_filename_in_disk(user.profile.zone, f"{tmp}/portfolio.csv")
            
        lol_csv=ic.lol
        r=ic.get()
        r=lod.lod_filter_dictionaries(r, lambda d, index: "Product wasn't found" in d["log"])
        for d in r:
            got_=[]
            for csv_ in lol_csv: 
                print(csv_[1], d["code"])
                if csv_[1] in d["code"] :
                    got_.append(csv_)
            d["csv"]=got_
        lod.lod_print(r)
