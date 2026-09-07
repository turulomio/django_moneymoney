from rest_framework import status
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from moneymoney import models
from moneymoney.reusing import tests_helpers

def test_Splits_validation(self):
    # Retrieve test product (e.g. ID 79328 from fixtures)
    product = models.Products.objects.get(pk=79328)
    
    # Try to save split with invalid before/after
    split_invalid_before = models.Splits(
        datetime=timezone.now(),
        products=product,
        before=0,
        after=2
    )
    with self.assertRaises(ValidationError):
        split_invalid_before.save()

    split_invalid_after = models.Splits(
        datetime=timezone.now(),
        products=product,
        before=1,
        after=-5
    )
    with self.assertRaises(ValidationError):
        split_invalid_after.save()

def test_Splits_integration_flow(self):
    # 1. Setup mock data
    # Retrieve a product from fixtures
    product = models.Products.objects.get(pk=79328)
    
    # Create Quotes with specific datetimes (using numbers divisible by 6 to avoid rounding errors)
    now = timezone.now()
    dt_10_days_ago = now - timedelta(days=10)
    dt_5_days_ago = now - timedelta(days=5)
    dt_today = now
    
    quote1 = models.Quotes.objects.create(products=product, datetime=dt_10_days_ago, quote=Decimal('120.000000'))
    quote2 = models.Quotes.objects.create(products=product, datetime=dt_5_days_ago, quote=Decimal('120.000000'))
    quote3 = models.Quotes.objects.create(products=product, datetime=dt_today, quote=Decimal('65.000000'))

    # Retrieve an account and operation type
    account = models.Accounts.objects.all()[0]
    op_type_purchase = models.Operationstypes.objects.get(pk=4) # Shares purchase
    concept_buy = models.Concepts.objects.get(pk=28) # Shares purchase concept
    
    # Create an Investment
    investment = models.Investments.objects.create(
        name="Test Split Investment",
        active=True,
        accounts=account,
        selling_price=Decimal('180.000000'),
        products=product,
        daily_adjustment=False,
        balance_percentage=Decimal('100.000000'),
        decimals=6
    )

    # Create Investment operations
    dt_15_days_ago = now - timedelta(days=15)
    dt_3_days_ago = now - timedelta(days=3)
    
    # Operation 1 (15 days ago, should be affected)
    op1 = models.Investmentsoperations.objects.create(
        operationstypes=op_type_purchase,
        investments=investment,
        shares=Decimal('12.000000'),
        taxes=Decimal('0.00'),
        commission=Decimal('0.00'),
        price=Decimal('120.000000'),
        datetime=dt_15_days_ago,
        currency_conversion=Decimal('1.000000')
    )
    
    # Operation 2 (3 days ago, should NOT be affected by a split 4 days ago)
    op2 = models.Investmentsoperations.objects.create(
        operationstypes=op_type_purchase,
        investments=investment,
        shares=Decimal('5.000000'),
        taxes=Decimal('0.00'),
        commission=Decimal('0.00'),
        price=Decimal('115.000000'),
        datetime=dt_3_days_ago,
        currency_conversion=Decimal('1.000000')
    )

    # Create Dividend
    dt_12_days_ago = now - timedelta(days=12)
    dividend = models.Dividends.objects.create(
        investments=investment,
        gross=Decimal('120.00'),
        taxes=Decimal('0.00'),
        net=Decimal('120.00'),
        dps=Decimal('12.000000'),
        datetime=dt_12_days_ago,
        concepts=concept_buy,
        commission=Decimal('0.00'),
        currency_conversion=Decimal('1.000000')
    )

    # Create Order 1 (15 days ago, should be affected by split 4 days ago)
    order1 = models.Orders.objects.create(
        date=dt_15_days_ago.date(),
        shares=Decimal('12.000000'),
        price=Decimal('120.000000'),
        investments=investment
    )

    # Create Order 2 (3 days ago, should NOT be affected)
    order2 = models.Orders.objects.create(
        date=dt_3_days_ago.date(),
        shares=Decimal('5.000000'),
        price=Decimal('115.000000'),
        investments=investment
    )

    # Create Dps 1 (15 days ago, should be affected)
    dps1 = models.Dps.objects.create(
        date=dt_15_days_ago.date(),
        gross=Decimal('12.000000'),
        products=product,
        paydate=dt_15_days_ago.date()
    )

    # Create Dps 2 (3 days ago, should NOT be affected)
    dps2 = models.Dps.objects.create(
        date=dt_3_days_ago.date(),
        gross=Decimal('15.000000'),
        products=product,
        paydate=dt_3_days_ago.date()
    )

    # Create EstimationsDps 1 (15 days ago, should be affected)
    est1 = models.EstimationsDps.objects.create(
        year=dt_15_days_ago.year - 1,
        products=product,
        estimation=Decimal('24.000000'),
        date_estimation=dt_15_days_ago.date()
    )

    # Create EstimationsDps 2 (3 days ago, should NOT be affected)
    est2 = models.EstimationsDps.objects.create(
        year=dt_3_days_ago.year,
        products=product,
        estimation=Decimal('30.000000'),
        date_estimation=dt_3_days_ago.date()
    )

    # 2. Apply a 2-for-1 split (Before=1, After=2) 4 days ago
    dt_split = now - timedelta(days=4)
    split = models.Splits.objects.create(
        datetime=dt_split,
        products=product,
        before=1,
        after=2,
        comment="2-for-1 stock split test"
    )

    # 3. Assert values are adjusted correctly
    quote1.refresh_from_db()
    quote2.refresh_from_db()
    quote3.refresh_from_db()
    self.assertAlmostEqual(quote1.quote, Decimal('60.000000'))
    self.assertAlmostEqual(quote2.quote, Decimal('60.000000'))
    self.assertAlmostEqual(quote3.quote, Decimal('65.000000'))

    op1.refresh_from_db()
    op2.refresh_from_db()
    self.assertAlmostEqual(op1.shares, Decimal('24.000000'))
    self.assertAlmostEqual(op1.price, Decimal('60.000000'))
    self.assertAlmostEqual(op2.shares, Decimal('5.000000'))
    self.assertAlmostEqual(op2.price, Decimal('115.000000'))

    investment.refresh_from_db()
    self.assertAlmostEqual(investment.selling_price, Decimal('90.000000'))

    dividend.refresh_from_db()
    self.assertAlmostEqual(dividend.dps, Decimal('6.000000'))

    order1.refresh_from_db()
    order2.refresh_from_db()
    self.assertAlmostEqual(order1.shares, Decimal('24.000000'))
    self.assertAlmostEqual(order1.price, Decimal('60.000000'))
    self.assertAlmostEqual(order2.shares, Decimal('5.000000'))
    self.assertAlmostEqual(order2.price, Decimal('115.000000'))

    dps1.refresh_from_db()
    dps2.refresh_from_db()
    self.assertAlmostEqual(dps1.gross, Decimal('6.000000'))
    self.assertAlmostEqual(dps2.gross, Decimal('15.000000'))

    est1.refresh_from_db()
    est2.refresh_from_db()
    self.assertAlmostEqual(est1.estimation, Decimal('12.000000'))
    self.assertAlmostEqual(est2.estimation, Decimal('30.000000'))

    # Assert list_without_splits returns original values
    quotes_without = models.Quotes.list_without_splits()
    q1_w = next(item for item in quotes_without if item['id'] == quote1.id)
    self.assertAlmostEqual(q1_w['quote'], Decimal('120.000000'))

    ops_without = models.Investmentsoperations.list_without_splits()
    op1_w = next(item for item in ops_without if item['id'] == op1.id)
    self.assertAlmostEqual(op1_w['shares'], Decimal('12.000000'))
    self.assertAlmostEqual(op1_w['price'], Decimal('120.000000'))

    orders_without = models.Orders.list_without_splits()
    order1_w = next(item for item in orders_without if item['id'] == order1.id)
    self.assertAlmostEqual(order1_w['shares'], Decimal('12.000000'))
    self.assertAlmostEqual(order1_w['price'], Decimal('120.000000'))

    dps_without = models.Dps.list_without_splits()
    dps1_w = next(item for item in dps_without if item['id'] == dps1.id)
    self.assertAlmostEqual(dps1_w['gross'], Decimal('12.000000'))

    est_without = models.EstimationsDps.list_without_splits()
    est1_w = next(item for item in est_without if item['id'] == est1.id)
    self.assertAlmostEqual(est1_w['estimation'], Decimal('24.000000'))

    banks_without = models.Banks.list_without_splits()
    self.assertIsInstance(banks_without, list)
    self.assertGreater(len(banks_without), 0)
    self.assertIsInstance(banks_without[0], dict)

    # 4. Update the split to a 3-for-1 split (Before=1, After=3)
    split.after = 3
    split.save()

    # 5. Assert values are re-adjusted correctly for 3-for-1 split
    quote1.refresh_from_db()
    quote2.refresh_from_db()
    quote3.refresh_from_db()
    self.assertAlmostEqual(quote1.quote, Decimal('40.000000'))
    self.assertAlmostEqual(quote2.quote, Decimal('40.000000'))
    self.assertAlmostEqual(quote3.quote, Decimal('65.000000'))

    op1.refresh_from_db()
    op2.refresh_from_db()
    self.assertAlmostEqual(op1.shares, Decimal('36.000000'))
    self.assertAlmostEqual(op1.price, Decimal('40.000000'))
    self.assertAlmostEqual(op2.shares, Decimal('5.000000'))
    self.assertAlmostEqual(op2.price, Decimal('115.000000'))

    investment.refresh_from_db()
    self.assertAlmostEqual(investment.selling_price, Decimal('60.000000'))

    dividend.refresh_from_db()
    self.assertAlmostEqual(dividend.dps, Decimal('4.000000'))

    order1.refresh_from_db()
    order2.refresh_from_db()
    self.assertAlmostEqual(order1.shares, Decimal('36.000000'))
    self.assertAlmostEqual(order1.price, Decimal('40.000000'))
    self.assertAlmostEqual(order2.shares, Decimal('5.000000'))
    self.assertAlmostEqual(order2.price, Decimal('115.000000'))

    dps1.refresh_from_db()
    dps2.refresh_from_db()
    self.assertAlmostEqual(dps1.gross, Decimal('4.000000'))
    self.assertAlmostEqual(dps2.gross, Decimal('15.000000'))

    est1.refresh_from_db()
    est2.refresh_from_db()
    self.assertAlmostEqual(est1.estimation, Decimal('8.000000'))
    self.assertAlmostEqual(est2.estimation, Decimal('30.000000'))

    # 6. Delete the split
    split.delete()

    # 7. Assert all values are fully reverted back to original
    quote1.refresh_from_db()
    quote2.refresh_from_db()
    quote3.refresh_from_db()
    self.assertAlmostEqual(quote1.quote, Decimal('120.000000'))
    self.assertAlmostEqual(quote2.quote, Decimal('120.000000'))
    self.assertAlmostEqual(quote3.quote, Decimal('65.000000'))

    op1.refresh_from_db()
    op2.refresh_from_db()
    self.assertAlmostEqual(op1.shares, Decimal('12.000000'))
    self.assertAlmostEqual(op1.price, Decimal('120.000000'))
    self.assertAlmostEqual(op2.shares, Decimal('5.000000'))
    self.assertAlmostEqual(op2.price, Decimal('115.000000'))

    investment.refresh_from_db()
    self.assertAlmostEqual(investment.selling_price, Decimal('180.000000'))

    dividend.refresh_from_db()
    self.assertAlmostEqual(dividend.dps, Decimal('12.000000'))

    order1.refresh_from_db()
    order2.refresh_from_db()
    self.assertAlmostEqual(order1.shares, Decimal('12.000000'))
    self.assertAlmostEqual(order1.price, Decimal('120.000000'))
    self.assertAlmostEqual(order2.shares, Decimal('5.000000'))
    self.assertAlmostEqual(order2.price, Decimal('115.000000'))

    dps1.refresh_from_db()
    dps2.refresh_from_db()
    self.assertAlmostEqual(dps1.gross, Decimal('12.000000'))
    self.assertAlmostEqual(dps2.gross, Decimal('15.000000'))

    est1.refresh_from_db()
    est2.refresh_from_db()
    self.assertAlmostEqual(est1.estimation, Decimal('24.000000'))
    self.assertAlmostEqual(est2.estimation, Decimal('30.000000'))


