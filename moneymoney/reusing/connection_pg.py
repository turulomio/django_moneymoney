## THIS IS FILE IS FROM https://github.com/turulomio/reusingcode/python/connection_pg.py
## IF YOU NEED TO UPDATE IT PLEASE MAKE A PULL REQUEST IN THAT PROJECT AND DOWNLOAD FROM IT
## DO NOT UPDATE IT IN YOUR CODE

from datetime import datetime
from logging import debug
from psycopg2 import OperationalError
from psycopg2.extras import DictConnection

class Connection:
    def __init__(self):
        self.user=None
        self.password=None
        self.server=None
        self.port=None
        self.db=None
        self._con=None
        self.init=None
        self.last_sql=""

    def init__create(self, user, password, server, port, db):
        self.user=user
        self.password=password
        self.server=server
        self.port=port
        self.db=db
        return self

    def cursor(self):
        return self._con.cursor()

    def mogrify(self, sql, arr):
        cur=self._con.cursor()
        s=cur.mogrify(sql, arr)
        cur.close()
        self.last_sql=s
        return  s

    ## Sometimes it's needed to work with sql after converting %s as a string.
    ## There is a problem with '%' when is used in a field and I use sql_insert returning a string
    ## So I need to keep both parameters (sql, arr) and mogrify converts them correctly
    def sql_string(self, sql, arr):
        try:
            from moneymoney.casts import b2s
        except ImportError:
            raise NotImplementedError("You need https://github.com/turulomio/django_moneymoney/moneymoney/casts.py to use this function.")
        return b2s(self.mogrify(sql,arr))

    def setAutocommit(self, b):
        self._con.autocommit = b

    ## Used to execute an sql command without returning anything
    def execute(self, sql, arr=[]):
        cur=self._con.cursor()
        s=self.mogrify(sql,arr)
        cur.execute(s)
        cur.close()

    def cursor_one_row(self, sql, arr=[]):
        cur=self._con.cursor()
        s=self.mogrify(sql,arr)
        cur.execute(s)
        if cur.rowcount==0:
            cur.close()
            return None
        elif cur.rowcount==1:
            row=cur.fetchone()
            cur.close()
            return row
        else:
            cur.close()
            debug("More than one row is returned in cursor_one_row. Use cursor_rows instead.")
            return None

    def cursor_rows(self, sql, arr=[]):
        cur=self._con.cursor()
        s=self.mogrify(sql,arr)
        cur.execute(s)
        rows=cur.fetchall()
        cur.close()
        return rows

    def load_script(self, file):
        cur= self._con.cursor()
        f = open(file,'r', encoding='utf-8')
        procedures=f.read()
        self.last_sql=procedures
        cur.execute(procedures)
        cur.close()
        f.close()

    def cursor_one_column(self, sql, arr=[]):
        """Returns un array with the results of the column"""
        cur=self._con.cursor()
        s=self.mogrify(sql,arr)
        cur.execute(s)
        for row in cur:
            arr.append(row[0])
        cur.close()
        return arr

    def cursor_one_field(self, sql, arr=[]):
        """Returns only one field"""
        cur=self._con.cursor()
        s=self.mogrify(sql,arr)
        cur.execute(s)
        if cur.rowcount==0:
            return None
        row=cur.fetchone()[0]
        cur.close()
        return row

    def commit(self):
        self._con.commit()

    def rollback(self):
        self._con.rollback()

    def connection_string(self):
        return "dbname='{}' port='{}' user='{}' host='{}' password='{}'".format(self.db, self.port, self.user, self.server, self.password)

    ## Returns an url of the type psql://
    def url_string(self):
        return "psql://{}@{}:{}/{}".format(self.user, self.server, self.port, self.db)


    ## @param connection_string string. If None automatic connection_string is generated from attributes
    ## @return boolean True if connection was made
    def connect(self, connection_string=None):
        if connection_string==None:
            s=self.connection_string()
        else:
            s=connection_string
        try:
            self._con=DictConnection(s)
            self.init=datetime.now()
            self._active=True
            return True
        except OperationalError as e:
            self._active=False
            print('Unable to connect: {}'.format(e))
            print('Connection string used: {}'.format(s))
            return False

    def disconnect(self):
        if self.is_active()==True:
            self._con.close()
            self._active=False

    ##Returns if connection is active
    def is_active(self):
        return self._active

    def is_superuser(self):
        """Checks if the user has superuser role"""
        res=False
        cur=self.cursor()
        cur.execute("SELECT rolsuper FROM pg_roles where rolname=%s;", (self.user, ))
        if cur.rowcount==1:
            if cur.fetchone()[0]==True:
                res=True
        cur.close()
        return res

    ## Function to get password user PGPASSWORD environment or ask in console for it
    def get_password(self,  gettext_module=None, gettex_locale=None):
        try:
            import gettext
            t=gettext.translation(gettext_module,  gettex_locale)
            _=t.gettext
        except:
            _=str

        from os import environ
        from getpass import getpass
        try:
            self.password=environ['PGPASSWORD']
        except:
            print(_("Write the password for {}").format(self.url_string()))
            self.password=getpass()
        return self.password

    def unogenerator_values_in_sheet(self,doc, coord_start, sql, params=[], columns_header=0, color_row_header=0xffdca8, color_column_header=0xc0FFc0, color=0xFFFFFF, styles=None):
        from unogenerator.commons import Coord as C, guess_object_style
        cur=self._con.cursor()
        s=self.mogrify(sql, params)
        cur.execute(s)
        rows=cur.fetchall()
        cur.close()
        coord_start=C.assertCoord(coord_start)

        keys=[]
        for desc in cur.description:
            keys.append(desc.name)

        for column,  key in enumerate(keys):       
            doc.addCellWithStyle(coord_start.addColumnCopy(column), key, color_row_header, "BoldCenter")
        coord_data=coord_start.addRowCopy(1)

        #Data
        for row, od in enumerate(rows):
            for column, key in enumerate(keys):
                if styles is None:
                    style=guess_object_style(od[key])
                elif styles.__class__.__name__ != "list":
                    style=styles
                else:
                    style=styles[column]
    
                if column+1<=columns_header:
                    color_=color_column_header
                else:
                    color_=color

                doc.addCellWithStyle(coord_data.addRowCopy(row).addColumnCopy(column), od[key], color_, style)

    ## @params columns_widths must be a list
    def unogenerator_sheet(self, filename,  sql, params=[], sheet_name="Data", columns_widths=None, columns_header=0, color_row_header=0xffdca8, color_column_header=0xc0FFc0, color=0xFFFFFF, styles=None):
        from unogenerator import ODS_Standard, __version__
        doc=ODS_Standard()
        doc.setMetadata(
            "Query result",  
            "Query result", 
            "Connection_pg from https://github.com/turulomio/reusingcode/", 
            f"This file have been generated with ConnectionPg and UnoGenerator-{__version__}. You can see UnoGenerator main page in http://github.com/turulomio/unogenerator/",
            ["unogenerator", "sql", "query"]
        )
        doc.createSheet(sheet_name)
        if columns_widths is not None:
            doc.setColumnsWidth(columns_widths)

        self.unogenerator_values_in_sheet(doc, "A1", sql, params,columns_header, color_row_header, color_column_header,  color, styles)
        doc.removeSheet(0)
        doc.save(filename)
        doc.close()


