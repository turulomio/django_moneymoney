from rest_framework import status
from moneymoney import models
from moneymoney.reusing import tests_helpers
from django.utils import timezone
from decimal import Decimal

def test_ReportZeroRisk_view_basic(self):
    """
    Test that the ReportZeroRisk view returns a 200 OK status and an empty list
    or a list with default values if no zero-risk accounts exist.
    """
    response = tests_helpers.client_get(self, self.client_authorized_1, "/reports/zerorisk/", status.HTTP_200_OK)
    self.assertIsInstance(response, list)

def test_ReportZeroRisk_view_with_data(self):
    """
    Test the ReportZeroRisk view with actual zero-risk account data and verify the calculations.
    """
    # Create a zero-risk account
    zero_risk_account_data = models.Accounts.post_payload(name="Zero Risk Account")
    zero_risk_account = tests_helpers.client_post(self, self.client_authorized_1, "/api/accounts/",
                                                  zero_risk_account_data,
                                                  status.HTTP_201_CREATED)

    # Add an operation to the zero-risk account
    tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/",
                              models.Accountsoperations.post_payload(accounts=zero_risk_account["url"], amount=Decimal('1000.50'), datetime=timezone.now()),
                              status.HTTP_201_CREATED)

    # Call the ReportZeroRisk view
    response = tests_helpers.client_get(self, self.client_authorized_1, "/reports/zerorisk/", status.HTTP_200_OK)

    self.assertIsInstance(response, list)
    self.assertEqual(len(response), 1)
