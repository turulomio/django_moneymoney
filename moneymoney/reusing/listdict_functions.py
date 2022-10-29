## THIS IS FILE IS FROM https://github.com/turulomio/django_moneymoney/moneymoney/listdict_functions.py
## IF YOU NEED TO UPDATE IT PLEASE MAKE A PULL REQUEST IN THAT PROJECT AND DOWNLOAD FROM IT
## DO NOT UPDATE IT IN YOUR CODE

from collections import OrderedDict

## El objetivo es crear un objeto list_dict que se almacenera en self.ld con funciones set
## set_from_db #Todo se carga desde base de datos con el minimo parametro posible
## set_from_db_and_variables #Preguntara a base datos aquellas variables que falten. Aunque no estén en los parámetros p.e. money_convert
## set_from_variables #Solo con variables
## set #El listdict ya está hecho pero se necesita el objeto para operar con el
##class Do:
##    def __init__(self,d):
##        self.d=d
##        self.create_attributes()
##
##    def number_keys(self):
##        return len(self.d)
##
##    def has_key(self,key):
##        return key in self.d
##
##    def print(self):
##        listdict_print(self.d)
##
##    ## Creates an attibute from a key
##    def create_attributes(self):
##        for key, value in self.d.items():
##            setattr(self, key, value)




## Class that return a object to manage listdict
## El objetivo es crear un objeto list_dict que se almacenera en self.ld con funciones set
## set_from_db #Todo se carga desde base de datos con el minimo parametro posible
## set_from_db_and_variables #Preguntara a base datos aquellas variables que falten. Aunque no estén en los parámetros p.e. money_convert
## set_from_variables #Solo con variables
## set #El listdict ya está hecho pero se necesita el objeto para operar con el
class Ldo:
    def __init__(self, name=None):
        self.name=self.__class__.__name__ if name is None else name
        self.ld=[]

    def length(self):
        return len(self.ld)

    def has_key(self,key):
        return listdict_has_key(self.ld,key)

    def print(self):
        listdict_print(self.ld)

    def print_first(self):
        listdict_print_first(self.ld)

    def sum(self, key, ignore_nones=True):
        return listdict_sum(self.ld, key, ignore_nones)

    def list(self, key, sorted=True):
        return listdict2list(self.ld, key, sorted)

    def average_ponderated(self, key_numbers, key_values):
        return listdict_average_ponderated(self.ld, key_numbers, key_values)

    def set(self, ld):
        del self.ld
        self.ld=ld
        return self

    def is_set(self):
        if hasattr(self, "ld"):
            return True
        print(f"You must set your listdict in {self.name}")
        return False

    def append(self,o):
        self.ld.append(o)

    def first(self):
        return self.ld[0] if self.length()>0 else None

    ## Return list keys of the first element[21~
    def first_keys(self):
        if self.length()>0:
            return self.first().keys()
        else:
            return "I can't show keys"
    
    def order_by(self, key, reverse=False):
        self.ld=sorted(self.ld,  key=lambda item: item[key], reverse=reverse)
        
    def json(self):
        return listdict2json(self.ld)

def listdict_has_key(listdict, key):
    if len(listdict)==0:
        return False
    return key in listdict[0]


## Order data columns. None values are set at the beginning
def listdict_order_by(ld, key, reverse=False, none_at_top=True):
    nonull=[]
    null=[]
    for o in ld:
        com=o[key]
        if com is None:
            null.append(o)
        else:
            nonull.append(o)
    nonull=sorted(nonull, key=lambda item: item[key], reverse=reverse)
    if none_at_top==True:#Set None at top of the list
        return null+nonull
    else:
        return nonull+null



def listdict_print(listdict):
    for row in listdict:
        print(row)

def listdict_print_first(listdict):
    if len(listdict)==0:
        print("No rows in listdict")
        return
    print("Printing first dict in a listdict")
    keys=list(listdict[0].keys())
    keys.sort()
    for key in keys:
        print(f"    - {key}: {listdict[0][key]}")

def listdict_sum(listdict, key, ignore_nones=True):
    r=0
    for d in listdict:
        if ignore_nones is True and d[key] is None:
            continue
        r=r+d[key]
    return r




def listdict_sum_negatives(listdict, key):
    r=0
    for d in listdict:
        if d[key] is None or d[key]>0:
            continue
        r=r+d[key]
    return r

def listdict_sum_positives(listdict, key):
    r=0
    for d in listdict:
        if d[key] is None or d[key]<0:
            continue
        r=r+d[key]
    return r


def listdict_average(listdict, key):
    return listdict_sum(listdict,key)/len(listdict)

def listdict_average_ponderated(listdict, key_numbers, key_values):
    prods=0
    for d in listdict:
        prods=prods+d[key_numbers]*d[key_values]
    return prods/listdict_sum(listdict, key_numbers)


def listdict_median(listdict, key):
    from statistics import median
    return median(listdict2list(listdict, key, sorted=True))


## Converts a listdict to a dict using key as new dict key, and value as the key of the value field
def listdict2dictkv(listdict, key, value):
    d={}
    for ld in listdict:
        d[ld[key]]=ld[value]
    return d

## Converts a listdict to a dict using key as new dict key, and the dict as a value
def listdict2dict(listdict, key):
    d={}
    for ld in listdict:
        d[ld[key]]=ld
    return d

