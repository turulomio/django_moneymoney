from datetime import datetime, timedelta
from moneymoney import models, investing_com
from moneymoney.reusing import tests_helpers
from pydicts import lod
from rest_framework import status



def test_ProductsRange(self):
    def generate_url(d):            
        call=f"?product={d['product']}&totalized_operations={d['totalized_operations']}&percentage_between_ranges={d['percentage_between_ranges']}&percentage_gains={d['percentage_gains']}&amount_to_invest={d['amount_to_invest']}&recomendation_methods={d['recomendation_methods']}"
        for o in d["investments"]:
            call=call+f"&investments[]={o}"
        return f"/products/ranges/{call}"
    ############################################
    # Product hasn't quotes
    d={
        "product": "http://testserver/api/products/79329/",   
        "recomendation_methods": 8, #SMA10 
        "investments":[] ,
        "totalized_operations":True, 
        "percentage_between_ranges":2500, 
        "percentage_gains":2500, 
        "amount_to_invest": 10000
    }
    tests_helpers.client_get(self, self.client_authorized_1, generate_url(d) , status.HTTP_400_BAD_REQUEST)
    
    #Adding a quote and test again without investments
    for i in range(30):
        tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(datetime=datetime(2023,1,1)+timedelta(days=i), quote=i+1), status.HTTP_201_CREATED)
    tests_helpers.client_get(self, self.client_authorized_1, generate_url(d) , status.HTTP_200_OK)

    #Adding an investment operation and an order
    dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",  models.Investments.post_payload(), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/",  models.Investmentsoperations.post_payload(investments=dict_investment["url"]), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/orders/",  models.Orders.post_payload(date_=self.now.date(), investments=dict_investment["url"]), status.HTTP_201_CREATED)
    d={
        "product": "http://testserver/api/products/79329/",   
        "recomendation_methods":10,  #HMA10
        "investments":[dict_investment["id"], ] ,
        "totalized_operations":True, 
        "percentage_between_ranges":2500, 
        "percentage_gains":2500, 
        "amount_to_invest": 10000
    }
    r=tests_helpers.client_get(self, self.client_authorized_1, generate_url(d) , status.HTTP_200_OK)
    r
