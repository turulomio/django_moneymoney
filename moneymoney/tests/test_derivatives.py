from rest_framework import status
from moneymoney import models
from moneymoney.reusing import tests_helpers
from django.utils import timezone
from decimal import Decimal
from moneymoney import types

def test_Derivatives_view(self):
    # Ensure an investment exists for FastOperationsCoverage
    # This also ensures product 79329 has quotes, as it's the default for Investments.post_payload
    dict_investment = tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",
                                                models.Investments.post_payload(name="Derivatives Test Investment"),
                                                status.HTTP_201_CREATED)

    # Test Case 1: Initially empty
    response_empty = tests_helpers.client_get(self, self.client_authorized_1, "/derivatives/", status.HTTP_200_OK)
    self.assertEqual(response_empty["derivatives"], [])
    self.assertEqual(response_empty["balance"], [])

    # Test Case 2: Accountsoperations only
    # Jan 2023
    ao_payload_1 = models.Accountsoperations.post_payload(
        concepts=f"/api/concepts/{types.eConcept.DerivativesAdjustment}/",
        amount=Decimal('100.00'),
        datetime=timezone.datetime(2023, 1, 15, 10, 0, 0, tzinfo=timezone.UTC)
    )
    tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/", ao_payload_1, status.HTTP_201_CREATED)

    ao_payload_2 = models.Accountsoperations.post_payload(
        concepts=f"/api/concepts/{types.eConcept.FastInvestmentOperations}/",
        amount=Decimal('50.00'),
        datetime=timezone.datetime(2023, 1, 20, 11, 0, 0, tzinfo=timezone.UTC)
    )
    tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/", ao_payload_2, status.HTTP_201_CREATED)

    # Feb 2023
    ao_payload_3 = models.Accountsoperations.post_payload(
        concepts=f"/api/concepts/{types.eConcept.DerivativesAdjustment}/",
        amount=Decimal('200.00'),
        datetime=timezone.datetime(2023, 2, 10, 12, 0, 0, tzinfo=timezone.UTC)
    )
    tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/", ao_payload_3, status.HTTP_201_CREATED)

    response_ao = tests_helpers.client_get(self, self.client_authorized_1, "/derivatives/", status.HTTP_200_OK)

    self.assertEqual(response_ao["balance"][0]["total"], Decimal('350'))

    # Test Case 3: FastOperationsCoverage data (added to existing data)
    # Jan 2023
    foc_payload_1 = {
        "datetime": timezone.datetime(2023, 1, 25, 13, 0, 0, tzinfo=timezone.UTC),
        "investments": dict_investment["url"],
        "amount": Decimal('20.00'),
        "comment": "FOC 1"
    }
    tests_helpers.client_post(self, self.client_authorized_1, "/api/fastoperationscoverage/", foc_payload_1, status.HTTP_201_CREATED)

    # Feb 2023
    foc_payload_2 = {
        "datetime": timezone.datetime(2023, 2, 20, 14, 0, 0, tzinfo=timezone.UTC),
        "investments": dict_investment["url"],
        "amount": Decimal('30.00'),
        "comment": "FOC 2"
    }
    tests_helpers.client_post(self, self.client_authorized_1, "/api/fastoperationscoverage/", foc_payload_2, status.HTTP_201_CREATED)