## Returns a list from a listdict key
## @param listdict
## @param key String with the key to extract
## @param sorted Boolean. If true sorts final result
## @param cast String. "str", "float", casts the content of the key
def listdict2list(listdict, key, sorted=False, cast=None):
    r=[]
    for ld in listdict:
        if cast is None:
            r.append(ld[key])
        elif cast == "str":
            r.append(str(ld[key]))
        elif cast == "float":
            r.append(float(ld[key]))
    if sorted is True:
        r.sort()
    return r


## Returns a list from a listdict key, with distinct values, not all values
## @param listdict
## @param key String with the key to extract
## @param sorted Boolean. If true sorts final result
## @param cast String. "str", "float", casts the content of the key
def listdict2list_distinct(listdict, key, sorted=False, cast=None):
    set_=set()
    for ld in listdict:
        if cast is None:
            set_.add(ld[key])
        elif cast == "str":
            set_.add(str(ld[key]))
        elif cast == "float":
            set_.add(float(ld[key]))
    r=list(set_)
    if sorted is True:
        r.sort()
    return r



def listdict2json(listdict):
    try:
        from casts import var2json
    except ImportError:
        raise NotImplementedError("You need https://github.com/turulomio/reusingcode/python/casts.py to use this function.")
    
    if len(listdict)==0:
        return "[]"

    r="["
    for o in listdict:
        d={}
        for field in o.keys():
            d[field]=var2json(o[field])
        r=r+str(d).replace("': 'null'", "': null").replace("': 'true'", "': true").replace("': 'false'", "': false") +","
    r=r[:-1]+"]"
    return r

## Returns the max of a key in listdict
def listdict_max(listdict, key):
    return max(listdict2list(listdict,key))

## Returns the min of a key in listdict
def listdict_min(listdict, key):
    return min(listdict2list(listdict,key))

## Converts a list of ordereddict to a list of rows. ONLY DATA
## @params keys If None we must suppose is an ordered dict or keys will be randomized
def listdict2listofrows(lod,  keys=None):
    if len(lod)==0:
        return []
        
    if keys is None:
        keys=lod[0].keys()
        
    r=[]  
    for od in lod:
        row_r=[]
        for key in keys:
            row_r.append(od[key])
        r.append(row_r)
    return r

def listdict2listofordereddicts(ld, keys):
    if len(ld)==0:
        return []
                
    r=[]  
    for d in ld:
        r_d=OrderedDict()
        for key in keys:
            r_d[key]=d[key]
        r.append(r_d)
    return r


## Returns the dictionary that has the max value of a key. Not necessary is unique
def listdict_max(ld, key):
     print("TODO")

## Returns maximum value of a given key. Is unique. REturns NOne if listdict is empty
def listdict_max_value(ld, key):
     if len(ld)>0:
          r=ld[0][key]
     else:
         return None
     for d in ld:
         if  d[key]>r:
             r=d[key]
     return r

## Returns minimum value of a given key. Is unique. REturns NOne if listdict is empty
def listdict_min_value(ld, key):
     if len(ld)>0:
          r=ld[0][key]
     else:
         return None
     for d in ld:
         if  d[key]<r:
             r=d[key]
     return r

## Converts a tipical groyp by lor with year, month, value into an other lor with year, 1, 2, 3 .... 12, total 
def listdict_year_month_value_transposition(ld, key_year="year", key_month="month", key_value="value"):
    if len(ld)==0:
       return []

    if not key_year in ld[0] or not key_month in ld[0] or not key_value in ld[0]:
        print("Keys names are not correct in dictionary in listdict_year_month_value_transposition function")
        return None

    min_year=listdict_min_value(ld, key_year)
    max_year=listdict_max_value(ld, key_year)
    #Initialize result
    r=[]
    for year in range(min_year,max_year+1):
        r.append({"year": year, "m1":0, "m2":0,  "m3":0, "m4":0, "m5":0, "m6":0, "m7":0, "m8":0, "m9":0, "m10":0, "m11":0, "m12":0, "total":0})

    #Assign values
    for d in ld:
        r[d[key_year]-min_year]["m"+str(d[key_month])]=d[key_value]

    #Calculate totals
    for year in range(min_year,max_year+1):
        d=r[year-min_year]
        d["total"]=d["m1"]+d["m2"]+d["m3"]+d["m4"]+d["m5"]+d["m6"]+d["m7"]+d["m8"]+d["m9"]+d["m10"]+d["m11"]+d["m12"]

    return r



if __name__ == "__main__":
    from datetime import datetime, date
    from decimal import Decimal
    ld=[]
    ld.append({"a": datetime.now(), "b": date.today(), "c": Decimal(12.32), "d": None, "e": int(12), "f":None, "g":True, "h":False})

    def print_lor(lor):
        print("")
        for row in lor:
            print(row)
            
    print(listdict2dictkv(ld, "a","b"))
    
    
    
    print ("-- List dict transposition")
    o=[
        {"year": 2022, "month": 1, "my_sum": 12},
        {"year": 2021, "month": 2, "my_sum": 123},
        {"year": 2019, "month": 5, "my_sum": 1},
        {"year": 2022, "month": 12, "my_sum": 12},
    ]
    print(listdict_year_month_value_transposition(o,key_value="my_sum"))