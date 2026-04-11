
from rest_framework import status
from moneymoney import models
from moneymoney.reusing import tests_helpers
from django.utils import timezone

def test_Currencies(self):
    # Runs currencies with empty data
    lod_empty_currencies=tests_helpers.client_get(self, self.client_authorized_1, "/currencies/", status.HTTP_200_OK)
    self.assertEqual(len(lod_empty_currencies), 0)
    self.assertCountEqual(models.Assets.currencies(), ["EUR"])


    # Create USD account to ensure we have EUR and USD currencies available
    tests_helpers.client_post(self, self.client_authorized_1, "/api/accounts/", models.Accounts.post_payload(name="USD Account", currency="USD"), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/", models.Accountsoperations.post_payload(), status.HTTP_201_CREATED)
    self.assertCountEqual(models.Assets.currencies(), ["EUR", "USD"])


    # Runs currencies with usd account and eur as user
    lod_currencies=tests_helpers.client_get(self, self.client_authorized_1, "/currencies/", status.HTTP_200_OK)
    self.assertEqual(len(lod_currencies), 2)
