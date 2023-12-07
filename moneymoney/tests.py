from datetime import date
from decimal import Decimal
from django.contrib.auth.models import User
from django.test import tag
from django.utils import timezone
from json import loads
from moneymoney import models, ios
from moneymoney.reusing import tests_helpers
from pydicts import lod
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from django.contrib.auth.models import Group

tag

class CtTestCase(APITestCase):
    fixtures=["all.json"] #Para cargar datos por defecto

    @classmethod
    def setUpClass(cls):
        """
            Only instantiated once
        """
        super().setUpClass()
        
        # User to test api
        cls.user_authorized_1 = User(
            email='testing@testing.com',
            first_name='Testing',
            last_name='Testing',
            username='testing',
        )
        cls.user_authorized_1.set_password('testing123')
        cls.user_authorized_1.save()
        
        # User to confront security
        cls.user_authorized_2 = User(
            email='other@other.com',
            first_name='Other',
            last_name='Other',
            username='other',
        )
        cls.user_authorized_2.set_password('other123')
        cls.user_authorized_2.save()
        
                
        # User to test api
        cls.user_catalog_manager = User(
            email='catalog_manager@catalog_manager.com',
            first_name='Catalog',
            last_name='Manager',
            username='catalog_manager',
        )
        cls.user_catalog_manager.set_password('catalog_manager123')
        cls.user_catalog_manager.save()
        cls.user_catalog_manager.groups.add(Group.objects.get(name='CatalogManager'))

        client = APIClient()
        response = client.post('/login/', {'username': cls.user_authorized_1.username, 'password': 'testing123',},format='json')
        result = loads(response.content)
        cls.token_user_authorized_1 = result
        
        response = client.post('/login/', {'username': cls.user_authorized_2.username, 'password': 'other123',},format='json')
        result = loads(response.content)
        cls.token_user_authorized_2 = result

        response = client.post('/login/', {'username': cls.user_catalog_manager.username, 'password': 'catalog_manager123',},format='json')
        result = loads(response.content)
        cls.token_user_catalog_manager=result
        
        cls.client_authorized_1=APIClient()
        cls.client_authorized_1.credentials(HTTP_AUTHORIZATION='Token ' + cls.token_user_authorized_1)
        cls.client_authorized_1.user=cls.user_authorized_1

        cls.client_authorized_2=APIClient()
        cls.client_authorized_2.credentials(HTTP_AUTHORIZATION='Token ' + cls.token_user_authorized_2)
        cls.client_authorized_2.user=cls.user_authorized_2
        
        cls.client_anonymous=APIClient()
        cls.client_anonymous.user=None
        
        cls.client_catalog_manager=APIClient()
        cls.client_catalog_manager.credentials(HTTP_AUTHORIZATION='Token ' + cls.token_user_catalog_manager)
        cls.client_catalog_manager.user=cls.user_catalog_manager
        
        cls.assertTrue(cls, models.Operationstypes.objects.all().count()>0,  "There aren't operationstypes")
        cls.assertTrue(cls, models.Products.objects.all().count()>0, "There aren't products")
        cls.assertTrue(cls, models.Concepts.objects.all().count()>0, "There aren't concepts")
        
        cls.bank=models.Banks.objects.create(name="Fixture bank", active=True)
        cls.account=models.Accounts.objects.create(name="Fixture account", active=True, banks=cls.bank, currency="EUR", decimals=2)
        cls.product=models.Products.objects.get(id=79228)


    def test_profile(self):
        """
            Test created users has its profile automatically generated
        """
        
        a=User()
        a.username="me"
        a.save()
        self.assertNotEqual(a, None)
        
        
        self.assertNotEqual(self.user_authorized_1.profile, None)
        self.assertNotEqual(self.user_authorized_2.profile, None)
        self.assertNotEqual(self.user_catalog_manager.profile, None)
        
        p=models.Products.objects.get(pk=79329)
        self.user_authorized_1.profile.favorites.add(p)
        self.user_authorized_1.profile.save()
        self.assertEqual(self.user_authorized_1.profile.favorites.count(), 1)        

