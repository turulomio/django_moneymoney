from rest_framework import status
from moneymoney import models
from moneymoney.reusing import tests_helpers
from django.utils import timezone

def test_Currencies(self):
    # Create USD account to ensure we have EUR and USD currencies available
    tests_helpers.client_post(self, self.client_authorized_1, "/api/accounts/", 
                              models.Accounts.post_payload(name="USD Account", currency="USD"), 
                              status.HTTP_201_CREATED)

    # Ensure product 74747 exists for EUR/USD conversion (hardcoded in view)
    if not models.Products.objects.filter(id=74747).exists():
        models.Products.objects.create(
            id=74747,
            name="EUR/USD",
            currency="USD",
            productstypes=models.Productstypes.objects.first(),
            productsstrategies=models.ProductsStrategies.objects.first(),
            leverages=models.Leverages.objects.first(),
            stockmarkets=models.Stockmarkets.objects.first(),
            percentage=100,
            obsolete=False,
            system=True
        )

    # Add a quote for 74747
    models.Quotes.objects.create(
        products_id=74747,
        datetime=timezone.now(),
        quote=1.2
    )

    # Call the view
    response = tests_helpers.client_get(self, self.client_authorized_1, "/currencies/", status.HTTP_200_OK)
    
    # Check EUR -> USD
    eur_usd = next((item for item in response if item["from"] == "EUR" and item["to"] == "USD"), None)
    self.assertIsNotNone(eur_usd)
    self.assertTrue(eur_usd["supported"])
    self.assertEqual(float(eur_usd["quote"]), 1.2)

    # Check USD -> EUR
    usd_eur = next((item for item in response if item["from"] == "USD" and item["to"] == "EUR"), None)
    self.assertIsNotNone(usd_eur)
    self.assertTrue(usd_eur["supported"])
    self.assertAlmostEqual(float(usd_eur["quote"]), 1/1.2, places=5)