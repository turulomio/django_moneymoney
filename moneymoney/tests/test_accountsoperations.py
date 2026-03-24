from moneymoney import models
from moneymoney.reusing import tests_helpers
from moneymoney.functions import print_object
from rest_framework import status
from pydicts import lod
from django.utils import timezone
from moneymoney import types
from moneymoney.tests import assert_max_queries
from django.test import tag
from datetime import timedelta
from decimal import Decimal


def test_accountsoperations_model(self):
    o=models.Accountsoperations()
    o.accounts_id=4
    o.amount=-1000
    o.datetime=timezone.now()
    o.concepts_id=types.eConcept.BankCommissions
    o.save()

    #Creates 2 refunds
    refund=o.create_refund(timezone.now(), 10, "")
    refund=o.create_refund(timezone.now(), 20, "")

    self.assertEqual(len(o.refunds.all()), 2)
    self.assertEqual(refund.refund_original, o)




def test_accountsoperations_refunds(self):
    #Adding an ao
    dict_ao=tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/",  models.Accountsoperations.post_payload(concepts=f"/api/concepts/{types.eConcept.BankCommissions}/", amount=-1000), status.HTTP_201_CREATED)
    
    # Make two refunds    
    with assert_max_queries(self, 14):#Complex save its ok now
        dict_refund1=tests_helpers.client_post(self, self.client_authorized_1, dict_ao["url"]+"create_refund/", {"datetime": timezone.now(), "refund_amount":100, "comment": "First refund"} , status.HTTP_200_OK)
        self.assertEqual(dict_refund1["refund_original"],dict_ao["url"])

    dict_refund2=tests_helpers.client_post(self, self.client_authorized_1, dict_ao["url"]+"create_refund/", {"datetime": timezone.now(), "refund_amount":200, "comment": "Second refund"} , status.HTTP_200_OK)
    self.assertEqual(dict_refund2["refund_original"],dict_ao["url"])

    # Get refunds

    with assert_max_queries(self, 5):
        lod_refunds=tests_helpers.client_get(self, self.client_authorized_1, dict_ao["url"]+"get_refunds/" , status.HTTP_200_OK)
        sum_refunds=lod.lod_sum(lod_refunds, "amount")
        self.assertEqual(dict_ao["amount"]+sum_refunds, -700)

    # Set a too much high refund
    tests_helpers.client_post(self, self.client_authorized_1, dict_ao["url"]+"create_refund/", {"datetime": timezone.now(), "refund_amount":2000, "comment": "Too much"} , status.HTTP_400_BAD_REQUEST)

@tag("current")
def test_accountsoperations_different_currency(self):
    # Creates a new account with USD
    account_usd=models.Accounts.objects.create(name="New account", banks_id=3, active=True, decimals=2, currency="USD")
    ao_usd=models.Accountsoperations.objects.create(accounts=account_usd, amount=-1000, datetime=timezone.now(), concepts_id=types.eConcept.BankCommissions)
    self.assertEqual(ao_usd.accounts.currency, "USD")
    self.assertEqual(account_usd.balance(timezone.now(),currency_user="EUR")["balance_account_currency"],-1000)
    self.assertEqual(account_usd.balance(timezone.now(),currency_user="EUR")["balance_user_currency"],-1000)
    self.assertEqual(account_usd.balance(timezone.now(),currency_user="USD")["balance_account_currency"],-1000)
    self.assertEqual(account_usd.balance(timezone.now(),currency_user="USD")["balance_user_currency"],-1000)

    # Creates a new quote with EURUSD yesterday
    models.Quotes.objects.create(products_id=74747, datetime=timezone.now()-timedelta(days=1), quote=1.1)
    self.assertEqual(account_usd.balance(timezone.now(),currency_user="EUR")["balance_account_currency"],-1000) #USD
    self.assertEqual(account_usd.balance(timezone.now(),currency_user="EUR")["balance_user_currency"], Decimal('-909.0909090909090909090909091') ) #EUR
    self.assertEqual(account_usd.balance(timezone.now(),currency_user="USD")["balance_account_currency"],-1000) #USD
    self.assertEqual(account_usd.balance(timezone.now(),currency_user="USD")["balance_user_currency"],-1000) #USD