#            
#    def test_investments_operations(self):
#        ##Currencies must be the same
#        account=factory.AccountsFactory.create(currency="EUR")
#        product=factory.ProductsFactory.create(currency="EUR")
#        investment=factory.InvestmentsFactory.create(accounts=account, products=product)
#        for i in range(3):
#            factory.QuotesFactory.create(products=product)
#        mf_io=factory_helpers.MyFactory(factory.InvestmentsoperationsFactory, "Colaborative", "/api/investmentsoperations/")
#        io_payload=mf_io.factory.build(investments=investment, operationstypes=models.Operationstypes.objects.get(pk=eOperationType.SharesPurchase))
#        r=self.client_authorized_1.post("/api/investmentsoperations/", mf_io.serialize(io_payload, remove_id_url=True))
#    
#    def test_estimations_dps(self):     
#        """
#            Checks estimationsdps loginc
#        """
#        print()
#        print("test_estimations_dps")
#        mf=factory_helpers.MyFactory(factory.EstimationsDpsFactory, "Colaborative", "/api/estimationsdps/")
#        
#        #Trying to insert the same year and product twice. I alter date_estimation
#        payload=mf.post_payload(self.user_authorized_1)
#        self.assertEqual(mf.model_count(), 0)
#        self.client_authorized_1.post(mf.url, payload)
#        self.assertEqual(mf.model_count(), 1)
#        payload["estimation"]="12.3456"
#        r=self.client_authorized_1.post(mf.url, payload)
#        self.assertEqual(mf.model_count(), 1)
#        self.assertEqual(loads(r.content)["estimation"], 12.3456)
    
#    def test_accounts(self):
#        """
#            Checks accounts logic
#        """
#        mf=self.factories_manager.find(factory.AccountsFactory)
#        mfao=self.factories_manager.find(factory.AccountsoperationsionsFactory)
#        mfao
#        #Checks there is one account
#        self.assertEqual(mf.model_count(), 1)
#        
#        #Create a new account
#        r=self.client_authorized_1.post(mf.url, mf.post_payload(self.client_authorized_1))
#        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
#        
#        #Create a new account operation
#        ao=mfao.factory.build(accounts__currency="EUR", amount=-1492,  comment="CAN YOU FIND ME?", concepts=models.Concepts.objects.get(pk=7), accounts=models.Accounts.objects.get(pk=4))
#        
#        
#        r=self.client_authorized_1.post(mfao.url, mfao.serialize(ao, remove_id_url=True))
#        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
#        ao =loads(r.content)
#        
#        #Find account operation with search
#        r=self.client_authorized_1.get(mfao.url+"?search=FIND ME")
#        self.assertEqual(r.status_code, status.HTTP_200_OK)
#                
#        #List accounts with balance
#        r=self.client_authorized_1.get(mf.url+"withbalance/")
#        self.assertEqual(r.status_code, status.HTTP_200_OK)
#        accounts=loads(r.content)
#        self.assertEqual(accounts[0]["balance_account"], -1492)
#        
#        account_balance=cursor_one_row("select * from account_balance(%s,%s,%s)", (4, timezone.now(), 'EUR'))
#        self.assertEqual(account_balance["balance_account_currency"], -1492)
#        accounts_balance=cursor_one_row("select * from accounts_balance(%s,%s)", (timezone.now(), 'EUR'))
#        self.assertEqual(accounts_balance["accounts_balance"], -1492)
#        total_balance=models.Assets.pl_total_balance(timezone.now(), "EUR")
#        self.assertEqual(total_balance["total_user"], -1492)


