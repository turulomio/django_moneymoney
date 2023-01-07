from decimal import Decimal
from django.core.management import call_command
from django.db import connection
from django.urls import reverse
from django.utils import timezone
from inspect import getmembers, isclass
from io import StringIO
from json import loads
from re import sub
from rest_framework import status
from sys import modules
from tabulate import tabulate

class TestModel:
    """
        Object to help easy test generations
    """
    catalog=False ## Readonly for users
    private=True ## Not visible between users
    example=[]
    first_fixture_id=1#First id in model with fixture
    
    def __repr__ (cls):
        return cls.model_string()
    def __str__ (cls):
        return cls.model_string()
    
    @classmethod
    def url_model_name(cls):
        """
            test_model
        """
        return sub('(?!^)([A-Z]+)', r'_\1', cls.model_string()).lower()
        
        
        
    @classmethod
    def create(cls, index, client):
        """
            returns dict creation
        """
        r=client.post(cls.hlu(), cls.get_examples(0, client)) #Linka al primer recipe. Debería crear todo nuevo recursivo, pero parece funciona
        #print("Creado", cls.model_string(),  r.content)
        return loads(r.content)
        
    @classmethod
    def get_examples(cls, index, client):
        if index+1>len(cls.examples):
            print(cls.model_string(),"No existen examples")
            r= {}
        else:
            r={}#Se crea uno nuevo porque modificamos y sino modificariamos la class
            for k, v in cls.examples[index].items():
                if  isclass(v) and issubclass(v, TestModel):#Creates a new item a set value its hlu
                    d=v.create(0, client)
                    r[k]=v.hlu(d["id"])
                else:
                    r[k]=v           
        return r
        
    @classmethod
    def model_string(cls):
        """
            TestModel
        """
        return cls.__name__[2:]
    
    @classmethod
    def hlu(cls, id=None):
        hlu_base=f"http://testserver/api/{cls.url_model_name()}/"
        if id is None:
            return hlu_base
        return f"{hlu_base}{id}/"
        
        
    @classmethod
    def hlu_first_fixture(cls):
        return cls.hlu(cls.first_fixture_id)
        
def td_string():
    return "afdfa"
    
def td_integer():
    return 1
    
def td_decimal():
    return Decimal("12.212")
    
def td_timezone():
    return timezone.now()
    
            
class TestModelManager:
    def __init__(self):
        self.arr=[]
        
    ## Method to iterate self.arr iterating object
    def __iter__(self):
        return iter(self.arr)

    def catalogs(self):
        r=self.__class__()
        for tm in self.arr:
            if tm.catalog is True:
                r.append(tm)
        return r
    def not_catalogs(self):
        r=self.__class__()
        for tm in self.arr:
            if tm.catalog is False:
                r.append(tm)
        return r
    def private(self):
        r=self.__class__()
        for tm in self.arr:
            if tm.private is True:
                r.append(tm)
        return r
        
    def append(self, o):
        self.arr.append(o)
        
    @classmethod
    def from_module_with_testmodels(cls, module_name):
        """
        Class method Carga tmModels desde test_data.py

        @param module_name DESCRIPTION
        @type TYPE
        @return DESCRIPTION
        @rtype TYPE
        """
        r=cls()
        for name, obj in getmembers(modules[module_name]):
            if isclass(obj):
                if issubclass(obj, TestModel) and obj.__name__!="TestModel":
                    r.append(obj)
        
        print (len(r.arr), "TestModel classes found")
        return r


#Hyperlinkurl
def hlu(name, id):
    return 'http://testserver' + reverse(name+'-detail', kwargs={'pk': id})

## ESTE COMANDO FALLA EN TESTCASE DEBIDO AL ROLLBACK DE CADA CLASE Y NO PERMITE
## CREAR DOS METODOS EN CADA TESTCASE NI PONIENDOLO EN SETUPDATA
## NO PERMITE USAR EXECUTE
## EN UPDATE DATA INTENTO HACER TRICK PARA PONER SEQUENCES A PUNTO
def call_command_sqlsequencerreset(appname):
    """
        Execute python manager sqlsequencereset
    """
    output=StringIO()
    call_command("sqlsequencereset", appname, stdout=output, no_color=True)
    sql = output.getvalue()
    with connection.cursor() as cursor:
        cursor.execute(sql)

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
    
    
def test_only_retrieve_and_list_actions_allowed(apitestclass,  client,  tm):
    """
    Function Checks api_model can be only accessed fot get and list views

    @param api_model DESCRIPTION
    @type TYPE
    """

    r=client.post(tm.hlu(), {})
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
    
def test_crud(apitestclass, client, tm):
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
        payload=tm.get_examples(i, client)
#        print(tm.__name__,"PAYLOAD", payload)

        r=client.post(tm.hlu(), payload)
        
        apitestclass.assertEqual(r.status_code, status.HTTP_201_CREATED, f"post method of {tm.model_string()}")
        d=loads(r.content)
        id=d["id"]
        
        r=client.put(tm.hlu(id), payload)
        apitestclass.assertEqual(r.status_code, status.HTTP_200_OK, f"put method of {tm.model_string()}")
        
        r=client.patch(tm.hlu(id), payload)
        apitestclass.assertEqual(r.status_code, status.HTTP_200_OK, f"patch method of {tm.model_string()}")
        
        
        r=client.get(tm.hlu(id))
        apitestclass.assertEqual(r.status_code, status.HTTP_200_OK, f"get method of {tm.model_string()}")
        
        r=client.get(tm.hlu())
        apitestclass.assertEqual(r.status_code, status.HTTP_200_OK, f"list method of {tm.model_string()}")
        
        r=client.delete(tm.hlu(id))
        apitestclass.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT, f"delete method of {tm.model_string()}")
        
    
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
        
