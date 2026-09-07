from rest_framework import status
from moneymoney.reusing import tests_helpers
    

def test_CatalogManager(self):
    r=tests_helpers.client_get(self, self.client_authorized_1,  "/catalog_manager/", status.HTTP_200_OK)
    self.assertFalse(r)
    r=tests_helpers.client_get(self, self.client_catalog_manager,  "/catalog_manager/", status.HTTP_200_OK)
    self.assertTrue(r)
    r=tests_helpers.client_get(self, self.client_anonymous,  "/catalog_manager/", status.HTTP_401_UNAUTHORIZED)
    self.assertEqual(r["detail"], "Authentication credentials were not provided.")

    