def test_Splits_no_cross_product_interference(self):
    # Setup Product A (affected) and Product B (unaffected)
    product_a = models.Products.objects.get(pk=79328)
    product_b = models.Products.objects.get(pk=79329)
    
    now = timezone.now()
    dt_10_days_ago = now - timedelta(days=10)
    
    quote_a = models.Quotes.objects.create(products=product_a, datetime=dt_10_days_ago, quote=Decimal('120.000000'))
    quote_b = models.Quotes.objects.create(products=product_b, datetime=dt_10_days_ago, quote=Decimal('120.000000'))
    
    # Create split on Product A
    models.Splits.objects.create(
        datetime=now - timedelta(days=5),
        products=product_a,
        before=1,
        after=2
    )
    
    quote_a.refresh_from_db()
    quote_b.refresh_from_db()
    
    self.assertAlmostEqual(quote_a.quote, Decimal('60.000000'))
    self.assertAlmostEqual(quote_b.quote, Decimal('120.000000'))  # Product B quote must remain unchanged!


def test_Splits_multiple_splits(self):
    product = models.Products.objects.get(pk=79328)
    now = timezone.now()
    dt_10_days_ago = now - timedelta(days=10)
    
    quote = models.Quotes.objects.create(products=product, datetime=dt_10_days_ago, quote=Decimal('120.000000'))
    
    # Split 1: 5 days ago (2-for-1)
    split1 = models.Splits.objects.create(
        datetime=now - timedelta(days=5),
        products=product,
        before=1,
        after=2
    )
    quote.refresh_from_db()
    self.assertAlmostEqual(quote.quote, Decimal('60.000000'))
    
    # Split 2: 2 days ago (3-for-1)
    split2 = models.Splits.objects.create(
        datetime=now - timedelta(days=2),
        products=product,
        before=1,
        after=3
    )
    quote.refresh_from_db()
    self.assertAlmostEqual(quote.quote, Decimal('20.000000'))  # 120 / 2 / 3 = 20
    
    # Revert Split 2 (delete)
    split2.delete()
    quote.refresh_from_db()
    self.assertAlmostEqual(quote.quote, Decimal('60.000000'))  # Back to 120 / 2 = 60
    
    # Revert Split 1 (delete)
    split1.delete()
    quote.refresh_from_db()
    self.assertAlmostEqual(quote.quote, Decimal('120.000000'))  # Back to original 120


