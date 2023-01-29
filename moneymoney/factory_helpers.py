## THIS IS FILE IS FROM https://github.com/turulomio/django_moneymoney/moneymoney/factory_helpers.py
## IF YOU NEED TO UPDATE IT PLEASE MAKE A PULL REQUEST IN THAT PROJECT AND DOWNLOAD FROM IT
## DO NOT UPDATE IT IN YOUR CODE

## It's used to autamatize common test classifing them by FACTORY_TYPES
## You'll have to do your own tests

## Some payloads are generated automatically. For complex payloads, you can pass your own function to autmatize this common tests

## Client must have user attribute in instatntiation

from json import loads
from rest_framework import status
from tabulate import tabulate
from . import serializers
from rest_framework.test import APIRequestFactory

FACTORY_TYPES=        [
            "PublicCatalog", #Catalog can be listed  and retrieved LR without authentication. Nobody can CUD
            "PrivateCatalog", #Catalog can be listed  and retrieved only with authentication. Nobody can CUD
            "PublicEditableCatalog", #Catalog can be listed  and retrieved LR without authentication. CatalogManager group can CUD
            "PrivateEditableCatalog", #Catalog can be listed  and retrieved only with authentication. CatalogManagert group can CUD
            "Private", #Table content  is filtered by authenticated user. User can¡t see other users content
            "Colaborative",  # All authenticated user can LR and CUD
            "Public",  # models can be LR for anonymous users
            "Anonymous",  #Anonymous users can LR and CUD
        ]

def serialize( o, serializer=None):
    f = APIRequestFactory()
    request = f.post('/', {})
    serializer=o.__class__.__name__+"Serializer" if serializer is None else serializer
    return getattr(serializers, serializer)(o, context={'request': request}).data

class MyFactory:
    def __init__(self, factory, type, url, post_payload_function=None):
        """
           @param post_payload_function Function that returns a dict that will be used to post_payload
        """
        self.post_payload_external_function=post_payload_function
        self.factory=factory
        self.type=type
        self.url=url
        
    def __str__(self):
        return self.url
        
    def model(self):        
        return self.factory._meta.model
        
    def model_count(self):
        return self.model().objects.count()

    #Hyperlinkurl
    def hlu(self, id):
        return f'http://testserver{self.url}{id}/'

    def post_payload(self, client):
        """
            Returns a dict with the client.post payload
            If post_payload_external_function is defined, returns its value
            Else generates a basic serialize payload
        """
    
        if self.post_payload_external_function is not None:
            return self.post_payload_external_function(client.user)

        ## factory.create. Creates an object with all dependencies. Si le quito "id" y "url" sería uno nuevo
        o=self.factory.create()
        o.delete()
        payload=serialize(o)
        del payload["id"]
        del payload["url"]
        return payload

    def test_by_type(self, apitestclass,  client_authenticated_1, client_authenticated_2, client_anonymous, client_catalog_manager):
        if self.type=="Colaborative":
            self.tests_Collaborative(apitestclass, client_authenticated_1, client_authenticated_2, client_anonymous)
        if self.type=="PrivateEditableCatalog":
            self.tests_PrivateEditableCatalog(apitestclass, client_authenticated_1, client_anonymous, client_catalog_manager)
        if self.type=="Private":
            self.tests_Private(apitestclass, client_authenticated_1, client_authenticated_2, client_anonymous)
        
    ## action can be None, to ignore test or status_code returned
    def common_actions_tests(self, apitestclass,  client,  post=status.HTTP_200_OK, get=status.HTTP_200_OK, list=status.HTTP_200_OK,  put=status.HTTP_200_OK, patch=status.HTTP_200_OK, delete=status.HTTP_200_OK):
#        print(self.post_payload(client))
        r=client.post(self.url, self.post_payload(client),format="json")
#        print(r, r.content)
        apitestclass.assertEqual(r.status_code, post, f"create action of {self}. {r}. {r.content}")

        created_json=loads(r.content)
        try:
            id=created_json["id"]
        except:#User couldn't post any, I look for a id in database  to check the rest of actions, son in automatic test make a first post
            qs=self.model().objects.all()
            if qs.count()>0:
                id=qs[0].id