#    def test_banks(self):
#        print()
#        print("test_banks")
#        tests_helpers.common_tests_Private(self,  '/api/banks/', models.Banks.post_payload(),  self.client_authorized_1, self.client_authorized_2, self.client_anonymous)

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
        
    def test_Investments(self):
        dict_account=tests_helpers.client_get(self, self.client_authorized_1, "/api/accounts/4/", status.HTTP_200_OK)
        dict_product=tests_helpers.client_get(self, self.client_authorized_1, "/api/products/79228/", status.HTTP_200_OK)
        payload=models.Investments.post_payload(products=dict_product["url"], accounts=dict_account["url"])
        tests_helpers.common_tests_Collaborative(self, "/api/investments/", payload, self.client_authorized_1, self.client_authorized_2, self.client_anonymous)
        

    def test_EstimationsDps(self):
        # common _tests
        tests_helpers.common_tests_Collaborative(self, "/api/estimationsdps/", models.EstimationsDps.post_payload(), self.client_authorized_1, self.client_authorized_2, self.client_anonymous)
        
        # two estimations same product
        tests_helpers.client_post(self, self.client_authorized_1, "/api/estimationsdps/",  models.EstimationsDps.post_payload(estimation=1), status.HTTP_201_CREATED)
        dict_estimationdps_1=tests_helpers.client_post(self, self.client_authorized_1, "/api/estimationsdps/",  models.EstimationsDps.post_payload(estimation=2), status.HTTP_201_CREATED)
        dict_estimationsdps=tests_helpers.client_get(self, self.client_authorized_1, f"/api/estimationsdps/?product={dict_estimationdps_1['products']}", status.HTTP_200_OK)
        self.assertTrue(len(dict_estimationsdps),  1)
        self.assertTrue(dict_estimationsdps[0]["estimation"], 2)

    def test_IOS_with_client(self):
        #IOS.from_ids
        tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(), status.HTTP_201_CREATED)
        dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(), status.HTTP_201_CREATED)
        
        dict_io_1=tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(investments=dict_investment["url"]), status.HTTP_201_CREATED)#Al actualizar ao asociada ejecuta otro plio
        self.assertTrue(models.Accountsoperations.objects.filter(comment=f"10000,{dict_io_1['id']}").exists())#Comprueba que existe ao
        
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
        dict_io_2=tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(dict_investment["url"], shares=-1, price=20), status.HTTP_201_CREATED) #Removes one share
        self.assertTrue(models.Accountsoperations.objects.filter(comment=f"10000,{dict_io_2['id']}").exists())#Comprueba que existe ao
        
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
        dict_io_2=tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(investments=dict_investment_2["url"]), status.HTTP_201_CREATED)#Al actualizar ao asociada ejecuta otro plio
       
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
        

    def test_IOS(self):
        tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(), status.HTTP_201_CREATED)
        dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(), status.HTTP_201_CREATED)
        dict_io_1=tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(dict_investment["url"]), status.HTTP_201_CREATED)#Al actualizar ao asociada ejecuta otro plio
        self.assertTrue(models.Accountsoperations.objects.filter(comment=f"10000,{dict_io_1['id']}").exists())#Comprueba que existe ao
        ios_=ios.IOS.from_ids( timezone.now(),  'EUR',  [dict_investment["id"]],  ios.IOSModes.ios_totals_sumtotals)
        self.assertEqual(ios_.d_total_io_current(dict_investment["id"])["balance_user"], 10000)
        dict_io_2=tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(dict_investment["url"], shares=-1, price=20), status.HTTP_201_CREATED) #Removes one share
        self.assertTrue(models.Accountsoperations.objects.filter(comment=f"10000,{dict_io_2['id']}").exists())#Comprueba que existe ao
        ios_=ios.IOS.from_ids( timezone.now(),  'EUR',  [dict_investment["id"]],  ios.IOSModes.ios_totals_sumtotals) #Recaulculates IOS
        self.assertEqual(ios_.d_total_io_current(dict_investment["id"])["balance_user"], 9990)
        
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
#        ios_.print_d(1)

        
        
        
        #IOS.from_merging_io_current
        ## Adding a new investment and new investmentsoperations with same product
        dict_investment_2=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(), status.HTTP_201_CREATED)
        dict_io_2=tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(dict_investment_2["url"]), status.HTTP_201_CREATED)#Al actualizar ao asociada ejecuta otro plio
        ios_merged=ios.IOS.from_qs_merging_io_current(timezone.now(), 'EUR', models.Investments.objects.all(), ios.IOSModes.ios_totals_sumtotals)
        self.assertEqual(ios_merged.entries(),  ['79329'])
        
        #Get zerorisk balance
        ios_.sum_total_io_current_zerorisk_user()
        
        
    def test_ConceptsReport(self):
        #test empty
        tests_helpers.client_get(self, self.client_authorized_1, f"/reports/concepts/?year={date.today().year}&month={date.today().month}", status.HTTP_200_OK)
        #test value
        tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/",  models.Accountsoperations.post_payload(), status.HTTP_201_CREATED)
        r=tests_helpers.client_get(self, self.client_authorized_1, f"/reports/concepts/?year={date.today().year}&month={date.today().month}", status.HTTP_200_OK)
        self.assertEqual(len(r["positive"]), 1)
        
    @tag("current")
    def test_Concepts_DataTransfer(self):
        # New personal concept
        dict_concept_from=tests_helpers.client_post(self, self.client_authorized_1, "/api/concepts/", models.Concepts.post_payload(name="Concept from"), status.HTTP_201_CREATED)
        
        # We create an accounts operations, creditcardsoperations and dividends with this new concept
        dict_ao=tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/",  models.Accountsoperations.post_payload(concepts=dict_concept_from["url"]), status.HTTP_201_CREATED)
        dict_cc=tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcards/",  models.Creditcards.post_payload(), status.HTTP_201_CREATED)
        dict_cco=tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcardsoperations/",  models.Creditcardsoperations.post_payload(creditcards=dict_cc["url"], concepts=dict_concept_from["url"]), status.HTTP_201_CREATED)
        dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",  models.Investments.post_payload(accounts=dict_ao["accounts"]), status.HTTP_201_CREATED)
        dict_dividend=tests_helpers.client_post(self, self.client_authorized_1, "/api/dividends/",  models.Dividends.post_payload(investments=dict_investment["url"], concepts=dict_concept_from["url"]), status.HTTP_201_CREATED)
        
        # We create a new personal concepto to transfer to
        dict_concept_to=tests_helpers.client_post(self, self.client_authorized_1, "/api/concepts/", models.Concepts.post_payload(name="Concept to"), status.HTTP_201_CREATED)
        
        # We transfer data from concept_from to concept_to
        tests_helpers.client_post(self, self.client_authorized_1, f"{dict_concept_from['url']}data_transfer/", {"to": dict_concept_to["url"]}, status.HTTP_200_OK)
        
        # We check that concepts have been changed
        dict_ao_after=tests_helpers.client_get(self, self.client_authorized_1, dict_ao["url"]  , status.HTTP_200_OK)
        self.assertEqual(dict_ao_after["concepts"], dict_concept_to["url"])
        dict_cco_after=tests_helpers.client_get(self, self.client_authorized_1, dict_cco["url"]  , status.HTTP_200_OK)
        self.assertEqual(dict_cco_after["concepts"], dict_concept_to["url"])
        dict_dividend_after=tests_helpers.client_get(self, self.client_authorized_1, dict_dividend["url"]  , status.HTTP_200_OK)
        self.assertEqual(dict_dividend_after["concepts"], dict_concept_to["url"])
        
        # Bad request
        tests_helpers.client_post(self, self.client_authorized_1, f"{dict_concept_from['url']}data_transfer/", {}, status.HTTP_400_BAD_REQUEST)

    @tag("current")
    def test_Concepts_HistoricalData(self):
        # We create an accounts operations, creditcardsoperations and dividends with this new concept        
        dict_cc=tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcards/",  models.Creditcards.post_payload(), status.HTTP_201_CREATED)
        for i in range(5):
            tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/",  models.Accountsoperations.post_payload(datetime=timezone.now().replace(year= 2010+i)), status.HTTP_201_CREATED)
            tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcardsoperations/",  models.Creditcardsoperations.post_payload(creditcards=dict_cc["url"]), status.HTTP_201_CREATED)
        # We transfer data from concept_from to concept_to
        dict_historical_report_1=tests_helpers.client_get(self, self.client_authorized_1, "http://testserver/api/concepts/1/historical_report/", status.HTTP_200_OK)
        self.assertEqual(dict_historical_report_1["total"], 10000)
        # Empty request
        dict_historical_report_2=tests_helpers.client_get(self, self.client_authorized_1, "http://testserver/api/concepts/2/historical_report/", status.HTTP_200_OK)
        self.assertEqual(dict_historical_report_2["total"], 0)
        
        
    def test_Creditcards_Payments(self):        
        # We create a credit card and a creditcard operation and make a payment
        dict_cc=tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcards/",  models.Creditcards.post_payload(), status.HTTP_201_CREATED)
        dict_cco_1=tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcardsoperations/",  models.Creditcardsoperations.post_payload(creditcards=dict_cc["url"]), status.HTTP_201_CREATED)
        dict_cco_2=tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcardsoperations/",  models.Creditcardsoperations.post_payload(creditcards=dict_cc["url"]), status.HTTP_201_CREATED)
        dict_cco_3=tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcardsoperations/",  models.Creditcardsoperations.post_payload(creditcards=dict_cc["url"]), status.HTTP_201_CREATED)
        tests_helpers.client_post(self, self.client_authorized_1, f"{dict_cc['url']}pay/",  {"dt_payment":timezone.now(), "cco":[dict_cco_1["id"], ]}, status.HTTP_200_OK)
        tests_helpers.client_post(self, self.client_authorized_1, f"{dict_cc['url']}pay/",  {"dt_payment":timezone.now(), "cco":[dict_cco_2["id"], dict_cco_3["id"] ]}, status.HTTP_200_OK)
        
        #We list payments
        dict_payments=tests_helpers.client_get(self, self.client_authorized_1, f"{dict_cc['url']}payments/", status.HTTP_200_OK)
        self.assertTrue(dict_payments[0]["count"], 1)
        self.assertTrue(dict_payments[1]["count"], 2)
        

    def test_CatalogManager(self):
        r=tests_helpers.client_get(self, self.client_authorized_1,  "/catalog_manager/", status.HTTP_200_OK)
        self.assertFalse(r)
        r=tests_helpers.client_get(self, self.client_catalog_manager,  "/catalog_manager/", status.HTTP_200_OK)
        self.assertTrue(r)
        r=tests_helpers.client_get(self, self.client_anonymous,  "/catalog_manager/", status.HTTP_200_OK)
        self.assertFalse(r)


    def test_Concepts(self):
        
#        tests_helpers.common_tests_Private
        # Action used empty
        r=tests_helpers.client_get(self, self.client_authorized_1,  "/api/concepts/used/", status.HTTP_200_OK)
        self.assertEqual(lod.lod_sum(r, "used"), 0)
        
