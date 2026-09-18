from io import StringIO
from contextlib import redirect_stdout
from unittest.mock import patch, MagicMock
from decimal import Decimal
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone
from datetime import datetime, timezone as dt_timezone
from moneymoney import models


def test_command_products_update_invalid_ticker(self):
    out = StringIO()
    err = StringIO()
    with redirect_stdout(out):
        with self.assertRaises(CommandError):
            call_command('products_update', 'invalid_provider', stderr=err)


def test_command_products_update_selection_and_dryrun(self):
    # Setup test product 1: associated to investment, has ticker_yahoo
    p1 = models.Products.objects.get(id=79329)
    p1.ticker_yahoo = "SAN.MC"
    p1.save()

    inv = models.Investments.objects.create(
        name="Investment P1",
        active=True,
        accounts_id=4,
        products=p1,
        selling_price=0,
        daily_adjustment=False,
        balance_percentage=100
    )

    # Setup test product 2: in favorites, has ticker_yahoo
    p2 = models.Products.objects.get(id=79328)
    p2.ticker_yahoo = "BBVA.MC"
    p2.save()
    self.user_authorized_1.profile.favorites.add(p2)

    # Setup test product 3: has investment, but ticker_yahoo is empty/None
    p3 = models.Products.objects.get(id=79327)
    p3.ticker_yahoo = None
    p3.save()
    models.Investments.objects.create(
        name="Investment P3",
        active=True,
        accounts_id=4,
        products=p3,
        selling_price=0,
        daily_adjustment=False,
        balance_percentage=100
    )

    # Setup test product 4: has ticker_yahoo, but NO investment and NOT in favorites
    p4 = models.Products.objects.get(id=79326)
    p4.ticker_yahoo = "TEF.MC"
    p4.save()
    self.user_authorized_1.profile.favorites.remove(p4)

    mock_dt = datetime(2026, 9, 18, 10, 0, 0, tzinfo=dt_timezone.utc)

    def mock_fetch_yahoo(product, ticker_value):
        if ticker_value == "SAN.MC":
            return {'datetime': mock_dt, 'quote': Decimal("12.500000")}, None
        elif ticker_value == "BBVA.MC":
            return {'datetime': mock_dt, 'quote': Decimal("9.250000")}, None
        return None, "Not found"

    out = StringIO()
    with patch('moneymoney.management.commands.products_update.Command.fetch_yahoo', side_effect=mock_fetch_yahoo):
        with redirect_stdout(out):
            call_command('products_update', 'yahoo', delay=0)

    output = out.getvalue()
    # P1 and P2 should be selected (total 2 selected)
    self.assertIn("Seleccionados: 2", output)
    self.assertIn("Buscados: 2", output)
    self.assertIn("Tiempo:", output)
    self.assertIn("insert", output)
    self.assertIn("12.5", output)
    self.assertIn("9.25", output)

    # Since --write was not passed (dry-run), quotes should NOT be saved
    self.assertFalse(models.Quotes.objects.filter(products=p1, datetime=mock_dt).exists())
    self.assertFalse(models.Quotes.objects.filter(products=p2, datetime=mock_dt).exists())


def test_command_products_update_write_and_update_detection(self):
    p1 = models.Products.objects.get(id=79329)
    p1.ticker_yahoo = "SAN.MC"
    p1.save()

    inv = models.Investments.objects.create(
        name="Investment P1",
        active=True,
        accounts_id=4,
        products=p1,
        selling_price=0,
        daily_adjustment=False,
        balance_percentage=100
    )

    mock_dt = datetime(2026, 9, 18, 10, 0, 0, tzinfo=dt_timezone.utc)

    # 1. First run with --write: should be an "insert"
    out1 = StringIO()
    with patch('moneymoney.management.commands.products_update.Command.fetch_yahoo', return_value=({'datetime': mock_dt, 'quote': Decimal("12.500000")}, None)):
        with redirect_stdout(out1):
            call_command('products_update', 'yahoo', '--write', delay=0)

    output1 = out1.getvalue()
    self.assertIn("insert", output1)
    self.assertIn("Seleccionados: 1", output1)
    self.assertIn("Buscados: 1", output1)

    # Quote must exist in DB now
    quote_in_db = models.Quotes.objects.filter(products=p1, datetime=mock_dt).first()
    self.assertIsNotNone(quote_in_db)
    self.assertEqual(quote_in_db.quote, Decimal("12.500000"))

    # 2. Second run with updated price: should detect "update"
    out2 = StringIO()
    with patch('moneymoney.management.commands.products_update.Command.fetch_yahoo', return_value=({'datetime': mock_dt, 'quote': Decimal("13.000000")}, None)):
        with redirect_stdout(out2):
            call_command('products_update', 'yahoo', '--write', delay=0)

    output2 = out2.getvalue()
    self.assertIn("update", output2)

    # DB quote should have been updated
    quote_updated = models.Quotes.objects.filter(products=p1, datetime=mock_dt).first()
    self.assertEqual(quote_updated.quote, Decimal("13.000000"))


