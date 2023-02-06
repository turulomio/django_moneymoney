from decimal import Decimal
from .casts import str2bool, string2list_of_integers
from .datetime_functions import string2dtaware, string2date
from urllib import parse

## Returns a model obect
def RequestGetUrl(request, field, class_,  default=None):
    try:
        r = object_from_url(request.GET.get(field), class_)
    except:
        r=default
    return r
 
## Returns a model obect
def RequestUrl(request, field, class_,  default=None, select_related=[], prefetch_related=[]):
#    try:
        r = object_from_url(request.data.get(field), class_, select_related, prefetch_related)
#    except:
#        r=default
        return r 

## Returns a query_set obect
def RequestListUrl(request, field, class_,  default=None,select_related=[],prefetch_related=[]):
    try:
       r=queryset_from_list_of_urls(request.data.get(field), class_, select_related, prefetch_related)
    except:
        r=default
    return r

def RequestDate(request, field, default=None):
    try:
        r = string2date(request.data.get(field))
    except:
        r=default
    return r

def RequestGetDate(request, field, default=None):
    try:
        r = string2date(request.GET.get(field))
    except:
        r=default
    return r


def RequestBool(request, field, default=None):
    try:
        r = str2bool(str(request.data.get(field)))
    except:
        r=default
    return r        
def RequestGetBool(request, field, default=None):
    try:
        r = str2bool(request.GET.get(field))
    except:
        r=default
    return r

def RequestGetDecimal(request, field, default=None):
    try:
        r = Decimal(request.GET.get(field))
    except:
        r=default
    return r

def RequestGetInteger(request, field, default=None):
    try:
        r = int(request.GET.get(field))
    except:
        r=default
    return r
def RequestInteger(request, field, default=None):
    try:
        r = int(request.data.get(field))
    except:
        r=default
    return r
    
def RequestGetString(request, field, default=None):
    try:
        r = request.GET.get(field, default)
    except:
        r=default
    return r

def RequestGetListOfStringIntegers(request, field, default=None, separator=","):    
    try:
        r = string2list_of_integers(request.GET.get(field), separator)
    except:
        r=default
    return r
    
    
## Used to get array in this situation calls when investments is an array of integers
    ## To use this methos use axios 
    ##            var headers={...this.myheaders(),params:{investments:this.strategy.investments,otra:"OTTRA"}}
    ##            return axios.get(`${this.$store.state.apiroot}/api/dividends/`, headers)
    ## request.GET returns <QueryDict: {'investments[]': ['428', '447'], 'otra': ['OTRA']}>

def RequestGetListOfIntegers(request, field, default=[]):    
    try:
        r=[]
        items=request.GET.getlist(field, [])
        for i in items:
            r.append(int(i))
    except:
        r=default
    return r

def RequestGetListOfStrings(request, field, default=[]):    
    try:
        r=[]
        items=request.GET.getlist(field, [])
        for i in items:
            r.append(str(i))
    except:
        r=default
    return r

def RequestGetListOfBooleans(request, field, default=[]):    
    try:
        r=[]
        items=request.GET.getlist(field, [])
        for i in items:
            r.append(str2bool(i))
    except:
        r=default
    return r

def RequestListOfIntegers(request, field, default=None,  separator=","):
    try:
        r = string2list_of_integers(str(request.data.get(field))[1:-1], separator)
    except:
        r=default
    return r

def RequestGetDtaware(request, field, default=None):
    try:
        r = string2dtaware(request.GET.get(field), "JsUtcIso", request.local_zone)
    except:
        r=default
    return r

def RequestDtaware(request, field, timezone_string, default=None):
    try:
        r = string2dtaware(request.data.get(field), "JsUtcIso", timezone_string)
    except:
        r=default
    return r

def RequestDecimal(request, field, default=None):
    try:
        r = Decimal(request.data.get(field))
    except:
        r=default
    return r
def RequestString(request, field, default=None):
    try:
        r = request.data.get(field)        
    except:
        r=default
    return r

def id_from_url(url):
    if url is None:
        return None
    parts=url.split("/")
    return int(parts[len(parts)-2])


def ids_from_list_of_urls(list_):
    r=[]
    for url in list_:
        r.append(id_from_url(url))
    return r

def object_from_url(url, class_, select_related=[], prefetch_related=[]):
    id_=id_from_url(url)
    if id_ is None:
        return None
    else:
        try:
            return class_.objects.prefetch_related(*prefetch_related).select_related(*select_related).get(pk=id_from_url(url))
        except e:
            print (e)

def queryset_from_list_of_urls(list_, class_, select_related=[], prefetch_related=[]):
    ids=ids_from_list_of_urls(list_)
    return class_.objects.filter(pk__in=ids).prefetch_related(*prefetch_related).select_related(*select_related)

## Returns false if some arg is None
def all_args_are_not_none(*args):
    for arg in args:
        if arg is None:
            return False
    return True

## Returns false if some args is None or ""
def all_args_are_not_empty(*args):
    for arg in args:
        if arg is None or arg=="":
            return False
    return True
