from django.contrib.auth.models import User
from django.test import tag
from json import loads
from moneymoney import models
from moneymoney import factory
from moneymoney import factory_helpers 

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
        
        cls.factories_manager=factory_helpers.MyFactoriesManager()
        ##Must be all models urls
        cls.factories_manager.append(factory.AccountsFactory, "Colaborative", "/api/accounts/")
        cls.factories_manager.append(factory.BanksFactory, "Colaborative", "/api/banks/")
        cls.factories_manager.append(factory.LeveragesFactory, "PrivateEditableCatalog", "/api/leverages/")
        
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

        cls.client_authorized_2=APIClient()
        cls.client_authorized_2.credentials(HTTP_AUTHORIZATION='Token ' + cls.token_user_authorized_2)
        
        cls.client_anonymous=APIClient()
        
        cls.client_catalog_manager=APIClient()
        cls.client_catalog_manager.credentials(HTTP_AUTHORIZATION='Token ' + cls.token_user_catalog_manager)
        
        cls.assertTrue(cls, models.Operationstypes.objects.all().count()>0,  "There aren't operationstypes")
        cls.assertTrue(cls, models.Products.objects.all().count()>0, "There aren't products")
        cls.assertTrue(cls, models.Concepts.objects.all().count()>0, "There aren't concepts")


    def test_factory_by_type(self):
        print()
        
        self.factories_manager.find(factory.AccountsFactory).print_batch(3)
        for f in self.factories_manager:
            print("test_factory_by_type", f.type,  f)
            f.test_by_type(self, self.client_authorized_1, self.client_authorized_2, self.client_anonymous, self.client_catalog_manager)
        
    
