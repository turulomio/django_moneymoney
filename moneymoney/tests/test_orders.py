from moneymoney import models
from moneymoney.reusing import tests_helpers
from rest_framework import status


def test_Orders(self):
    # common _tests y deja creada una activa        
    dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",  models.Investments.post_payload(), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(products=dict_investment["products"]), status.HTTP_201_CREATED)

    tests_helpers.common_tests_Collaborative(self, "/api/orders/", models.Orders.post_payload(investments=dict_investment["url"]), self.client_authorized_1, self.client_authorized_2, self.client_anonymous)
