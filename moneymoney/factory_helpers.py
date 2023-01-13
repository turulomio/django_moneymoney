## THIS IS FILE IS FROM https://github.com/turulomio/django_moneymoney/moneymoney/factory_helpers.py
## IF YOU NEED TO UPDATE IT PLEASE MAKE A PULL REQUEST IN THAT PROJECT AND DOWNLOAD FROM IT
## DO NOT UPDATE IT IN YOUR CODE

from json import loads
from rest_framework import status
from tabulate import tabulate
from . import serializers
from rest_framework.test import APIRequestFactory

def serialize( o, serializer=None):
    f = APIRequestFactory()
    request = f.post('/', {})
    serializer=o.__class__.__name__+"Serializer" if serializer is None else serializer
    return getattr(serializers, serializer)(o, context={'request': request}).data

class MyFactory:
    def __init__(self, factory, type, url):
        self.factory=factory
        self.type=type
        self.url=url
        
    def __str__(self):
        return self.factory.__class__.__name__
            
    #Hyperlinkurl
    def hlu(self, id):
        return f'http://testserver{self.url}{id}/'
        
        
    def test_crud(self, apitestclass, client):
        """
        Function Makes all action operations to factory with client to all examples

        """
        ## factory.create. Creates an object with all dependencies. Si le quito "id" y "url" sería uno nuevo
        o=self.factory.create()
        o.delete()
        o.id=None
        new_payload=serialize(o)
        del new_payload["id"]
        del new_payload["url"]

        r=client.post(self.url, new_payload)
        
        apitestclass.assertEqual(r.status_code, status.HTTP_201_CREATED, f"post method of {self}")
        d=loads(r.content)
        id=d["id"]
        payload=d
        
        
        r=client.put(self.hlu(id), payload)
        apitestclass.assertEqual(r.status_code, status.HTTP_200_OK, f"put method of {self}")
        
        r=client.patch(self.hlu(id), payload)
        apitestclass.assertEqual(r.status_code, status.HTTP_200_OK, f"patch method of {self}")
        
        r=client.get(self.hlu(id))
        apitestclass.assertEqual(r.status_code, status.HTTP_200_OK, f"get method of {self}")
        
        r=client.get(self.url)
        apitestclass.assertEqual(r.status_code, status.HTTP_200_OK, f"list method of {self}")
        
        r=client.delete(self.hlu(id))
        apitestclass.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT, f"delete method of {self}")

factory_types=[
    "PublicCatalog", #Catalog can be listed  and retrieved LR without authentication. CatalogManager permisssión can CUD
    "PrivateCatalog", #Catalog can be listed  and retrieved only with authentication. CatalogManager permisssión can CUD
    "Private", #Table content  is filtered by authenticated user. User can¡t see other users content
    "Colaborative",  # All authenticated user can LR and CUD
    "Public",  # models can be LR for anonymous users
    "Anonymous",  #Anonymous users can LR and CUD
]
            
class FactoriesManager:
    def __init__(self):
        self.arr=[]
        

    ## Method to iterate self.arr iterating object
    def __iter__(self):
        return iter(self.arr)
    def length(self):
        return len(self.arr)
        
    def append(self, o, type, url):
        if type not in factory_types:
            raise ("Factory type is not recognized")
        self.arr.append(MyFactory(o, type, url))
        
    def list(self):
        r=[]
        for mf in self.arr:
            r.append(mf)
        return r
        
    def list_by_type(self, type):
        r=[]
        for mf in self.arr:
            if mf.type==type:
                r.append(mf)
        return r
        


def test_cross_user_data_with_post(apitestclass, client1,  client2,  tm):
    """
        Test to check if a recent post by client 1 is accessed by client2
        
        Returns the content of the post
        
        Serializers must have id field
        
        example:
        test_cross_user_data_with_post(self, client1, client2, "/api/biometrics/", { "datetime": timezone.now(), "weight": 71, "height": 180, "activities": hlu("activities", 0), "weight_wishes": hlu("weightwishes", 0)})
    """

    
    r=client1.post(tm.hlu(), tm.get_examples(0, client1), format="json")    
    apitestclass.assertEqual(r.status_code, status.HTTP_201_CREATED, f"{tm.hlu()}, {r.content}")
    return_=r.content
    testing_id=loads(r.content)["id"]
    
    #other tries to access url
    r=client1.get(tm.hlu(testing_id))
    apitestclass.assertEqual(r.status_code, status.HTTP_200_OK,  f"{tm.hlu()}, {r.content}")
    
    #other tries to access url
    r=client2.get(tm.hlu(testing_id))
    apitestclass.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND, f"{tm.hlu()}, {r.content}. WARNING: Client2 can access Client1 post")
    
    return loads(return_)
    
    

