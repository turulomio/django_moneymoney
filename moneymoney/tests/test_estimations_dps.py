from rest_framework import status
from moneymoney import models
from moneymoney.reusing import tests_helpers


def test_EstimationsDps(self):
    # common _tests
    tests_helpers.common_tests_Collaborative(self, "/api/estimationsdps/", models.EstimationsDps.post_payload(), self.client_authorized_1, self.client_authorized_2, self.client_anonymous)
    
    # two estimations same product
    tests_helpers.client_post(self, self.client_authorized_1, "/api/estimationsdps/",  models.EstimationsDps.post_payload(estimation=1), status.HTTP_201_CREATED)
    dict_estimationdps_1=tests_helpers.client_post(self, self.client_authorized_1, "/api/estimationsdps/",  models.EstimationsDps.post_payload(estimation=2), status.HTTP_201_CREATED)
    dict_estimationsdps=tests_helpers.client_get(self, self.client_authorized_1, f"/api/estimationsdps/?product={dict_estimationdps_1['products']}", status.HTTP_200_OK)
    self.assertTrue(len(dict_estimationsdps),  1)
    self.assertTrue(dict_estimationsdps[0]["estimation"], 2)