from moneymoney import models
from moneymoney.reusing import tests_helpers
from rest_framework import status
from django.utils import timezone
from moneymoney import ios

def test_IOS(self):
    """
        31/12           1000 shares         9€          9000€
        yesterday    1000 shares        10€         10000€ 
        
        Balance 10€ is 20000€
        
        self.today           -1 shares               11€     
        
        Balance a 11€ =22000€-11=21.989€
        
        Gains current year [0] = 999*11 - 999*9=1998
        Gains current year [1] = 1000*10 - 1000*9=1000
        
        Sum gains current year= 2998
        
        
    
    """
    dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(), status.HTTP_201_CREATED)
    
    #Bought last year
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(datetime=self.dtaware_last_year, quote=9), status.HTTP_201_CREATED)#Last year quote
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(datetime=self.dtaware_last_year, investments=dict_investment["url"], price=9), status.HTTP_201_CREATED)#Al actualizar ao asociada ejecuta otro plio

    #Bouth yesterday
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(datetime=self.dtaware_yesterday, quote=10), status.HTTP_201_CREATED)#Quote at buy moment
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(datetime=self.dtaware_yesterday, investments=dict_investment["url"], price=10), status.HTTP_201_CREATED)#Al actualizar ao asociada ejecuta otro plio

    ios_=ios.IOS.from_ids( timezone.now(),  'EUR',  [dict_investment["id"]],  ios.IOSModes.ios_totals_sumtotals)
    self.assertEqual(ios_.d_total_io_current(dict_investment["id"])["balance_user"], 20000)
    
    #Sell self.today
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(dict_investment["url"], shares=-1, price=11), status.HTTP_201_CREATED) #Removes one share
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(quote=11), status.HTTP_201_CREATED)#Sets quote to price to get currrent_year_gains
    ios_=ios.IOS.from_ids( timezone.now(),  'EUR',  [dict_investment["id"]],  ios.IOSModes.ios_totals_sumtotals) #Recaulculates IOS
    self.assertEqual(ios_.d_total_io_current(dict_investment["id"])["balance_user"], 21989)
    
    #Get zerorisk balance
    ios_.sum_total_io_current_zerorisk_user()
    
    # Current year gains addition
    ios_.io_current_addition_current_year_gains()
    self.assertEqual(ios_.sum_total_io_current()["current_year_gains_user"], 2998)
    
    #IOS.simulation
    simulation=[
        {
            'id': -1, 
            'operationstypes_id': 4, 
            'investments_id': dict_investment["id"], 
            'shares': -1, 
            'taxes': 0, 
            'commission': 0, 
            'price': 10, 
            'datetime': timezone.now(), 
            'comment': 'Simulation', 
            'currency_conversion': 1, 
        }, 
    ]
    ios_=ios.IOS.from_ids( timezone.now(),  'EUR',  [dict_investment["id"]],  ios.IOSModes.ios_totals_sumtotals, simulation) #Makes simulation

    #IOS.from_merging_io_current
    ## Adding a new investment and new investmentsoperations with same product
    dict_investment_2=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(dict_investment_2["url"]), status.HTTP_201_CREATED)#Al actualizar ao asociada ejecuta otro plio
    ios_merged=ios.IOS.from_qs_merging_io_current(timezone.now(), 'EUR', models.Investments.objects.all(), ios.IOSModes.ios_totals_sumtotals)
    self.assertEqual(ios_merged.entries(),  ['79329'])
    


def test_IOS_with_client(self):
    #IOS.from_ids
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(), status.HTTP_201_CREATED)
    dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(), status.HTTP_201_CREATED)
    
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(investments=dict_investment["url"]), status.HTTP_201_CREATED)#Al actualizar ao asociada ejecuta otro plio
    
    #Get IOS_ids of first
    dict_ios_ids_pp={
        "datetime":timezone.now(), 
        "classmethod_str":"from_ids", 
        "investments": [dict_investment["id"], ], 
        "mode":ios.IOSModes.ios_totals_sumtotals, 
        "currency": "EUR", 
        "simulation":[], 
    }
    dict_ios_ids_1=tests_helpers.client_post(self, self.client_authorized_1, "/ios/", dict_ios_ids_pp, status.HTTP_200_OK)
    first_entry=dict_ios_ids_1["entries"][0]
    self.assertEqual(dict_ios_ids_1[first_entry]["total_io_current"]["balance_user"], 10000)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(dict_investment["url"], shares=-1, price=20), status.HTTP_201_CREATED) #Removes one share
    
    dict_ios_ids_2=tests_helpers.client_post(self, self.client_authorized_1, "/ios/", dict_ios_ids_pp, status.HTTP_200_OK)
    self.assertEqual(dict_ios_ids_2[first_entry]["total_io_current"]["balance_user"], 9990)
    
    #IOS.simulation
    simulation=[
        {
            'id': -1, 
            'operationstypes_id': 4, 
            'investments_id': dict_investment["id"], 
            'shares': -1, 
            'taxes': 0, 
            'commission': 0, 
            'price': 10, 
            'datetime': timezone.now(), 
            'comment': 'Simulation', 
            'currency_conversion': 1, 
        }, 
    ]
    dict_ios_ids_pp["simulation"]=simulation
    dict_ios_ids_simulation=tests_helpers.client_post(self, self.client_authorized_1, "/ios/", dict_ios_ids_pp, status.HTTP_200_OK)
    self.assertEqual(dict_ios_ids_simulation[first_entry]["total_io_current"]["balance_user"], 9980)
    
    #IOS.from_merging_io_current
    ## Adding a new investment and new investmentsoperations with same product
    dict_investment_2=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(investments=dict_investment_2["url"]), status.HTTP_201_CREATED)#Al actualizar ao asociada ejecuta otro plio
    
    dict_ios_ids_merging_pp={
        "datetime":timezone.now(), 
        "classmethod_str":"from_ids_merging_io_current", 
        "investments": [dict_investment["id"], dict_investment_2["id"] ], 
        "mode":ios.IOSModes.ios_totals_sumtotals, 
        "currency": "EUR", 
        "simulation":[], 
    }
    dict_ios_ids_merging=tests_helpers.client_post(self, self.client_authorized_1, "/ios/", dict_ios_ids_merging_pp, status.HTTP_200_OK)
    self.assertEqual(dict_ios_ids_merging["79329"]["total_io_current"]["balance_user"], 19990)
    
    #IOS.from_merging_io_current simulation
    simulation=[
        {
            'id': -1, 
            'operationstypes_id': 4, 
            'investments_id': 79329,  
            'shares': -1, 
            'taxes': 0, 
            'commission': 0, 
            'price': 10, 
            'datetime': timezone.now(), 
            'comment': 'Simulation', 
            'currency_conversion': 1, 
        }, 
    ]
    dict_ios_ids_merging_pp["simulation"]=simulation
    dict_ios_ids_simulation=tests_helpers.client_post(self, self.client_authorized_1, "/ios/", dict_ios_ids_merging_pp, status.HTTP_200_OK)
    self.assertEqual(dict_ios_ids_simulation["79329"]["total_io_current"]["balance_user"], 19980)