def test_command_products_update_not_found_with_reason(self):
    p1 = models.Products.objects.get(id=79329)
    p1.ticker_yahoo = "FAIL.MC"
    p1.save()

    inv = models.Investments.objects.create(
        name="Investment Fail",
        active=True,
        accounts_id=4,
        products=p1,
        selling_price=0,
        daily_adjustment=False,
        balance_percentage=100
    )

    out = StringIO()
    with patch('moneymoney.management.commands.products_update.Command.fetch_yahoo', return_value=(None, "HTTP 404")):
        with redirect_stdout(out):
            call_command('products_update', 'yahoo', delay=0)

    output = out.getvalue()
    self.assertIn("No encontrados:", output)
    self.assertIn("FAIL.MC", output)
    self.assertIn("HTTP 404", output)
    self.assertIn("Seleccionados: 1", output)
    self.assertIn("Buscados: 0", output)


def test_command_products_update_fetchers_mocked(self):
    p = models.Products.objects.get(id=79329)
    p.ticker_yahoo = "SAN.MC"
    p.ticker_google = "BME:SAN"
    p.ticker_morningstar = "F000001W2L"
    p.ticker_quefondos = "N4390"
    p.ticker_investingcom = "SAN#BME"
    p.save()

    inv = models.Investments.objects.create(
        name="Inv for fetchers",
        active=True,
        accounts_id=4,
        products=p,
        selling_price=0,
        daily_adjustment=False,
        balance_percentage=100
    )

    # Test Yahoo with 429 retry then success
    resp_429 = MagicMock()
    resp_429.status_code = 429

    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.json.return_value = {
        'chart': {
            'result': [{
                'meta': {
                    'regularMarketPrice': 12.90,
                    'regularMarketTime': 1789716914
                }
            }]
        }
    }

    with patch('time.sleep') as mock_sleep:
        with patch('requests.Session.get', side_effect=[resp_429, resp_200]):
            out = StringIO()
            with redirect_stdout(out):
                call_command('products_update', 'yahoo', delay=0)
            self.assertIn("12.9", out.getvalue())
            self.assertIn("Buscados: 1", out.getvalue())

    # Test Google
    with patch('requests.Session.get') as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '<span jsname="Pdsbrc"><span>€15.60</span></span>'
        mock_get.return_value = mock_resp

        out = StringIO()
        with redirect_stdout(out):
            call_command('products_update', 'google', delay=0)
        self.assertIn("15.6", out.getvalue())
        self.assertIn("Buscados: 1", out.getvalue())

    # Test Morningstar
    with patch('requests.Session.get') as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '<td class="text">23,45</td>'
        mock_get.return_value = mock_resp

        out = StringIO()
        with redirect_stdout(out):
            call_command('products_update', 'morningstar', delay=0)
        self.assertIn("23.45", out.getvalue())
        self.assertIn("Buscados: 1", out.getvalue())

    # Test Quefondos
    with patch('requests.Session.get') as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '<span class="floatright">18,72</span>'
        mock_get.return_value = mock_resp

        out = StringIO()
        with redirect_stdout(out):
            call_command('products_update', 'quefondos', delay=0)
        self.assertIn("18.72", out.getvalue())
        self.assertIn("Buscados: 1", out.getvalue())

    # Test Investing.com
    with patch('requests.Session.get') as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '<span class="last-price">14,20</span>'
        mock_get.return_value = mock_resp

        out = StringIO()
        with redirect_stdout(out):
            call_command('products_update', 'investingcom', delay=0)
        self.assertIn("14.2", out.getvalue())
        self.assertIn("Buscados: 1", out.getvalue())
