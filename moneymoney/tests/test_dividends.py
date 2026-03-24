from rest_framework import status
from moneymoney import models
from moneymoney.reusing import tests_helpers
from django.utils import timezone
from decimal import Decimal

def test_Dividends(self):

    # Ensure an investment exists for Dividends
    # This also ensures product 79329 has quotes, as it's the default for Investments.post_payload
    dict_investment_1 = tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",
                                                  models.Investments.post_payload(name="Dividend Test Investment 1"),
                                                  status.HTTP_201_CREATED)
    
    dict_investment_2 = tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",
                                                  models.Investments.post_payload(name="Dividend Test Investment 2"),
                                                  status.HTTP_201_CREATED)

    # Ensure quotes exist for the products
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",
                              models.Quotes.post_payload(products=dict_investment_1["products"], quote=10),
                              status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",
                              models.Quotes.post_payload(products=dict_investment_2["products"], quote=12),
                              status.HTTP_201_CREATED)

    # --- Test Create Dividend ---
    initial_ao_count = models.Accountsoperations.objects.count()
    
    dividend_payload = models.Dividends.post_payload(
        investments=dict_investment_1["url"],
        gross=Decimal('100.00'),
        taxes=Decimal('20.00'),
        net=Decimal('80.00'),
        dps=Decimal('0.50'),
        datetime=timezone.now() - timezone.timedelta(days=30),
        commission=Decimal('5.00')
    )
    dict_dividend_1 = tests_helpers.client_post(self, self.client_authorized_1, "/api/dividends/",
                                                dividend_payload, status.HTTP_201_CREATED)

    # Check associated operation    
    self.assertIsNotNone(dict_dividend_1["accountsoperations"])
    dict_associated_ao=tests_helpers.client_get(self, self.client_authorized_1, dict_dividend_1["accountsoperations"], status.HTTP_200_OK)
    self.assertEqual(dict_associated_ao["amount"], Decimal('75.00'))



    # Test validation: negative taxes/commissions
    invalid_dividend_payload = models.Dividends.post_payload(
        investments=dict_investment_1["url"],
        gross=Decimal('100.00'),
        taxes=Decimal('-20.00'), # Invalid
        net=Decimal('120.00'),
        dps=Decimal('0.50'),
        datetime=timezone.now(),
        commission=Decimal('5.00')
    )
    response = tests_helpers.client_post(self, self.client_authorized_1, "/api/dividends/",
                                         invalid_dividend_payload, status.HTTP_400_BAD_REQUEST)
    self.assertEqual(response["__all__"][0], "Taxes and commissions must be equal or greater than zero")

    # --- Test Retrieve Dividend ---
    retrieved_dividend = tests_helpers.client_get(self, self.client_authorized_1,
                                                  dict_dividend_1["url"], status.HTTP_200_OK)
    self.assertEqual(retrieved_dividend["id"], dict_dividend_1["id"])
    self.assertEqual(Decimal(str(retrieved_dividend["gross"])), Decimal('100.00'))
    self.assertEqual(retrieved_dividend["investments"], dict_investment_1["url"])

    # --- Test List Dividends ---
    # Create a second dividend for filtering tests
    dividend_payload_2 = models.Dividends.post_payload(
        investments=dict_investment_2["url"],
        gross=Decimal('50.00'),
        taxes=Decimal('10.00'),
        net=Decimal('40.00'),
        dps=Decimal('0.25'),
        datetime=timezone.now() - timezone.timedelta(days=10),
        commission=Decimal('2.00')
    )
    dict_dividend_2 = tests_helpers.client_post(self, self.client_authorized_1, "/api/dividends/",
                                                dividend_payload_2, status.HTTP_201_CREATED)

    # List all dividends
    list_all = tests_helpers.client_get(self, self.client_authorized_1, "/api/dividends/", status.HTTP_200_OK)
    self.assertEqual(len(list_all), 2)

    # List by investment
    list_by_investment = tests_helpers.client_get(self, self.client_authorized_1,
                                                  f"/api/dividends/?investments[]={dict_investment_1['id']}",
                                                  status.HTTP_200_OK)
    self.assertEqual(len(list_by_investment), 1)
    self.assertEqual(list_by_investment[0]["id"], dict_dividend_1["id"])

    # --- Test Update Dividend ---
    updated_gross = Decimal('120.00')
    dict_dividend_1["gross"] = str(updated_gross) # API expects string for Decimal
    dict_dividend_1["net"] = str(updated_gross - Decimal('20.00')) # Update net to match
    updated_dividend = tests_helpers.client_put(self, self.client_authorized_1,
                                                dict_dividend_1["url"], dict_dividend_1, status.HTTP_200_OK)
    self.assertEqual(Decimal(str(updated_dividend["gross"])), updated_gross)

    # --- Test Delete Dividend ---
    tests_helpers.client_delete(self, self.client_authorized_1, dict_dividend_1["url"], {}, status.HTTP_204_NO_CONTENT)
    self.assertEqual(models.Dividends.objects.count(), 1)
    self.assertEqual(models.Accountsoperations.objects.count(), initial_ao_count + 1) # Only dict_dividend_2's AO remains
    tests_helpers.client_get(self, self.client_authorized_1, dict_dividend_1["url"], status.HTTP_404_NOT_FOUND)