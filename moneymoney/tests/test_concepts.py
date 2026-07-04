from datetime import date
from rest_framework import status
from decimal import Decimal
from moneymoney import models
from moneymoney.reusing import tests_helpers
from pydicts import lod


def test_Concepts(self):
    # Action used empty
    r=tests_helpers.client_get(self, self.client_authorized_1,  "/api/concepts/used/", status.HTTP_200_OK)
    self.assertEqual(lod.lod_sum(r, "used"), 0, "Initially, no concept should be in use.")

    # Create an operation using a concept
    tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/",  models.Accountsoperations.post_payload(), status.HTTP_201_CREATED)

    # Check 'used' action again
    r_after = tests_helpers.client_get(self, self.client_authorized_1, "/api/concepts/used/", status.HTTP_200_OK)
    self.assertGreater(lod.lod_sum(r_after, "used"), 0, "After creating an operation, at least one concept should be marked as used.")


    
def test_ConceptsReport(self):
    # 1. Test with no data
    r_empty = tests_helpers.client_get(self, self.client_authorized_1, f"/reports/concepts/?year={date.today().year}&month={date.today().month}", status.HTTP_200_OK)
    self.assertEqual(len(r_empty["positive"]), 0, "Positive concepts report should be empty initially.")
    self.assertEqual(len(r_empty["negative"]), 0, "Negative concepts report should be empty initially.")

    # 2. Test with a single positive AccountsOperation
    ao_amount = Decimal('150.75')
    tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/",  models.Accountsoperations.post_payload(amount=ao_amount), status.HTTP_201_CREATED)
    r_ao = tests_helpers.client_get(self, self.client_authorized_1, f"/reports/concepts/?year={date.today().year}&month={date.today().month}", status.HTTP_200_OK)
    self.assertEqual(len(r_ao["positive"]), 1, "Should be one positive concept after one AO.")
    self.assertEqual(r_ao["positive"][0]["total"], ao_amount, "The total should match the AO amount.")

    # 3. Test with a positive CreditCardsOperation for the SAME concept
    # This should not create a new entry but update the existing one.
    cco_amount = Decimal('50.25')
    dict_cc = tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcards/",  models.Creditcards.post_payload(), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcardsoperations/",  models.Creditcardsoperations.post_payload(creditcards=dict_cc["url"], amount=cco_amount), status.HTTP_201_CREATED)
    
    r_combined = tests_helpers.client_get(self, self.client_authorized_1, f"/reports/concepts/?year={date.today().year}&month={date.today().month}", status.HTTP_200_OK)
    self.assertEqual(len(r_combined["positive"]), 1, "Should not have duplicate concepts after adding a CCO for the same concept.")
    self.assertEqual(r_combined["positive"][0]["total"], ao_amount + cco_amount, "The total should be the sum of AO and CCO amounts.")
    self.assertEqual(len(r_combined["negative"]), 0, "Negative concepts report should still be empty.")

    # 4. Test with a negative operation to populate the 'negative' list
    negative_amount = Decimal('-99.99')
    dict_concept_expense = tests_helpers.client_post(self, self.client_authorized_1, "/api/concepts/", models.Concepts.post_payload(name="Expense Concept", operationstypes="/api/operationstypes/1/"), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/",  models.Accountsoperations.post_payload(concepts=dict_concept_expense["url"], amount=negative_amount), status.HTTP_201_CREATED)

    r_final = tests_helpers.client_get(self, self.client_authorized_1, f"/reports/concepts/?year={date.today().year}&month={date.today().month}", status.HTTP_200_OK)
    self.assertEqual(len(r_final["positive"]), 1, "Positive concepts count should remain 1.")
    self.assertEqual(len(r_final["negative"]), 1, "Should be one negative concept after adding an expense.")
    self.assertEqual(r_final["negative"][0]["total"], negative_amount, "The total of the negative concept should match the expense amount.")

    
def test_Concepts_DataTransfer(self):
    # New personal concept
    dict_concept_from=tests_helpers.client_post(self, self.client_authorized_1, "/api/concepts/", models.Concepts.post_payload(name="Concept from"), status.HTTP_201_CREATED)
    
    # We create an accounts operations, creditcardsoperations and dividends with this new concept
    dict_ao=tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/",  models.Accountsoperations.post_payload(concepts=dict_concept_from["url"], amount=-1000), status.HTTP_201_CREATED)
    dict_cc=tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcards/",  models.Creditcards.post_payload(), status.HTTP_201_CREATED)
    dict_cco=tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcardsoperations/",  models.Creditcardsoperations.post_payload(creditcards=dict_cc["url"], concepts=dict_concept_from["url"]), status.HTTP_201_CREATED)
    dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",  models.Investments.post_payload(accounts=dict_ao["accounts"]), status.HTTP_201_CREATED)
    dict_dividend=tests_helpers.client_post(self, self.client_authorized_1, "/api/dividends/",  models.Dividends.post_payload(investments=dict_investment["url"], concepts=dict_concept_from["url"]), status.HTTP_201_CREATED)
    
    # We create a new personal concepto to transfer to
    dict_concept_to=tests_helpers.client_post(self, self.client_authorized_1, "/api/concepts/", models.Concepts.post_payload(name="Concept to"), status.HTTP_201_CREATED)
    
    # We transfer data from concept_from to concept_to
    tests_helpers.client_post(self, self.client_authorized_1, f"{dict_concept_from['url']}data_transfer/", {"to": dict_concept_to["url"]}, status.HTTP_200_OK)
    
    # We check that concepts have been changed
    dict_ao_after=tests_helpers.client_get(self, self.client_authorized_1, dict_ao["url"]  , status.HTTP_200_OK)
    self.assertEqual(dict_ao_after["concepts"], dict_concept_to["url"])
    dict_cco_after=tests_helpers.client_get(self, self.client_authorized_1, dict_cco["url"]  , status.HTTP_200_OK)
    self.assertEqual(dict_cco_after["concepts"], dict_concept_to["url"])
    dict_dividend_after=tests_helpers.client_get(self, self.client_authorized_1, dict_dividend["url"]  , status.HTTP_200_OK)
    self.assertEqual(dict_dividend_after["concepts"], dict_concept_to["url"])
    
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