def test_cross_user_data(apitestclass, client1,  client2,  url):
    """
        Test to check if a hyperlinked model url can be accesed by client_belongs and not by client_other
        
        example:
        test_cross_user_data(self, client1, client2, "/api/biometrics/2/"})
    """
   
    #other tries to access url
    r=client1.get(url)
    apitestclass.assertEqual(r.status_code, status.HTTP_200_OK,  url)
    
    #other tries to access url
    r=client2.get(url)
    apitestclass.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND, f"{url}. WARNING: Client2 can access Client1 post")
    
    
def test_only_retrieve_and_list_actions_allowed(apitestclass,  client,  tm, log=False):
    """
    Function Checks api_model can be only accessed fot get and list views

    @param api_model DESCRIPTION
    @type TYPE
    """
    
    if log is True:
        print(f"+  {tm.__name__}. test_only_retrive_and_list_actions_allowed. POST...")
    r=client.post(tm.hlu(), {})
    if log is True:
        print(f"   - {r}")
        print(f"   - {r.content}")
    apitestclass.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN, f"create action of {tm.model_string()}")

    r=client.get(tm.hlu())
    apitestclass.assertEqual(r.status_code, status.HTTP_200_OK, f"list method of {tm.model_string()}")
    r=client.get(tm.hlu_first_fixture())
    apitestclass.assertEqual(r.status_code, status.HTTP_200_OK, f"retrieve method of {tm.model_string()}")
    r=client.put(tm.hlu_first_fixture())
    apitestclass.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN, f"update method of {tm.model_string()}")
    r=client.patch(tm.hlu_first_fixture())
    apitestclass.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN, f"partial_update method of {tm.model_string()}")
    r=client.delete(tm.hlu_first_fixture())
    apitestclass.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN, f"destroy method of {tm.model_string()}")
    

        
    
def test_crud_unauthorized_anonymous(apitestclass, client_anonymous, client_authorized, tm):
    """
    Function Makes all action operations to tm with client to all examples

    @param apitestclass DESCRIPTION
    @type TYPE
    @param client DESCRIPTION
    @type TYPE
    @param tm DESCRIPTION
    @type TYPE
    """
    for i in range(len(tm.examples)):
        r=client_anonymous.post(tm.hlu(), {})
        
        apitestclass.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED, f"post method of {tm.model_string()}")
        
        
        #Authorized client creates for testing purposes
        payload=tm.get_examples(i, client_authorized)
        r=client_authorized.post(tm.hlu(), payload)
        apitestclass.assertEqual(r.status_code, status.HTTP_201_CREATED, f"post method of {tm.model_string()}")
        d=loads(r.content)
        id=d["id"]
        
        r=client_anonymous.put(tm.hlu(id), payload)
        apitestclass.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED, f"put method of {tm.model_string()}")
        
        r=client_anonymous.patch(tm.hlu(id), payload)
        apitestclass.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED, f"patch method of {tm.model_string()}")
        
        
        r=client_anonymous.get(tm.hlu(id))
        apitestclass.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED, f"get method of {tm.model_string()}")
        
        r=client_anonymous.get(tm.hlu())
        apitestclass.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED, f"list method of {tm.model_string()}")
        
        r=client_anonymous.delete(tm.hlu(id))
        apitestclass.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED, f"delete method of {tm.model_string()}")

    
def print_list(client, list_url, limit=10):
    r=client.get(list_url)
    print(f"\nPrinting {limit} rows of {list_url}")
    lod=loads(r.content)[:limit]
    print(tabulate(lod, headers="keys", tablefmt="psql"))
        
