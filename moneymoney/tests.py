from django.contrib.auth.models import User
from django.test import tag
from django.utils import timezone
from json import loads
from moneymoney import models, factory, factory_helpers 
from moneymoney.reusing.connection_dj import cursor_one_row
from moneymoney.types import eOperationType
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from django.contrib.auth.models import Group

tag

class PostPayload:
    """
        Post payload for automatic test with factory_test
    """
    @staticmethod
    def Account(user=None):
        user=User.objects.get(username="testing") if user is None else user
        account=factory.AccountsFactory.create(currency="EUR")
        d=factory_helpers.serialize(account)
        account.delete()
        del d["id"]
        del d["url"]
        return d
    @staticmethod
    def Dividend(user=None):
        user=User.objects.get(username="testing") if user is None else user
        o=factory.DividendsFactory.create()
        d=factory_helpers.serialize(o)
        o.delete()
        del d["id"]
        del d["url"]
        d["accountsoperations"]=None#It has been deleted with o.delete()
        return d
    @staticmethod
    def Investmentsoperations(user=None):
        user=User.objects.get(username="testing") if user is None else user
        o=factory.InvestmentsoperationsFactory.create(investments__accounts__currency="EUR", investments__products__currency="EUR")
        factory.QuotesFactory.create_batch(3, products=o.investments.products)
        d=factory_helpers.serialize(o)
        o.delete()
        del d["id"]
        del d["url"]
        return d

class CtTestCase(APITestCase):
    fixtures=["all.json"] #Para cargar datos por defecto

    @classmethod
    def setUpClass(cls):
        """
            Only instantiated once
        """
        super().setUpClass()
        
        cls.factories_manager=factory_helpers.MyFactoriesManager()
        ##Must be all models urls
        cls.factories_manager.append(factory.AccountsFactory, "Colaborative", "/api/accounts/", PostPayload.Account)
        cls.factories_manager.append(factory.AccountsoperationsionsFactory, "Colaborative", "/api/accountsoperations/")
        cls.factories_manager.append(factory.BanksFactory, "Colaborative", "/api/banks/")
        cls.factories_manager.append(factory.ConceptsFactory, "Colaborative", "/api/concepts/")
        cls.factories_manager.append(factory.CreditcardsFactory, "Colaborative", "/api/creditcards/")
        cls.factories_manager.append(factory.CreditcardsoperationsFactory, "Colaborative", "/api/creditcardsoperations/")
        cls.factories_manager.append(factory.DividendsFactory, "Colaborative", "/api/dividends/", PostPayload.Dividend)
        cls.factories_manager.append(factory.EstimationsDpsFactory, "Colaborative", "/api/estimationsdps/")
        cls.factories_manager.append(factory.InvestmentsFactory, "Colaborative", "/api/investments/")
        cls.factories_manager.append(factory.InvestmentsoperationsFactory, "Colaborative", "/api/investmentsoperations/", PostPayload.Investmentsoperations)
        cls.factories_manager.append(factory.LeveragesFactory, "PrivateEditableCatalog", "/api/leverages/")
        cls.factories_manager.append(factory.OperationstypesFactory, "PrivateEditableCatalog", "/api/operationstypes/")
        #cls.factories_manager.append(factory.ProfileFactory, "Private", "/api/profile/", PostPayload.Profile) #Doesn't work due to profile is created by signal and has duplicity when testing
        #cls.factories_manager.append(factory.ProductsFactory, "PrivateEditableCatalog", "/api/products/", PostPayload.Product) #Doesn't work due to products has id<0 Personal and id>0 System. Too specific for generic tests
        cls.factories_manager.append(factory.ProductstypesFactory, "PrivateEditableCatalog", "/api/productstypes/")
        cls.factories_manager.append(factory.StockmarketsFactory, "PrivateEditableCatalog", "/api/stockmarkets/")
        
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

    def test_factory_by_type(self):
        print()
        for f in self.factories_manager:
            print("test_factory_by_type", f.type,  f)
            f.test_by_type(self, self.client_authorized_1, self.client_authorized_2, self.client_anonymous, self.client_catalog_manager)
            
    def test_investments_operations(self):
        #self.factories_manager.find(factory.InvestmentsFactory).print_batch(3)
        ##Currencies must be the same
        account=factory.AccountsFactory.create(currency="EUR")
        product=factory.ProductsFactory.create(currency="EUR")
        investment=factory.InvestmentsFactory.create(accounts=account, products=product)
#        print(account)
#        print(investment)
#        print(product)
#        print(investment.products)
        for i in range(100):
            quote=factory.QuotesFactory.create(products=product)
#        print(quote)
#        mf_io=factory_helpers.MyFactory(factory.InvestmentsoperationsFactory, "Colaborative", "/api/investmentsoperations/")
#        io_payload=mf_io.post_payload(investments=investment, operationstypes=models.Operationstypes.objects.get(pk=eOperationType.SharesPurchase))
##        print(io_payload)
#        r=self.client_authorized_1.post("/api/investmentsoperations/", io_payload)
##        print(r.content)
#        qs_ao=models.Accountsoperations.objects.all()
##        for ao in qs_ao:
##            print(factory_helpers.serialize(ao))
#            
            
        quote,    investment
        
    
    def test_estimations_dps(self):     
        """
            Checks estimationsdps loginc
        """
        print()
        print("test_estimations_dps")
        mf=factory_helpers.MyFactory(factory.EstimationsDpsFactory, "Colaborative", "/api/estimationsdps/")
        
        #Trying to insert the same year and product twice. I alter date_estimation
        payload=mf.post_payload(self.user_authorized_1)
        self.assertEqual(mf.model_count(), 0)
        self.client_authorized_1.post(mf.url, payload)
        self.assertEqual(mf.model_count(), 1)
        payload["estimation"]="12.3456"
        r=self.client_authorized_1.post(mf.url, payload)
        self.assertEqual(mf.model_count(), 1)
        self.assertEqual(loads(r.content)["estimation"], 12.3456)
    
    def test_accounts(self):
        """
            Checks accounts logic
        """
        mf=self.factories_manager.find(factory.AccountsFactory)
        mfao=self.factories_manager.find(factory.AccountsoperationsionsFactory)
        mfao
        #Checks there is one account
        self.assertEqual(mf.model_count(), 1)
        
        #Create a new account
        r=self.client_authorized_1.post(mf.url, mf.post_payload(self.client_authorized_1))
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        
#        #Create a new account operation
#        r=self.client_authorized_1.post(mfao.url, mfao.post_payload(accounts__currency="EUR", amount=-1492,  comment="CAN YOU FIND ME?", concepts=models.Concepts.objects.get(pk=7), accounts=models.Accounts.objects.get(pk=4)))
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
#        total_balance=cursor_one_row("select * from total_balance(%s,%s)", (timezone.now(), 'EUR'))
#        self.assertEqual(total_balance["total_user"], -1492)
#        
#        # Gets annual reports
#        year=int(ao["datetime"][0:4])
##        month=int(ao["datetime"][5:7])
#        r=self.client_authorized_1.get(f"/reports/annual/{year}/")
#        total=loads(r.content)
#        print(total)
#        r=self.client_authorized_1.get(f"/reports/annual/income/{year}/")
#        total=loads(r.content)
#        print(total)