#                print("Using id ", id)
            else:
                print(r,  r.content, self.url, self.post_payload())
                self.print_model()
                raise ("No objects to get an id,  assigning 1")
                

        r=client.get(self.url)
        apitestclass.assertEqual(r.status_code, list, f"list method of {self.url}")
        r=client.get(self.hlu(id))
        apitestclass.assertEqual(r.status_code, get, f"retrieve method of {self.hlu(id)}")
        r=client.put(self.hlu(id), created_json,format="json")
        apitestclass.assertEqual(r.status_code, put, f"update method of {self.hlu(id)}. {self.hlu(id)}")
        r=client.patch(self.hlu(id), created_json,format="json")
        apitestclass.assertEqual(r.status_code, patch, f"partial_update method of {self.hlu(id)}")
        r=client.delete(self.hlu(id))
        apitestclass.assertEqual(r.status_code, delete, f"destroy method of {self.hlu(id)}")
        
    def print_batch(self, number=3):
        lod=[]
        for i in range(3):
            o=self.factory.create()
            lod.append(serialize(o))
        if len(lod)==0:
            print("No data to print_batch")
        print(tabulate(lod, headers="keys", tablefmt="psql"))

        
    def print_model(self):
        lod=[]
        for o in self.model().objects.all():
            lod.append(serialize(o))
        if len(lod)==0:
            print("No data to print_model")
        print(tabulate(lod, headers="keys", tablefmt="psql"))
        
    def tests_Collaborative(self, apitestclass, client_authenticated_1, client_authenticated_2, client_anonymous):
        """
        Function Makes all action operations to factory with client to all examples

        """
        client_authenticated_1.post(self.url, self.post_payload(client_authenticated_1), format="json") #Always will be one to test anonymous
        
        ### TEST OF CLIENT_AUTHENTICATED_1
        self.common_actions_tests(apitestclass, client_authenticated_1, 
            post=status.HTTP_201_CREATED, 
            get=status.HTTP_200_OK, 
            list=status.HTTP_200_OK, 
            put=status.HTTP_200_OK, 
            patch=status.HTTP_200_OK, 
            delete=status.HTTP_204_NO_CONTENT
        )         
        
        ### TEST OF CLIENT_AUTHENTICATED_2
        self.common_actions_tests(apitestclass, client_authenticated_2, 
            post=status.HTTP_201_CREATED, 
            get=status.HTTP_200_OK, 
            list=status.HTTP_200_OK, 
            put=status.HTTP_200_OK, 
            patch=status.HTTP_200_OK, 
            delete=status.HTTP_204_NO_CONTENT
        )
        
        ### TEST OF CLIENT_ANONYMOUS
        self.common_actions_tests(apitestclass, client_anonymous, 
            post=status.HTTP_401_UNAUTHORIZED, 
            get=status.HTTP_401_UNAUTHORIZED, 
            list=status.HTTP_401_UNAUTHORIZED, 
            put=status.HTTP_401_UNAUTHORIZED, 
            patch=status.HTTP_401_UNAUTHORIZED, 
            delete=status.HTTP_401_UNAUTHORIZED
        )     
        
    def tests_Private(self, apitestclass, client_authenticated_1, client_authenticated_2, client_anonymous):
        """
           Make Private model tests
        """
        client_authenticated_1.post(self.url, self.post_payload(client_authenticated_1), format="json") #Always will be one to test anonymous

        ### TEST OF CLIENT_AUTHENTICATED_1
        self.common_actions_tests(apitestclass, client_authenticated_1, 
            post=status.HTTP_201_CREATED, 
            get=status.HTTP_200_OK, 
            list=status.HTTP_200_OK, 
            put=status.HTTP_200_OK, 
            patch=status.HTTP_200_OK, 
            delete=status.HTTP_204_NO_CONTENT
        )

        # 1 creates and 2 cant get
        r1=client_authenticated_1.post(self.url, self.post_payload(client_authenticated_1), format="json")
        apitestclass.assertEqual(r1.status_code, status.HTTP_201_CREATED, f"{self.url}, {r1.content}")
        r1_id=loads(r1.content)["id"]
    
        r=client_authenticated_2.get(self.hlu(r1_id))
        apitestclass.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND, f"{self.url}, {r.content}. WARNING: Client2 can access Client1 post")

        # 2 creates and 1 cant get
        r2=client_authenticated_2.post(self.url, self.post_payload(client_authenticated_2), format="json")
        apitestclass.assertEqual(r2.status_code, status.HTTP_201_CREATED, f"{self.url}, {r2.content}")
        r2_id=loads(r2.content)["id"]

        r=client_authenticated_1.get(self.hlu(r2_id))
        apitestclass.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND, f"{self.url}, {r.content}. WARNING: Client1 can access Client2 post")
            
        ### TEST OF CLIENT_AUTHENTICATED_2
        self.common_actions_tests(apitestclass, client_authenticated_2, 
            post=status.HTTP_201_CREATED, 
            get=status.HTTP_200_OK, 
            list=status.HTTP_200_OK, 
            put=status.HTTP_200_OK, 
            patch=status.HTTP_200_OK, 
            delete=status.HTTP_204_NO_CONTENT
        )
        
        ### TEST OF CLIENT_ANONYMOUS
        self.common_actions_tests(apitestclass, client_anonymous, 
            post=status.HTTP_401_UNAUTHORIZED, 
            get=status.HTTP_401_UNAUTHORIZED, 
            list=status.HTTP_401_UNAUTHORIZED, 
            put=status.HTTP_401_UNAUTHORIZED, 
            patch=status.HTTP_401_UNAUTHORIZED, 
            delete=status.HTTP_401_UNAUTHORIZED
        )     
        
        
    def tests_PrivateEditableCatalog(self, apitestclass,  client_authenticated_1, client_anonymous, client_catalog_manager):
        """
        Function make all checks to privatecatalogs factories with different clients
        """
        client_authenticated_1.post(self.url, self.post_payload(client_authenticated_1), format="json") #Always will be one to test anonymous
        ### TEST OF CLIENT_AUTHENTICATED_1
        self.common_actions_tests(apitestclass, client_authenticated_1, 
            post=status.HTTP_403_FORBIDDEN, 
            get=status.HTTP_200_OK, 
            list=status.HTTP_200_OK, 
            put=status.HTTP_403_FORBIDDEN, 
            patch=status.HTTP_403_FORBIDDEN, 
            delete=status.HTTP_403_FORBIDDEN
        )            
        ### TEST OF CLIENT_ANONYMOUS
        self.common_actions_tests(apitestclass, client_anonymous, 
            post=status.HTTP_401_UNAUTHORIZED, 
            get=status.HTTP_401_UNAUTHORIZED, 
            list=status.HTTP_401_UNAUTHORIZED, 
            put=status.HTTP_401_UNAUTHORIZED, 
            patch=status.HTTP_401_UNAUTHORIZED, 
            delete=status.HTTP_401_UNAUTHORIZED
        )    
        ### TEST OF CLIENT_CATALOG_MANAGER
        self.common_actions_tests(apitestclass, client_catalog_manager, 
            post=status.HTTP_201_CREATED, 
            get=status.HTTP_200_OK, 
            list=status.HTTP_200_OK, 
            put=status.HTTP_200_OK, 
            patch=status.HTTP_200_OK, 
            delete=status.HTTP_204_NO_CONTENT
        )


            
class MyFactoriesManager:
    def __init__(self):
        self.arr=[]
        
        
    def get_factory_types(self):
        return FACTORY_TYPES
        

    ## Method to iterate self.arr iterating object
    def __iter__(self):
        return iter(self.arr)
    def length(self):
        return len(self.arr)
        
    def append(self, o, type, url,post_payload_function=None):
        if type not in self.get_factory_types():
            raise ("Factory type is not recognized")
        self.arr.append(MyFactory(o, type, url,post_payload_function))
        
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
        
    def find(self, factory):
        """
        Public method Find by factory

        @param factory DESCRIPTION
        @type TYPE
        @return DESCRIPTION
        @rtype TYPE
        """
        for mf in self:
            if mf.factory==factory:
                return mf
        return None


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


