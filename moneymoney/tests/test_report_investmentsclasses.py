from rest_framework import status
from moneymoney import models
from moneymoney.reusing import tests_helpers
from pydicts import lod



def test_InvestmentsClasses(self):
    #Empty
    dict_classes=tests_helpers.client_get(self, self.client_authorized_1, "/investments/classes/", status.HTTP_200_OK)
    self.assertEqual(lod.lod_sum(dict_classes["by_producttype"], "balance"),  0)
    
    # With one investmentoperation and one account operation        
    tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/",  models.Accountsoperations.post_payload(amount=10000), status.HTTP_201_CREATED)
    dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(products=dict_investment["products"]), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(investments=dict_investment["url"]), status.HTTP_201_CREATED)#Al actualizar ao asociada ejecuta otro plio
    dict_classes=tests_helpers.client_get(self, self.client_authorized_1, "/investments/classes/", status.HTTP_200_OK)
    self.assertEqual(lod.lod_sum(dict_classes["by_producttype"], "balance"), 10000)


