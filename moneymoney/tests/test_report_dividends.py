from rest_framework import status
from moneymoney import models
from moneymoney.reusing import tests_helpers
from django.utils import timezone
from datetime import date

def test_ReportDividends(self):
    # Create an investment
    dict_investment = tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",
                                                models.Investments.post_payload(name="Investment for dividends report"),
                                                status.HTTP_201_CREATED)
    
    # Add quotes for the product (79329 is default in post_payload)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",
                              models.Quotes.post_payload(products=dict_investment["products"], quote=100),
                              status.HTTP_201_CREATED)

    # Add investment operation to have shares
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/",
                              models.Investmentsoperations.post_payload(investments=dict_investment["url"], shares=10, price=10),
                              status.HTTP_201_CREATED)

    # Add EstimationDps
    tests_helpers.client_post(self, self.client_authorized_1, "/api/estimationsdps/",
                              models.EstimationsDps.post_payload(products=dict_investment["products"], estimation=5, year=timezone.now().year),
                              status.HTTP_201_CREATED)

    # Call the report view
    response = tests_helpers.client_get(self, self.client_authorized_1, "/reports/dividends/", status.HTTP_200_OK)
    
    # Check response
    found = False
    for item in response:
        # We check if this is our investment by checking shares and estimated value
        if item["shares"] == 10 and item["estimated"] == 50:
             found = True
             self.assertEqual(item["dps"], 5)
             self.assertEqual(item["current_price"], 100)
             break
    
    self.assertTrue(found)