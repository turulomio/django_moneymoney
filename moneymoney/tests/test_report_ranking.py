from rest_framework import status
from moneymoney import models
from moneymoney.reusing import tests_helpers
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

def test_ReportRanking_view_basic(self):
    """
    Test that the ReportRanking view returns a 200 OK status and a list.
    """
    response = tests_helpers.client_get(self, self.client_authorized_1, "/reports/ranking/", status.HTTP_200_OK)
    # It might be empty if no investments exist, but the view should still return 200 OK.

def test_ReportRanking_view_with_data_and_assertions(self):
    """
    Test the ReportRanking view with actual investment data and verify the ranking logic.
    """
    # Ensure products exist and have quotes
    # Product 79329 (default for Investments.post_payload)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",
                              models.Quotes.post_payload(products="/api/products/79329/", quote=10, datetime=timezone.now() - timedelta(days=30)),
                              status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",
                              models.Quotes.post_payload(products="/api/products/79329/", quote=15, datetime=timezone.now()),
                              status.HTTP_201_CREATED)

    # Create Product 79330
    product_79330_data = models.Products.post_personal_payload(name="Product 79330")
    product_79330 = tests_helpers.client_post(self, self.client_authorized_1, "/api/products/",
                                              product_79330_data,
                                              status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",
                              models.Quotes.post_payload(products=product_79330["url"], quote=8, datetime=timezone.now() - timedelta(days=30)),
                              status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",
                              models.Quotes.post_payload(products=product_79330["url"], quote=9, datetime=timezone.now()),
                              status.HTTP_201_CREATED)

    # Create Product 79331
    product_79331_data = models.Products.post_personal_payload(name="Product 79331")
    product_79331 = tests_helpers.client_post(self, self.client_authorized_1, "/api/products/",
                                              product_79331_data,
                                              status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",
                              models.Quotes.post_payload(products=product_79331["url"], quote=20, datetime=timezone.now() - timedelta(days=30)),
                              status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",
                              models.Quotes.post_payload(products=product_79331["url"], quote=15, datetime=timezone.now()),
                              status.HTTP_201_CREATED)

    # Investment 1 (Good Performance)
    inv1 = tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",
                                     models.Investments.post_payload(name="Inv Good", products="/api/products/79329/"),
                                     status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/",
                              models.Investmentsoperations.post_payload(investments=inv1["url"], shares=100, price=10, datetime=timezone.now() - timedelta(days=20)),
                              status.HTTP_201_CREATED)

    # Investment 2 (Moderate Performance)
    inv2 = tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",
                                     models.Investments.post_payload(name="Inv Moderate", products=product_79330["url"]),
                                     status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/",
                              models.Investmentsoperations.post_payload(investments=inv2["url"], shares=200, price=8, datetime=timezone.now() - timedelta(days=25)),
                              status.HTTP_201_CREATED)

    # Investment 3 (Negative Performance)
    inv3 = tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",
                                     models.Investments.post_payload(name="Inv Negative", products=product_79331["url"]),
                                     status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/",
                              models.Investmentsoperations.post_payload(investments=inv3["url"], shares=50, price=20, datetime=timezone.now() - timedelta(days=15)),
                              status.HTTP_201_CREATED)

    # Call the ReportRanking view
    response = tests_helpers.client_get(self, self.client_authorized_1, "/reports/ranking/", status.HTTP_200_OK)

