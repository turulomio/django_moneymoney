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
    # Adds a dividend to control it only appears in dividends not in dividends+incomes        
    dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(), status.HTTP_201_CREATED)        
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(quote=10), status.HTTP_201_CREATED)  
    tests_helpers.client_post(self, self.client_authorized_1, "/api/dividends/",  models.Dividends.post_payload(datetime=casts.dtaware_month_end(self.static_year, self.static_month, self.timezone_madrid), investments=dict_investment["url"]), status.HTTP_201_CREATED)        
    dod_=tests_helpers.client_get(self, self.client_authorized_1, f"/reports/annual/income/details/{self.static_year}/{self.static_month}/", status.HTTP_200_OK)
    self.assertEqual(len(dod_["dividends"]), 1 )
    self.assertEqual(len(dod_["incomes"]), 0 )

def test_ReportAnnualGainsByProductstypes(self):
    tests_helpers.client_get(self, self.client_authorized_1, f"/reports/annual/gainsbyproductstypes/{self.today_year}/", status.HTTP_200_OK)
    #lod.lod_print(dict_)
    #TODO All kind of values
