from rest_framework import status
from moneymoney import models
from moneymoney.reusing import tests_helpers
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from pydicts import casts



def test_ReportInvestmentsLastOperation_view(self):
    # Ensure quotes exist for product 79329
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",
                              models.Quotes.post_payload(products="/api/products/79329/", quote=10, datetime=self.dtaware_last_year - timedelta(days=10)),
                              status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",
                              models.Quotes.post_payload(products="/api/products/79329/", quote=12, datetime=self.dtaware_last_year + timedelta(days=5)),
                              status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",
                              models.Quotes.post_payload(products="/api/products/79329/", quote=13, datetime=timezone.now()),
                              status.HTTP_201_CREATED)

    # Investment 1: Product 79329
    dict_investment_1 = tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",
                                                  models.Investments.post_payload(name="Inv 1", selling_price=Decimal('15.00')),
                                                  status.HTTP_201_CREATED)
    # Operation 1 for Inv 1 (older)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/",
                              models.Investmentsoperations.post_payload(investments=dict_investment_1["url"], shares=100, price=10, datetime=self.dtaware_last_year),
                              status.HTTP_201_CREATED)
    # Operation 2 for Inv 1 (newer, this should be the "last operation")
    last_op_datetime_inv1 = timezone.now() - timedelta(days=1)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/",
                              models.Investmentsoperations.post_payload(investments=dict_investment_1["url"], shares=50, price=12, datetime=last_op_datetime_inv1),
                              status.HTTP_201_CREATED)

    # Investment 2: Product 79329 (different investment, same product)
    dict_investment_2 = tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",
                                                  models.Investments.post_payload(name="Inv 2", selling_price=Decimal('16.00')),
                                                  status.HTTP_201_CREATED)
    # Operation for Inv 2 (older than last op of Inv 1)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/",
                              models.Investmentsoperations.post_payload(investments=dict_investment_2["url"], shares=200, price=8, datetime=self.dtaware_last_year + timedelta(days=10)),
                              status.HTTP_201_CREATED)

    current_quote = 13.0
    
    # --- Test method=0 (Separated investments) ---
    response_method_0 = tests_helpers.client_get(self, self.client_authorized_1, "/reports/investments/lastoperation/?method=0", status.HTTP_200_OK)
    
    self.assertIsInstance(response_method_0, dict)
    self.assertIn("entries", response_method_0)
    self.assertEqual(len(response_method_0["entries"]), 2) # Should have both investments

    # Verify Investment 1 data
    inv1_data = response_method_0[str(dict_investment_1["id"])]



    # --- Test method=1 (Merging current operations) ---
    response_method_1 = tests_helpers.client_get(self, self.client_authorized_1, "/reports/investments/lastoperation/?method=1", status.HTTP_200_OK)

