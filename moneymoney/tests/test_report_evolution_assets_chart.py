from rest_framework import status
from moneymoney import models
from moneymoney.reusing import tests_helpers
from django.utils import timezone
from datetime import date, timedelta

def test_ReportEvolutionAssetsChart(self):
    # Create an investment
    dict_investment = tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",
                                                models.Investments.post_payload(name="Investment for evolution chart"),
                                                status.HTTP_201_CREATED)
    
    # Add quotes for the product (79329 is default in post_payload)
    # Add a quote in the past (more than a year ago)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",
                              models.Quotes.post_payload(products=dict_investment["products"], quote=100, datetime=timezone.now() - timedelta(days=400)),
                              status.HTTP_201_CREATED)
    # Add a quote recently
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",
                              models.Quotes.post_payload(products=dict_investment["products"], quote=120, datetime=timezone.now()),
                              status.HTTP_201_CREATED)

    # Add investment operation to have shares in the past
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/",
                              models.Investmentsoperations.post_payload(investments=dict_investment["url"], shares=10, price=100, datetime=timezone.now() - timedelta(days=380)),
                              status.HTTP_201_CREATED)

    current_year = date.today().year
    
    # Test with current year (last 12 months logic)
    response = tests_helpers.client_get(self, self.client_authorized_1, f"/reports/evolution_assets_chart/?from={current_year}", status.HTTP_200_OK)
    
    self.assertTrue(len(response) > 0)
    # Check structure of the first element
    item = response[0]
    self.assertIn("datetime", item)
    self.assertIn("total_user", item)
    self.assertIn("invested_user", item)
    self.assertIn("investments_user", item)
    self.assertIn("accounts_user", item)
    self.assertIn("zerorisk_user", item)
    
    # Test with a previous year
    response_past = tests_helpers.client_get(self, self.client_authorized_1, f"/reports/evolution_assets_chart/?from={current_year-1}", status.HTTP_200_OK)
    self.assertTrue(len(response_past) > 0)