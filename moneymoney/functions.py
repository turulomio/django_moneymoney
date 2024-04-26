from django.db import connection
from django.conf import settings
from django.http.response import JsonResponse
from io import StringIO
from json import loads        
from functools import wraps
from requests import get
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, APIClient
from rest_framework.request import Request


def dictfetchall(cursor):
    """
    Return all rows from a cursor as a dict.
    Assume the column names are unique.
    """
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

##  This method can be used as a function when decorators are not allowed (DRF actions)
def show_queries_function(only_numbers=True):
    sum_=0
    for d in connection.queries:
        if settings.DEBUG is True and only_numbers is False:
            print (f"[{d['time']}] {d['sql']}")
        sum_=sum_+float(d['time'])
    if settings.DEBUG is True:
        print (f"{len(connection.queries)} db queries took {round(sum_*1000,2)} ms")
        
        
def qs_to_ids(qs):
    """
        Returns a list of ids from a qs
    """
    return list(qs.values_list('id', flat=True))
    
def qs_to_urls(request, qs):
    """
        Returns a list of hurls
        Needs to have hurl defined in url
    """
    r=[]
    for o in qs:
        r.append(o.hurl(request, o.id))
    return r

def print_object(o):
    print(o.__class__.__name__)
    # Access the __dict__ attribute to get a dictionary of model fields and values
    for attribute, value in o.__dict__.items():
        if attribute in ["_state"]:
            continue
        print(f"  + {attribute}: {value}")
    print()

def string_oneline_object(o):
    r=f"{o.__class__.__name__} #{o.id} ["
    # Access the __dict__ attribute to get a dictionary of model fields and values
    for attribute, value in o.__dict__.items():
        if attribute in ["_state",  "id"]:
            continue
        r+=str(value)+", "
    return r[:-2]+ "]"

def internal_modelviewset_request(modelviewset, method, params,  params_method, user=None):
    """
        Used to create requests to call views from other views
        Parameters:
            modelviewset: ModelViewSEt Class
            method: String with the method list, ....
            params: dictionary with params key: value
            params_method: Where params should go, GET, data ....
            user: User for authenticated methods
        
    """
    factory=APIRequestFactory()
    request=factory.get('/fakepath/')
    if params_method=="GET":
        new_params=request.GET.copy()
        for k, v in params.items():
            new_params[k]=v
        request.GET=new_params
    
    #Convert to a drf request
    drf_request=Request(request) #Convert to a drf request
    
    #Set user authentication
    if user is not None:
        request.user=user
        drf_request.user=user
    
    #Call viewset
    viewset=modelviewset() #Instanciated
    viewset.request=drf_request
    viewset.format_kwarg=None
    viewset.action=method
    
    #Call method by name
    r=getattr(viewset, method)(drf_request)
    #r=viewset.list(drf_request)
#    print(r, r.__class__)

    if r.__class__==JsonResponse:
        return loads(r.content.decode("utf-8"))
    elif r.__class__==Response:
        return r.json()
    else:
        raise Exception("Error returning in internal_modelviewset_request")


def suppress_stdout(func):
    """Decorator to suppress print statements in the function being decorated."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        import sys
        # Redirect stdout to nowhere
        original_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            return func(*args, **kwargs)
        finally:
            # Restore original stdout
            sys.stdout = original_stdout
    return wrapper


def requests_get(url, request):
    """
        url must be an absolute_uri
    """

    if settings.TESTING:
        client=APIClient()
        client.credentials(HTTP_AUTHORIZATION=request.headers["Authorization"])
        language_headers={"HTTP_ACCEPT_LANGUAGE": request.headers['Accept-Language']}
        return client.get(url, **language_headers)
    else:   
        from django.utils.translation import get_language_from_request
        language = get_language_from_request(request)
        headers={
            'Authorization': f"Token {request.user.auth_token.key}",
            'Accept-Language': f"{language}-{language}",
            'Content-Type':'application/json'
        }    
        return get(url, headers=headers, verify=False)

