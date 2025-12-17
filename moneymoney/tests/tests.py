from datetime import date, datetime, timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction, connection
from asgiref.sync import sync_to_async
from django.test import tag
from functools import wraps
from json import loads
from logging import getLogger, ERROR
from moneymoney import models, ios, investing_com, functions, types
from moneymoney.reusing import tests_helpers
from pydicts import lod, casts, dod
from request_casting.request_casting import id_from_url
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from django.utils import timezone
from django.contrib.auth.models import Group



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

    def test_have_different_sign(self):
        assert functions.have_different_sign(1, 1)==False
        assert functions.have_different_sign(1, -1)==True
        assert functions.have_different_sign(-1, 1)==True
        assert functions.have_different_sign(-1, -1)==False
        assert functions.have_different_sign(0, 1)==True
        assert functions.have_different_sign(-1, 0)==True
        assert functions.have_different_sign(0, 0)==True        

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
   
    def test_Investmentsoperations(self):
        # Create investments
        inv=models.Investments()
        inv.name="Investment to test investments operations"
        inv.active=True
        inv.accounts_id=4
        inv.products_id=81718 #Index
        inv.selling_price=0
        inv.daily_adjustment=False
        inv.balance_percentage=100
        inv.full_clean()
        inv.save()

        # Create investment operation
        io=models.Investmentsoperations()
        io.datetime=timezone.now()
        io.operationstypes_id=types.eOperationType.SharesPurchase
        io.investments=inv
        io.price=10
        io.shares=100
        io.commission=1
        io.taxes=1
        io.currency_conversion=1
        io.comment="Testing"
        with self.assertRaises(ValidationError) as cm:
            io.full_clean()
        self.assertEqual("Investment operation can't be created because its related product hasn't quotes.", cm.exception.message_dict['__all__'][0])

        #Adds a quote
        models.Quotes.objects.create(products_id=inv.products_id, datetime=casts.dtaware_now(),quote=10)

        # Creates now investment wich product has a quoite
        io.full_clean()
        io.save()

        # Check associated_ao exists
        self.assertEqual(io.associated_ao.amount, -1002)

        # Now i change operations type to AddShares
        io.operationstypes_id=types.eOperationType.SharesAdd
        io.full_clean()
        io.save()
        self.assertEqual(io.associated_ao.amount, -2)

        #Now I remove commissions and taxes
        io.commission=0
        io.taxes=0
        io.full_clean()
        io.save()
        self.assertEqual(io.associated_ao, None)

    def test_Investmentstransfers(self):
        # Add needed quotes for this test
        models.Quotes.objects.create(products_id=81718, datetime=casts.dtaware_now(),quote=10)
        models.Quotes.objects.create(products_id=81719, datetime=casts.dtaware_now(),quote=10)


        # Create investments
        origin=models.Investments()
        origin.name="Investment origin"
        origin.active=True
        origin.accounts_id=4
        origin.products_id=79329 #Index
        origin.selling_price=0
        origin.daily_adjustment=False
        origin.balance_percentage=100
        origin.full_clean()
        origin.save()


        destiny=models.Investments()
        destiny.name="Investment destiny"
        destiny.active=True
        destiny.accounts_id=4
        destiny.products_id=81718 #Fund
        destiny.selling_price=0
        destiny.daily_adjustment=False
        destiny.balance_percentage=100
        destiny.full_clean()
        destiny.save()

        # Create investment transfer
        it=models.Investmentstransfers()
        it.datetime_origin=timezone.now()
        it.investments_origin=origin
        it.shares_origin=100
        it.price_origin=10
        it.datetime_destiny=timezone.now()
        it.investments_destiny=destiny
        it.shares_destiny=1000
        it.price_destiny=1
        it.comment="Test investment transfer"

        #Fails due to the ValidationError
        with self.assertRaises(ValidationError) as cm:
            it.full_clean()
        self.assertEqual("Investment transfer can't be created if products types are not the same", cm.exception.message_dict['__all__'][0])

        # Tries to transfer to same origin and destiny
        it.investments_origin=destiny
        with self.assertRaises(ValidationError) as cm:
            it.full_clean()
        self.assertEqual("Investment transfer can't be created if investments are the same", cm.exception.message_dict['__all__'][0])

        # Tries to transfer with origin shares and destiny shares with the same sign
        it.investments_origin=origin# To avoid upper error
        origin.products_id=81719 # Now both are funds and different investments
        origin.full_clean()
        origin.save()
        with self.assertRaises(ValidationError) as cm:
            it.full_clean()
        self.assertEqual("Shares amount can't be of the same sign", cm.exception.message_dict['__all__'][0])

        
        it.shares_origin=-100 # To avoid upper error
        it.full_clean()
        it.save()

        # Checks investments operations
        io_origin=models.Investmentsoperations.objects.get(associated_it=it, operationstypes_id=types.eOperationType.TransferSharesOrigin)
        io_destiny=models.Investmentsoperations.objects.get(associated_it=it, operationstypes_id=types.eOperationType.TransferSharesDestiny)



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
        o.amount=-1000
        o.datetime=timezone.now()
        o.concepts_id=types.eConcept.BankCommissions
        o.save()

        #Creates 2 refunds
        refund=o.create_refund(timezone.now(), 10, "")
        refund=o.create_refund(timezone.now(), 20, "")

        self.assertEqual(len(o.refunds.all()), 2)
        self.assertEqual(refund.refund_original, o)



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

