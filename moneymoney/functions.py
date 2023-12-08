
from django.db import connection
from moneymoney.exceptions import CanImportUnoException
from unogenerator import can_import_uno

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


def can_import_uno_moneymoney():
        if not can_import_uno(True):
            raise CanImportUnoException("I couldn't import uno  and run this code")
