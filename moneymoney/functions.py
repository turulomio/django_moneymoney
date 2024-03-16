from django.db import connection

def dictfetchall(cursor):
    """
    Return all rows from a cursor as a dict.
    Assume the column names are unique.
    """
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

##  This method can be used as a function when decorators are not allowed (DRF actions)
def show_queries_function():
    sum_=0
    for d in connection.queries:
        print (f"[{d['time']}] {d['sql']}")
        sum_=sum_+float(d['time'])
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
    
