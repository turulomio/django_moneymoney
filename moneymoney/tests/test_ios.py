from moneymoney import models
from moneymoney.reusing import tests_helpers
from rest_framework import status
from decimal import Decimal
from django.utils import timezone
from moneymoney import ios
from django.test import tag

def _setup_ios_api_test_data(self):
    """Helper to setup basic investment data and return an investment dictionary."""
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(quote=10), status.HTTP_201_CREATED)
    dict_inv1 = tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(name="Inv1"), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(investments=dict_inv1["url"], shares=1000, price=10), status.HTTP_201_CREATED)
    return dict_inv1

@tag("current")
def test_ios_internal_calculations(self):
    """
    Tests the inner calculations of the IOS Python class.
    31/12           1000 shares         9€          9000€
    yesterday       1000 shares        10€         10000€ 
    Balance 10€ is 20000€
    self.today      -1 shares          11€     
    Balance a 11€ = 22000€ - 11 = 21.989€
    Gains current year [0] = 999*11 - 999*9 = 1998
    Gains current year [1] = 1000*10 - 1000*9 = 1000
    Sum gains current year = 2998
    """
    dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(), status.HTTP_201_CREATED)
    
    #Bought last year
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(datetime=self.dtaware_last_year, quote=9), status.HTTP_201_CREATED)#Last year quote
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(datetime=self.dtaware_last_year, investments=dict_investment["url"], price=9, shares=1000), status.HTTP_201_CREATED)#Al actualizar ao asociada ejecuta otro plio

    #Bougth yesterday
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(datetime=self.dtaware_yesterday, quote=10), status.HTTP_201_CREATED)#Quote at buy moment
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(datetime=self.dtaware_yesterday, investments=dict_investment["url"], price=10, shares=1000), status.HTTP_201_CREATED)#Al actualizar ao asociada ejecuta otro plio

    ios_=ios.IOS.from_ids( timezone.now(),  'EUR',  [dict_investment["id"]],  ios.IOSModes.ios_totals_sumtotals, request=None)
    self.assertEqual(ios_.d_total_io_current(dict_investment["id"])["balance_user"], 20000)
    
    #Sell self.today
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(dict_investment["url"], shares=-1, price=11), status.HTTP_201_CREATED) #Removes one share
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(quote=11), status.HTTP_201_CREATED)#Sets quote to price to get currrent_year_gains
    ios_=ios.IOS.from_ids( timezone.now(),  'EUR',  [dict_investment["id"]],  ios.IOSModes.ios_totals_sumtotals, request=None) #Recaulculates IOS
    self.assertEqual(ios_.d_total_io_current(dict_investment["id"])["balance_user"], 21989)
    
    #Get zerorisk balance
    ios_.sum_total_io_current_zerorisk_user()
    
    # Current year gains addition
    ios_.io_current_addition_current_year_gains()
    self.assertEqual(ios_.sum_total_io_current()["current_year_gains_user"], 2998)
    
def test_ios_api_from_ids(self):
    dict_inv1 = _setup_ios_api_test_data(self)
    payload = {
        "datetime": timezone.now(),
        "classmethod_str": "from_ids",
        "investments": [dict_inv1["id"]],
        "mode": ios.IOSModes.ios_totals_sumtotals,
        "currency": "EUR"
    }
    res = tests_helpers.client_post(self, self.client_authorized_1, "/ios/", payload, status.HTTP_200_OK)
    entry = str(dict_inv1["id"])
    
    self.assertIn(entry, res["entries"])
    self.assertEqual(res[entry]["total_io_current"]["balance_user"], 10000)

def test_ios_api_from_ids_with_simulation(self):
    dict_inv1 = _setup_ios_api_test_data(self)
    payload = {
        "datetime": timezone.now(),
        "classmethod_str": "from_ids_with_simulation",
        "investments": [dict_inv1["id"]],
        "mode": ios.IOSModes.ios_totals_sumtotals,
        "currency": "EUR",
        "simulation": [{
            'id': -1,
            'operationstypes_id': 4,
            'investments_id': dict_inv1["id"],
            'shares': -100,
            'taxes': 0,
            'commission': 0,
            'price': 10,
            'datetime': timezone.now(),
            'comment': 'Simulation',
            'currency_conversion': 1,
        }]
    }
    res = tests_helpers.client_post(self, self.client_authorized_1, "/ios/", payload, status.HTTP_200_OK)
    entry = str(dict_inv1["id"])
    
    # Original balance = 10000. Simulated sold 100 shares @ 10 -> balance should be 9000
    self.assertEqual(res[entry]["total_io_current"]["balance_user"], 9000)

