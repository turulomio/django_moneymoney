from datetime import date, datetime, timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import tag
from django.utils import timezone
from json import loads
from logging import getLogger, ERROR
from moneymoney import models, ios, investing_com, functions, types
from moneymoney.reusing import tests_helpers
from pydicts import lod, casts, dod
from request_casting.request_casting import id_from_url
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from django.contrib.auth.models import Group
from asgiref.sync import async_to_sync, sync_to_async

tag,  dod

js_image_b64="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII="

timezone_madrid="Europe/Madrid"
today=date.today()
today_year=today.year
today_month=today.month        

yesterday=date.today()-timedelta(days=1)
yesterday_year=yesterday.year
yesterday_month=yesterday.month

dtaware_last_year=casts.dtaware_year_end(today_year-1, timezone_madrid)
dtaware_now=casts.dtaware_now()
dtaware_yesterday=dtaware_now-timedelta(days=1)

# Defines report moment for static reports to avoid problems with asserts
static_year=2024
static_month=1

# Concepts url
hurl_concepts_oa=f"http://testserver/api/concepts/{types.eConcept.OpenAccount}/"
hurl_concepts_fo=f"http://testserver/api/concepts/{types.eConcept.FastInvestmentOperations}/"


class Functions(APITestCase):
    @functions.suppress_stdout
    def test_print_object(self):
        b=models.Banks()
        b.name="Newbank"
        b.save()
        functions.print_object(b)
        
    
    def test_string_oneline_object(self):
        b=models.Banks()
        b.name="Newbank"
        b.save()
        assert len(functions.string_oneline_object(b))>0
        
        

class Models(APITestCase):
    fixtures=["all.json"] #Para cargar datos por defecto
    
    def test_Accounts(self):
        a=models.Accounts()
        a.name="New account"
        a.banks_id=3
        a.active=True
        a.decimals=2
        a.save()
        str(a)

    def test_Operationstypes(self):
        o=models.Operationstypes.objects.get(pk=1)
        str(o)    
    
    def test_Stockmarkets(self):
        o=models.Stockmarkets.objects.get(pk=1)
        str(o)
        o.dtaware_closes(today)
        o.dtaware_closes_futures(today)
        o.dtaware_today_closes()
        o.dtaware_today_closes_futures()
        o.dtaware_starts(today)
        o.dtaware_today_starts()
        o.estimated_datetime_for_daily_quote()
        o.estimated_datetime_for_intraday_quote()
        o.estimated_datetime_for_intraday_quote(delay=True)
        
    def test_Accountsoperations(self):
        o=models.Accountsoperations()
        o.accounts_id=4
        o.amount=1000
        o.datetime=timezone.now()
        o.concepts_id=1
        o.save()
        str(o)
        repr(o)

    def test_Banks(self):
        o=models.Banks.objects.get(pk=3)
        str(o)
    
    def test_Products(self):    
        # qs_distinct_with_investments empty
        qs=models.Products.qs_distinct_with_investments()
        self.assertEqual(qs.count(), 0)
        
        # qs_distinct_with_investments not empty
        inv=models.Investments()
        inv.name="Investment name"
        inv.active=True
        inv.accounts_id=4
        inv.products_id=79329
        inv.selling_price=0
        inv.daily_adjustment=False
        inv.balance_percentage=100
        inv.save()
        qs=models.Products.qs_distinct_with_investments()
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs[0].id, 79329)

    def test_Quotes(self):
        for i in range(4):
            models.Quotes.objects.create(products_id=79328+i, datetime=casts.dtaware_now(),quote=i)
            models.Quotes.objects.create(products_id=79328+i, datetime=casts.dtaware_now(),quote=i*10)

        with self.assertNumQueries(1):
            quotes=models.Quotes.qs_last_quotes()
            self.assertEqual(quotes.count(), 4)

class API(APITestCase):
    fixtures=["all.json"] #Para cargar datos por defecto

    @classmethod
    def setUpClass(cls):
        """
            Only instantiated once
        """
        super().setUpClass()


        # Store original logging level and set it higher to suppress warnings
        logger = getLogger('django.request')
        logger.setLevel(ERROR) # This will suppress INFO and WARNING

        
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
        
        cls.now=timezone.now()


    def test_Profile(self):
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

    def test_ReportAnnual(self):
        tests_helpers.client_get(self, self.client_authorized_1, f"/reports/annual/{today_year}/", status.HTTP_200_OK)
        
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
        dict_dividend=tests_helpers.client_post(self, self.client_authorized_1, "/api/dividends/",  models.Dividends.post_payload(datetime=casts.dtaware_month_end(static_year, static_month, timezone_madrid), investments=dict_investment["url"]), status.HTTP_201_CREATED)
        lod_=tests_helpers.client_get(self, self.client_authorized_1, f"/reports/annual/income/{static_year}/", status.HTTP_200_OK)
        self.assertEqual(lod_[0]["total"],  dict_dividend["net"])

    def test_ReportAnnualIncomeDetails(self):       
        # Adds a dividend to control it only appears in dividends not in dividends+incomes        
        dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(), status.HTTP_201_CREATED)        
        tests_helpers.client_post(self, self.client_authorized_1, "/api/dividends/",  models.Dividends.post_payload(datetime=casts.dtaware_month_end(static_year, static_month, timezone_madrid), investments=dict_investment["url"]), status.HTTP_201_CREATED)        
        dod_=tests_helpers.client_get(self, self.client_authorized_1, f"/reports/annual/income/details/{static_year}/{static_month}/", status.HTTP_200_OK)
        self.assertEqual(len(dod_["dividends"]), 1 )
        self.assertEqual(len(dod_["incomes"]), 0 )

    def test_ReportAnnualGainsByProductstypes(self):
        tests_helpers.client_get(self, self.client_authorized_1, f"/reports/annual/gainsbyproductstypes/{today_year}/", status.HTTP_200_OK)
        #lod.lod_print(dict_)
        #TODO All kind of values

    def test_Quotes(self):
        for i in range(2):
            tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(quote=i+1), status.HTTP_201_CREATED)

        with self.assertNumQueries(2):
            quotes=tests_helpers.client_get(self, self.client_authorized_1, f"/api/quotes/?last=true", status.HTTP_200_OK)       

    @tag("current")
    def test_Quotes_get_quotes(self):
        quotes=[]
        for i in range(1000):
            quotes.append(tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(quote=i+1), status.HTTP_201_CREATED))
        
        #Creates a dict_tupled to query massive quotes
        lod_=[]
        fivedays=casts.dtaware_now()-timedelta(days=5)
        for quote in quotes:
            lod_.append({"products_id": 79329,  "datetime": casts.str2dtaware(quote["datetime"])})
        lod_.append({"products_id":79329,  "datetime": fivedays})#Doesn't exist
        
#        lod.lod_print(lod_)
       
        # Gets quotes and checks them with quotes list
        response=sync_to_async(models.Quotes.get_quotes(lod_))

        # Wait for the async call to complete
        r= sync_to_sync(response)
        print(r)
        for i in range(5):
            quotes_datetime=casts.str2dtaware(quotes[i]["datetime"])
            self.assertEqual(quotes[i]["quote"], r[79329][quotes_datetime]["quote"]   )
            
        self.assertEqual(r[79329][fivedays]["quote"], None)

