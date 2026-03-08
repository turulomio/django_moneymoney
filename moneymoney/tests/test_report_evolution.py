from moneymoney import models
from moneymoney.reusing import tests_helpers
from rest_framework import status
from django.utils import timezone
from datetime import date, timedelta



def test_ReportEvolutionAssets_view(self):
    # Create an investment
    dict_investment = tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",
                                                models.Investments.post_payload(name="Investment for evolution assets report"),
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
    
    # Test with current year
    response = tests_helpers.client_get(self, self.client_authorized_1, f"/reports/evolutionassets/{current_year}/", status.HTTP_200_OK)
    self.assertTrue(len(response) > 0)
    
    # Test with a previous year
    response_past = tests_helpers.client_get(self, self.client_authorized_1, f"/reports/evolutionassets/{current_year-1}/", status.HTTP_200_OK)
    self.assertTrue(len(response_past) > 0)

def test_ReportEvolutionInvested_view(self):
    # Reuse the investment and operations setup from previous tests for efficiency
    # Assuming an investment and operations exist from other tests or are created here.
    # For a standalone test, you would create them as in test_ReportEvolutionAssets_view.
    
    # Call the report view for the current year
    current_year = date.today().year
    response = tests_helpers.client_get(self, self.client_authorized_1, f"/reports/evolutioninvested/{current_year}/", status.HTTP_200_OK)
    
    self.assertTrue(len(response) > 0)