from rest_framework import status
from moneymoney import models
from moneymoney.reusing import tests_helpers

def test_Products(self):
    # Personal products CRUD
    dict_pp=tests_helpers.client_post(self, self.client_authorized_1, "/api/products/", models.Products.post_personal_payload(), status.HTTP_201_CREATED)
    dict_pp_update=dict_pp.copy()
    dict_pp_update["comment"]="Updated"
    dict_pp_update["system"]=False
    dict_pp_update=tests_helpers.client_put(self, self.client_authorized_1, dict_pp["url"], dict_pp_update, status.HTTP_200_OK)
    tests_helpers.client_delete(self, self.client_authorized_1, dict_pp["url"], dict_pp_update, status.HTTP_204_NO_CONTENT)
    
    # System products CRUD
    tests_helpers.client_post(self, self.client_authorized_1, "/api/products/", models.Products.post_system_payload(), status.HTTP_400_BAD_REQUEST)
    dict_sp=tests_helpers.client_post(self, self.client_catalog_manager, "/api/products/", models.Products.post_system_payload(), status.HTTP_201_CREATED)
    dict_sp_update=dict_sp.copy()
    dict_sp_update["comment"]="Updated"
    dict_sp_update["system"]=True
    tests_helpers.client_put(self, self.client_authorized_1, dict_sp["url"], dict_sp_update, status.HTTP_400_BAD_REQUEST)
    dict_sp_update=tests_helpers.client_put(self, self.client_catalog_manager, dict_sp["url"], dict_sp_update, status.HTTP_200_OK)
    tests_helpers.client_delete(self, self.client_authorized_1, dict_sp["url"], dict_sp_update, status.HTTP_400_BAD_REQUEST)
    tests_helpers.client_delete(self, self.client_catalog_manager, dict_sp["url"], dict_sp_update, status.HTTP_204_NO_CONTENT)

def test_Products_delete_last_quote(self):
    # Personal products CRUD
    dict_pp=tests_helpers.client_post(self, self.client_authorized_1, "/api/products/", models.Products.post_personal_payload(), status.HTTP_201_CREATED)
    
    # Create two quotes
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/", models.Quotes.post_payload(products=dict_pp["url"], quote=10), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/", models.Quotes.post_payload(products=dict_pp["url"], quote=12), status.HTTP_201_CREATED)
    
    self.assertEqual(models.Quotes.objects.filter(products_id=dict_pp["id"]).count(), 2)
    
    # Delete last quote
    tests_helpers.client_post(self, self.client_authorized_1, f"{dict_pp['url']}delete_last_quote/", {}, status.HTTP_204_NO_CONTENT)
    
    self.assertEqual(models.Quotes.objects.filter(products_id=dict_pp["id"]).count(), 1)
    self.assertEqual(models.Quotes.objects.get(products_id=dict_pp["id"]).quote, 10)

def test_Products_search_with_quotes(self):
    # Create product
    dict_pp=tests_helpers.client_post(self, self.client_authorized_1, "/api/products/", models.Products.post_personal_payload(name="SearchMe"), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/", models.Quotes.post_payload(products=dict_pp["url"], quote=10), status.HTTP_201_CREATED)
    
    # Search by text
    r=tests_helpers.client_get(self, self.client_authorized_1, "/api/products/search_with_quotes/?search=SearchMe", status.HTTP_200_OK)
    self.assertEqual(len(r), 1)
    self.assertEqual(r[0]["id"], dict_pp["id"])
    self.assertEqual(r[0]["last"], 10)
    
    # Search by favorites
    p=models.Products.objects.get(pk=dict_pp["id"])
    self.user_authorized_1.profile.favorites.add(p)
    r=tests_helpers.client_get(self, self.client_authorized_1, "/api/products/search_with_quotes/?search=:FAVORITES", status.HTTP_200_OK)
    ids=[x["id"] for x in r]
    self.assertIn(dict_pp["id"], ids)
    
    # Search by investments
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(products=dict_pp["url"]), status.HTTP_201_CREATED)
    r=tests_helpers.client_get(self, self.client_authorized_1, "/api/products/search_with_quotes/?search=:INVESTMENTS", status.HTTP_200_OK)
    ids=[x["id"] for x in r]
    self.assertIn(dict_pp["id"], ids)

def test_Products_historical_information(self):
    from datetime import timedelta
    # Create product
    dict_pp=tests_helpers.client_post(self, self.client_authorized_1, "/api/products/", models.Products.post_personal_payload(name="Historical"), status.HTTP_201_CREATED)
    
    # Create quotes in different months
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/", models.Quotes.post_payload(products=dict_pp["url"], quote=10, datetime=self.now), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/", models.Quotes.post_payload(products=dict_pp["url"], quote=20, datetime=self.now-timedelta(days=40)), status.HTTP_201_CREATED)
    
    r=tests_helpers.client_get(self, self.client_authorized_1, f"{dict_pp['url']}historical_information/", status.HTTP_200_OK)
    self.assertTrue("quotes" in r)
    self.assertTrue("percentages" in r)
    self.assertTrue(len(r["quotes"])>0)
