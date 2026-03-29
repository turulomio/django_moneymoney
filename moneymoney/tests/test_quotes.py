from rest_framework import status
from moneymoney import models
from moneymoney.reusing import tests_helpers
from django.utils import timezone
from datetime import timedelta
from pydicts import casts
from asgiref.sync import sync_to_async


def test_Quotes_model(self):
    for i in range(4):
        models.Quotes.objects.create(products_id=79328+i, datetime=casts.dtaware_now(),quote=i)
        models.Quotes.objects.create(products_id=79328+i, datetime=casts.dtaware_now(),quote=i*10)

    with self.assertNumQueries(1):
        quotes=models.Quotes.qs_last_quotes()
        self.assertEqual(quotes.count(), 4)


def test_Quotes(self):
    for i in range(2):
        tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(quote=i+1), status.HTTP_201_CREATED)

    with self.assertNumQueries(1):
        quotes=tests_helpers.client_get(self, self.client_authorized_1, f"/api/quotes/?last=true", status.HTTP_200_OK)     

def test_Quotes_ohcl(self):
    for i in range(3):
        tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(quote=i+1,datetime=casts.dtaware_now()-timedelta(days=i), products="/api/products/79228/") , status.HTTP_201_CREATED)

    with self.assertNumQueries(2):
        ohcl=tests_helpers.client_get(self, self.client_authorized_1, f"/products/quotes/ohcl/?product=/api/products/79228/", status.HTTP_200_OK)      
    self.assertEqual(len(ohcl), 3)

