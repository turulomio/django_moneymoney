from datetime import timedelta
from moneymoney import models
from moneymoney.reusing import tests_helpers
from rest_framework import status


def test_Alerts(self):
    # Create an expired order
    dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",  models.Investments.post_payload(), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(products=dict_investment["products"]), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1,  "/api/orders/", models.Orders.post_payload(investments=dict_investment["url"], expiration=self.today-timedelta(days=1)), status.HTTP_201_CREATED)
    
    # Create an account inactive with balance
    dict_account=tests_helpers.client_post(self, self.client_authorized_1, "/api/accounts/",  models.Accounts.post_payload(active=False), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/",  models.Accountsoperations.post_payload(accounts=dict_account["url"]), status.HTTP_201_CREATED)

    # Create an investmentoperation in an inactive investment
    dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",  models.Investments.post_payload(active=False), status.HTTP_201_CREATED)        
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(dict_investment["url"]), status.HTTP_201_CREATED)#Al actualizar ao asociada ejecuta otro plio
    dict_investment=tests_helpers.client_put(self, self.client_authorized_1, dict_investment["url"], models.Investments.post_payload(active=False), status.HTTP_200_OK)     

    # Create a bank inactive with accounts
    dict_bank=tests_helpers.client_post(self, self.client_authorized_1, "/api/banks/",  models.Banks.post_payload(active=False), status.HTTP_201_CREATED)
    dict_account=tests_helpers.client_post(self, self.client_authorized_1, "/api/accounts/",  models.Accounts.post_payload(banks=dict_bank["url"]), status.HTTP_201_CREATED)        
    tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/",  models.Accountsoperations.post_payload(accounts=dict_account["url"]), status.HTTP_201_CREATED)

    # Create an unfinished investments transfer
    dict_investment_for_it=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",  models.Investments.post_payload(), status.HTTP_201_CREATED)  
    dict_it=tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentstransfers/", models.Investmentstransfers.post_payload(investments_origin=dict_investment_for_it["url"], investments_destiny=dict_investment_for_it["url"], datetime_destiny=None), status.HTTP_201_CREATED)
    self.assertEqual(dict_it["finished"], False)


    # Search alerts
    lod_alerts=tests_helpers.client_get(self, self.client_authorized_1, "/alerts/",  status.HTTP_200_OK)
    self.assertEqual(len(lod_alerts["orders_expired"]), 1 )
    self.assertEqual(len(lod_alerts["accounts_inactive_with_balance"]), 1 )
    self.assertEqual(len(lod_alerts["investments_inactive_with_balance"]), 1 )
    self.assertEqual(len(lod_alerts["banks_inactive_with_balance"]), 1 )
    self.assertEqual(len(lod_alerts["investments_transfers_unfinished"]), 1 )