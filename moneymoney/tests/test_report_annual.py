from rest_framework import status
from moneymoney import models
from moneymoney.reusing import tests_helpers
from pydicts import casts

def test_ReportAnnual(self):
    tests_helpers.client_get(self, self.client_authorized_1, f"/reports/annual/{self.today_year}/", status.HTTP_200_OK)
    
def test_ReportAnnualRevaluation(self):
    
    dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(investments=dict_investment["url"]), status.HTTP_201_CREATED)
    
    #Without lastyear quote
    tests_helpers.client_get(self, self.client_authorized_1, "/reports/annual/revaluation/", status.HTTP_200_OK)
    
    #Only Zero
    tests_helpers.client_get(self, self.client_authorized_1, "/reports/annual/revaluation/?only_zero=true", status.HTTP_200_OK)

def test_ReportAnnualIncome(self):        
    # Adds a dividend to control it only appears in dividends not in dividends+incomes        
    dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(), status.HTTP_201_CREATED)        
    dict_dividend=tests_helpers.client_post(self, self.client_authorized_1, "/api/dividends/",  models.Dividends.post_payload(datetime=casts.dtaware_month_end(self.static_year, self.static_month, self.timezone_madrid), investments=dict_investment["url"]), status.HTTP_201_CREATED)
    lod_=tests_helpers.client_get(self, self.client_authorized_1, f"/reports/annual/income/{self.static_year}/", status.HTTP_200_OK)
    self.assertEqual(lod_[0]["total"],  dict_dividend["net"])

def test_ReportAnnualIncomeDetails(self):       

    dt_static=datetime=casts.dtaware_month_end(self.static_year, self.static_month, self.timezone_madrid)
    # Adds a dividend to control it only appears in dividends not in dividends+incomes        
    dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(), status.HTTP_201_CREATED)        
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(quote=10), status.HTTP_201_CREATED)  
    tests_helpers.client_post(self, self.client_authorized_1, "/api/dividends/",  models.Dividends.post_payload(datetime=dt_static, investments=dict_investment["url"]), status.HTTP_201_CREATED)        
    dod_=tests_helpers.client_get(self, self.client_authorized_1, f"/reports/annual/income/details/{self.static_year}/{self.static_month}/", status.HTTP_200_OK)
    self.assertEqual(len(dod_["dividends"]), 1 )
    self.assertEqual(len(dod_["incomes"]), 0 )



    """
    Test case to create an account in USD, an account operation,
    a debit credit card, and attempt to create a credit card operation for it.
    The last step is expected to fail due to validation.
    """
    # 1. Create an account in USD currency
    usd_account_payload = models.Accounts.post_payload(name="USD Account", currency="USD", decimals=2)
    dict_usd_account = tests_helpers.client_post(self, self.client_authorized_1, "/api/accounts/", usd_account_payload, status.HTTP_201_CREATED)
    usd_account_url = dict_usd_account["url"]

    # 2. Create an Accountsoperations for this account
    ao_payload = models.Accountsoperations.post_payload(datetime=dt_static, accounts=usd_account_url, amount=100.00, comment="Initial deposit USD")
    tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/", ao_payload, status.HTTP_201_CREATED)

    # 3. Create a credit card with deferred=False (a debit card)
    debit_cc_payload = models.Creditcards.post_payload( name="Debit Card USD", accounts=usd_account_url, deferred=False)
    dict_debit_cc = tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcards/", debit_cc_payload, status.HTTP_201_CREATED)
    debit_cc_url = dict_debit_cc["url"]

    # 4. Attempt to create a Creditcardsoperations for the debit card. This should fail.
    cco_payload = models.Creditcardsoperations.post_payload(datetime=dt_static, creditcards=debit_cc_url, amount=50.00, comment="Debit card expense USD")
    tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcardsoperations/", cco_payload, status.HTTP_400_BAD_REQUEST)

    dod_=tests_helpers.client_get(self, self.client_authorized_1, f"/reports/annual/income/details/{self.static_year}/{self.static_month}/", status.HTTP_200_OK)
    from pydicts import dod
    dod.dod_print(dod_)


def test_ReportAnnualGainsByProductstypes(self):
    tests_helpers.client_get(self, self.client_authorized_1, f"/reports/annual/gainsbyproductstypes/{self.today_year}/", status.HTTP_200_OK)
    #lod.lod_print(dict_)
    #TODO All kind of values
