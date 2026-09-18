from datetime import timedelta
from moneymoney import models
from moneymoney.reusing import tests_helpers
from rest_framework import status


def test_Alerts(self):
    # Create an expired order
    dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",  models.Investments.post_payload(), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(products=dict_investment["products"], datetime=self.dtaware_now - timedelta(days=365)), status.HTTP_201_CREATED)
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

    # Create an investment operation on product 79226 with quote after the operation
    dict_inv_79226 = tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(products="/api/products/79226/"), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/", models.Quotes.post_payload(products="/api/products/79226/", datetime=self.dtaware_now), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(investments=dict_inv_79226["url"], datetime=self.dtaware_now - timedelta(days=10)), status.HTTP_201_CREATED)

    # Search alerts
    lod_alerts=tests_helpers.client_get(self, self.client_authorized_1, "/alerts/",  status.HTTP_200_OK)
    self.assertEqual(len(lod_alerts["orders_expired"]), 1 )
    self.assertEqual(len(lod_alerts["accounts_inactive_with_balance"]), 1 )
    self.assertEqual(len(lod_alerts["investments_inactive_with_balance"]), 1 )
    self.assertEqual(len(lod_alerts["banks_inactive_with_balance"]), 1 )
    self.assertEqual(len(lod_alerts["investments_transfers_unfinished"]), 1 )
    self.assertEqual(len(lod_alerts["products_without_quotes_before_operations"]), 1 )
    self.assertEqual(lod_alerts["products_without_quotes_before_operations"][0]["url"], "http://testserver/api/products/79226/" )
    self.assertIn("datetime", lod_alerts["products_without_quotes_before_operations"][0])
    self.assertEqual(lod_alerts["products_without_quotes_before_operations"][0]["datetime"], (self.dtaware_now - timedelta(days=10)).isoformat().replace("+00:00", "Z"))

    # Now add quote before the operation datetime and verify alert disappears
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/", models.Quotes.post_payload(products="/api/products/79226/", datetime=self.dtaware_now - timedelta(days=20)), status.HTTP_201_CREATED)
    lod_alerts=tests_helpers.client_get(self, self.client_authorized_1, "/alerts/",  status.HTTP_200_OK)
    self.assertEqual(len(lod_alerts["products_without_quotes_before_operations"]), 0 )


def test_Alerts_benchmark(self):
    """
    Benchmark test for Alerts endpoint with scaled dataset.
    Populates hundreds of quotes, operations, accounts, and orders to test index efficiency.
    """
    import time
    from decimal import Decimal

    # Setup 5 products with 100 historical quotes each (500 quotes)
    products = list(models.Products.objects.filter(obsolete=False)[:5])
    quotes_to_create = []
    for product in products:
        for day in range(1, 101):
            dt = self.dtaware_now - timedelta(days=day)
            quotes_to_create.append(
                models.Quotes(
                    products=product,
                    datetime=dt,
                    quote=Decimal("100.000000") + Decimal(str(day * 0.1))
                )
            )
    models.Quotes.objects.bulk_create(quotes_to_create)

    # Setup inactive and active accounts with operations
    bank = models.Banks.objects.first()
    concept = models.Concepts.objects.first()
    accounts_to_create = [
        models.Accounts(name=f"Bench Account {i}", banks=bank, active=(i % 2 == 0), currency="EUR", decimals=2)
        for i in range(10)
    ]
    models.Accounts.objects.bulk_create(accounts_to_create)
    all_accounts = list(models.Accounts.objects.filter(name__startswith="Bench Account"))

    # Bulk insert account operations
    ao_to_create = []
    for acc in all_accounts:
        for day in range(1, 21):
            ao_to_create.append(
                models.Accountsoperations(
                    accounts=acc,
                    concepts=concept,
                    amount=Decimal("50.00"),
                    datetime=self.dtaware_now - timedelta(days=day)
                )
            )
    models.Accountsoperations.objects.bulk_create(ao_to_create)

    # Setup investments with operations
    optype = models.Operationstypes.objects.get(id=4)
    investments_to_create = [
        models.Investments(
            name=f"Bench Inv {i}",
            active=(i % 2 == 0),
            accounts=all_accounts[i % len(all_accounts)],
            products=products[i % len(products)],
            selling_price=Decimal("0"),
            daily_adjustment=False,
            balance_percentage=Decimal("100"),
            decimals=6
        )
        for i in range(6)
    ]
    models.Investments.objects.bulk_create(investments_to_create)
    all_investments = list(models.Investments.objects.filter(name__startswith="Bench Inv"))

    invops_to_create = []
    for inv in all_investments:
        for day in range(1, 15):
            invops_to_create.append(
                models.Investmentsoperations(
                    investments=inv,
                    operationstypes=optype,
                    shares=Decimal("10.000000"),
                    price=Decimal("100.000000"),
                    taxes=Decimal("0.00"),
                    commission=Decimal("0.00"),
                    currency_conversion=Decimal("1.0000000000"),
                    datetime=self.dtaware_now - timedelta(days=day)
                )
            )
    models.Investmentsoperations.objects.bulk_create(invops_to_create)

    # Setup orders
    orders_to_create = [
        models.Orders(
            date=self.today - timedelta(days=5),
            expiration=self.today - timedelta(days=2),
            shares=Decimal("10.000000"),
            price=Decimal("100.000000"),
            investments=all_investments[0],
            executed=None
        )
    ]
    models.Orders.objects.bulk_create(orders_to_create)

    # Warmup call
    tests_helpers.client_get(self, self.client_authorized_1, "/alerts/", status.HTTP_200_OK)

    # Benchmark multiple calls
    iterations = 5
    start_time = time.perf_counter()
    for _ in range(iterations):
        resp = tests_helpers.client_get(self, self.client_authorized_1, "/alerts/", status.HTTP_200_OK)
        self.assertIn("server_time", resp)
        self.assertIn("orders_expired", resp)
        self.assertIn("products_without_quotes_before_operations", resp)

    elapsed_time = time.perf_counter() - start_time
    avg_time_per_request = elapsed_time / iterations

    # Average request time should be well below 250ms (0.25s) with database indexes
    self.assertLess(avg_time_per_request, 0.25, f"Alerts.get too slow: {avg_time_per_request:.4f}s per request")