def test_Splits_api_endpoints(self):
    # Test API endpoint creation, list, update, delete
    product = models.Products.objects.get(pk=79328)
    product_url = f"http://testserver/api/products/{product.id}/"
    
    # Create via API POST
    payload = {
        "datetime": (timezone.now() - timedelta(days=5)).isoformat(),
        "products": product_url,
        "before": 1,
        "after": 2,
        "comment": "API split test"
    }
    
    response = tests_helpers.client_post(self, self.client_authorized_1, "/api/splits/", payload, status.HTTP_201_CREATED)
    split_id = response["id"]
    
    # Verify split object exists in DB
    self.assertTrue(models.Splits.objects.filter(pk=split_id).exists())
    
    # List endpoint
    list_response = tests_helpers.client_get(self, self.client_authorized_1, "/api/splits/", status.HTTP_200_OK)
    self.assertGreaterEqual(len(list_response), 1)
    
    # Filter list by product
    filtered_response = tests_helpers.client_get(self, self.client_authorized_1, f"/api/splits/?product={product_url}", status.HTTP_200_OK)
    self.assertGreaterEqual(len(filtered_response), 1)
    
    # Invalid POST validation error (before = -1)
    payload_invalid = payload.copy()
    payload_invalid["before"] = -1
    tests_helpers.client_post(self, self.client_authorized_1, "/api/splits/", payload_invalid, status.HTTP_400_BAD_REQUEST)
