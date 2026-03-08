
from decimal import Decimal
from moneymoney import models
from moneymoney.reusing import tests_helpers
from rest_framework import status
from django.utils import timezone



def test_Accounts_model(self):
    a=models.Accounts()
    a.name="New account"
    a.banks_id=3
    a.active=True
    a.decimals=2
    a.save()
    str(a)

def test_Accounts(self):
    #accounts_balance with empty database
    qs_accounts=models.Accounts.objects.filter(active=True)
    r=models.Accounts.accounts_balance(qs_accounts, timezone.now(), 'EUR')
    self.assertEqual(r["balance_user_currency"], Decimal(0))
    
    #Adding an ao
    tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/",  models.Accountsoperations.post_payload(), status.HTTP_201_CREATED)
    
    #accounts_balance with empty database
    qs_accounts=models.Accounts.objects.filter(active=True)
    r=models.Accounts.accounts_balance(qs_accounts, timezone.now(), 'EUR')
    self.assertEqual(r["balance_user_currency"], 1000)
