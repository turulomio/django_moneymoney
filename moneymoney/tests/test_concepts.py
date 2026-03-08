from datetime import date
from rest_framework import status
from moneymoney import models
from moneymoney.reusing import tests_helpers
from pydicts import lod


def test_Concepts(self):
    # Action used empty
    r=tests_helpers.client_get(self, self.client_authorized_1,  "/api/concepts/used/", status.HTTP_200_OK)
    self.assertEqual(lod.lod_sum(r, "used"), 0)




    
def test_ConceptsReport(self):
    #test empty
    tests_helpers.client_get(self, self.client_authorized_1, f"/reports/concepts/?year={date.today().year}&month={date.today().month}", status.HTTP_200_OK)
    #test value
    tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/",  models.Accountsoperations.post_payload(), status.HTTP_201_CREATED)
    r=tests_helpers.client_get(self, self.client_authorized_1, f"/reports/concepts/?year={date.today().year}&month={date.today().month}", status.HTTP_200_OK)
    self.assertEqual(len(r["positive"]), 1)
    
def test_Concepts_DataTransfer(self):
    # New personal concept
    dict_concept_from=tests_helpers.client_post(self, self.client_authorized_1, "/api/concepts/", models.Concepts.post_payload(name="Concept from"), status.HTTP_201_CREATED)
    
    # We create an accounts operations, creditcardsoperations and dividends with this new concept
    dict_ao=tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/",  models.Accountsoperations.post_payload(concepts=dict_concept_from["url"], amount=-1000), status.HTTP_201_CREATED)
    dict_cc=tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcards/",  models.Creditcards.post_payload(), status.HTTP_201_CREATED)
    dict_cco=tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcardsoperations/",  models.Creditcardsoperations.post_payload(creditcards=dict_cc["url"], concepts=dict_concept_from["url"]), status.HTTP_201_CREATED)
    dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",  models.Investments.post_payload(accounts=dict_ao["accounts"]), status.HTTP_201_CREATED)
    
    # We create a new personal concepto to transfer to
    dict_concept_to=tests_helpers.client_post(self, self.client_authorized_1, "/api/concepts/", models.Concepts.post_payload(name="Concept to"), status.HTTP_201_CREATED)
    
    # We transfer data from concept_from to concept_to
    tests_helpers.client_post(self, self.client_authorized_1, f"{dict_concept_from['url']}data_transfer/", {"to": dict_concept_to["url"]}, status.HTTP_200_OK)
    
    # We check that concepts have been changed
    dict_ao_after=tests_helpers.client_get(self, self.client_authorized_1, dict_ao["url"]  , status.HTTP_200_OK)
    self.assertEqual(dict_ao_after["concepts"], dict_concept_to["url"])
    dict_cco_after=tests_helpers.client_get(self, self.client_authorized_1, dict_cco["url"]  , status.HTTP_200_OK)
    self.assertEqual(dict_cco_after["concepts"], dict_concept_to["url"])
    
    # Bad request
    tests_helpers.client_post(self, self.client_authorized_1, f"{dict_concept_from['url']}data_transfer/", {}, status.HTTP_400_BAD_REQUEST)

def test_Concepts_HistoricalData(self):
    # We create an accounts operations, creditcardsoperations and dividends with this new concept        
    dict_cc=tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcards/",  models.Creditcards.post_payload(), status.HTTP_201_CREATED)
    for i in range(5):
        tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/",  models.Accountsoperations.post_payload(datetime=self.now.replace(year= 2010+i)), status.HTTP_201_CREATED)
        tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcardsoperations/",  models.Creditcardsoperations.post_payload(creditcards=dict_cc["url"]), status.HTTP_201_CREATED)
    # We transfer data from concept_from to concept_to
    dict_historical_report_1=tests_helpers.client_get(self, self.client_authorized_1, "http://testserver/api/concepts/1/historical_report/", status.HTTP_200_OK)
    self.assertEqual(dict_historical_report_1["total"], 10000)
    # Empty request
    dict_historical_report_2=tests_helpers.client_get(self, self.client_authorized_1, "http://testserver/api/concepts/2/historical_report/", status.HTTP_200_OK)
    self.assertEqual(dict_historical_report_2["total"], 0)

def test_Concepts_HistoricalDataDetailed(self):
    # We create an accounts operations, creditcardsoperations and dividends with this new concept        
    dict_cc=tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcards/",  models.Creditcards.post_payload(), status.HTTP_201_CREATED)
    for i in range(2):
        tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/",  models.Accountsoperations.post_payload(), status.HTTP_201_CREATED)
        tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcardsoperations/",  models.Creditcardsoperations.post_payload(creditcards=dict_cc["url"]), status.HTTP_201_CREATED)
    # We transfer data from concept_from to concept_to
    dict_historical_report_1=tests_helpers.client_get(self, self.client_authorized_1, f"http://testserver/api/concepts/1/historical_report_detail/?year={self.now.year}&month={self.now.month}", status.HTTP_200_OK)
    self.assertEqual(len(dict_historical_report_1["ao"]), 2)
    self.assertEqual(len(dict_historical_report_1["cco"]), 2)
    # Empty request
    dict_historical_report_empty=tests_helpers.client_get(self, self.client_authorized_1, f"http://testserver/api/concepts/2/historical_report_detail/?year={self.now.year}&month={self.now.month}", status.HTTP_200_OK)
    self.assertEqual(len(dict_historical_report_empty["ao"]), 0)
    self.assertEqual(len(dict_historical_report_empty["cco"]), 0)
    # Bad request
    tests_helpers.client_get(self, self.client_authorized_1, "http://testserver/api/concepts/1/historical_report_detail/", status.HTTP_400_BAD_REQUEST)
