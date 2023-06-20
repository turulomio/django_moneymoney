## THIS IS FILE IS FROM https://github.com/turulomio/reusingcode/python/request_casting.py
## IF YOU NEED TO UPDATE IT PLEASE MAKE A PULL REQUEST IN THAT PROJECT AND DOWNLOAD FROM IT
## DO NOT UPDATE IT IN YOUR CODE
from decimal import Decimal
from .casts import str2bool, string2list_of_integers
from .datetime_functions import string2dtaware, string2date

class RequestCastingError(Exception):
    pass

## Returns a model obect
def RequestGetUrl(request, field, class_,  default=None, select_related=[], prefetch_related=[]):
    """
        If field doesn't exists return default
    """
    if not field in request.GET:
        return default
    return object_from_url(request.GET.get(field), class_)
 
## Returns a model obect
def RequestUrl(request, field, class_,  default=None, select_related=[], prefetch_related=[]):
    if not field in request.data:
        return default
    return  object_from_url(request.data.get(field), class_, select_related, prefetch_related)

## Returns a query_set obect
def RequestListUrl(request, field, class_,  default=None,select_related=[],prefetch_related=[]):
    if not field in request.data:
        return default

    r=queryset_from_list_of_urls(request.data.get(field), class_, select_related, prefetch_related)
    return r

def RequestDate(request, field, default=None):
    if not field in request.data:
        return default

    if request.data.get(field) is None:
        return default

    try:
        return string2date(request.data.get(field))
    except:
        raise RequestCastingError("Error in RequestDate")

def RequestGetDate(request, field, default=None):
    if not field in request.GET:
        return default

    try:
        r = string2date(request.GET.get(field))
    except:
        raise RequestCastingError("Error in RequestGetDate")
    return r


def RequestBool(request, field, default=None):
    if not field in request.data:
        return default

    try:
        return str2bool(str(request.data.get(field)))
    except:
        raise RequestCastingError("Error in RequestBool")

def RequestGetBool(request, field, default=None):
    if not field in request.GET:
        return default

    try:
        return  str2bool(request.GET.get(field))
    except:
        raise RequestCastingError("Error in RequestGetBool")

def RequestGetDecimal(request, field, default=None):
    if not field in request.GET:
        return default

    try:
        return Decimal(request.GET.get(field))
    except:
        raise RequestCastingError("Error in RequestGetDate")

def RequestGetInteger(request, field, default=None):
    if not field in request.GET:
        return default

    try:
        return int(request.GET.get(field))
    except:
        raise RequestCastingError("Error in RequestGetInteger")


def RequestInteger(request, field, default=None):
    if not field in request.data:
        return default

    try:
        return int(request.data.get(field))
    except:
        raise RequestCastingError("Error in RequestInteger")

def RequestGetString(request, field, default=None):
    if not field in request.GET:
        return default

    try:
        return request.GET.get(field, default)
    except:
        raise RequestCastingError("Error in RequestGetDate")


def RequestGetListOfStringIntegers(request, field, default=None, separator=","):    
    if not field in request.GET:
        return default

    try:
        return string2list_of_integers(request.GET.get(field), separator)
    except:
        raise RequestCastingError("Error in RequestGetListOfStringIntegers")

    
    
## Used to get array in this situation calls when investments is an array of integers
    ## To use this methos use axios 
    ##            var headers={...this.myheaders(),params:{investments:this.strategy.investments,otra:"OTTRA"}}
    ##            return axios.get(`${this.$store.state.apiroot}/api/dividends/`, headers)
    ## request.GET returns <QueryDict: {'investments[]': ['428', '447'], 'otra': ['OTRA']}>

def RequestGetListOfIntegers(request, field, default=[]):    
    if not field in request.GET:
        return default

    try:
        r=[]
        items=request.GET.getlist(field, [])
        for i in items:
            r.append(int(i))
        return r
    except:
        raise RequestCastingError("Error in RequestGetListOfIntegers")

def RequestGetListOfStrings(request, field, default=[]):    
    if not field in request.GET:
        return default

    try:
        r=[]
        items=request.GET.getlist(field, [])
        for i in items:
            r.append(str(i))
        return r
    except:
        raise RequestCastingError("Error in RequestGetListOfStrings")

def RequestGetListOfBooleans(request, field, default=[]):    
    if not field in request.GET:
        return default

    try:
        r=[]
        items=request.GET.getlist(field, [])
        for i in items:
            r.append(str2bool(i))
        return r
    except:
        raise RequestCastingError("Error in RequestGetListOfBooleans")

def RequestListOfIntegers(request, field, default=None,  separator=","):
    if not field in request.data:
        return default

    try:
        return string2list_of_integers(str(request.data.get(field))[1:-1], separator)
    except:
        raise RequestCastingError("Error in RequestListOfIntegers")

def RequestGetDtaware(request, field, timezone_string, default=None):
    if not field in request.GET:
        return default

    try:
        return string2dtaware(request.GET.get(field), "JsUtcIso", timezone_string)
    except:
        raise RequestCastingError("Error in RequestGetDtaware")


def RequestDtaware(request, field, timezone_string, default=None):
    if not field in request.data:
        return default

    try:
        return string2dtaware(request.data.get(field), "JsUtcIso", timezone_string)
    except:
        raise RequestCastingError("Error in RequestDtaware")


def RequestDecimal(request, field, default=None):
    if not field in request.data:
        return default

    try:
        return Decimal(request.data.get(field))
    except:
        raise RequestCastingError("Error in RequestDecimal")

def RequestString(request, field, default=None):
    if not field in request.data:
        return default
    try:
        return request.data.get(field)
    except:
        raise RequestCastingError("Error in RequestString")

def ids_from_list_of_urls(list_):
    r=[]
    for url in list_:
        r.append(id_from_url(url))
    return r

def id_from_url(url):
    if url is None:
        return None
    parts=url.split("/")
    return int(parts[len(parts)-2])

def parse_from_url(url):
    """
        Returns a tuple (model_url and id) from a django hyperlinked url
        For example https://localhost/api/products/1/ ==> ('products', 1)
    """
    if url is None:
        return None,None
    try:
        parts=url.split("/")
        return parts[len(parts)-3], int(parts[len(parts)-2])
    except:
        print("Error parsing url", url)
        return None,None


def object_from_url(url, class_, select_related=[], prefetch_related=[], model_url=None):
    """
        By default this method validates that url has the name of the class_ in lowercase as model_url
        For example. Products model should contain /products/ in url and then its id
                     ProductsMine should contain /productsmain/ or /products_main/ or /products-main/
        If your url is not in the ones before, you can use model_url to pass your own url to validate
        If we woudn't validate a param could pass other model with the same id and give wrong results
    """
    if url is None:
        return None
    # Get id and model_url
    if model_url is None:
        model_url, id_=parse_from_url(url)
    else:
        id_=id_from_url(url)

    #Validation
    if id_ is None:
        return None

    if class_.__name__.lower() != model_url.lower().replace("-","").replace("_",""):
        comment=f"url couldn't be validated {url} ==> {class_.__name__} {model_url} {id_}"
        raise RequestCastingError(comment)

    #Get result
    return class_.objects.prefetch_related(*prefetch_related).select_related(*select_related).get(pk=id_from_url(url))

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
