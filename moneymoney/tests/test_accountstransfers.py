from django.utils import timezone
from moneymoney import models, functions

from request_casting.request_casting import id_from_url
from moneymoney.reusing import tests_helpers
from moneymoney.tests import assert_max_queries
from rest_framework import status

def test_Accountstransfers(self):      
    tests_helpers.client_get(self, self.client_authorized_1, "/api/accounts/4/", status.HTTP_200_OK)
    dict_destiny=tests_helpers.client_post(self, self.client_authorized_1, "/api/accounts/",  models.Accounts.post_payload(), status.HTTP_201_CREATED)

    # Create transfer  
    with assert_max_queries(self, 47):
        dict_transfer=tests_helpers.client_post(self, self.client_authorized_1, "/api/accountstransfers/",  models.Accountstransfers.post_payload(destiny=dict_destiny["url"]), status.HTTP_201_CREATED)
    with assert_max_queries(self,2):
        tests_helpers.client_get(self, self.client_authorized_1, "/api/accountsoperations/", status.HTTP_200_OK)
    self.assertEqual(models.Accountsoperations.objects.filter(associated_transfer__id=dict_transfer["id"]).count(), 3)
    self.assertEqual(list(models.Accountsoperations.objects.filter(associated_transfer__id=dict_transfer["id"]).values_list("id",  flat=True)), [id_from_url(dict_transfer["ao_origin"]), id_from_url(dict_transfer["ao_destiny"]), id_from_url(dict_transfer["ao_commission"])])
    self.assertEqual(models.Accountsoperations.objects.get(pk=id_from_url(dict_transfer["ao_origin"])).amount, -1000)
    self.assertEqual(models.Accountsoperations.objects.get(pk=id_from_url(dict_transfer["ao_destiny"])).amount, 1000)
    self.assertEqual(models.Accountsoperations.objects.get(pk=id_from_url(dict_transfer["ao_commission"])).amount, -10)
        
    # Update transfer
    dict_transfer_updated=tests_helpers.client_put(self, self.client_authorized_1, dict_transfer["url"],  models.Accountstransfers.post_payload(datetime=timezone.now(), amount=999, commission=9, destiny=dict_destiny["url"]), status.HTTP_200_OK)
    self.assertEqual(list(models.Accountsoperations.objects.filter(associated_transfer__id=dict_transfer["id"]).values_list("id",  flat=True)), [id_from_url(dict_transfer_updated["ao_origin"]), id_from_url(dict_transfer_updated["ao_destiny"]), id_from_url(dict_transfer_updated["ao_commission"])])   
    self.assertEqual(models.Accountsoperations.objects.filter(pk__in=[id_from_url(dict_transfer["ao_origin"]), id_from_url(dict_transfer["ao_destiny"]), id_from_url(dict_transfer["ao_commission"])]).count(), 0)
    self.assertEqual(models.Accountsoperations.objects.get(pk=id_from_url(dict_transfer_updated["ao_origin"])).amount, -999)
    self.assertEqual(models.Accountsoperations.objects.get(pk=id_from_url(dict_transfer_updated["ao_destiny"])).amount, 999)
    self.assertEqual(models.Accountsoperations.objects.get(pk=id_from_url(dict_transfer_updated["ao_commission"])).amount, -9)

    # Delete transfer
    self.client_authorized_1.delete(dict_transfer["url"])
    with self.assertRaises(models.Accountstransfers.DoesNotExist):
        models.Accountstransfers.objects.get(id=dict_transfer["id"])
    self.assertEqual(models.Accountsoperations.objects.filter(associated_transfer__id=dict_transfer["id"]).count(), 0)
