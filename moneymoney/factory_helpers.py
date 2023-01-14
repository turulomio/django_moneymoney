## THIS IS FILE IS FROM https://github.com/turulomio/django_moneymoney/moneymoney/factory_helpers.py
## IF YOU NEED TO UPDATE IT PLEASE MAKE A PULL REQUEST IN THAT PROJECT AND DOWNLOAD FROM IT
## DO NOT UPDATE IT IN YOUR CODE

## This module allows to automatizate tests that has a catalog, authorized users, private tables, public tables
## If you need to addapt this code you can subclass all classes, even types

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
        return self.url
        
    def model(self):        
        return self.factory._meta.model

    #Hyperlinkurl
    def hlu(self, id):
        return f'http://testserver{self.url}{id}/'
        
    def post_payload(self):
        ## factory.create. Creates an object with all dependencies. Si le quito "id" y "url" sería uno nuevo
        o=self.factory.create()
        o.delete()
        o.id=None
        payload=serialize(o)
        del payload["id"]
        del payload["url"]
        return payload
        
    def test_by_type(self, apitestclass,  client_authenticated_1, client_authenticated_2, client_anonymous, client_catalog_manager):
        if self.type=="Colaborative":
            self.tests_Collaborative(apitestclass, client_authenticated_1, client_authenticated_2, client_anonymous)
        if self.type=="PrivateEditableCatalog":
            self.tests_PrivateEditableCatalog(apitestclass, client_authenticated_1, client_anonymous, client_catalog_manager)
        
        
    ## action can be None, to ignore test or status_code returned
    def common_actions_tests(self, apitestclass,  client,  post=status.HTTP_200_OK, get=status.HTTP_200_OK, list=status.HTTP_200_OK,  put=status.HTTP_200_OK, patch=status.HTTP_200_OK, delete=status.HTTP_200_OK):
        r=client.post(self.url, self.post_payload())
        apitestclass.assertEqual(r.status_code, post, f"create action of {self}")

        created_json=loads(r.content)
        try:
            id=created_json["id"]
        except:#User couldn't post any, I look for a id in database  to check the rest of actions
            qs=self.model().objects.all()
            if qs.count()>0:
                id=qs[0].id
            else:
                raise "No objects to get an id"


        r=client.get(self.url)
        apitestclass.assertEqual(r.status_code, list, f"list method of {self.url}")
        r=client.get(self.hlu(id))
        apitestclass.assertEqual(r.status_code, get, f"retrieve method of {self.hlu(id)}")
        r=client.put(self.hlu(id), created_json)
        apitestclass.assertEqual(r.status_code, put, f"update method of {self.hlu(id)}. {self.hlu(id)}")
        r=client.patch(self.hlu(id), created_json)
        apitestclass.assertEqual(r.status_code, patch, f"partial_update method of {self.hlu(id)}")
        r=client.delete(self.hlu(id))
        apitestclass.assertEqual(r.status_code, delete, f"destroy method of {self.hlu(id)}")
        
    def print_batch(self, number=3):
        lod=[]
        for i in range(3):
            o=self.factory.create()
            lod.append(serialize(o))
        print(tabulate(lod, headers="keys", tablefmt="psql"))
        
    def tests_Collaborative(self, apitestclass, client_authenticated_1, client_authenticated_2, client_anonymous):
        """
        Function Makes all action operations to factory with client to all examples

        """
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
        
        
    def tests_PrivateEditableCatalog(self, apitestclass,  client_authenticated_1, client_anonymous, client_catalog_manager):
        """
        Function make all checks to privatecatalogs factories with different clients
        """
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
        return [
            "PublicCatalog", #Catalog can be listed  and retrieved LR without authentication. Nobody can CUD
            "PrivateCatalog", #Catalog can be listed  and retrieved only with authentication. Nobody can CUD
            "PublicEditableCatalog", #Catalog can be listed  and retrieved LR without authentication. CatalogManager group can CUD
            "PrivateEditableCatalog", #Catalog can be listed  and retrieved only with authentication. CatalogManagert group can CUD
            "Private", #Table content  is filtered by authenticated user. User can¡t see other users content
            "Colaborative",  # All authenticated user can LR and CUD
            "Public",  # models can be LR for anonymous users
            "Anonymous",  #Anonymous users can LR and CUD
        ]
        

    ## Method to iterate self.arr iterating object
    def __iter__(self):
        return iter(self.arr)
    def length(self):
        return len(self.arr)
        
    def append(self, o, type, url):
        if type not in self.get_factory_types():
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


