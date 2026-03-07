from rest_framework import status
from moneymoney import models
from moneymoney.reusing import tests_helpers
from django.utils import timezone
from datetime import timedelta

def test_Investments(self):
    dict_account=tests_helpers.client_get(self, self.client_authorized_1, "/api/accounts/4/", status.HTTP_200_OK)
    dict_product=tests_helpers.client_get(self, self.client_authorized_1, "/api/products/79228/", status.HTTP_200_OK)
    payload=models.Investments.post_payload(products=dict_product["url"], accounts=dict_account["url"])
    tests_helpers.common_tests_Collaborative(self, "/api/investments/", payload, self.client_authorized_1, self.client_authorized_2, self.client_anonymous)

# Helper to ensure necessary quotes exist for tests
def _ensure_quotes_exist_for_deletable_tests(self):
    # Product 79329 is used by default in Investments.post_payload
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",
                              models.Quotes.post_payload(products="/api/products/79329/", quote=10),
                              status.HTTP_201_CREATED)
    # Products 81718 and 81719 are used for Investmentstransfers
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",
                              models.Quotes.post_payload(products="/api/products/81718/", quote=10),
                              status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",
                              models.Quotes.post_payload(products="/api/products/81719/", quote=10),
                              status.HTTP_201_CREATED)

# Helper to create an investment
def _create_investment_for_deletable_test(self, name_suffix=""):
    _ensure_quotes_exist_for_deletable_tests(self) # Ensure quotes are there
    payload = models.Investments.post_payload(
        name=f"Test Investment {name_suffix}",
        products="/api/products/79329/", # Default product
        accounts="/api/accounts/4/" # Default account
    )
    return tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", payload, status.HTTP_201_CREATED)

# Helper to get is_deletable status
def _get_investment_deletable_status(self, investment_url):
    investment_data = tests_helpers.client_get(self, self.client_authorized_1, investment_url, status.HTTP_200_OK)
    return investment_data.get("is_deletable")

def test_investment_is_deletable_initially(self):
    dict_investment = _create_investment_for_deletable_test(self, "Initially Deletable")
    self.assertTrue(_get_investment_deletable_status(self, dict_investment["url"]))

def test_investment_is_deletable_with_investmentsoperations(self):
    dict_investment = _create_investment_for_deletable_test(self, "With IO")
    self.assertTrue(_get_investment_deletable_status(self, dict_investment["url"]))

    io_payload = models.Investmentsoperations.post_payload(investments=dict_investment["url"])
    dict_io = tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", io_payload, status.HTTP_201_CREATED)
    self.assertFalse(_get_investment_deletable_status(self, dict_investment["url"]))

    tests_helpers.client_delete(self, self.client_authorized_1, dict_io["url"], {}, status.HTTP_204_NO_CONTENT)
    self.assertTrue(_get_investment_deletable_status(self, dict_investment["url"]))

def test_investment_is_deletable_with_dividends(self):
    dict_investment = _create_investment_for_deletable_test(self, "With Dividends")
    self.assertTrue(_get_investment_deletable_status(self, dict_investment["url"]))

    dividend_payload = models.Dividends.post_payload(investments=dict_investment["url"])
    dict_dividend = tests_helpers.client_post(self, self.client_authorized_1, "/api/dividends/", dividend_payload, status.HTTP_201_CREATED)
    self.assertFalse(_get_investment_deletable_status(self, dict_investment["url"]))

    tests_helpers.client_delete(self, self.client_authorized_1, dict_dividend["url"], {}, status.HTTP_204_NO_CONTENT)
    self.assertTrue(_get_investment_deletable_status(self, dict_investment["url"]))

def test_investment_is_deletable_with_orders(self):
    dict_investment = _create_investment_for_deletable_test(self, "With Orders")
    self.assertTrue(_get_investment_deletable_status(self, dict_investment["url"]))

    order_payload = models.Orders.post_payload(investments=dict_investment["url"])
    dict_order = tests_helpers.client_post(self, self.client_authorized_1, "/api/orders/", order_payload, status.HTTP_201_CREATED)
    self.assertFalse(_get_investment_deletable_status(self, dict_investment["url"]))

    tests_helpers.client_delete(self, self.client_authorized_1, dict_order["url"], {}, status.HTTP_204_NO_CONTENT)
    self.assertTrue(_get_investment_deletable_status(self, dict_investment["url"]))

