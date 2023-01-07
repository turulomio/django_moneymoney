from django.contrib.auth.models import User
from django.test import tag
#from django.utils import timezone
from json import loads
#from rest_framework import status
from moneymoney import models
from moneymoney.tests_helpers import print_list
from rest_framework.test import APIClient, APITestCase
from django.contrib.auth.models import Group

print_list    
tag

class CtTestCase(APITestCase):
    fixtures=["other.json","products.json"] #Para cargar datos por defecto

    @classmethod
    def setUpClass(cls):
        """
            Only instantiated once
        """
        super().setUpClass()
        
        #cls.tmm=TestModelManager.from_module_with_testmodels("calories_tracker.tests_data")
        
        # User to test api
        cls.user_testing = User(
            email='testing@testing.com',
            first_name='Testing',
            last_name='Testing',
            username='testing',
        )
        cls.user_testing.set_password('testing123')
        cls.user_testing.save()
        
        # User to confront security
        cls.user_other = User(
            email='other@other.com',
            first_name='Other',
            last_name='Other',
            username='other',
        )
        cls.user_other.set_password('other123')
        cls.user_other.save()
        
                
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
        response = client.post('/login/', {'username': cls.user_testing.username, 'password': 'testing123',},format='json')
        result = loads(response.content)
        cls.token_user_testing = result
        
        response = client.post('/login/', {'username': cls.user_other.username, 'password': 'other123',},format='json')
        result = loads(response.content)
        cls.token_user_other = result

        response = client.post('/login/', {'username': cls.user_catalog_manager.username, 'password': 'catalog_manager123',},format='json')
        result = loads(response.content)
        cls.token_user_catalog_manager=result
        
        cls.client_testing=APIClient()
        cls.client_testing.credentials(HTTP_AUTHORIZATION='Token ' + cls.token_user_testing)

        cls.client_other=APIClient()
        cls.client_other.credentials(HTTP_AUTHORIZATION='Token ' + cls.token_user_other)
        
        cls.client_anonymous=APIClient()
        
        cls.client_catalog_manager=APIClient()
        cls.client_catalog_manager.credentials(HTTP_AUTHORIZATION='Token ' + cls.token_user_catalog_manager)
    
    def test_products(self):

        print(User.objects.all())
        print(models.Products.objects.all())
        print_list(self.client_testing, "products")
