from django.db import connection
from django.conf import settings
from rest_framework.test import APIRequestFactory
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
    
def lod_remove_duplicates(lod_):
    seen = set()
    unique_dicts = []
    for d in lod_:
        # Convert dictionary to a tuple of its items for hashability
        t = tuple(d.items())
        if t not in seen:
            seen.add(t)
            unique_dicts.append(d)
#    print("Original",  len(lod_),  "Final",  len(unique_dicts))
    return unique_dicts


def internal_modelviewset_request(modelviewset, method, params):
    """
        Used to create requests to call views from other views
    """
    if method=="list":
        factory=APIRequestFactory()
        request=factory.get('/fakepath/')
        params=request.GET.copy()
        for k, v in params.items():
            params[k]=v
        request.GET=params
        drf_request=Request(request) #Convert to a drf request
        
        viewset=modelviewset() #Instanciated
        viewset.request=drf_request
        viewset.format_kwarg=None
        viewset.action=method
        r=viewset.list(drf_request)
#        print(r, r.__class__)
#        from json import dumps
#        return dumps(r.content)

#        if r.__class__=
        from json import loads
        return loads(r.content.decode("utf-8"))
        
        
        