def test_investment_is_deletable_with_investmentstransfers_origin(self):
    dict_investment_origin = _create_investment_for_deletable_test(self, "IT Origin")
    dict_investment_destiny = _create_investment_for_deletable_test(self, "IT Destiny") # Need another investment for destiny
    self.assertTrue(_get_investment_deletable_status(self, dict_investment_origin["url"]))

    it_payload = models.Investmentstransfers.post_payload(
        investments_origin=dict_investment_origin["url"],
        investments_destiny=dict_investment_destiny["url"],
        shares_origin=-100,
        shares_destiny=100
    )
    dict_it = tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentstransfers/", it_payload, status.HTTP_201_CREATED)
    self.assertFalse(_get_investment_deletable_status(self, dict_investment_origin["url"]))

    tests_helpers.client_delete(self, self.client_authorized_1, dict_it["url"], {}, status.HTTP_204_NO_CONTENT)
    self.assertTrue(_get_investment_deletable_status(self, dict_investment_origin["url"]))

def test_investment_is_deletable_with_investmentstransfers_destiny(self):
    dict_investment_origin = _create_investment_for_deletable_test(self, "IT Origin 2")
    dict_investment_destiny = _create_investment_for_deletable_test(self, "IT Destiny 2")
    self.assertTrue(_get_investment_deletable_status(self, dict_investment_destiny["url"]))

    it_payload = models.Investmentstransfers.post_payload(
        investments_origin=dict_investment_origin["url"],
        investments_destiny=dict_investment_destiny["url"],
        shares_origin=-100,
        shares_destiny=100
    )
    dict_it = tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentstransfers/", it_payload, status.HTTP_201_CREATED)
    self.assertFalse(_get_investment_deletable_status(self, dict_investment_destiny["url"]))

    tests_helpers.client_delete(self, self.client_authorized_1, dict_it["url"], {}, status.HTTP_204_NO_CONTENT)
    self.assertTrue(_get_investment_deletable_status(self, dict_investment_destiny["url"]))

def test_investment_is_deletable_with_strategies_generic(self):
    dict_investment = _create_investment_for_deletable_test(self, "With SG")
    self.assertTrue(_get_investment_deletable_status(self, dict_investment["url"]))

    sg_payload = models.StrategiesGeneric.post_payload(
        strategy=models.Strategies.post_payload(name="SG Test", type=models.StrategiesTypes.Generic),
        investments=[dict_investment["url"]]
    )
    dict_sg = tests_helpers.client_post(self, self.client_authorized_1, "/api/strategies_generic/", sg_payload, status.HTTP_201_CREATED)
    self.assertFalse(_get_investment_deletable_status(self, dict_investment["url"]))

    tests_helpers.client_delete(self, self.client_authorized_1, dict_sg["url"], {}, status.HTTP_204_NO_CONTENT)
    self.assertTrue(_get_investment_deletable_status(self, dict_investment["url"]))

def test_investment_is_deletable_with_strategies_products_range(self):
    dict_investment = _create_investment_for_deletable_test(self, "With SPR")
    self.assertTrue(_get_investment_deletable_status(self, dict_investment["url"]))

    spr_payload = models.StrategiesProductsRange.post_payload(
        strategy=models.Strategies.post_payload(name="SPR Test", type=models.StrategiesTypes.Ranges),
        product="/api/products/79329/", # Use the same product as the investment
        investments=[dict_investment["url"]]
    )
    dict_spr = tests_helpers.client_post(self, self.client_authorized_1, "/api/strategies_productsrange/", spr_payload, status.HTTP_201_CREATED)
    self.assertFalse(_get_investment_deletable_status(self, dict_investment["url"]))

    tests_helpers.client_delete(self, self.client_authorized_1, dict_spr["url"], {}, status.HTTP_204_NO_CONTENT)
    self.assertTrue(_get_investment_deletable_status(self, dict_investment["url"]))

def test_investment_is_deletable_with_fast_operations_coverage(self):
    dict_investment = _create_investment_for_deletable_test(self, "With FOC")
    self.assertTrue(_get_investment_deletable_status(self, dict_investment["url"]))

    foc_payload = {
        "datetime": timezone.now(),
        "investments": dict_investment["url"],
        "amount": 100.00,
        "comment": "Test FOC"
    }
    dict_foc = tests_helpers.client_post(self, self.client_authorized_1, "/api/fastoperationscoverage/", foc_payload, status.HTTP_201_CREATED)
    self.assertFalse(_get_investment_deletable_status(self, dict_investment["url"]))

    tests_helpers.client_delete(self, self.client_authorized_1, dict_foc["url"], {}, status.HTTP_204_NO_CONTENT)
    self.assertTrue(_get_investment_deletable_status(self, dict_investment["url"]))
