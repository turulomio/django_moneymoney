from django.contrib.auth.models import User
from django.test import tag
from django.utils import timezone
from json import loads
from moneymoney import models, ios
#from moneymoney.reusing.connection_dj import cursor_one_row
from moneymoney.reusing import tests_helpers
#from moneymoney.types import eOperationType
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


    def test_profile(self):
        """
            Test created users has its profile automatically generated
        """
        print()
        print("test_profile")
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
#        self.assertTrue(models.Accountsoperations.objects.filter(comment=f"10000,{loads(r.content)['id']}").exists())
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
    @tag("current")
    def test_IOS(self):
        print()
        print("test_IOS")
        
        #IOS.from_ids
        dict_account=tests_helpers.client_get(self, self.client_authorized_1, "/api/accounts/4/", status.HTTP_200_OK)
        dict_product=tests_helpers.client_get(self, self.client_authorized_1, "/api/products/79329/", status.HTTP_200_OK)
        tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(product=dict_product["url"], quote=10), status.HTTP_201_CREATED)
        dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(dict_account["url"], dict_product["url"]), status.HTTP_201_CREATED)
        tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(dict_investment["url"]), status.HTTP_201_CREATED)#Al actualizar ao asociada ejecuta otro plio
        ios_=ios.IOS.from_ids( timezone.now(),  'EUR',  [dict_investment["id"]],  1)
        self.assertEqual(ios_.d_total_io_current(1)["balance_user"], 10000)
        tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(dict_investment["url"], shares=-1), status.HTTP_201_CREATED) #Removes one share
        ios_=ios.IOS.from_ids( timezone.now(),  'EUR',  [dict_investment["id"]],  1) #Recaulculates IOS
        self.assertEqual(ios_.d_total_io_current(1)["balance_user"], 9990)

        
    