def test_ios_api_from_all(self):
    dict_inv1 = _setup_ios_api_test_data(self)
    payload = {
        "datetime": timezone.now(),
        "classmethod_str": "from_all",
        "investments": [],
        "mode": ios.IOSModes.ios_totals_sumtotals,
        "currency": "EUR"
    }
    res = tests_helpers.client_post(self, self.client_authorized_1, "/ios/", payload, status.HTTP_200_OK)
    entry = str(dict_inv1["id"])
    
    self.assertIn(entry, res["entries"])
    self.assertEqual(res[entry]["total_io_current"]["balance_user"], 10000)

def test_ios_api_from_all_merging_io_current(self):
    dict_inv1 = _setup_ios_api_test_data(self)
    dict_inv2 = tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(name="Inv2"), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(investments=dict_inv2["url"], shares=500, price=10), status.HTTP_201_CREATED)

    payload = {
        "datetime": timezone.now(),
        "classmethod_str": "from_all_merging_io_current",
        "investments": [],
        "mode": ios.IOSModes.ios_totals_sumtotals,
        "currency": "EUR"
    }
    res = tests_helpers.client_post(self, self.client_authorized_1, "/ios/", payload, status.HTTP_200_OK)
    
    # Assuming both use default product 79329
    merged_entry = "79329"
    self.assertIn(merged_entry, res["entries"])
    self.assertEqual(res[merged_entry]["total_io_current"]["balance_user"], 15000)

def test_ios_api_from_ids_merging_io_current(self):
    dict_inv1 = _setup_ios_api_test_data(self)
    dict_inv2 = tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(name="Inv2"), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(investments=dict_inv2["url"], shares=500, price=10), status.HTTP_201_CREATED)

    # Sell 100 shares from Inv1 to generate a historical operation
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(investments=dict_inv1["url"], shares=-100, price=15, datetime=timezone.now()), status.HTTP_201_CREATED)

    payload = {
        "datetime": timezone.now(),
        "classmethod_str": "from_ids_merging_io_current",
        "investments": [dict_inv1["id"], dict_inv2["id"]],
        "mode": ios.IOSModes.ios_totals_sumtotals,
        "currency": "EUR"
    }
    res = tests_helpers.client_post(self, self.client_authorized_1, "/ios/", payload, status.HTTP_200_OK)
    
    merged_entry = "79329"
    self.assertIn(merged_entry, res["entries"])
    
    # Original Inv1: 1000, sold 100 -> 900. Inv2: 500. Total = 1400 @ price 10 = 14000.
    self.assertEqual(res[merged_entry]["total_io_current"]["balance_user"], 14000)
    self.assertEqual(len(res[merged_entry]["io_historical"]), 1)
    self.assertEqual(res[merged_entry]["total_io_historical"]["gains_net_user"], 500)

def test_ios_api_from_ids_merging_io_current_with_simulation(self):
    dict_inv1 = _setup_ios_api_test_data(self)
    dict_inv2 = tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(name="Inv2"), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(investments=dict_inv2["url"], shares=500, price=10), status.HTTP_201_CREATED)

    payload = {
        "datetime": timezone.now(),
        "classmethod_str": "from_ids_merging_io_current_with_simulation",
        "investments": [dict_inv1["id"], dict_inv2["id"]],
        "mode": ios.IOSModes.ios_totals_sumtotals,
        "currency": "EUR",
        "simulation": [{
            'id': -1,
            'operationstypes_id': 4,
            'investments_id': 79329,  # Target the product ID directly since operations are merged
            'shares': -500,
            'taxes': 0,
            'commission': 0,
            'price': 10,
            'datetime': timezone.now(),
            'comment': 'Simulation',
            'currency_conversion': 1,
        }]
    }
    res = tests_helpers.client_post(self, self.client_authorized_1, "/ios/", payload, status.HTTP_200_OK)
    
    merged_entry = "79329"
    self.assertIn(merged_entry, res["entries"])
    # Original combined balance = 15000. Simulated sold 500 shares @ 10 -> balance should be 10000
    self.assertEqual(res[merged_entry]["total_io_current"]["balance_user"], 10000)
