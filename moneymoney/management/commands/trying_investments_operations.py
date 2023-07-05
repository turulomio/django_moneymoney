from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from moneymoney import models, investment_operations_new
from moneymoney.reusing.connection_dj import show_queries_function
from pydicts import lod

show_queries_function

class Command(BaseCommand):
    help = 'Testing new investments operations'

    def handle(self, *args, **options):
#        self.investments_operations_por_un_id()
        #self.investments_operations_por_varios_ids()       
        self.investments_operations_todas()
        #show_queries_function()
        
        
    def investments_operations_por_un_id(self):
#        print(investment_operations_new.quote(79329, timezone.now()-timedelta(days=365)))
#        print(investment_operations_new.currency_factor(timezone.now()-timedelta(days=365), 'EUR', 'USD'))
#        print(investment_operations_new.currency_factor(timezone.now()-timedelta(days=365), 'USD', 'EUR'))
#        return
        s=datetime.now()
        data={
            "productstypes_id":2,
            "products_id":81742, 
            "currency_product":"EUR", 
            "currency_account":"EUR", 
            "currency_user":"EUR", 
        }
        lod_=models.Investmentsoperations.objects.filter(investments__id=334).values()
        
        d=investment_operations_new.calculate_io_lazy(timezone.now(), data,  lod_, 'EUR')
        print(d.keys())
        lod.lod_print(d["io"])
        lod.lod_print(d["io_current"])
        lod.lod_print(d["io_historical"])
        d["lazy_quotes"], d["lazy_factors"]=investment_operations_new.get_quotes_and_factors(d["lazy_quotes"], d["lazy_factors"])
        d=investment_operations_new.calculate_io_finish(d, d)
        print("LAZY", datetime.now()-s)        
        
        
    def investments_operations_por_varios_ids(self):
        s=datetime.now()
        lod_investments=[{
            "investments_id":334, 
            "productstypes_id":2,
            "products_id":81742, 
            "currency_product":"EUR", 
            "currency_account":"EUR", 
            "currency_user":"EUR", 
        }, 
        {
            "investments_id":127, 
            "productstypes_id":2,
            "products_id":79329, 
            "currency_product":"EUR", 
            "currency_account":"EUR", 
            "currency_user":"EUR", 
        }]
        lod_=models.Investmentsoperations.objects.filter(investments__id__in=[334, 127]).values()
        
        lod.lod_print(lod_)
        t=investment_operations_new.calculate_ios_lazy(timezone.now(), lod_investments,  lod_, 'EUR')
        t["lazy_quotes"], t["lazy_factors"]=investment_operations_new.get_quotes_and_factors(t["lazy_quotes"], t["lazy_factors"])
        t=investment_operations_new.calculate_ios_finish(t, 1)
        print(t)
        print("LAZY", datetime.now()-s)
        

    def investments_operations_todas(self):
        s=datetime.now()
        lod_investments=investment_operations_new.generate_lod_data_from_qs(models.Investments.objects.all().select_related("products", "products__productstypes", "accounts",  "products__leverages"), 'EUR')
        lod_=models.Investmentsoperations.objects.all().values()
        
        t=investment_operations_new.calculate_ios_lazy(timezone.now(), lod_investments,  lod_, 'EUR')
        t["lazy_quotes"], t["lazy_factors"]=investment_operations_new.get_quotes_and_factors(t["lazy_quotes"], t["lazy_factors"])
        t=investment_operations_new.calculate_ios_finish(t, 3)
        print(t)
        print("LAZY", datetime.now()-s)
        