## Function that adds an argparse argument group with connection parameters
## @param parser Argparse object
## @param gettext_module Gettext module
## @param gettex_locale Locale path
## @param default_user
## @param default_port
## @param default_server
## @param default_db
def argparse_connection_arguments_group(parser, gettext_module=None,  gettex_locale=None,  default_user="postgres", default_port=5432, default_server="127.0.0.1",  default_db="postgres"):
    try:
        import gettext
        t=gettext.translation(gettext_module,  gettex_locale)
        _=t.gettext
    except:
        _=str

    group_db=parser.add_argument_group(_("Postgres database connection parameters"))
    group_db.add_argument('--user', help=_('Postgresql user'), default=default_user)
    group_db.add_argument('--port', help=_('Postgresql server port'), default=default_port)
    group_db.add_argument('--server', help=_('Postgresql server address'), default=default_server)
    group_db.add_argument('--db', help=_('Postgresql database'), default=default_db)
    
## Function that generate the start of a scritp just with connection arguments
def script_with_connection_arguments(name="",  description="", epilog="", version="", gettext_module=None, gettext_locale=None): 
    import argparse
    parser=argparse.ArgumentParser(prog=name, description=description, epilog=epilog, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--version', action='version', version=version)
    argparse_connection_arguments_group(parser, gettext_module, gettext_locale)

    global args
    args=parser.parse_args()

    con=Connection()

    con.user=args.user
    con.server=args.server
    con.port=args.port
    con.db=args.db
    
    con.get_password(gettext_module, gettext_locale)
    con.connect()
    return con


if __name__ == "__main__":
    con=script_with_connection_arguments("connection_pg_demo", "This is a connection script demo",  "Developed by Mariano Muñoz", "",  None, None)
    print("Is connection active?",  con.is_active())
    if con.is_active():
        sql="select name, setting, sourceline, pending_restart from pg_settings"
        con.unogenerator_sheet("prueba.ods",  sql, columns_widths=(10,10,4,4))
        print("File prueba.ods has been generated")