# class API(APITestCase):
#     fixtures=["all.json"] #Para cargar datos por defecto

#     @classmethod
#     def setUpClass(cls):
#         """
#             Only instantiated once
#         """
#         super().setUpClass()


#         # Store original logging level and set it higher to suppress warnings
#         logger = getLogger('django.request')
#         logger.setLevel(ERROR) # This will suppress INFO and WARNING

        
#         # User to test api
#         cls.user_authorized_1 = User(
#             email='testing@testing.com',
#             first_name='Testing',
#             last_name='Testing',
#             username='testing',
#         )
#         cls.user_authorized_1.set_password('testing123')
#         cls.user_authorized_1.save()
        
#         # User to confront security
#         cls.user_authorized_2 = User(
#             email='other@other.com',
#             first_name='Other',
#             last_name='Other',
#             username='other',
#         )
#         cls.user_authorized_2.set_password('other123')
#         cls.user_authorized_2.save()
        
                
#         # User to test api
#         cls.user_catalog_manager = User(
#             email='catalog_manager@catalog_manager.com',
#             first_name='Catalog',
#             last_name='Manager',
#             username='catalog_manager',
#         )
#         cls.user_catalog_manager.set_password('catalog_manager123')
#         cls.user_catalog_manager.save()
#         cls.user_catalog_manager.groups.add(Group.objects.get(name='CatalogManager'))

#         client = APIClient()
#         response = client.post('/login/', {'username': cls.user_authorized_1.username, 'password': 'testing123',},format='json')
#         result = loads(response.content)
#         cls.token_user_authorized_1 = result
        
#         response = client.post('/login/', {'username': cls.user_authorized_2.username, 'password': 'other123',},format='json')
#         result = loads(response.content)
#         cls.token_user_authorized_2 = result

#         response = client.post('/login/', {'username': cls.user_catalog_manager.username, 'password': 'catalog_manager123',},format='json')
#         result = loads(response.content)
#         cls.token_user_catalog_manager=result
        
#         cls.client_authorized_1=APIClient()
#         cls.client_authorized_1.credentials(HTTP_AUTHORIZATION='Token ' + cls.token_user_authorized_1)
#         cls.client_authorized_1.user=cls.user_authorized_1

#         cls.client_authorized_2=APIClient()
#         cls.client_authorized_2.credentials(HTTP_AUTHORIZATION='Token ' + cls.token_user_authorized_2)
#         cls.client_authorized_2.user=cls.user_authorized_2
        
#         cls.client_anonymous=APIClient()
#         cls.client_anonymous.user=None
        
#         cls.client_catalog_manager=APIClient()
#         cls.client_catalog_manager.credentials(HTTP_AUTHORIZATION='Token ' + cls.token_user_catalog_manager)
#         cls.client_catalog_manager.user=cls.user_catalog_manager
        
#         cls.assertTrue(cls, models.Operationstypes.objects.all().count()>0,  "There aren't operationstypes")
#         cls.assertTrue(cls, models.Products.objects.all().count()>0, "There aren't products")
#         cls.assertTrue(cls, models.Concepts.objects.all().count()>0, "There aren't concepts")
        
#         cls.bank=models.Banks.objects.create(name="Fixture bank", active=True)
#         cls.account=models.Accounts.objects.create(name="Fixture account", active=True, banks=cls.bank, currency="EUR", decimals=2)
#         cls.product=models.Products.objects.get(id=79228)
        
#         cls.now=timezone.now()
