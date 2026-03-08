from rest_framework import status
from moneymoney import models
from moneymoney.reusing import tests_helpers
from django.utils import timezone



def test_Creditcards(self):
    # common _tests y deja creada una activa
    tests_helpers.common_tests_Collaborative(self, "/api/creditcards/", models.Creditcards.post_payload(), self.client_authorized_1, self.client_authorized_2, self.client_anonymous)
    
    # create cc one active and one inactive
    dict_cc=tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcards/",  models.Creditcards.post_payload(active=False), status.HTTP_201_CREATED)
    
    # List all
    lod_all=tests_helpers.client_get(self, self.client_authorized_1, "http://testserver/api/creditcards/", status.HTTP_200_OK)
    self.assertEqual(len(lod_all), 2)
    
    # List active
    lod_=tests_helpers.client_get(self, self.client_authorized_1, "http://testserver/api/creditcards/?active=true", status.HTTP_200_OK)
    self.assertEqual(len(lod_), 1)
    
    # List account 2
    lod_=tests_helpers.client_get(self, self.client_authorized_1, "http://testserver/api/creditcards/?account=200", status.HTTP_200_OK)
    self.assertEqual(len(lod_), 0)
    
    # List active accounts=1
    lod_=tests_helpers.client_get(self, self.client_authorized_1, "http://testserver/api/creditcards/?active=true&accounts=4", status.HTTP_200_OK)
    self.assertEqual(len(lod_), 1)
    
    # Try to change deferred attribute, but can't be updated
    dict_cc_debit=dict_cc.copy()
    dict_cc_debit["deferred"]=False
    tests_helpers.client_put(self, self.client_authorized_1, dict_cc["url"], dict_cc_debit , status.HTTP_400_BAD_REQUEST)

def test_Creditcards_WithBalance(self):
    # create cc one active and one inactive
    dict_debit=tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcards/",  models.Creditcards.post_payload(deferred=False), status.HTTP_201_CREATED)
    dict_cc=tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcards/",  models.Creditcards.post_payload(deferred=True), status.HTTP_201_CREATED)
    
    #Creates a cco
    tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcardsoperations/",  models.Creditcardsoperations.post_payload(creditcards=dict_cc["url"], amount=22.22), status.HTTP_201_CREATED)
    
    # Can't  create a cco with a debit cc
    tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcardsoperations/",  models.Creditcardsoperations.post_payload(creditcards=dict_debit["url"], amount=22.22), status.HTTP_400_BAD_REQUEST)
    
    # Compares balance
    lod_=tests_helpers.client_get(self, self.client_authorized_1, "http://testserver/api/creditcards/withbalance/", status.HTTP_200_OK)
    self.assertEqual(len(lod_), 2)
    self.assertEqual(lod_[0]["balance"], 0)#not deferred (debit)
    self.assertEqual(lod_[1]["balance"], 22.22)

def test_Creditcards_Payments(self):        
    # We create a credit card and a creditcard operation and make a payment
    dict_cc=tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcards/",  models.Creditcards.post_payload(), status.HTTP_201_CREATED)
    dict_cco_1=tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcardsoperations/",  models.Creditcardsoperations.post_payload(creditcards=dict_cc["url"]), status.HTTP_201_CREATED)
    dict_cco_2=tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcardsoperations/",  models.Creditcardsoperations.post_payload(creditcards=dict_cc["url"]), status.HTTP_201_CREATED)
    dict_cco_3=tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcardsoperations/",  models.Creditcardsoperations.post_payload(creditcards=dict_cc["url"]), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, f"{dict_cc['url']}pay/",  {"dt_payment":timezone.now(), "cco":[dict_cco_1["id"], ]}, status.HTTP_200_OK)
    tests_helpers.client_post(self, self.client_authorized_1, f"{dict_cc['url']}pay/",  {"dt_payment":timezone.now(), "cco":[dict_cco_2["id"], dict_cco_3["id"] ]}, status.HTTP_200_OK)
    
    #We list payments
    dict_payments=tests_helpers.client_get(self, self.client_authorized_1, f"{dict_cc['url']}payments/", status.HTTP_200_OK)
    self.assertTrue(dict_payments[0]["count"], 1)
    self.assertTrue(dict_payments[1]["count"], 2)
    
def test_Creditcards_OperationsWithBalance(self):
    # Create a deferred credit card
    dict_cc = tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcards/",
                                        models.Creditcards.post_payload(deferred=True), status.HTTP_201_CREATED)

    # Create some CCOs
    cco_payload_1 = models.Creditcardsoperations.post_payload(creditcards=dict_cc["url"], amount=50.00, comment="CCO 1")
    dict_cco_1 = tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcardsoperations/", cco_payload_1, status.HTTP_201_CREATED)

    cco_payload_2 = models.Creditcardsoperations.post_payload(creditcards=dict_cc["url"], amount=30.00, comment="CCO 2")
    dict_cco_2 = tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcardsoperations/", cco_payload_2, status.HTTP_201_CREATED)

    cco_payload_3 = models.Creditcardsoperations.post_payload(creditcards=dict_cc["url"], amount=20.00, comment="CCO 3")
    dict_cco_3 = tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcardsoperations/", cco_payload_3, status.HTTP_201_CREATED)

    # Test with paid=False (initially all are unpaid)
    lod_unpaid = tests_helpers.client_get(self, self.client_authorized_1,
                                          f"{dict_cc['url']}operationswithbalance/?paid=false", status.HTTP_200_OK)
    self.assertEqual(len(lod_unpaid), 3)
    self.assertEqual(lod_unpaid[0]["amount"], 50.00)
    self.assertEqual(lod_unpaid[0]["balance"], 50.00)
    self.assertEqual(lod_unpaid[1]["amount"], 30.00)
    self.assertEqual(lod_unpaid[1]["balance"], 80.00)
    self.assertEqual(lod_unpaid[2]["amount"], 20.00)
    self.assertEqual(lod_unpaid[2]["balance"], 100.00)

    # Make a payment for cco_1
    dict_payment_ao = tests_helpers.client_post(self, self.client_authorized_1, f"{dict_cc['url']}pay/",
                                                {"dt_payment": timezone.now(), "cco": [dict_cco_1["id"]]},
                                                status.HTTP_200_OK)

    # Test with paid=True
    lod_paid = tests_helpers.client_get(self, self.client_authorized_1,
                                        f"{dict_cc['url']}operationswithbalance/?paid=true", status.HTTP_200_OK)
    self.assertEqual(len(lod_paid), 1)
    self.assertEqual(lod_paid[0]["amount"], 50.00)
    self.assertEqual(lod_paid[0]["balance"], 50.00)
    self.assertTrue(lod_paid[0]["paid"])

    # Test with accountsoperations_id
    lod_by_ao = tests_helpers.client_get(self, self.client_authorized_1,
                                         f"{dict_cc['url']}operationswithbalance/?accountsoperations_id={dict_payment_ao['id']}",
                                         status.HTTP_200_OK)
    self.assertEqual(len(lod_by_ao), 1)
    self.assertEqual(lod_by_ao[0]["amount"], 50.00)
    self.assertEqual(lod_by_ao[0]["balance"], 50.00)
    self.assertTrue(lod_by_ao[0]["paid"])

    # Test bad request (no parameters)
    tests_helpers.client_get(self, self.client_authorized_1, f"{dict_cc['url']}operationswithbalance/", status.HTTP_400_BAD_REQUEST)