#        # Products basic_results empty
#        p=models.Products.objects.get(pk=79330)
#        assert p.basic_results()["lastyear"]==None
#
#
#        # Products without quotes
#        now=timezone.now()
#        lod_=[{"products_id": 79330,  "datetime": now}, ]
#        r=models.Quotes.get_quotes(lod_)
#        assert r[79330][now]["quote"]==None

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

    def test_Accountsoperations_associated_fields(self):
        #Add a investment operation to check associated_io
        tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(), status.HTTP_201_CREATED)
        dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(), status.HTTP_201_CREATED)        
        dict_io=tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(investments=dict_investment["url"]), status.HTTP_201_CREATED)#Al actualizar ao asociada ejecuta otro plio
        dict_associated_ao_with_associated_io=tests_helpers.client_get(self, self.client_authorized_1, dict_io["associated_ao"],  status.HTTP_200_OK)
        self.assertEqual(dict_associated_ao_with_associated_io["associated_io"], dict_io["url"])
        
        #Add a dividend to check associated_dividend
        dict_dividend=tests_helpers.client_post(self, self.client_authorized_1, "/api/dividends/",  models.Dividends.post_payload(investments=dict_investment["url"]), status.HTTP_201_CREATED)
        dict_associated_ao_with_associated_dividend=tests_helpers.client_get(self, self.client_authorized_1, dict_dividend["accountsoperations"],  status.HTTP_200_OK)
        self.assertEqual(dict_associated_ao_with_associated_dividend["associated_dividend"], dict_dividend["url"])

    def test_Accountstransfers(self):        
        tests_helpers.client_get(self, self.client_authorized_1, "/api/accounts/4/", status.HTTP_200_OK)
        dict_destiny=tests_helpers.client_post(self, self.client_authorized_1, "/api/accounts/",  models.Accounts.post_payload(), status.HTTP_201_CREATED)

        # Create transfer
        dict_transfer=tests_helpers.client_post(self, self.client_authorized_1, "/api/accountstransfers/",  models.Accountstransfers.post_payload(destiny=dict_destiny["url"]), status.HTTP_201_CREATED)
        
        tests_helpers.client_get(self, self.client_authorized_1, "/api/accountsoperations/", status.HTTP_200_OK)
        self.assertEqual(models.Accountsoperations.objects.filter(associated_transfer__id=dict_transfer["id"]).count(), 3)
        self.assertEqual(list(models.Accountsoperations.objects.filter(associated_transfer__id=dict_transfer["id"]).values_list("id",  flat=True)), [id_from_url(dict_transfer["ao_origin"]), id_from_url(dict_transfer["ao_destiny"]), id_from_url(dict_transfer["ao_commission"])])
        self.assertEqual(models.Accountsoperations.objects.get(pk=id_from_url(dict_transfer["ao_origin"])).amount, -1000)
        self.assertEqual(models.Accountsoperations.objects.get(pk=id_from_url(dict_transfer["ao_destiny"])).amount, 1000)
        self.assertEqual(models.Accountsoperations.objects.get(pk=id_from_url(dict_transfer["ao_commission"])).amount, -10)
        
        # Update transfer
        dict_transfer_updated=tests_helpers.client_put(self, self.client_authorized_1, dict_transfer["url"],  models.Accountstransfers.post_payload(datetime=timezone.now(), amount=999, commission=9), status.HTTP_200_OK)
        self.assertEqual(list(models.Accountsoperations.objects.filter(associated_transfer__id=dict_transfer["id"]).values_list("id",  flat=True)), [id_from_url(dict_transfer_updated["ao_origin"]), id_from_url(dict_transfer_updated["ao_destiny"]), id_from_url(dict_transfer_updated["ao_commission"])])   
        self.assertEqual(models.Accountsoperations.objects.filter(pk__in=[id_from_url(dict_transfer["ao_origin"]), id_from_url(dict_transfer["ao_destiny"]), id_from_url(dict_transfer["ao_commission"])]).count(), 0)
        self.assertEqual(models.Accountsoperations.objects.get(pk=id_from_url(dict_transfer_updated["ao_origin"])).amount, -999)
        self.assertEqual(models.Accountsoperations.objects.get(pk=id_from_url(dict_transfer_updated["ao_destiny"])).amount, 999)
        self.assertEqual(models.Accountsoperations.objects.get(pk=id_from_url(dict_transfer_updated["ao_commission"])).amount, -9)
    
        # Delete transfer
        self.client_authorized_1.delete(dict_transfer["url"])
        with self.assertRaises(models.Accountstransfers.DoesNotExist):
            models.Accountstransfers.objects.get(id=dict_transfer["id"])
        self.assertEqual(models.Accountsoperations.objects.filter(associated_transfer__id=dict_transfer["id"]).count(), 0)
        
        #Check minvaluevalidator works with full_clean in save()
        t=models.Accountstransfers()
        t.datetime=timezone.now()
        t.origin_id=4
        t.destiny_id=dict_destiny["id"]
        t.amount=-1000
        t.commission=-3
        with self.assertRaises(ValidationError):
            t.save()

    def test_Investments(self):
        dict_account=tests_helpers.client_get(self, self.client_authorized_1, "/api/accounts/4/", status.HTTP_200_OK)
        dict_product=tests_helpers.client_get(self, self.client_authorized_1, "/api/products/79228/", status.HTTP_200_OK)
        payload=models.Investments.post_payload(products=dict_product["url"], accounts=dict_account["url"])
        tests_helpers.common_tests_Collaborative(self, "/api/investments/", payload, self.client_authorized_1, self.client_authorized_2, self.client_anonymous)

    def test_InvestmentsClasses(self):
        #Empty
        dict_classes=tests_helpers.client_get(self, self.client_authorized_1, "/investments/classes/", status.HTTP_200_OK)
        self.assertEqual(lod.lod_sum(dict_classes["by_producttype"], "balance"),  0)
        
        # With one investmentoperation and one account operation        
        tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/",  models.Accountsoperations.post_payload(amount=10000), status.HTTP_201_CREATED)
        dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(), status.HTTP_201_CREATED)
        tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(products=dict_investment["products"]), status.HTTP_201_CREATED)
        tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(investments=dict_investment["url"]), status.HTTP_201_CREATED)#Al actualizar ao asociada ejecuta otro plio
        dict_classes=tests_helpers.client_get(self, self.client_authorized_1, "/investments/classes/", status.HTTP_200_OK)
        self.assertEqual(lod.lod_sum(dict_classes["by_producttype"], "balance"), 10000)

    def test_InvestmentsChangeSellingPrice(self):
        dict_investment_1=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",  models.Investments.post_payload(), status.HTTP_201_CREATED)
        dict_investment_2=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",  models.Investments.post_payload(), status.HTTP_201_CREATED)
        
        dict_changed=tests_helpers.client_post(self, self.client_authorized_1, "/investments/changesellingprice/",  {
            "selling_price":1, 
            "selling_expiration":date.today(), 
            "investments":[dict_investment_1["url"], dict_investment_2["url"]]
        }, status.HTTP_200_OK)
        assert dict_changed[0]["selling_price"]==1
        dict_changed=tests_helpers.client_post(self, self.client_authorized_1, "/investments/changesellingprice/",  {
            "selling_price":0, 
            "selling_expiration": None, 
            "investments":[dict_investment_1["url"], dict_investment_2["url"]]
        }, status.HTTP_200_OK)
        assert dict_changed[0]["selling_price"]==0
    
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

    def test_Investmentsoperations(self):        
        # Create an investment operation
        tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(), status.HTTP_201_CREATED)
        dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(), status.HTTP_201_CREATED)
        dict_io=tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(dict_investment["url"]), status.HTTP_201_CREATED)#Al actualizar ao asociada ejecuta otro plio
       
        # Checks exists associated_ao
        self.assertEqual(models.Accountsoperations.objects.get(pk=id_from_url(dict_io["associated_ao"])).investmentsoperations.id, dict_io["id"])#Comprueba que existe ao
        
        # Update io        
        dict_io_updated=tests_helpers.client_put(self, self.client_authorized_1, dict_io["url"], models.Investmentsoperations.post_payload(dict_investment["url"], shares=10000), status.HTTP_200_OK)
        
        # Checks dict_io associated_ao doesn't exist and dict_io_updated associated_ao doesn
        with self.assertRaises(models.Accountsoperations.DoesNotExist):
            models.Accountsoperations.objects.get(pk=id_from_url(dict_io["associated_ao"]))
        models.Accountsoperations.objects.get(pk=id_from_url(dict_io_updated["associated_ao"]))
        
        # Delete io
        self.client_authorized_1.delete(dict_io_updated["url"])

        # Checks associated_ao doesn't exist and io doesn't exist
        with self.assertRaises(models.Accountsoperations.DoesNotExist):
            models.Accountsoperations.objects.get(pk=id_from_url(dict_io_updated["associated_ao"]))
            
        with self.assertRaises(models.Investmentsoperations.DoesNotExist):
            models.Investmentsoperations.objects.get(pk=dict_io_updated["id"])

    def test_IOS(self):
        """
            31/12           1000 shares         9€          9000€
            yesterday    1000 shares        10€         10000€ 
            
            Balance 10€ is 20000€
            
            today           -1 shares               11€     
            
            Balance a 11€ =22000€-11=21.989€
            
            Gains current year [0] = 999*11 - 999*9=1998
            Gains current year [1] = 1000*10 - 1000*9=1000
            
            Sum gains current year= 2998
            
            
        
        """
        dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(), status.HTTP_201_CREATED)
        
        #Bought last year
        tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(datetime=dtaware_last_year, quote=9), status.HTTP_201_CREATED)#Last year quote
        tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(datetime=dtaware_last_year, investments=dict_investment["url"], price=9), status.HTTP_201_CREATED)#Al actualizar ao asociada ejecuta otro plio

        #Bouth yesterday
        tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(datetime=dtaware_yesterday, quote=10), status.HTTP_201_CREATED)#Quote at buy moment
        tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(datetime=dtaware_yesterday, investments=dict_investment["url"], price=10), status.HTTP_201_CREATED)#Al actualizar ao asociada ejecuta otro plio

        ios_=ios.IOS.from_ids( timezone.now(),  'EUR',  [dict_investment["id"]],  ios.IOSModes.ios_totals_sumtotals)
        self.assertEqual(ios_.d_total_io_current(dict_investment["id"])["balance_user"], 20000)
        
        #Sell today
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
        

        
    def test_ConceptsReport(self):
        #test empty
        tests_helpers.client_get(self, self.client_authorized_1, f"/reports/concepts/?year={date.today().year}&month={date.today().month}", status.HTTP_200_OK)
        #test value
        tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/",  models.Accountsoperations.post_payload(), status.HTTP_201_CREATED)
        r=tests_helpers.client_get(self, self.client_authorized_1, f"/reports/concepts/?year={date.today().year}&month={date.today().month}", status.HTTP_200_OK)
        self.assertEqual(len(r["positive"]), 1)
        
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


    def test_Concepts_HistoricalData(self):
        # We create an accounts operations, creditcardsoperations and dividends with this new concept        
        dict_cc=tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcards/",  models.Creditcards.post_payload(), status.HTTP_201_CREATED)
        for i in range(5):
            tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/",  models.Accountsoperations.post_payload(datetime=self.now.replace(year= 2010+i)), status.HTTP_201_CREATED)
            tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcardsoperations/",  models.Creditcardsoperations.post_payload(creditcards=dict_cc["url"]), status.HTTP_201_CREATED)
        # We transfer data from concept_from to concept_to
        dict_historical_report_1=tests_helpers.client_get(self, self.client_authorized_1, "http://testserver/api/concepts/1/historical_report/", status.HTTP_200_OK)
        self.assertEqual(dict_historical_report_1["total"], 10000)
        # Empty request
        dict_historical_report_2=tests_helpers.client_get(self, self.client_authorized_1, "http://testserver/api/concepts/2/historical_report/", status.HTTP_200_OK)
        self.assertEqual(dict_historical_report_2["total"], 0)

    def test_Concepts_HistoricalDataDetailed(self):
        # We create an accounts operations, creditcardsoperations and dividends with this new concept        
        dict_cc=tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcards/",  models.Creditcards.post_payload(), status.HTTP_201_CREATED)
        for i in range(2):
            tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/",  models.Accountsoperations.post_payload(), status.HTTP_201_CREATED)
            tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcardsoperations/",  models.Creditcardsoperations.post_payload(creditcards=dict_cc["url"]), status.HTTP_201_CREATED)
        # We transfer data from concept_from to concept_to
        dict_historical_report_1=tests_helpers.client_get(self, self.client_authorized_1, f"http://testserver/api/concepts/1/historical_report_detail/?year={self.now.year}&month={self.now.month}", status.HTTP_200_OK)
        self.assertEqual(len(dict_historical_report_1["ao"]), 2)
        self.assertEqual(len(dict_historical_report_1["cco"]), 2)
        # Empty request
        dict_historical_report_empty=tests_helpers.client_get(self, self.client_authorized_1, f"http://testserver/api/concepts/2/historical_report_detail/?year={self.now.year}&month={self.now.month}", status.HTTP_200_OK)
        self.assertEqual(len(dict_historical_report_empty["ao"]), 0)
        self.assertEqual(len(dict_historical_report_empty["cco"]), 0)
        # Bad request
        tests_helpers.client_get(self, self.client_authorized_1, "http://testserver/api/concepts/1/historical_report_detail/", status.HTTP_400_BAD_REQUEST)
    
    def test_Alerts(self):
        # Create an expired order
        dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",  models.Investments.post_payload(), status.HTTP_201_CREATED)
        tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(products=dict_investment["products"]), status.HTTP_201_CREATED)
        tests_helpers.client_post(self, self.client_authorized_1,  "/api/orders/", models.Orders.post_payload(investments=dict_investment["url"], expiration=today-timedelta(days=1)), status.HTTP_201_CREATED)
        
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

        # Search alerts
        lod_alerts=tests_helpers.client_get(self, self.client_authorized_1, "/alerts/",  status.HTTP_200_OK)
        self.assertEqual(len(lod_alerts["orders_expired"]), 1 )
        self.assertEqual(len(lod_alerts["accounts_inactive_with_balance"]), 1 )
        self.assertEqual(len(lod_alerts["investments_inactive_with_balance"]), 1 )
        self.assertEqual(len(lod_alerts["banks_inactive_with_balance"]), 1 )


    
    def test_Creditcards(self):
        # common _tests y deja creada una activa
        tests_helpers.common_tests_Collaborative(self, "/api/creditcards/", models.Creditcards.post_payload(), self.client_authorized_1, self.client_authorized_2, self.client_anonymous)
        
        # create cc one active and one inactive
        dict_cc=tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcards/",  models.Creditcards.post_payload(active=False), status.HTTP_201_CREATED)
        
        # List all
        lod_all=tests_helpers.client_get(self, self.client_authorized_1, "http://testserver/api/creditcards/", status.HTTP_200_OK)
        self.assertEqual(len(lod_all), 2)
        
        # List active
        lod_=tests_helpers.client_get(self, self.client_authorized_1, "http://testserver/api/creditcards/?active=true", status.HTTP_200_OK)
        self.assertEqual(len(lod_), 1)
        
        # List account 2
        lod_=tests_helpers.client_get(self, self.client_authorized_1, "http://testserver/api/creditcards/?account=200", status.HTTP_200_OK)
        self.assertEqual(len(lod_), 0)
        
        # List active accounts=1
        lod_=tests_helpers.client_get(self, self.client_authorized_1, "http://testserver/api/creditcards/?active=true&accounts=4", status.HTTP_200_OK)
        self.assertEqual(len(lod_), 1)
        
        # Try to change deferred attribute, but can't be updated
        dict_cc_debit=dict_cc.copy()
        dict_cc_debit["deferred"]=False
        tests_helpers.client_put(self, self.client_authorized_1, dict_cc["url"], dict_cc_debit , status.HTTP_400_BAD_REQUEST)

    def test_Creditcards_WithBalance(self):
        # create cc one active and one inactive
        dict_debit=tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcards/",  models.Creditcards.post_payload(deferred=False), status.HTTP_201_CREATED)
        dict_cc=tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcards/",  models.Creditcards.post_payload(deferred=True), status.HTTP_201_CREATED)
        
        #Creates a cco
        tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcardsoperations/",  models.Creditcardsoperations.post_payload(creditcards=dict_cc["url"], amount=22.22), status.HTTP_201_CREATED)
        
        # Can't  create a cco with a debit cc
        tests_helpers.client_post(self, self.client_authorized_1, "/api/creditcardsoperations/",  models.Creditcardsoperations.post_payload(creditcards=dict_debit["url"], amount=22.22), status.HTTP_400_BAD_REQUEST)
        
        # Compares balance
        lod_=tests_helpers.client_get(self, self.client_authorized_1, "http://testserver/api/creditcards/withbalance/", status.HTTP_200_OK)
        self.assertEqual(len(lod_), 2)
        self.assertEqual(lod_[0]["balance"], 0)#not deferred (debit)
        self.assertEqual(lod_[1]["balance"], 22.22)

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
        # Action used empty
        r=tests_helpers.client_get(self, self.client_authorized_1,  "/api/concepts/used/", status.HTTP_200_OK)
        self.assertEqual(lod.lod_sum(r, "used"), 0)
        
    @tag("current")
    def test_ProductsRange(self):
        def generate_url(d):            
            call=f"?product={d['product']}&totalized_operations={d['totalized_operations']}&percentage_between_ranges={d['percentage_between_ranges']}&percentage_gains={d['percentage_gains']}&amount_to_invest={d['amount_to_invest']}&recomendation_methods={d['recomendation_methods']}"
            for o in d["investments"]:
                call=call+f"&investments[]={o}"
            return f"/products/ranges/{call}"
        ############################################
        # Product hasn't quotes
        d={
            "product": "http://testserver/api/products/79329/",   
            "recomendation_methods": 8, #SMA10 
            "investments":[] ,
            "totalized_operations":True, 
            "percentage_between_ranges":2500, 
            "percentage_gains":2500, 
            "amount_to_invest": 10000
        }
        tests_helpers.client_get(self, self.client_authorized_1, generate_url(d) , status.HTTP_400_BAD_REQUEST)
        
        #Adding a quote and test again without investments
        for i in range(30):
            tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(datetime=datetime(2023,1,1)+timedelta(days=i), quote=i+1), status.HTTP_201_CREATED)
        tests_helpers.client_get(self, self.client_authorized_1, generate_url(d) , status.HTTP_200_OK)

        #Adding an investment operation and an order
        dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",  models.Investments.post_payload(), status.HTTP_201_CREATED)
        tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/",  models.Investmentsoperations.post_payload(investments=dict_investment["url"]), status.HTTP_201_CREATED)
        tests_helpers.client_post(self, self.client_authorized_1, "/api/orders/",  models.Orders.post_payload(date_=self.now.date(), investments=dict_investment["url"]), status.HTTP_201_CREATED)
        d={
            "product": "http://testserver/api/products/79329/",   
            "recomendation_methods":10,  #HMA10
            "investments":[dict_investment["id"], ] ,
            "totalized_operations":True, 
            "percentage_between_ranges":2500, 
            "percentage_gains":2500, 
            "amount_to_invest": 10000
        }
        r=tests_helpers.client_get(self, self.client_authorized_1, generate_url(d) , status.HTTP_200_OK)
        r

    def test_investing_com(self):
        self.assertEqual(models.Quotes.objects.count(), 0)
        lol_portfolio=[['\ufeff"Nombre"', 'Símbolo', 'Mercado', 'Último', 'Compra', 'Venta', 'Horario ampliado', 'Horario ampliado (%)', 'Apertura', 'Anterior', 'Máximo', 'Mínimo', 'Var.', '% var.', 'Vol.', 'Fecha próx. resultados', 'Hora', 'Cap. mercado', 'Ingresos', 'Vol. promedio (3m)', 'BPA', 'PER', 'Beta', 'Dividendo', 'Rendimiento', '5 minutos', '15 minutos', '30 minutos', '1 hora', '5 horas', 'Diario', 'Semanal', 'Mensual', 'Diario', 'Semanal', 'Mensual', 'Anual', '1 año', '3 años'], ['Bankinter Capital 3 Fi', '0P00000FB5', 'BME', '759,283', '-', '-', '--', '--', '759,283', '759,215', '759,283', '759,283', '+0,070', '+0,01%', '-', '--', '12/12', '54.670.000.000', '', '-', '-', '-', '-', '-', '-', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '0,01%', '0,05%', '0,28%', '2,47%', '2,49%', '0,94%'], ['La Française Trésorerie Isr R', 'LP60081294', 'EPA', '88.070,350', '-', '-', '--', '--', '88.070,350', '88.060,813', '88.070,350', '88.070,350', '+9,540', '+0,01%', '-', '--', '13:00:00', '-', '', '-', '-', '-', '-', '-', '-', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '0,01%', '0,08%', '0,32%', '3,16%', '3,23%', '2,40%'], ['Renta 4 Renta Fija 6 Meses Fi', '0P0000KY8J', 'BME', '11,799', '-', '-', '--', '--', '11,799', '11,798', '11,799', '11,799', '+0,001', '+0,01%', '-', '--', '12/12', '-', '', '-', '-', '-', '-', '-', '-', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '0,01%', '0,06%', '0,32%', '3,06%', '3,11%', '2,24%'], ['Xtrackers S&P 500 2x Leveraged Daily Swap UCITS ETF 1C', 'DBPG.DE', 'ETR', '142,70', '142,62', '142,70', '--', '--', '142,52', '141,38', '142,82', '142,24', '+1,32', '+0,93%', '18.370', '--', '17:28:29', '246.110.000', '', '14.044', '-', '-', '-', '-', '-', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '0,93%', '3,65%', '7,02%', '39,74%', '24,37%', '62,45%'], ['Futuros Nasdaq 100', 'NQH24', 'CME', '16.774,25', '16.774,25', '16.774,75', '--', '--', '16.596,00', '16.575,50', '16.806,50', '16.576,00', '+198,75', '+1,20%', '537.710', '--', '21:10:40', '-', '', '-', '-', '-', '-', '-', '-', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '1,30%', '4,83%', '5,74%', '52,34%', '42,90%', '34,80%'], ['Lyxor UCITS NASDAQ-100 Daily Leverage', 'LQQ.PA', 'EPA', '811,60', '-', '-', '--', '--', '811,90', '801,10', '816,50', '809,90', '+10,50', '+1,31%', '7.294', '--', '17:35:08', '-', '', '6.216', '-', '-', '-', '-', '-', 'Venta fuerte', 'Venta', 'Compra', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '1,31%', '6,71%', '7,93%', '108,88%', '71,44%', '52,50%'], ['Xtrackers FTSE 100 Income UCITS ETF 1D', 'XUKX.DE', 'ETR', '8,61', '8,61', '8,61', '--', '--', '8,61', '8,62', '8,63', '8,61', '-0,01', '-0,10%', '191', '--', '17:17:04', '74.790.000', '', '4.394', '-', '-', '-', '28,06', '3,79%', 'Venta', 'Venta', 'Venta', 'Venta', 'Compra', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '-0,10%', '-0,07%', '1,41%', '4,26%', '0,53%', '18,94%'], ['Dws Floating Rate Notes Lc', '0P00000N4I', 'LU', '86,250', '-', '-', '--', '--', '86,250', '86,230', '86,250', '86,250', '+0,020', '+0,02%', '-', '--', '12/12', '-', '', '-', '-', '-', '-', '-', '-', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '0,02%', '0,08%', '0,42%', '4,17%', '4,29%', '2,95%'], ['Redeia Corporacion SA', 'REDE', 'BME', '15,305', '15.310', '15.320', '--', '--', '15,270', '15,305', '15,360', '15,230', '+0,030', '+0,20%', '757,511', '21.02.2024', '', '8.260.000.000', '2.100.000.000', '1.059.088', '1,22', '12,55', '0,412', '0.81', '5.3%', 'Venta fuerte', 'Neutral', 'Venta fuerte', 'Venta', 'Neutral', 'Neutral', 'Compra', 'Venta fuerte', '0,20%', '-0,65%', '2,96%', '-5,87%', '-12,19%', '-9,22%'], ['Vocento S.A.', 'VOC.MC', 'BME', '0,624', '-', '-', '--', '--', '0,622', '0,624', '0,630', '0,602', '0,000', '0,00%', '52.000', '26.02.2024', '17:35:18', '75.140.000', 'N/A', '21.407', '0,107', '5,83', '0,981', '0,0373', '5,97%', 'Compra fuerte', 'Compra', 'Neutral', 'Neutral', 'Venta', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', '0,00%', '-1,89%', '-0,95%', '-1,27%', '-10,34%', '-23,72%'], ['Telecom Italia', 'TLIT.MI', 'BIT', '0,2491', '-', '-', '--', '--', '0,2578', '0,2586', '0,2585', '0,2491', '-0,0095', '-3,67%', '190.634.951', '21.02.2024', '17:35:15', '5.310.000.000', '16.210.000.000', '165.664.338', '-0,153', '-1,63', '1,04', '-', '-', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', '-3,67%', '-5,39%', '-5,21%', '15,16%', '18,51%', '-35,32%'], ['Técnicas Reunidas S.A.', 'TRE', 'BME', '8,260', '8,200', '8,300', '--', '--', '8,350', '8,260', '8,425', '8,240', '-0,120', '-1,43%', '195.325', '27.02.2024', '17:35:18', '644.080.000', '4.670.000.000', '179.576', '0,691', '11,92', '1,74', '-', '-', 'Venta', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', '-1,43%', '-3,79%', '-6,46%', '-9,43%', '-12,50%', '-20,12%'], ['Repsol S.A.', 'REP', 'BME', '13,230', '13,220', '13,280', '--', '--', '13,410', '13,230', '13,420', '13,160', '-0,270', '-2,00%', '5.083.327', '15.02.2024', '17:41:46', '16.920.000.000', '54.130.000.000', '4.204.968', '2,89', '4,58', '1,00', '0,0203', '0,15%', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Neutral', '-2,00%', '-4,79%', '-4,37%', '-10,91%', '-7,77%', '57,55%'], ['Renta 4 Pegasus R Fi', '0173321003.ES', 'BME', '15,59', '-', '-', '--', '--', '15,59', '15,58', '15,59', '15,59', '+0,01', '+0,09%', '-', '--', '12/12', '27.450.000.000', '', '-', '-', '-', '-', '-', '-', 'Compra', 'Compra', 'Compra', 'Compra', 'Compra', 'Compra', 'Compra fuerte', 'Compra fuerte', '0,09%', '0,12%', '1,88%', '6,89%', '5,49%', '-1,93%'], ['Orange SA', 'ORAN.PA', 'EPA', '10,80', '-', '-', '--', '--', '11,13', '11,16', '11,13', '10,74', '-0,36', '-3,21%', '10.599.170', '15.02.2024', '17:35:18', '28.830.000.000', '43.720.000.000', '4.854.149', '0,601', '18,04', '0,142', '0,7', '6,27%', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Neutral', 'Neutral', '-3,21%', '-3,00%', '-1,35%', '16,37%', '16,49%', '8,00%'], ['Mediaset España Comunicación S.A.', 'TL5', 'BME', '2,890', '2,866', '2,904', '--', '--', '2,910', '2,890', '3,012', '2,850', '0,000', '0,00%', '-', '--', '02/05', '905.050.000', '857.840.000', '258.943', '0,569', '5,08', '1,11', '-', '-', 'Neutral', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', '0,00%', '-7,67%', '-5,12%', '-12,79%', '-31,29%', '-5,56%'], ['Lyxor UCITS Daily Leverage CAC 40', 'LVC.PA', 'EPA', '37,30', '-', '-', '--', '--', '37,49', '37,45', '37,79', '37,30', '-0,16', '-0,41%', '166.734', '--', '17:35:21', '-', '', '287.161', '-', '-', '-', '-', '-', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Neutral', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '-0,41%', '2,42%', '9,71%', '35,88%', '25,21%', '91,01%'], ['Lyxor UCITS Ibex35 (DR) D-EUR', 'LYXIB.MC', 'BME', '100,94', '100,50', '106,00', '--', '--', '101,10', '101,06', '101,40', '100,86', '-0,16', '-0,16%', '18.298', '--', '17:29:00', '-', '', '7.432', '-', '-', '-', '1,4094', '-', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Neutral', 'Compra fuerte', 'Compra fuerte', '-0,16%', '-4,27%', '2,07%', '23,41%', '21,44%', '25,58%'], ['Intel Corporation', 'INTC.O', 'NASDAQ', '44,27', '-', '-', '--', '--', '44,07', '44,04', '44,72', '43,33', '+0,24', '+0,53%', '20.254.272', '25.01.2024', '21:20:28', '187.860.000.000', '52.860.000.000', '37.470.812', '-0,395', '-111,85', '0,893', '0,5', '1,14%', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '0,66%', '7,41%', '12,48%', '67,73%', '56,86%', '-12,17%'], ['ING Groep NV', 'INGA.AS', 'AS', '13,54', '-', '-', '--', '--', '13,60', '13,62', '13,64', '13,54', '-0,07', '-0,54%', '11.001.234', '01.02.2024', '17:35:03', '46.170.000.000', '34.060.000.000', '11.036.945', '4,37', '3,11', '-', '0,821', '6,03%', 'Venta fuerte', 'Venta fuerte', 'Venta', 'Venta', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '-0,54%', '2,03%', '8,62%', '18,90%', '19,00%', '71,26%'], ['Indra Sistemas S.A.', 'IDR', 'BME', '14,010', '13,990', '14,050', '--', '--', '14,140', '14,010', '14,220', '14,010', '-0,110', '-0,78%', '251.204', '27.02.2024', '17:35:18', '2.470.000.000', '4.230.000.000', '436.618', '1,15', '12,20', '0,991', '0,2025', '1,43%', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta', 'Venta', 'Compra fuerte', 'Compra fuerte', '-0,78%', '-1,48%', '0,21%', '31,55%', '36,28%', '107,56%'], ['Grifols S.A.', 'GRLS', 'BME', '13,825', '13,810', '13,900', '--', '--', '14,010', '13,825', '14,120', '13,755', '-0,095', '-0,68%', '788.544', '29.02.2024', '17:35:26', '9.400.000.000', '6.540.000.000', '1.215.768', '0,034', '407,35', '0,534', '-', '-', 'Venta', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Compra', 'Compra fuerte', 'Compra fuerte', 'Compra', '-0,68%', '-0,82%', '12,72%', '28,37%', '27,71%', '-43,98%'], ['Ferrovial S.A.', 'FER', 'BME', '32,610', '32,560', '32,700', '--', '--', '32,400', '32,610', '32,740', '32,290', '+0,220', '+0,68%', '1.011.326', '29.02.2024', '17:35:18', '23.640.000.000', '7.960.000.000', '1.086.310', '0,328', '99,48', '0,912', '0,7147', '2,21%', 'Venta fuerte', 'Neutral', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '0,68%', '0,87%', '9,47%', '33,27%', '27,18%', '46,78%'], ['Accion IBEX 35 Cotizado Armonizado FI', 'BBVAI.MC', 'BME', '10,17', '10,10', '10,35', '--', '--', '10,20', '10,20', '10,22', '10,17', '+0,01', '+0,10%', '4.163', '--', '15:30:00', '-', '', '47.918', '-', '-', '-', '0,234', '2,29%', 'Compra fuerte', 'Compra fuerte', 'Neutral', 'Neutral', 'Neutral', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '0,10%', '-1,36%', '5,06%', '22,86%', '21,26%', '24,18%'], ['Ercros S.A.', 'ECR.MC', 'BME', '2,485', '2,485', '2,500', '--', '--', '2,465', '2,475', '2,515', '2,460', '+0,010', '+0,40%', '86.610', '29.02.2024', '17:35:18', '235.570.000', '815.050.000', '110.570', '0,345', '7,26', '1,01', '0,1215', '4,91%', 'Neutral', 'Venta', 'Neutral', 'Compra', 'Compra', 'Neutral', 'Venta fuerte', 'Venta fuerte', '0,40%', '1,64%', '-2,74%', '-23,30%', '-24,70%', '10,44%'], ['Enagás S.A.', 'ENAG', 'BME', '16,850', '16,810', '16,910', '--', '--', '16,800', '16,850', '16,935', '16,725', '+0,095', '+0,57%', '1.038.218', '20.02.2024', '17:40:42', '4.400.000.000', '911.200.000', '763.721', '1,08', '15,61', '0,599', '1,3932', '8,32%', 'Venta fuerte', 'Venta fuerte', 'Venta', 'Compra', 'Neutral', 'Compra', 'Compra fuerte', 'Venta', '0,57%', '-0,82%', '5,44%', '8,53%', '-2,88%', '-17,32%'], ['Ebro Foods S.A.', 'EBRO', 'BME', '15,500', '15,470', '15,570', '--', '--', '15,600', '15,500', '15,660', '15,440', '-0,100', '-0,64%', '57.492', '29.02.2024', '17:35:18', '2.390.000.000', '3.090.000.000', '77.819', '1,14', '13,61', '0,173', '0,4617', '2,96%', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', '-0,64%', '-0,64%', '-2,64%', '5,73%', '3,75%', '-22,69%'], ['Danone SA', 'DANO.PA', 'EPA', '59,31', '-', '-', '--', '--', '59,60', '59,55', '59,65', '59,15', '-0,24', '-0,40%', '1.134.387', '21.02.2024', '17:35:14', '38.010.000.000', '28.500.000.000', '1.082.750', '2,04', '29,04', '0,484', '2', '3,36%', 'Venta', 'Venta fuerte', 'Venta fuerte', 'Venta', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '-0,40%', '1,00%', '2,05%', '20,48%', '19,26%', '13,06%'], ['Commerzbank AG O.N.', 'CBKG', 'ETR', '10,855', '10.865', '10.915', '--', '--', '10,800', '10,855', '10,965', '10,730', '+0,020', '+0,18%', '5,179,785', '15.02.2024', '', '13.510.000.000', '9.910.000.000', '6.868.726', '1,86', '5,84', '1,28', '0.2', '1.85%', 'Compra fuerte', 'Compra fuerte', 'Compra', 'Compra', 'Venta fuerte', 'Venta', 'Compra fuerte', 'Compra fuerte', '0,18%', '-5,40%', '0,14%', '22,85%', '39,99%', '111,52%'], ['Coca-Cola Co', 'KO', 'NYSE', '59,99', '-', '-', '--', '--', '59,42', '59,42', '59,99', '59,26', '+0,57', '+0,96%', '7.879.193', '15.02.2024', '21:20:28', '258.840.000.000', '45.030.000.000', '15.164.101', '2,49', '23,95', '0,592', '1,84', '3,1%', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '0,90%', '2,30%', '4,99%', '-5,75%', '-6,31%', '12,54%'], ['Clínica Baviera S.A.', 'CBAV.MC', 'BME', '21,900', '21,200', '22,900', '--', '--', '21,800', '21,800', '21,900', '21,500', '+0,100', '+0,46%', '1.904', '27.02.2024', '17:35:18', '355.410.000', '217.330.000', '1.986', '1,98', '11,01', '0,555', '1,053', '4,83%', 'Compra', 'Compra fuerte', 'Compra fuerte', 'Neutral', 'Neutral', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '0,46%', '0,92%', '8,96%', '25,50%', '20,33%', '102,78%'], ['CaixaBank S.A.', 'CABK', 'BME', '3,880', '3,876', '3,902', '--', '--', '3,868', '3,880', '3,901', '3,854', '+0,013', '+0,34%', '9.534.776', '02.02.2024', '17:40:21', '29.080.000.000', '13.230.000.000', '11.637.669', '0,545', '7,11', '-', '0,1868', '4,83%', 'Venta fuerte', 'Venta fuerte', 'Neutral', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Compra', 'Compra fuerte', '0,34%', '-5,27%', '-1,82%', '5,66%', '15,13%', '73,99%'], ['Allianz SE VNA O.N.', 'ALVG', 'ETR', '244,95', '244,98', '245,23', '--', '--', '245,60', '244,95', '246,05', '244,75', '-0,55', '-0,22%', '767.675', '23.02.2024', '17:29:49', '95.740.000.000', '102.080.000.000', '821.605', '20,87', '11,73', '-', '11,4', '4,64%', 'Venta fuerte', 'Venta fuerte', 'Venta', 'Compra', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '-0,22%', '1,66%', '9,11%', '21,93%', '20,07%', '27,59%'], ['Koninklijke Ahold Delhaize NV', 'AD.AS', 'AS', '26,24', '-', '-', '--', '--', '26,80', '26,81', '26,82', '26,24', '-0,57', '-2,14%', '2.600.637', '14.02.2024', '17:35:05', '25.240.000.000', '88.980.000.000', '1.996.072', '2,30', '11,43', '0,268', '1,08', '4,03%', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', '-2,14%', '-2,38%', '-3,23%', '-2,24%', '-5,39%', '11,99%'], ['Adolfo Domínguez S.A.', 'ADZ.MC', 'BME', '4,880', '4,860', '4,980', '--', '--', '4,860', '4,860', '4,880', '4,860', '+0,020', '+0,41%', '3.386', '16.01.2024', '17:29:27', '45.030.000', '114.180.000', '2.288', '0,017', '287,06', '0,785', '-', '-', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', '0,41%', '-1,21%', '-2,40%', '21,09%', '23,54%', '10,66%'], ['Actividades de Construcción y Servicios S.A.', 'ACS', 'BME', '39,070', '39,000', '39,140', '--', '--', '38,080', '39,070', '39,160', '38,080', '+1,090', '+2,87%', '834.668', '28.02.2024', '17:35:18', '10.290.000.000', '35.480.000.000', '483.880', '2,94', '13,27', '1,08', '1,6297', '4,29%', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '2,87%', '5,40%', '13,48%', '48,46%', '47,64%', '67,20%'], ['Acerinox S.A.', 'ACX', 'BME', '10,030', '9,990', '10,040', '--', '--', '10,030', '10,030', '10,105', '9,982', '0,000', '0,00%', '813.727', '27.02.2024', '17:35:18', '2.490.000.000', '6.800.000.000', '717.343', '0,654', '15,32', '1,26', '0,486', '4,85%', 'Compra fuerte', 'Compra', 'Neutral', 'Venta fuerte', 'Venta fuerte', 'Neutral', 'Compra fuerte', 'Compra fuerte', '0,00%', '-1,62%', '1,87%', '8,53%', '10,10%', '14,58%'], ['Acciona S.A.', 'ANA', 'BME', '130,550', '130,800', '131,150', '--', '--', '130,400', '130,550', '131,750', '130,150', '+0,600', '+0,46%', '59.938', '29.02.2024', '17:35:23', '7.170.000.000', '14.160.000.000', '97.649', '12,92', '10,13', '0,676', '3,653', '2,81%', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Neutral', 'Neutral', 'Neutral', 'Venta fuerte', '0,46%', '-3,08%', '-0,65%', '-24,05%', '-28,89%', '19,44%'], ['Renta 4 Valor Relativo R Fi', '0P0000NQOD', 'BME', '14,43', '-', '-', '--', '--', '14,43', '14,42', '14,43', '14,43', '+0,02', '+0,11%', '-', '--', '12/12', '166.580.000', '', '-', '-', '-', '-', '-', '-', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '0,11%', '0,02%', '0,89%', '4,79%', '3,82%', '-0,01%'], ['Renta 4 Activos Globales R Fi', 'LP68572540', 'BME', '7,644', '-', '-', '--', '--', '7,644', '7,642', '7,644', '7,644', '+0,002', '+0,02%', '-', '--', '12/12', '160.780.000.000', '', '-', '-', '-', '-', '-', '-', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '0,02%', '0,25%', '1,34%', '6,26%', '4,32%', '6,02%'], ['Futuros Russell 2000', 'RTYH24', 'CME', '1.952,10', '1.952,00', '1.952,30', '--', '--', '1.905,20', '1.904,20', '1.970,00', '1.890,00', '+47,90', '+2,52%', '269.991', '--', '21:11:00', '-', '', '-', '-', '-', '-', '-', '-', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '3,07%', '4,71%', '8,72%', '10,83%', '7,75%', '2,47%'], ['Renta 4 Global Acciones Pp', '0P0000OQ3V', 'BME', '25,705', '-', '-', '--', '--', '25,705', '25,549', '25,705', '25,705', '+0,160', '+0,61%', '-', '--', '11/12', '25.820.000.000', '', '-', '-', '-', '-', '-', '-', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '0,61%', '1,28%', '4,30%', '9,06%', '4,17%', '15,62%'], ['Futuros oro', 'GC', 'ICE', '2.036,00', '2.035,50', '2.036,50', '--', '--', '1.995,00', '1.993,20', '2.036,00', '1.988,00', '+42,80', '+2,15%', '160.168', '--', '21:20:57', '-', '', '-', '-', '-', '-', '-', '-', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Neutral', 'Compra fuerte', 'Compra fuerte', '1,99%', '-0,74%', '3,37%', '11,31%', '11,77%', '10,95%'], ['Futuros KOSPI 200', 'KSc1', 'KRX', '336,90', '336,60', '337,20', '--', '--', '339,30', '337,00', '339,90', '336,80', '-3,60', '-1,06%', '-', '--', '07:09:52', '-', '', '-', '-', '-', '-', '-', '-', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Compra', 'Compra', 'Compra fuerte', 'Compra fuerte', '-1,06%', '1,02%', '2,78%', '15,04%', '8,19%', '-7,77%'], ['Russell 2000', 'US2000', 'NYSE', '1.934,80', '1,934.60', '1,935.00', '--', '--', '1.882,10', '1.881,27', '1.948,30', '1.868,55', '+53,53', '+2,85%', '-', '--', '', '-', '', '-', '-', '-', '-', '-', '-', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '2,84%', '4,46%', '7,58%', '9,85%', '6,28%', '1,09%'], ['Bankinter S.A.', 'BKT', 'BME', '6,054', '6,033', '6,089', '--', '--', '6,022', '6,054', '6,084', '5,976', '+0,044', '+0,73%', '2.447.771', '25.01.2024', '17:35:18', '5.450.000.000', '2.260.000.000', '2.551.005', '0,777', '7,79', '0,815', '0,3184', '5,3%', 'Venta fuerte', 'Venta', 'Neutral', 'Neutral', 'Venta fuerte', 'Venta fuerte', 'Compra', 'Compra', '0,73%', '-3,32%', '-3,17%', '-3,41%', '2,54%', '89,42%'], ['PSI', '.PSI20', 'ELI', '6.456,88', '-', '-', '--', '--', '6.426,77', '6.427,78', '6.485,63', '6.425,51', '+29,10', '+0,45%', '73,139,080', '--', '', '-', '', '101.095.534', '-', '-', '-', '-', '-', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Neutral', 'Compra', 'Compra fuerte', 'Compra fuerte', '0,45%', '-2,32%', '1,84%', '12,76%', '11,57%', '35,08%'], ['Nasdaq 100', '.NDX', 'NASDAQ', '16.518,59', '-', '-', '--', '--', '16.392,18', '16.354,25', '16.581,04', '16.357,21', '+164,34', '+1,00%', '127.042.634', '--', '21:20:34', '-', '', '253.152.877', '-', '-', '-', '-', '-', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '1,08%', '4,71%', '4,54%', '51,11%', '40,80%', '32,65%'], ['FTSE Latibex All Share', '.IBEXL', 'BME', '2.442,90', '-', '-', '--', '--', '2.453,20', '2.453,20', '2.463,20', '2.439,70', '-10,30', '-0,42%', '15.549', '--', '17:30:00', '-', '', '20.796', '-', '-', '-', '-', '-', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta', 'Compra fuerte', 'Compra fuerte', '-0,42%', '-1,31%', '-0,41%', '5,72%', '11,79%', '25,06%'], ['Nikkei 225', 'JP225', 'TYO', '32.926,35', '32.918,00', '32.932,00', '--', '--', '32.965,00', '32.926,35', '33.101,50', '32.855,00', '+81,30', '+0,25%', '-', '--', '06:59:58', '-', '', '1.045.285.171', '-', '-', '-', '-', '-', 'Venta fuerte', 'Venta fuerte', 'Neutral', 'Neutral', 'Neutral', 'Neutral', 'Compra fuerte', 'Compra fuerte', '0,25%', '-1,55%', '0,70%', '26,18%', '16,94%', '23,17%'], ['Hang Seng', 'HK50', 'HK', '16.247,00', '16.244,00', '16.250,00', '--', '--', '16.331,00', '16.247,00', '16.339,00', '16.145,00', '-154,50', '-0,94%', '-', '--', '08:59:59', '-', '', '1.989.148.069', '-', '-', '-', '-', '-', 'Compra fuerte', 'Neutral', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', '-0,94%', '-1,31%', '-6,61%', '-17,87%', '-17,42%', '-38,43%'], ['NASDAQ Composite', '.IXIC', 'NASDAQ', '14.689,87', '-', '-', '--', '--', '14.555,68', '14.533,40', '14.743,55', '14.517,53', '+156,48', '+1,08%', '-', '--', '21:20:54', '-', '', '956.270.329', '-', '-', '-', '-', '-', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '1,11%', '3,87%', '4,26%', '40,40%', '31,54%', '18,12%'], ['Dow Jones Industrial Average', '.DJI', 'NYSE', '36.980,53', '22.350,00', '22.352,00', '--', '--', '36.601,80', '36.577,94', '37.057,81', '36.523,59', '+402,59', '+1,10%', '212.934.902', '--', '21:20:39', '-', '', '293.093.352', '-', '-', '-', '-', '-', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '1,09%', '2,56%', '6,17%', '11,56%', '8,87%', '23,83%'], ['FTSE 100', 'UK100', 'LON', '7.548,44', '7.547,13', '7.548,93', '--', '--', '7.542,77', '7.548,44', '7.584,88', '7.542,68', '+5,67', '+0,08%', '998.797.481', '--', '17:35:01', '-', '', '662.117.859', '-', '-', '-', '-', '-', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '0,08%', '0,44%', '1,45%', '1,30%', '0,70%', '15,56%'], ['CAC 40', '.FCHI', 'EPA', '7.531,22', '-', '-', '--', '--', '7.542,10', '7.543,55', '7.579,25', '7.529,11', '-12,33', '-0,16%', '62.227.423', '--', '17:35:45', '-', '', '57.875.891', '-', '-', '-', '-', '-', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Neutral', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '-0,16%', '1,28%', '4,81%', '16,33%', '11,89%', '36,24%'], ['XAU/USD - Oro al contado Dólar', 'XAU/USD - Oro al contado Dólar', 'FX', '2.019,39', '2.019,25', '2.019,54', '--', '--', '1.979,51', '1.979,51', '2.019,39', '1.973,12', '+39,88', '+2,01%', '-', '--', '21:20:37', '-', '', '-', '-', '-', '-', '-', '-', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Neutral', 'Compra fuerte', 'Compra fuerte', '1,92%', '-0,37%', '2,79%', '10,58%', '11,63%', '10,42%'], ['Futuros FTSE MIB', 'IT40', 'Borsa Italiana', '30.717,50', '30.710,00', '30.725,00', '--', '--', '30.560,00', '30.625,00', '30.755,00', '30.465,00', '+92,50', '+0,30%', '27.416', '--', '21:20:53', '-', '', '-', '-', '-', '-', '-', '-', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '0,29%', '1,16%', '5,10%', '29,56%', '24,93%', '40,97%'], ['SMI', 'SWI20', 'SIX', '11.188,91', '11.191,20', '11.196,40', '--', '--', '11.153,77', '11.188,91', '11.255,50', '11.153,77', '+37,69', '+0,34%', '27.697.269', '--', '17:34:57', '-', '', '25.710.369', '-', '-', '-', '-', '-', 'Venta fuerte', 'Venta fuerte', 'Venta', 'Compra', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '0,34%', '1,70%', '4,42%', '4,28%', '0,25%', '7,87%'], ['Amadeus IT Holding S.A.', 'AMA', 'BME', '64,800', '64,510', '64,970', '--', '--', '65,700', '64,800', '66,020', '64,660', '-0,800', '-1,22%', '503.364', '29.02.2024', '17:35:18', '28.750.000.000', '5.260.000.000', '664.888', '2,28', '28,45', '1,24', '0,5994', '0,91%', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Neutral', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '-1,22%', '0,06%', '5,47%', '33,47%', '22,03%', '8,14%'], ['EUR/USD - Euro Dólar', 'EUR/USD - Euro Dólar', 'FX', '1,0883', '1,0883', '1,0883', '--', '--', '1,0791', '1,0792', '1,0896', '1,0773', '+0,0091', '+0,84%', '-', '--', '21:20:37', '-', '', '-', '-', '-', '-', '-', '-', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra', '0,83%', '1,12%', '0,03%', '1,68%', '1,87%', '-10,38%'], ['Atresmedia Corp. de Medios de Com. S.A.', 'A3M', 'BME', '3,586', '3,570', '3,610', '--', '--', '3,614', '3,586', '3,648', '3,586', '-0,044', '-1,21%', '602.801', '29.02.2024', '17:36:43', '808.390.000', '871.460.000', '286.345', '0,513', '7,01', '0,916', '0,324', '8,93%', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Neutral', 'Neutral', '-1,21%', '-6,74%', '-2,82%', '12,34%', '15,68%', '18,66%'], ['MULTI-UNITS LUXEMBOURG - Lyxor Daily LevDAX UCITS ETF - Acc', 'LYXLEVDAX.DE', 'ETR', '138,28', '138,24', '138,38', '--', '--', '139,10', '138,84', '139,28', '138,28', '-0,56', '-0,40%', '8.142', '--', '17:36:07', '-', '', '10.731', '-', '-', '-', '-', '-', 'Venta fuerte', 'Venta fuerte', 'Venta', 'Venta', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '-0,40%', '1,13%', '14,77%', '36,32%', '26,01%', '37,67%'], ['Lyxor UCITS Ibex 35 Doble Apalancado Diario C-EUR', 'IBEXA.MC', 'BME', '20,985', '20,820', '21,500', '--', '--', '21,095', '21,100', '21,250', '20,910', '-0,065', '-0,31%', '31.696', '--', '17:34:00', '-', '', '116.830', '-', '-', '-', '-', '-', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta', 'Compra', 'Compra fuerte', 'Compra fuerte', '-0,31%', '-3,14%', '10,11%', '52,66%', '47,72%', '60,51%'], ['Lyxor UCITS Stoxx 50 Daily Leverage', 'LVE.PA', 'EPA', '44,750', '-', '-', '--', '--', '44,880', '44,890', '45,210', '44,745', '-0,140', '-0,31%', '23.186', '--', '17:35:28', '115.560.000', '', '42.683', '-', '-', '-', '-', '-', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Neutral', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '-0,31%', '2,03%', '11,15%', '43,36%', '29,75%', '71,75%'], ['Banco Bilbao Vizcaya Argentaria SA', 'BBVA', 'BME', '8,426', '8,410', '8,450', '--', '--', '8,402', '8,426', '8,460', '8,324', '+0,006', '+0,07%', '8.409.884', '30.01.2024', '17:42:59', '49.170.000.000', '24.950.000.000', '16.036.125', '1,22', '6,90', '1,50', '0,3807', '4,52%', 'Neutral', 'Neutral', 'Neutral', 'Neutral', 'Venta', 'Neutral', 'Compra fuerte', 'Compra fuerte', '0,07%', '-2,11%', '2,53%', '49,56%', '52,18%', '109,19%'], ['Carmignac Sécurité Aw Eur Acc', '0P00000FB8', 'EPA', '1.770,230', '-', '-', '--', '--', '1.770,230', '1.769,580', '1.770,230', '1.770,230', '+0,650', '+0,04%', '-', '--', '12/12', '19.000.000.000', '', '-', '-', '-', '-', '-', '-', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '0,04%', '0,05%', '1,18%', '3,30%', '3,19%', '-1,34%'], ['Carmignac Patrimoine A Eur Acc', '0P00000FB4', 'EPA', '640,840', '-', '-', '--', '--', '640,840', '640,730', '640,840', '640,840', '+0,110', '+0,02%', '-', '--', '12/12', '199.690.000.000', '', '-', '-', '-', '-', '-', '-', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra', '0,02%', '0,35%', '1,53%', '-0,38%', '-0,47%', '-9,07%'], ['ArcelorMittal S.A.', 'MTS', 'BME', '24,010', '23,910', '24,020', '--', '--', '23,960', '24,010', '24,215', '23,800', '+0,040', '+0,17%', '219.220', '08.02.2024', '17:35:18', '20.100.000.000', '70.610.000.000', '268.401', '4,87', '5,31', '-', '0,4067', '1,7%', 'Neutral', 'Neutral', 'Venta', 'Venta', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Neutral', '0,17%', '1,80%', '12,78%', '-2,36%', '-4,06%', '38,18%'], ['Mapfre S.A.', 'MAP', 'BME', '1,981', '1,972', '1,991', '--', '--', '1,986', '1,981', '1,991', '1,974', '-0,004', '-0,20%', '1.797.483', '13.02.2024', '17:35:18', '6.070.000.000', '17.800.000.000', '2.527.803', '0,215', '9,21', '0,748', '0,1181', '5,95%', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Compra fuerte', 'Compra fuerte', '-0,20%', '-1,74%', '-2,22%', '9,45%', '10,12%', '18,48%'], ['Banco Santander S.A.', 'SAN', 'BME', '3,8380', '3,8300', '3,8550', '--', '--', '3,8585', '3,8380', '3,8800', '3,8220', '-0,0375', '-0,97%', '31.667.700', '31.01.2024', '17:43:23', '61.330.000.000', '44.140.000.000', '41.669.749', '0,612', '6,27', '1,36', '0,1138', '2,94%', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta', 'Compra', 'Compra fuerte', 'Compra fuerte', '-0,97%', '-3,00%', '4,19%', '36,95%', '38,81%', '47,59%'], ['Telefónica S.A.', 'TEF', 'BME', '3,6710', '3,6620', '3,6880', '--', '--', '3,7890', '3,6710', '3,7890', '3,6520', '-0,1290', '-3,39%', '21.420.215', '22.02.2024', '17:42:39', '20.930.000.000', '40.810.000.000', '14.964.626', '0,271', '13,55', '0,732', '0,243', '6,39%', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Neutral', '-3,39%', '-9,27%', '-1,77%', '8,45%', '10,34%', '11,98%'], ['IBEX 35', 'ES35', 'BME', '10.096,10', '10.094,85', '10.098,35', '--', '--', '10.116,00', '10.096,10', '10.158,70', '10.077,00', '-22,60', '-0,22%', '142.958.199', '--', '17:37:00', '-', '', '141.422.826', '-', '-', '-', '-', '-', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '-0,22%', '-1,58%', '4,91%', '22,69%', '20,76%', '24,02%'], ['S&P 500', 'US500', 'NYSE', '4.696,20', '4.695,95', '4.696,45', '--', '--', '4.646,73', '4.643,70', '4.710,09', '4.642,83', '+52,50', '+1,13%', '-', '--', '21:20:52', '-', '', '2.362.808.064', '-', '-', '-', '-', '-', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '1,15%', '3,24%', '4,48%', '22,33%', '17,56%', '28,77%'], ['Futuros S&P 500', 'ESH24', 'CME', '4.752,25', '4.752,25', '4.752,50', '--', '--', '4.700,50', '4.697,25', '4.764,25', '4.696,75', '+55,00', '+1,17%', '1.458.245', '--', '21:10:50', '-', '', '-', '-', '-', '-', '-', '-', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '1,34%', '3,34%', '5,52%', '23,28%', '19,06%', '30,54%'], ['CBOE Volatility Index', 'VIX', 'CBOE', '12,14', '-', '-', '--', '--', '12,07', '12,07', '12,46', '11,82', '+0,07', '+0,58%', '-', '--', '', '-', '', '-', '-', '-', '-', '-', '-', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', '0,50%', '-6,48%', '-14,34%', '-44,02%', '-42,62%', '-50,93%'], ['DAX', 'DE40', 'ETR', '16.766,05', '16.763,50', '16.765,50', '--', '--', '16.811,56', '16.766,05', '16.836,45', '16.760,12', '-25,69', '-0,15%', '65.413.494', '--', '17:34:59', '-', '', '72.135.931', '-', '-', '-', '-', '-', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Neutral', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '-0,15%', '0,66%', '7,38%', '20,41%', '15,95%', '26,79%'], ['Futuros DAX', 'FDXH4', 'Eurex', '17.065,5', '17,064.9', '17,066.1', '--', '--', '17.000,5', '17.000,0', '17.099,5', '16.935,5', '+65,5', '+0,39%', '40,249', '--', '', '-', '', '-', '-', '-', '-', '-', '-', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '0,41%', '1,11%', '8,89%', '20,67%', '16,11%', '28,92%'], ['Euro Stoxx 50', 'STOXX50', 'ETR', '4.530,35', '4.529,70', '4.531,00', '--', '--', '4.537,05', '4.530,35', '4.553,75', '4.529,35', '-6,26', '-0,14%', '-', '--', '17:34:57', '-', '', '28.424.891', '-', '-', '-', '-', '-', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '-0,14%', '1,05%', '5,56%', '19,42%', '13,96%', '29,29%'], ['Futuros Euro Stoxx 50', 'EU50', 'Eurex', '4.602', '4.602', '4.603', '--', '--', '4.586', '4.540', '4.612', '4.562', '+62', '+1,37%', '975.100', '--', '21:20:32', '-', '', '-', '-', '-', '-', '-', '-', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '1,41%', '2,42%', '6,90%', '21,64%', '15,77%', '31,28%'], ['Futuros IBEX 35', 'ES35', 'BME', '10.097,0', '10.096,0', '10.098,0', '--', '--', '10.125,0', '10.125,0', '10.160,5', '10.086,0', '-28,0', '-0,28%', '22.332', '--', '19:59:28', '-', '', '-', '-', '-', '-', '-', '-', 'Neutral', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Venta fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', '-0,28%', '-1,73%', '4,85%', '23,22%', '20,79%', '24,10%'], ['del Tesoro de España a 50 años (30-Jul-2066)', 'ES0000128E=RRPS', 'BME', '91,258', '91,258', '92,529', '--', '--', '89,716', '89,943', '91,516', '89,716', '+1,315', '+1,46%', '-', '--', '17:31:29', '-', '', '-', '-', '-', '-', '-', '-', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Venta', '1,46%', '1,08%', '10,14%', '4,38%', '-10,44%', '-50,30%'], ['del Tesoro de España a 32 años 4.2% (31-Ene-2037)', 'ES00001293=RRPS', 'BME', '108,611', '108,611', '108,832', '--', '--', '107,750', '107,809', '108,649', '107,750', '+0,802', '+0,74%', '-', '--', '17:30:41', '-', '', '-', '-', '-', '-', '-', '-', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Neutral', '0,74%', '0,44%', '4,98%', '4,42%', '-3,15%', '-32,22%'], ['del Tesoro de España a 32 años (30-Jul-2041)', 'ES0000121S=RRPS', 'BME', '114,577', '114,577', '114,860', '--', '--', '113,489', '113,596', '114,653', '113,489', '+0,981', '+0,86%', '-', '--', '17:30:42', '-', '', '-', '-', '-', '-', '-', '-', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Neutral', '0,86%', '0,54%', '6,15%', '3,72%', '-5,17%', '-36,47%'], ['del Tesoro de España a 31 años (31-Oct-2044)', 'ES0000124H=RRPS', 'BME', '121,820', '121,820', '122,150', '--', '--', '120,463', '120,628', '121,931', '120,463', '+1,192', '+0,99%', '-', '--', '17:30:46', '-', '', '-', '-', '-', '-', '-', '-', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Compra fuerte', 'Venta', '0,99%', '0,58%', '6,86%', '3,37%', '-6,82%', '-38,78%']]
        ic=investing_com.InvestingCom.from_lol("Europe/Madrid", lol_portfolio)
        ic.get()
        

    def test_Orders(self):
        # common _tests y deja creada una activa        
        dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",  models.Investments.post_payload(), status.HTTP_201_CREATED)
        tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(products=dict_investment["products"]), status.HTTP_201_CREATED)

        tests_helpers.common_tests_Collaborative(self, "/api/orders/", models.Orders.post_payload(investments=dict_investment["url"]), self.client_authorized_1, self.client_authorized_2, self.client_anonymous)

    def test_Products(self):
        # Personal products CRUD
        dict_pp=tests_helpers.client_post(self, self.client_authorized_1, "/api/products/", models.Products.post_personal_payload(), status.HTTP_201_CREATED)
        dict_pp_update=dict_pp.copy()
        dict_pp_update["comment"]="Updated"
        dict_pp_update["system"]=False
        dict_pp_update=tests_helpers.client_put(self, self.client_authorized_1, dict_pp["url"], dict_pp_update, status.HTTP_200_OK)
        tests_helpers.client_delete(self, self.client_authorized_1, dict_pp["url"], dict_pp_update, status.HTTP_204_NO_CONTENT)
        
        # System products CRUD
        tests_helpers.client_post(self, self.client_authorized_1, "/api/products/", models.Products.post_system_payload(), status.HTTP_400_BAD_REQUEST)
        dict_sp=tests_helpers.client_post(self, self.client_catalog_manager, "/api/products/", models.Products.post_system_payload(), status.HTTP_201_CREATED)
        dict_sp_update=dict_sp.copy()
        dict_sp_update["comment"]="Updated"
        dict_sp_update["system"]=True
        tests_helpers.client_put(self, self.client_authorized_1, dict_sp["url"], dict_sp_update, status.HTTP_400_BAD_REQUEST)
        dict_sp_update=tests_helpers.client_put(self, self.client_catalog_manager, dict_sp["url"], dict_sp_update, status.HTTP_200_OK)
        tests_helpers.client_delete(self, self.client_authorized_1, dict_sp["url"], dict_sp_update, status.HTTP_400_BAD_REQUEST)
        tests_helpers.client_delete(self, self.client_catalog_manager, dict_sp["url"], dict_sp_update, status.HTTP_204_NO_CONTENT)

    # def test_Strategies(self):
    #     # Creates an investment with a quote and an io
    #     dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",  models.Investments.post_payload(), status.HTTP_201_CREATED)
    #     tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(products=dict_investment["products"]), status.HTTP_201_CREATED)
    #     tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(dict_investment["url"]), status.HTTP_201_CREATED)

    #     # Creates a strategy for this investment
    #     dict_strategy=tests_helpers.client_post(self, self.client_authorized_1, "/api/strategies/",  models.Strategies.post_payload(investments=[dict_investment['url'], ]), status.HTTP_201_CREATED)
        
    #     # Gets strategy plio_id
    #     dict_strategy_plio=tests_helpers.client_get(self, self.client_authorized_1, f"{dict_strategy['url']}ios/",  status.HTTP_200_OK)
    #     self.assertEqual(dict_strategy_plio["entries"], ["79329"])
        
    #     # Gets strategies with balance
    #     lod_strategy_withbalance=tests_helpers.client_get(self, self.client_authorized_1, "/api/strategies/withbalance/",  status.HTTP_200_OK)
    #     self.assertEqual(len(lod_strategy_withbalance), 1)

    #     # Gests strategies by invesment
    #     lod_strategy_by_investment=tests_helpers.client_get(self, self.client_authorized_1, f"/api/strategies/?investment={dict_investment['url']}&active=true&type=2",  status.HTTP_200_OK)
    #     self.assertEqual(len(lod_strategy_by_investment), 1)

    def test_StrategiesFastOperations(self):
        # Opens account
        tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/",  models.Accountsoperations.post_payload(concepts=hurl_concepts_oa, amount=999999), status.HTTP_201_CREATED)

        # Create a FO strategy
        dict_strategy_fos=tests_helpers.client_post(self, self.client_authorized_1, "/api/strategies_fastoperations/",  models.StrategiesFastOperations.post_payload(strategy=models.Strategies.post_payload(name="FOS", type=models.StrategiesTypes.FastOperations), accounts=["http://testserver/api/accounts/4/"]), status.HTTP_201_CREATED)

        tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/",  models.Accountsoperations.post_payload(concepts=hurl_concepts_fo, amount=-10, comment="FO"), status.HTTP_201_CREATED)
        tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/",  models.Accountsoperations.post_payload(concepts=hurl_concepts_fo, amount=1010, comment="FO"), status.HTTP_201_CREATED)

        # Get FO strategy detailed view
        strategy_detail=tests_helpers.client_get(self, self.client_authorized_1, f"{dict_strategy_fos['url']}detailed/",  status.HTTP_200_OK)
        self.assertEqual(lod.lod_sum(strategy_detail,"amount"), 1000)

        #Update fos
        dict_strategy_fos=tests_helpers.client_put(self, self.client_authorized_1, dict_strategy_fos["url"],  models.StrategiesFastOperations.post_payload(strategy=models.Strategies.post_payload(name="FOS Updated", type=models.StrategiesTypes.FastOperations), accounts=["http://testserver/api/accounts/4/"]), status.HTTP_200_OK)
        self.assertEqual(dict_strategy_fos["strategy"]["name"], "FOS Updated")

        # Get a created StrategiesFastOperations
        dict_strategy_fos=tests_helpers.client_get(self, self.client_authorized_1, dict_strategy_fos["url"], status.HTTP_200_OK)
        self.assertEqual(dict_strategy_fos["strategy"]["name"], "FOS Updated")

        # Creates a strategy empty directly should fail, due to it redirect to StrategiesFastOperations and needs accounts ...
        tests_helpers.client_post(self, self.client_authorized_1, "/api/strategies/",  models.Strategies.post_payload(type=models.StrategiesTypes.FastOperations, name="FOS"), status.HTTP_405_METHOD_NOT_ALLOWED)

        # Update a strategy directly should fail
        tests_helpers.client_put(self, self.client_authorized_1, dict_strategy_fos["strategy"]["url"],  models.Strategies.post_payload(type=models.StrategiesTypes.FastOperations, name="FOS Direct update"), status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # GEt List of strategies
        strategies=tests_helpers.client_get(self, self.client_authorized_1, f"/api/strategies/",  status.HTTP_200_OK)
        self.assertEqual(len(strategies), 1)
        # GEt List of strategies with balance
        strategies=tests_helpers.client_get(self, self.client_authorized_1, f"/api/strategies/withbalance/",  status.HTTP_200_OK)
        self.assertEqual(len(strategies), 1)
        

        # Delete a strategy directly should fail
        tests_helpers.client_delete(self, self.client_authorized_1, dict_strategy_fos["strategy"]["url"], [], status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # Delete a strategy fast operation directly should delete
        after_delete=tests_helpers.client_delete(self, self.client_authorized_1, dict_strategy_fos["url"], [], status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(after_delete), 0)

    def test_StrategiesGeneric(self):
        # Creates an investment operation with a quote and an io
        dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",  models.Investments.post_payload(), status.HTTP_201_CREATED)
        tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(products=dict_investment["products"]), status.HTTP_201_CREATED)

        # Create a Generic strategy
        dict_strategy_generic=tests_helpers.client_post(self, self.client_authorized_1, "/api/strategies_generic/", models.StrategiesGeneric.post_payload(strategy=models.Strategies.post_payload(name="GS", type=models.StrategiesTypes.Generic), investments=[dict_investment["url"]]), status.HTTP_201_CREATED)

        tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(dict_investment["url"]), status.HTTP_201_CREATED)

        # Get FO strategy detailed view
        strategy_detail=tests_helpers.client_get(self, self.client_authorized_1, f"{dict_strategy_generic['url']}detailed/",  status.HTTP_200_OK)
        first_entry=strategy_detail["entries"][0]
        self.assertEqual(strategy_detail[first_entry]["total_io_current"]["balance_user"], 10000)

        #Update fos
        dict_strategy_generic=tests_helpers.client_put(self, self.client_authorized_1, dict_strategy_generic["url"],  models.StrategiesGeneric.post_payload(strategy=models.Strategies.post_payload(name="GS Updated", type=models.StrategiesTypes.Generic), investments=[dict_investment["url"]]), status.HTTP_200_OK)
        self.assertEqual(dict_strategy_generic["strategy"]["name"], "GS Updated")

        # Get a created StrategiesFastOperations
        dict_strategy_generic=tests_helpers.client_get(self, self.client_authorized_1, dict_strategy_generic["url"], status.HTTP_200_OK)
        self.assertEqual(dict_strategy_generic["strategy"]["name"], "GS Updated")

        # Creates a strategy empty directly should fail, due to it redirect to StrategiesFastOperations and needs accounts ...
        tests_helpers.client_post(self, self.client_authorized_1, "/api/strategies/",  models.Strategies.post_payload(type=models.StrategiesTypes.Generic, name="GS"), status.HTTP_405_METHOD_NOT_ALLOWED)

        # Tries to change type and returns error
        tests_helpers.client_put(self, self.client_authorized_1, dict_strategy_generic["url"],  models.StrategiesGeneric.post_payload(strategy=models.Strategies.post_payload(name="GS Updated", type=models.StrategiesTypes.FastOperations), investments=[dict_investment["url"]]), status.HTTP_400_BAD_REQUEST)

        # Update a strategy directly should fail
        tests_helpers.client_put(self, self.client_authorized_1, dict_strategy_generic["strategy"]["url"],  models.Strategies.post_payload(type=models.StrategiesTypes.Generic, name="GS Direct update"), status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # Delete a strategy directly should fail
        tests_helpers.client_delete(self, self.client_authorized_1, dict_strategy_generic["strategy"]["url"], [], status.HTTP_405_METHOD_NOT_ALLOWED)

        # GEt List of strategies
        strategies=tests_helpers.client_get(self, self.client_authorized_1, f"/api/strategies/",  status.HTTP_200_OK)
        # self.assertTrue("strategiesgeneric" in strategies[0])
        # GEt List of strategies with balance
        strategies=tests_helpers.client_get(self, self.client_authorized_1, f"/api/strategies/withbalance/",  status.HTTP_200_OK)
        self.assertEqual(len(strategies), 1)

        # Delete a strategy directly should fail
        tests_helpers.client_delete(self, self.client_authorized_1, dict_strategy_generic["strategy"]["url"], [], status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # Delete a strategy fast operation directly should delete
        after_delete=tests_helpers.client_delete(self, self.client_authorized_1, dict_strategy_generic["url"], [], status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(after_delete), 0)

    def test_StrategiesPairsInSameAccount(self):
        # Create a Pairs strategy with wrong type
        dict_strategy_pairs=tests_helpers.client_post(self, self.client_authorized_1, "/api/strategies_pairsinsameaccount/", models.StrategiesPairsInSameAccount.post_payload(strategy=models.Strategies.post_payload(name="PairS", type=models.StrategiesTypes.Generic)), status.HTTP_400_BAD_REQUEST)

        # Create a Pairs strategy 
        dict_strategy_pairs=tests_helpers.client_post(self, self.client_authorized_1, "/api/strategies_pairsinsameaccount/", models.StrategiesPairsInSameAccount.post_payload(strategy=models.Strategies.post_payload(name="PairS", type=models.StrategiesTypes.PairsInSameAccount)), status.HTTP_201_CREATED)

        # Get FO strategy detailed view
        strategy_detail=tests_helpers.client_get(self, self.client_authorized_1, f"{dict_strategy_pairs['url']}detailed/",  status.HTTP_200_OK)

        #Update fos
        dict_strategy_pairs=tests_helpers.client_put(self, self.client_authorized_1, dict_strategy_pairs["url"],  models.StrategiesPairsInSameAccount.post_payload(strategy=models.Strategies.post_payload(name="GS Updated", type=models.StrategiesTypes.PairsInSameAccount)), status.HTTP_200_OK)
        self.assertEqual(dict_strategy_pairs["strategy"]["name"], "GS Updated")

        # Get a created StrategiesFastOperations
        dict_strategy_pairs=tests_helpers.client_get(self, self.client_authorized_1, dict_strategy_pairs["url"], status.HTTP_200_OK)
        self.assertEqual(dict_strategy_pairs["strategy"]["name"], "GS Updated")

        # Creates a strategy empty directly should fail, due to it redirect to StrategiesFastOperations and needs accounts ...
        tests_helpers.client_post(self, self.client_authorized_1, "/api/strategies/",  models.Strategies.post_payload(type=models.StrategiesTypes.Generic, name="GS"), status.HTTP_405_METHOD_NOT_ALLOWED)

        # Tries to change type and returns error

        tests_helpers.client_put(self, self.client_authorized_1, dict_strategy_pairs["url"],  models.StrategiesPairsInSameAccount.post_payload(strategy=models.Strategies.post_payload(name="GS Updated", type=models.StrategiesTypes.Generic)), status.HTTP_400_BAD_REQUEST)

        # Update a strategy directly should fail
        tests_helpers.client_put(self, self.client_authorized_1, dict_strategy_pairs["strategy"]["url"],  models.Strategies.post_payload(type=models.StrategiesTypes.Generic, name="GS Direct update"), status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # Delete a strategy directly should fail
        tests_helpers.client_delete(self, self.client_authorized_1, dict_strategy_pairs["strategy"]["url"], [], status.HTTP_405_METHOD_NOT_ALLOWED)

        # GEt List of strategies
        strategies=tests_helpers.client_get(self, self.client_authorized_1, f"/api/strategies/",  status.HTTP_200_OK)
        self.assertEqual(len(strategies), 1)
        # GEt List of strategies with balance
        strategies=tests_helpers.client_get(self, self.client_authorized_1, f"/api/strategies/withbalance/",  status.HTTP_200_OK)
        self.assertEqual(len(strategies), 1)

        # Delete a strategy directly should fail
        tests_helpers.client_delete(self, self.client_authorized_1, dict_strategy_pairs["strategy"]["url"], [], status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # Delete a strategy fast operation directly should delete
        after_delete=tests_helpers.client_delete(self, self.client_authorized_1, dict_strategy_pairs["url"], [], status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(after_delete), 0)


    def test_StrategiesProductsRange(self):
        # Creates an investment operation with a quote and an io
        dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",  models.Investments.post_payload(), status.HTTP_201_CREATED)
        tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(products=dict_investment["products"]), status.HTTP_201_CREATED)
        # Create a Pairs strategy with wrong type
        dict_strategy_pr=tests_helpers.client_post(self, self.client_authorized_1, "/api/strategies_productsrange/", models.StrategiesProductsRange.post_payload(strategy=models.Strategies.post_payload(name="PRS", type=models.StrategiesTypes.Generic), investments=[dict_investment["url"]]), status.HTTP_400_BAD_REQUEST)

        # Create a Pairs strategy 
        dict_strategy_pr=tests_helpers.client_post(self, self.client_authorized_1, "/api/strategies_productsrange/", models.StrategiesProductsRange.post_payload(strategy=models.Strategies.post_payload(name="PRS", type=models.StrategiesTypes.Ranges), investments=[dict_investment["url"]]), status.HTTP_201_CREATED)

        # Get FO strategy detailed view
        strategy_detail=tests_helpers.client_get(self, self.client_authorized_1, f"{dict_strategy_pr['url']}detailed/",  status.HTTP_200_OK)

        #Update fos
        dict_strategy_pr=tests_helpers.client_put(self, self.client_authorized_1, dict_strategy_pr["url"],  models.StrategiesProductsRange.post_payload(strategy=models.Strategies.post_payload(name="PRS Updated", type=models.StrategiesTypes.Ranges), investments=[dict_investment["url"]]), status.HTTP_200_OK)
        self.assertEqual(dict_strategy_pr["strategy"]["name"], "PRS Updated")

        # Get a created StrategiesProductsRange
        dict_strategy_pr=tests_helpers.client_get(self, self.client_authorized_1, dict_strategy_pr["url"], status.HTTP_200_OK)
        self.assertEqual(dict_strategy_pr["strategy"]["name"], "PRS Updated")

        # Creates a strategy empty directly should fail, due to it redirect to StrategiesFastOperations and needs accounts ...
        tests_helpers.client_post(self, self.client_authorized_1, "/api/strategies/",  models.Strategies.post_payload(type=models.StrategiesTypes.Ranges, name="PRS"), status.HTTP_405_METHOD_NOT_ALLOWED)

        # Tries to change type and returns error
        tests_helpers.client_put(self, self.client_authorized_1, dict_strategy_pr["url"],  models.StrategiesPairsInSameAccount.post_payload(strategy=models.Strategies.post_payload(name="GS Updated", type=models.StrategiesTypes.Generic)), status.HTTP_400_BAD_REQUEST)

        # Update a strategy directly should fail
        tests_helpers.client_put(self, self.client_authorized_1, dict_strategy_pr["strategy"]["url"],  models.Strategies.post_payload(type=models.StrategiesTypes.Generic, name="GS Direct update"), status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # Delete a strategy directly should fail
        tests_helpers.client_delete(self, self.client_authorized_1, dict_strategy_pr["strategy"]["url"], [], status.HTTP_405_METHOD_NOT_ALLOWED)

        # GEt List of strategies
        strategies=tests_helpers.client_get(self, self.client_authorized_1, f"/api/strategies/",  status.HTTP_200_OK)
        self.assertEqual(len(strategies), 1)

        # GEt List of strategies with balance
        strategies=tests_helpers.client_get(self, self.client_authorized_1, f"/api/strategies/withbalance/",  status.HTTP_200_OK)
        self.assertEqual(len(strategies), 1)

        # Delete a strategy directly should fail
        tests_helpers.client_delete(self, self.client_authorized_1, dict_strategy_pr["strategy"]["url"], [], status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # Delete a strategy fast operation directly should delete
        after_delete=tests_helpers.client_delete(self, self.client_authorized_1, dict_strategy_pr["url"], [], status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(after_delete), 0)
