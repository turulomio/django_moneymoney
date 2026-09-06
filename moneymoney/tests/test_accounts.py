
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

def test_Accounts_balance_action(self):
    account = models.Accounts.objects.get(pk=4)
    # 1. Current balance
    res = tests_helpers.client_get(self, self.client_authorized_1, f"/api/accounts/{account.id}/balance/", status.HTTP_200_OK)
    self.assertEqual(res["id"], account.id)
    self.assertEqual(res["currency"], account.currency)
    self.assertIn("balance_account", res)
    self.assertIn("balance_user", res)
    initial_balance = res["balance_account"]

    # 2. Add an operation on 2024-05-15
    dt_op = timezone.datetime(2024, 5, 15, 12, 0, tzinfo=timezone.UTC)
    tests_helpers.client_post(
        self,
        self.client_authorized_1,
        "/api/accountsoperations/",
        models.Accountsoperations.post_payload(
            accounts=f"http://testserver/api/accounts/{account.id}/",
            amount=500,
            datetime=dt_op
        ),
        status.HTTP_201_CREATED
    )

    # 3. Check balance for month 2024-04 (before operation) -> should be initial_balance
    res_april = tests_helpers.client_get(self, self.client_authorized_1, f"/api/accounts/{account.id}/balance/?year=2024&month=4", status.HTTP_200_OK)
    self.assertEqual(res_april["balance_account"], initial_balance)

    # 4. Check balance for month 2024-05 (month of operation) -> should include +500
    res_may = tests_helpers.client_get(self, self.client_authorized_1, f"/api/accounts/{account.id}/balance/?year=2024&month=5", status.HTTP_200_OK)
    self.assertEqual(res_may["balance_account"], initial_balance + 500)

    # 5. Check balance with year filter only -> end of year 2024
    res_year = tests_helpers.client_get(self, self.client_authorized_1, f"/api/accounts/{account.id}/balance/?year=2024", status.HTTP_200_OK)
    self.assertEqual(res_year["balance_account"], initial_balance + 500)

    # 6. Error cases (HTTP 400 BAD REQUEST)
    # 6.1 Month without year
    tests_helpers.client_get(self, self.client_authorized_1, f"/api/accounts/{account.id}/balance/?month=5", status.HTTP_400_BAD_REQUEST)

    # 6.2 Invalid month (> 12)
    tests_helpers.client_get(self, self.client_authorized_1, f"/api/accounts/{account.id}/balance/?year=2024&month=13", status.HTTP_400_BAD_REQUEST)

    # 6.3 Invalid month (< 1)
    tests_helpers.client_get(self, self.client_authorized_1, f"/api/accounts/{account.id}/balance/?year=2024&month=0", status.HTTP_400_BAD_REQUEST)

    # 6.4 Non-integer month
    tests_helpers.client_get(self, self.client_authorized_1, f"/api/accounts/{account.id}/balance/?year=2024&month=abc", status.HTTP_400_BAD_REQUEST)

    # 6.5 Invalid year
    tests_helpers.client_get(self, self.client_authorized_1, f"/api/accounts/{account.id}/balance/?year=invalid", status.HTTP_400_BAD_REQUEST)

    # 6.6 Invalid datetime string
    tests_helpers.client_get(self, self.client_authorized_1, f"/api/accounts/{account.id}/balance/?datetime=not-a-datetime", status.HTTP_400_BAD_REQUEST)

    # 6.7 Conflicting datetime and year/month parameters
    tests_helpers.client_get(self, self.client_authorized_1, f"/api/accounts/{account.id}/balance/?year=2024&datetime=2024-05-15T12:00:00Z", status.HTTP_400_BAD_REQUEST)

