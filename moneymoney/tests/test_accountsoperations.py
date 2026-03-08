from moneymoney import models
from moneymoney.reusing import tests_helpers
from rest_framework import status
from pydicts import lod
from django.utils import timezone
from moneymoney import types
from moneymoney.tests import assert_max_queries




def test_Accountsoperations(self):
    o=models.Accountsoperations()
    o.accounts_id=4
    o.amount=-1000
    o.datetime=timezone.now()
    o.concepts_id=types.eConcept.BankCommissions
    o.save()

    #Creates 2 refunds
    refund=o.create_refund(timezone.now(), 10, "")
    refund=o.create_refund(timezone.now(), 20, "")

    self.assertEqual(len(o.refunds.all()), 2)
    self.assertEqual(refund.refund_original, o)





def test_Accountsoperations_refunds(self):
    #Adding an ao
    dict_ao=tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/",  models.Accountsoperations.post_payload(concepts=f"/api/concepts/{types.eConcept.BankCommissions}/", amount=-1000), status.HTTP_201_CREATED)
    
    # Make two refunds    
    with assert_max_queries(self, 14):#Complex save its ok now
        dict_refund1=tests_helpers.client_post(self, self.client_authorized_1, dict_ao["url"]+"create_refund/", {"datetime": timezone.now(), "refund_amount":100, "comment": "First refund"} , status.HTTP_200_OK)
        self.assertEqual(dict_refund1["refund_original"],dict_ao["url"])

    dict_refund2=tests_helpers.client_post(self, self.client_authorized_1, dict_ao["url"]+"create_refund/", {"datetime": timezone.now(), "refund_amount":200, "comment": "Second refund"} , status.HTTP_200_OK)
    self.assertEqual(dict_refund2["refund_original"],dict_ao["url"])

    # Get refunds

    with assert_max_queries(self, 5):
        lod_refunds=tests_helpers.client_get(self, self.client_authorized_1, dict_ao["url"]+"get_refunds/" , status.HTTP_200_OK)
        sum_refunds=lod.lod_sum(lod_refunds, "amount")
        self.assertEqual(dict_ao["amount"]+sum_refunds, -700)

    # Set a too much high refund
    tests_helpers.client_post(self, self.client_authorized_1, dict_ao["url"]+"create_refund/", {"datetime": timezone.now(), "refund_amount":2000, "comment": "Too much"} , status.HTTP_400_BAD_REQUEST)


def test_Accountsoperations_associated_fields(self):
    #Add a investment operation to check associated_io
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(), status.HTTP_201_CREATED)
    dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(), status.HTTP_201_CREATED)        
    dict_io=tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(investments=dict_investment["url"]), status.HTTP_201_CREATED)#Al actualizar ao asociada ejecuta otro plio
    dict_associated_ao_with_associated_io=tests_helpers.client_get(self, self.client_authorized_1, dict_io["associated_ao"],  status.HTTP_200_OK)
    self.assertEqual(dict_associated_ao_with_associated_io["associated_io"], dict_io["url"])
    
    #Add a dividend to check associated_dividend
    dict_dividend=tests_helpers.client_post(self, self.client_authorized_1, "/api/dividends/",  models.Dividends.post_payload(investments=dict_investment["url"]), status.HTTP_201_CREATED)
    dict_associated_ao_with_associated_dividend=tests_helpers.client_get(self, self.client_authorized_1, dict_dividend["accountsoperations"],  status.HTTP_200_OK)
    self.assertEqual(dict_associated_ao_with_associated_dividend["associated_dividend"], dict_dividend["url"])
    
