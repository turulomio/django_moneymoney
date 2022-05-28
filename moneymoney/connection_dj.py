## THIS IS FILE IS FROM https://github.com/turulomio/django_moneymoney/moneymoney/connection_dj.py
## IF YOU NEED TO UPDATE IT PLEASE MAKE A PULL REQUEST IN THAT PROJECT AND DOWNLOAD FROM IT
## DO NOT UPDATE IT IN YOUR CODE

from django.db import connection
from .casts import var2json


def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

def cursor_rows(sql, params=[]):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        row = dictfetchall(cursor)
    return row
    
## Returns a dictionary where key is its key. key must be in db result
def cursor_rows_as_dict(key, sql,  params=[]):
    d={}
    for row in cursor_rows(sql, params):
        d[row[key]]=row
    return d
    
def cursor_one_row(sql, params=[]):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
#        print(cursor.cursor.rowcount)
        if cursor.cursor.rowcount==0:
            return None
        row = dictfetchall(cursor)
    return row[0]

def cursor_one_column(sql, params=[]):
    r=[]
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows=cursor.fetchall()
        for row in rows:
            r.append(row[0])
    return r
        
def cursor_one_field(sql, params=[]):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
    return row[0]

def execute(sql, params=[]):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)

def sql2json(sql,  params=()):    
    r=[]
    for o in cursor_rows(sql, params):
        d={}
        for field in o.keys():
            d[field]=var2json(o[field])
        r.append(d)
    return r