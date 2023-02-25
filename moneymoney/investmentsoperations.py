from datetime import date, timedelta
from decimal import Decimal
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from math import ceil
from moneymoney.reusing.connection_dj import cursor_one_row, cursor_rows_as_dict, execute
from moneymoney.reusing.currency import Currency
from moneymoney.reusing.datetime_functions import string2dtnaive, dtaware
from moneymoney.reusing.listdict_functions import listdict_sum, listdict_print_first, listdict_order_by
from moneymoney.reusing.percentage import Percentage, percentage_between
from uuid import uuid4

Decimal
listdict_print_first

## TRAS MUCHAS VUELTAS LO MEJOR ES INVESTMENTS_OPERATIONS COMPLETO EN BASE DE DATOS POR MULTICURRENCY
## PERO SE HACE NECESARIO EL TOTALS SI EL SERVIDOR WEB ESTA FUERA DE LA BD
## ESTO ES ASÍ PORQUE TODO ESTO SE EJECUTA EN SERVIDOR
## DENTRO DE INVESTMENTS_OPERATIONS SOLO DEBE HABER CALCULOS QUE NECESITEN CONSULTAS BD SINO METODOS Y NO RECARGO
## LUEGO TODOS LOS CALCULOS SE PUEDEN HACER CON INVESTMENTS_OPERATIONS_MANAGER

## Converting dates to string in postgres functions return a string datetime instead of a dtaware. Here we convert it
def postgres_datetime_string_2_dtaware(s):
    str_dt_end=s[:19]            
    dt_end_naive=string2dtnaive(str_dt_end, "%Y-%m-%d %H:%M:%S")#Es un string desde postgres
    dt_end=dtaware(dt_end_naive.date(), dt_end_naive.time(), 'UTC')
    return dt_end

## Class to manage a single investment operation
class IO:
    def __init__(self, investment, d_io):
        self.investment=investment
        self.d=d_io
        
## Class to manage a single investment operation crrent
class IOC:
    def __init__(self, investment, d_ioc):
        self.investment=investment
        self.d=d_ioc
        
                
    def percentage_annual_account(self):
        if self.d["datetime"].year==date.today().year:
            lastyear=self.d["price_accou nt"] #Product value, self.money_price(type) not needed.
        else:
            lastyear=self.investment.products.basic_results()["lastyear"]
        if self.investment.products.basic_results()["lastyear"] is None or lastyear is None:
            return Percentage()

        if self.d["shares"]>0:
            return Percentage(self.investment.products.basic_results()["last"]-lastyear, lastyear)
        else:
            return Percentage(-(self.investment.products.basic_results()["last"]-lastyear), lastyear)                   

    def percentage_annual_investment(self):
        if self.d["datetime"].year==date.today().year:
            lastyear=self.d["price_investment"] #Product value, self.money_price(type) not needed.
        else:
            lastyear=self.investment.products.basic_results()["lastyear"]
        if self.investment.products.basic_results()["lastyear"] is None or lastyear is None:
            return Percentage()

        if self.d["shares"]>0:
            return Percentage(self.investment.products.basic_results()["last"]-lastyear, lastyear)
        else:
            return Percentage(-(self.investment.products.basic_results()["last"]-lastyear), lastyear)        
                
    def percentage_annual_user(self):
        if self.d["datetime"].year==date.today().year:
            lastyear=self.d["price_user"] #Product value, self.money_price(type) not needed.
        else:
            lastyear=self.investment.products.basic_results()["lastyear"]
        if self.investment.products.basic_results()["lastyear"] is None or lastyear is None:
            return Percentage()

        if self.d["shares"]>0:
            return Percentage(self.investment.products.basic_results()["last"]-lastyear, lastyear)
        else:
            return Percentage(-(self.investment.products.basic_results()["last"]-lastyear), lastyear)

    def age(self):
            return (date.today()-self.d["datetime"].date()).days

    def percentage_apr_account(self):
            dias=self.age()
            if dias==0:
                dias=1
            return Percentage(self.percentage_total_account()*365,  dias)

    def percentage_apr_investment(self):
            dias=self.age()
            if dias==0:
                dias=1
            return Percentage(self.percentage_total_investment()*365,  dias)
            
    def percentage_apr_user(self):
            dias=self.age()
            if dias==0:
                dias=1
            return Percentage(self.percentage_total_user()*365,  dias)


    def percentage_total_account(self):
        if self.d["invested_account"] is None:#initiating xulpymoney
            return Percentage()
        return Percentage(self.d['gains_gross_account'], self.d["invested_account"])

    def percentage_total_investment(self):
        if self.d["invested_investment"] is None:#initiating xulpymoney
            return Percentage()
        return Percentage(self.d['gains_gross_investment'], self.d["invested_investment"])
        
    def percentage_total_user(self):
        if self.d["invested_user"] is None:#initiating xulpymoney
            return Percentage()
        return Percentage(self.d['gains_gross_user'], self.d["invested_user"])
        
    def percentage_sellingpoint(self):
        if self.investment.selling_price is None or self.investment.selling_price==0:
            return Percentage()
        return percentage_between(self.investment.products.basic_results()["last"], self.investment.selling_price)

## Manage output of  investment_operations
## @param simulation boolean True si es simulation
class InvestmentsOperations:
    def __init__(self, request, investment,  str_ld_io, str_ld_io_current, str_ld_io_historical, simulation_name=None):
        self.request=request
        self.investment=investment
        
        if simulation_name is not None:
            self.simulation=True
        else:
            self.simulation=False
        self.simulation_name=simulation_name       

        self.io=eval(str_ld_io)
        
        investment_url=request.build_absolute_uri(reverse('investments-detail', args=(self.investment.id, )))
        for o in self.io:
            o["datetime"]=postgres_datetime_string_2_dtaware(o["datetime"])
            o ["url"]=self.request.build_absolute_uri(reverse('investmentsoperations-detail', args=(o["id"], )))
            o["investments"]=investment_url
            o["operationstypes"]=self.request.build_absolute_uri(reverse('operationstypes-detail', args=(o["operationstypes_id"],  )))

        self.io_current=eval(str_ld_io_current)
        for o in self.io_current:
            ioc=IOC(self.investment, o )
            o["datetime"]=postgres_datetime_string_2_dtaware(o["datetime"])
            o["operationstypes"]=self.request.build_absolute_uri(reverse('operationstypes-detail', args=(o["operationstypes_id"],  )))
            o["percentage_total_investment"]=ioc.percentage_total_investment().value, 
            o["percentage_apr_investment"]=ioc.percentage_apr_investment().value, 
            o["percentage_annual_investment"]= ioc.percentage_annual_investment().value,   
            o["investments"]=investment_url

        self.io_historical=eval(str_ld_io_historical)
        for index, o in enumerate(self.io_historical):
            o["investments"]=investment_url
            o["dt_start"]=postgres_datetime_string_2_dtaware(o["dt_start"])
            o["dt_end"]=postgres_datetime_string_2_dtaware(o["dt_end"])
            o["operationstypes"]=self.request.build_absolute_uri(reverse('operationstypes-detail', args=(o["operationstypes_id"],  )))        
            o["years"]=round(Decimal((o["dt_end"]-o["dt_start"]).days/365), 2)

    @classmethod
    def from_investment(cls, request,  investment, dt, local_currency):
        row_io= cursor_one_row("select * from investment_operations(%s,%s,%s)", (investment.pk, dt, local_currency))
        r=cls(request, investment,  row_io["io"], row_io['io_current'],  row_io['io_historical'])
        return r




    ##  @param investments list of investments
    ## @param listdict list of operations with first investment.id as new investment
    ## OJO OJO ESTA FUNCION CONSIDERA QUE TODAS LAS INVERSIONES  TIENEN LA MISMA ACCOUNT_CURRENCY QUE
    ## SINO FUERA ASI ESTARÏA MAL
    ## SI ES UNA SIMULACION DE VIRTUAL PONER EN investments SOLOL A VIRTUAL
    @classmethod
    def from_investment_simulation(cls, request,  investments, dt, local_currency,  listdict):
        ids=[]
        
        temporaltable="tt"+str(uuid4()).replace("-", "")
        for inv in investments:
            ids.append(inv.id)
        execute(f"""
        create temporary table  {temporaltable}
        as 
            select * from investmentsoperations where investments_id in %s and datetime<=%s;
        """, (tuple(ids), dt))
        
        #Actualiza todos los ids al primero de array
        execute(f"update {temporaltable} set investments_id=%s", (investments[0].id, ))
        
        for d in listdict:
            execute(f"insert into {temporaltable}(id, datetime,  shares,  price, commission,  taxes, operationstypes_id, currency_conversion, investments_id) values((select max(id)+1 from {temporaltable}), %s, %s, %s, %s, %s, %s, %s, %s)", 
            (d["datetime"], d["shares"], d["price"], d["commission"], d["taxes"], d["operationstypes_id"], d["currency_conversion"], d["investments_id"]))

        row_io= cursor_one_row("select * from investment_operations(%s,%s,%s,%s,%s,%s)", (investments[0].id, dt, local_currency, temporaltable, investments[0].accounts.currency, investments[0].products.id))
        simulation_name="Simulation from investments"+ str(ids)
        r=cls(request, investments[0],  row_io["io"], row_io['io_current'],  row_io['io_historical'], simulation_name=simulation_name)
        return r



    ## OJO OJO ESTA FUNCION CONSIDERA QUE TODAS LAS INVERSIONES  TIENEN LA MISMA ACCOUNT_CURRENCY
    ## SINO FUERA ASI ESTARÏA MAL
    @classmethod
    def from_merging_current_operations_with_same_product(cls, request, product, dt):
        #We need to convert investmentsoperationscurrent to investmentsoperations
        from moneymoney.models import Investments, Banks, Accounts
        ld=[]
        investments=Investments.objects.filter(active=True, products=product).select_related("accounts").select_related("products")
        iom=InvestmentsOperationsManager.from_investment_queryset(investments, dt, request)   
        bank=Banks()
        bank.name="Merging bank"
        bank.active=True
        bank.id=-1
        account=Accounts()
        account.name="Merging account"
        account.banks=bank
        account.active=True
        account.currency=request.user.profile.currency
        account.id=-1
        investment=Investments()
        investment.name=f"Merging {investments[0].products.name}"
        investment.accounts=account
        investment.products=product
        investment.id=-1
        for io in iom:
            for o in io.io_current:
                ld.append({
                    "datetime": o["datetime"], 
                    "shares": o ["shares"], 
                    "price": o ["price_investment"], 
                    "commission": o ["commissions_account"], 
                    "taxes": o ["taxes_account"], 
                    "operationstypes_id": o ["operationstypes_id"], 
                    "currency_conversion": o ["investment2account"], 
                    "investments_id": -1, 
                })
        ld=listdict_order_by(ld, "datetime")
        r=InvestmentsOperations.from_investment_simulation(request, [investment, ],  dt,  request.user.profile.currency,  ld)
        return r

    def json(self):
        r={}
        r["investment"]={
            "name": self.investment.name if self.simulation==False else self.simulation_name, 
            "selling_price": self.investment.selling_price, 
            "selling_expiration": self.investment.selling_expiration, 
            "fullName": self.investment.fullName() if self.simulation==False else self.simulation_name, 
            "gains_at_sellingpoint": self.current_gains_gross_investment_at_selling_price(), 
            "url": self.request.build_absolute_uri(reverse('investments-detail', args=(self.investment.id, ))), 
            "average_price_investment": self.current_average_price_investment(), 
            "active": self.investment.active, 
            "id":self.investment.id, 
            "daily_adjustment":self.investment.daily_adjustment, 
            "simulation": self.simulation, 
        }
        r["product"]={
            "name": self.investment.products.name, 
            "currency": self.investment.products.currency, 
            "url": self.request.build_absolute_uri(reverse('products-detail', args=(self.investment.products.id, ))), 
            "leverage_multiplier": self.investment.products.leverages.multiplier, 
            "leverage_real_multiplier": self.investment.products.real_leveraged_multiplier(), 
            "last": self.investment.products.basic_results()["last"], 
            "decimals": self.investment.products.decimals, 
        }
        r["io"]=self.io
        r["io_current"]=self.io_current
        r["io_historical"]=self.io_historical
        return r
        
    ## Returns the last operation of the io_current
    def  current_last_operation(self):
        if len(self.io_current)==0:
            return None
        r= self.io_current[len(self.io_current)-1]
        return r    ## Returns the last operation of the io_current

    def  current_last_operation_excluding_additions(self):
        for o in reversed(self.io_current):
            if o["operationstypes_id"]!=6:# Shares Additions
                return o
        return None
        
    def current_shares(self):
        return listdict_sum(self.io_current, "shares")

    def current_invested_user(self):
        return listdict_sum(self.io_current, "invested_user")
        
        
        
    def current_highest_price(self):
        r=0
        for o in self.io_current:
            if o["price_investment"]>r:
                r=o["price_investment"]
        return r
        
    def current_lowest_price(self):
        r=10000000
        for o in self.io_current:
            if o["price_investment"]<r:
                r=o["price_investment"]
        return r
        
    def current_average_price_account(self):
        """Calcula el precio medio de compra"""
        shares=self.current_shares()
        currency=self.investment.accounts.currency
        sharesxprice=Decimal(0)
        for o in self.io_current:
            sharesxprice=sharesxprice+o["shares"]*o["price_account"]
        return Currency(0, currency) if shares==Decimal(0) else Currency(sharesxprice/shares,  currency)

    def current_average_price_investment(self):
        """Calcula el precio medio de compra"""
        
        shares=self.current_shares()
        currency=self.investment.products.currency
        sharesxprice=Decimal(0)
        for o in self.io_current:
            sharesxprice=sharesxprice+o["shares"]*o["price_investment"]
        return Currency(0, currency) if shares==Decimal(0) else Currency(sharesxprice/shares,  currency)

    def current_average_price_user(self):
        """Calcula el precio medio de compra"""
        
        shares=self.current_shares()
        currency=self.request.user.profile.currency
        sharesxprice=Decimal(0)
        for o in self.io_current:
            sharesxprice=sharesxprice+o["shares"]*o["price_user"]
        return Currency(0, currency) if shares==Decimal(0) else Currency(sharesxprice/shares,  currency)
        
    def current_gains_net_user(self):
        return listdict_sum(self.io_current, "gains_net_user")
        
    def current_balance_futures_user(self):
        return listdict_sum(self.io_current, "balance_futures_user")
        
    def current_balance_investment(self):
        return listdict_sum(self.io_current, "balance_investment")

    def current_gains_gross_user(self):
        return listdict_sum(self.io_current, "gains_gross_user")
    
    def current_gains_gross_investment(self):
        return listdict_sum(self.io_current, "gains_gross_investment")

    def percentage_sellingpoint(self):
        if self.investment.selling_price is None or self.investment.selling_price==0:
            return Percentage()
        return percentage_between(self.investment.products.basic_results()["last"], self.investment.selling_price)

    def current_percentage_invested_user(self):
        return Percentage(self.current_gains_gross_user(), self.current_invested_user())

    def historical_gains_net_user(self):
        r=0
        for o in self.io_historical:
            r=r + o["gains_net_user"]
        return r   
    def historical_gains_net_user_between_dt(self, dt_from, dt_to):
        r=0
        for o in self.io_historical:
            if dt_from<=o["dt_end"] and o["dt_end"]<=dt_to:
                r=r + o["gains_net_user"]
        return r   
       
    def historical_commissions_user_between_dt(self, dt_from, dt_to):
        r=0
        for o in self.io_historical:
            if dt_from<=o["dt_end"] and o["dt_end"]<=dt_to:
                r=r + o["commissions_user"]
        return r
        
        
        
    ## @param listdict_ioc
    def current_gains_gross_investment_at_selling_price(self):
        #Get selling price gains
        if self.investment.selling_price in (None, 0):
            return None
        gains=0
        for o in self.io_current:
            gains=gains+o["shares"]*(self.investment.selling_price-o['price_investment'])*self.investment.products.real_leveraged_multiplier()
        return Currency(gains, self.investment.products.currency)

    def o_listdict_tabulator_homogeneus(self, request):
        for o in self.io:
            o["operationstypes"]=request.operationstypes[o["operationstypes_id"]]
        return self.io        
        
    def sum_io_commissions_account_between_dt(self, dt_from, dt_to):
        r=0
        for o in self.io:
            if dt_from<=o["datetime"] and o["datetime"]<=dt_to:
                r=r - o["commission_account"]
        return r


    ## Gets and investment operation from its listdict_io using an id
    ## @param id integer with the id of the investment operation
    def o_find_by_id(self,  id):
        for o in self.io:
            if o["id"]==id:
                return o


    ## ECHARTS
    def chart_evolution(self):
        if len(self.io)==0:
            return _("Insuficient data")
            
        from moneymoney.models import Dividends
        from django.utils import timezone
        
        qs_dividends=Dividends.objects.all().filter(investments_id=self.investment.id).order_by('datetime')
        #Gets investment important datetimes: operations, dividends, init and current time. For each datetime adds another at the beginning of the day, to get mountains in graph
        datetimes=set()
        datetimes.add(self.io[0]["datetime"]-timedelta(seconds=1))
        for op in self.io:
            datetimes.add(op["datetime"])
            datetimes.add(op["datetime"]+timedelta(seconds=1))
        for dividend in qs_dividends:
            datetimes.add(dividend.datetime)
        datetimes.add(timezone.now())
        datetimes_list=list(datetimes)
        datetimes_list.sort()
        
        invested=[]
        gains_dividends=[]
        balance=[]
        dividends=[]
        gains=[]
        
        for i, dt in enumerate(datetimes_list):
            oper_dt=InvestmentsOperations.from_investment(self.request, self.investment, dt, self.request.user.profile.currency)
            #Calculate dividends in datetime
            dividend_net=0
            for dividend in qs_dividends:
                if dividend.datetime<=dt:
                    dividend_net=dividend_net+dividend.net
    
            #Append data of that datetime
            invested.append(float(oper_dt.current_invested_user()))
            balance.append(float(oper_dt.current_balance_futures_user()))
            gains_dividends.append(float(oper_dt.historical_gains_net_user()+dividend_net))
            dividends.append(float(dividend_net))
            gains.append(float(oper_dt.historical_gains_net_user()))
        return {
            "datetimes": datetimes_list, 
            "invested": invested, 
            "balance":balance, 
            "gains_dividends":gains_dividends, 
            "dividends": dividends, 
            "gains": gains, 
        }

## Set of InvestmentsOperations
class InvestmentsOperationsManager:
    def __init__(self, request):
        self.request=request
        self.list=[]


    ## Generate object from and ids list
    @classmethod
    def from_investment_queryset(cls, qs_investments, dt, request):
        ids=tuple(qs_investments.values_list('pk',flat=True))
        
        r=cls(request)
        if len(ids)>0:
            rows=cursor_rows_as_dict("id","select id, t.* from investments, investment_operations(investments.id, %s, %s) as t where investments.id in %s;", (dt, request.user.profile.currency, ids))
            for investment in qs_investments:  
                row=rows[investment.id]
                r.append(InvestmentsOperations(request, investment,  row["io"], row['io_current'],  row['io_historical']))
        return r
        

    @classmethod
    def merging_all_current_operations_of_active_investments(cls, request, dt):
        #We need to convert investmentsoperationscurrent to investmentsoperations
        from moneymoney.models import Products
        r=cls(request)
        distinct_products=Products.qs_products_of_active_investments()
        for product in distinct_products:
            io=InvestmentsOperations.from_merging_current_operations_with_same_product(request, product,  dt)
            r.append(io)
        return r

    def __iter__(self):
        return iter(self.list)

    def list_of_investments_ids(self):
        r=[]
        for iot in self.list:
            r.append(iot.investment.id)
        return r

    def append(self, o):
        self.list.append(o)
        
        
    def current_highest_price(self):
        r=0
        for io in self.list:
            highest=io.current_highest_price()
            if highest>r:
                r=highest
        return r
        
    def current_lowest_price(self):
        r=10000000
        for io in self.list:
            lowest=io.current_lowest_price()
            if lowest<r:
                r=lowest
        return r
        
        
    def current_balance_futures_user(self):
        r=0
        for o in self.list:
            r=r + o.current_balance_futures_user()
        return r   

    def current_gains_gross_user(self):
        r=0
        for o in self.list:
            r=r + o.current_gains_gross_user()
        return r

    def current_gains_net_user(self):
        r=0
        for o in self.list:
            r=r + o.current_gains_net_user()
        return r   
        
    def current_invested_user(self):
        r=0
        for o in self.list:
            r=r + o.current_invested_user()
        return r   
        
    
    def historical_gains_net_user_between_dt(self, dt_from, dt_to):
        r=0
        for o in self.list:
                r=r + o.historical_gains_net_user_between_dt(dt_from, dt_to)
        return r

    def historical_commissions_user_between_dt(self, dt_from, dt_to):
        r=0
        for o in self.list:
                r=r + o.historical_commissions_user_between_dt(dt_from, dt_to)
        return r

    def LdoInvestmentsOperationsHeterogeneus_between(self, dt_from, dt_to):
        from moneymoney.listdict import LdoInvestmentsOperationsHeterogeneus
        r=LdoInvestmentsOperationsHeterogeneus(self.request)
        for io in self.list:
            for o in io.io:
                if dt_from<=o["datetime"] and o["datetime"]<=dt_to:
                    o["name"]=io.investment.fullName()
                    o["operationstypes"]=self.request.operationstypes[o["operationstypes_id"]]
                    r.append(o)
        r.order_by("datetime")
        return r        

    def LdoInvestmentsOperationsCurrentHeterogeneus_between(self, dt_from, dt_to):
        from moneymoney.listdict import LdoInvestmentsOperationsCurrentHeterogeneus
        r=LdoInvestmentsOperationsCurrentHeterogeneus(self.request)
        for io in self.list:
            for o in io.io_current:
                if dt_from<=o["datetime"] and o["datetime"]<=dt_to:
                    o["name"]=io.investment.fullName()
                    o["operationstypes"]=self.request.operationstypes[o["operationstypes_id"]]
                    r.append(o)
        r.order_by("datetime")
        return r
        
    def LdoInvestmentsOperationsHistoricalHeterogeneus_between(self, dt_from, dt_to):
        from moneymoney.listdict import LdoInvestmentsOperationsHistoricalHeterogeneus
        r=LdoInvestmentsOperationsHistoricalHeterogeneus(self.request)
        for io in self.list:
            for o in io.io_historical:
                if dt_from<=o["dt_end"] and o["dt_end"]<=dt_to:
                    o["name"]=io.investment.fullName()
                    o["operationstypes"]=self.request.operationstypes[o["operationstypes_id"]]
                    r.append(o)
        r.order_by("dt_end")
        return r
        
    def sum_io_commissions_account_between_dt(self, dt_from, dt_to):
        r=0
        for o in self.list:
                r=r + o.sum_io_commissions_account_between_dt(dt_from, dt_to)
        return r


##                        io                |                                                       io_current                                                        |                                           io_historical                                            
## ----------------------------------+-------------------------------------------------------------------------------------------------------------------------+----------------------------------------------------------------------------------------------------
##{'price': Decimal('142.083451')} | {'balance_user': 0, 'gains_gross_user': 0, 'gains_net_user': 0, 'shares': 0, 'price_investment': 0, 'invested_user': 0} | {'commissions_account': Decimal('0.00'), 'gains_net_user': Decimal('-649.1696967043800000000000')}
##select * from investment_operations_totals(1,now(),'EUR' );
## para sacar varios con información de la inversión
## select * from investments, investment_operations_totals(investments.id,now(),'EUR' ) as investment_operations_totals where investments.id in (1,2,3);
## para sacar varios sin informacion de la inversion
## select investment_operations_totals.* from investments, investment_operations_totals(investments.id,now(),'EUR' ) as investment_operations_totals where investments.id in (1,2,3);
## Manage output of  investment_operation_totals on one row
class InvestmentsOperationsTotals:
    def __init__(self, request, investment, str_d_io_total, str_d_io_current_total, str_d_io_historical_total):
        self.request=request
        self.investment=investment
        self.io_total=eval(str_d_io_total)
        self.io_total_current=eval(str_d_io_current_total)
        self.io_total_historical=eval(str_d_io_historical_total)

    @classmethod
    def from_investment(cls, request,  investment, dt, local_currency):
        row_io= cursor_one_row("select * from investment_operations_totals(%s,%s,%s)", (investment.pk, dt, local_currency))
        r=cls(request, investment,  row_io["io"], row_io['io_current'],  row_io['io_historical'])
        return r

    def current_last_day_diff(self):
            basic_quotes=self.investment.products.basic_results()
            try:
                return (basic_quotes['last']-basic_quotes['penultimate'])*self.io_total_current["shares"]*self.investment.products.real_leveraged_multiplier()
            except:
                return 0
    
    def json(self):
        r={}
        r["investment"]={
            "id": self.investment.id, 
            "name": self.investment.name, 
            "selling_price": self.investment.selling_price, 
            "selling_expiration": self.investment.selling_expiration, 
            "fullName": self.investment.fullName(), 
            "leverage_multiplier": self.investment.products.leverages.multiplier, 
            "leverage_real_multiplier": self.investment.products.real_leveraged_multiplier(), 
            "url": self.request.build_absolute_uri(reverse('investments-detail', args=(self.investment.id, ))), 
            "product": self.request.build_absolute_uri(reverse('products-detail', args=(self.investment.products.id, ))), 
        }
        r["product"]={
            "name": self.investment.products.name, 
            "currency": self.investment.products.currency, 
            "url": self.request.build_absolute_uri(reverse('products-detail', args=(self.investment.products.id, ))), 
        }
        r["io"]=self.io_total
        r["io_current"]=self.io_total_current
        r["io_historical"]=self.io_total_historical
#        r["tablename"]=self.tablename
        return r

        
## Manage several rows of investment_operation_totals in several rows (list)
class InvestmentsOperationsTotalsManager:
    def __init__(self, request):
        self.request=request
        self.list=[]
        

    ## Generate object from and ids list
    
    @classmethod
    def from_investment_queryset(cls, qs_investments, dt, request):
        ids=tuple(qs_investments.values_list('pk',flat=True))
        r=cls(request)
        if len(ids)>0:
            rows=cursor_rows_as_dict("id","select id, investment_operations_totals.* from investments, investment_operations_totals(investments.id, %s, %s ) as investment_operations_totals where investments.id in %s;", (dt, request.user.profile.currency, ids))
            for investment in qs_investments:  
                row=rows[investment.id]
                r.append(InvestmentsOperationsTotals(request, investment,  row["io"], row['io_current'],  row['io_historical']))
        return r
    
    @classmethod
    def from_all_investments(cls, request, dt):
        from moneymoney.models import Investments
        qs=Investments.objects.all().select_related("products")
        return cls.from_investment_queryset(qs, dt, request)
        
    def __iter__(self):
        return iter(self.list)
        
    def append(self, o):
        self.list.append(o)
        
    def current_invested_user(self):
        r=0
        for o in self.list:
            r=r + o.io_total_current["invested_user"]
        return r   

    def current_balance_user(self):
        r=0
        for o in self.list:
            r=r + o.io_total_current["balance_user"]
        return r   

    def current_balance_futures_user(self):
        r=0
        for o in self.list:
            r=r + o.io_total_current["balance_futures_user"]
        return r   

    def list_of_investments_ids(self):
        r=[]
        for iot in self.list:
            r.append(iot.investment.id)
        return r

    def current_gains_gross_user(self):
        r=0
        for o in self.list:
            r=r + o.io_total_current["gains_gross_user"]
        return r   
        
    def current_gains_net_user(self):
        r=0
        for o in self.list:
            r=r + o.io_total_current["gains_net_user"]
        return r     

    def historical_gains_net_user(self):
        r=0
        for o in self.list:
            r=r + o.io_total_historical["gains_net_user"]
        return r
        
    def find_by_id(self, id):
        for o in self.list:
            if o.investment.id==id:
                return o
        return None
        
    ## Generates a list with all diferent products in array
    def distinct_products(self):
        r=set()
        for iot in self.list:
            r.add(iot.investment.products)
        return list(r)
        
    ## Returns a json 
    def json(self):
        r=[]
        for iot in self.list:
            r.append(iot.json())
        return r
        
        
    def json_classes_by_pci(self):
        from moneymoney.models import Accounts
        accounts_balance=Accounts.balance_user_currency(Accounts.objects.filter(active=True), timezone.now())
        ld=[]
        for mode, name in (('p', 'Put'), ('c', 'Call'), ('i', 'Inline')):
            d={"name": name, "balance": 0,  "invested": 0}
            for iot in self.list:
                if iot.investment.products.pci==mode:
                    d["balance"]=d["balance"]+iot.io_total_current["balance_user"]
                    d["invested"]=d["invested"]+iot.io_total_current["invested_user"]
            if mode=="c":
                d["balance"]=d["balance"]+accounts_balance
                d["invested"]=d["invested"]+accounts_balance
            ld.append(d)
        
        return ld


    def json_classes(self):
        d={}
        d["by_leverage"]=self.json_classes_by_leverage()
        d["by_pci"]=self.json_classes_by_pci()
        d["by_percentage"]=self.json_classes_by_percentage()
        d["by_product"]=self.json_classes_by_product()
        d["by_producttype"]=self.json_classes_by_producttype()
        return d

    def json_classes_by_product(self):
        from moneymoney.models import Accounts
        accounts_balance=Accounts.balance_user_currency(Accounts.objects.filter(active=True), timezone.now())
        ld=[]
        for product in self.distinct_products():
            d={"name": product.fullName(), "balance": 0,  "invested": 0}
            for iot in self.list:
                if iot.investment.products==product:
                    d["balance"]=d["balance"]+iot.io_total_current["balance_user"]
                    d["invested"]=d["invested"]+iot.io_total_current["invested_user"]
            ld.append(d)
        ld.append({"name": "Accounts", "balance": accounts_balance,  "invested": accounts_balance})
        return ld

    def json_classes_by_percentage(self):
        from moneymoney.models import Accounts
        accounts_balance=Accounts.balance_user_currency(Accounts.objects.filter(active=True), timezone.now())
        ld=[]
        for percentage in range(0, 11):
            d={"name": f"{percentage*10}% variable", "balance": 0,  "invested": 0}
            for iot in self.list:
                if ceil(iot.investment.products.percentage/10.0)==percentage:
                    d["balance"]=d["balance"]+iot.io_total_current["balance_user"]
                    d["invested"]=d["invested"]+iot.io_total_current["invested_user"]
            if percentage==0:
                d["balance"]=d["balance"]+accounts_balance
                d["invested"]=d["invested"]+accounts_balance
            ld.append(d)
        return ld

    def json_classes_by_producttype(self):
        from moneymoney.models import Accounts, Productstypes
        accounts_balance=Accounts.balance_user_currency(Accounts.objects.filter(active=True), timezone.now())
        ld=[]
        for producttype in Productstypes.objects.all():
            d={"name": producttype.name, "balance": 0,  "invested": 0}
            for iot in self.list:
                if iot.investment.products.productstypes==producttype:
                    d["balance"]=d["balance"]+iot.io_total_current["balance_user"]
                    d["invested"]=d["invested"]+iot.io_total_current["invested_user"]
            if producttype.id==11:#Accounts
                d["balance"]=d["balance"]+accounts_balance
                d["invested"]=d["invested"]+accounts_balance
            ld.append(d)
        return ld
        
    def json_classes_by_leverage(self):
        from moneymoney.models import Accounts, Leverages
        accounts_balance=Accounts.balance_user_currency(Accounts.objects.filter(active=True), timezone.now())
        ld=[]
        for leverage in Leverages.objects.all():
            d={"name": leverage.name, "balance": 0,  "invested": 0}
            for iot in self.list:
                if iot.investment.products.leverages==leverage:
                    d["balance"]=d["balance"]+iot.io_total_current["balance_user"]
                    d["invested"]=d["invested"]+iot.io_total_current["invested_user"]
            if leverage.id==1:#Accounts
                d["balance"]=d["balance"]+accounts_balance
                d["invested"]=d["invested"]+accounts_balance
            ld.append(d)
        return ld

## Class to work with investmentsoperations inside a strategy_model
## It's not a merging. It must work with heterogeneous mode
class StrategyIO:
    ## @param strategy. It's a strategy model object
    ## @param dt. Be careful due to strategy has its from to end dt
    def __init__(self, request, strategy, dt=None, simulated_operations=[], temporaltable=None):
        self.request=request
        self.strategy=strategy
        self.simulated_operations=simulated_operations
        self.temporaltable=temporaltable
        self.dt=dt
        if dt is None:
            self.dt=self.strategy.dt_to_for_comparations()
        self.iom=InvestmentsOperationsManager.from_investment_queryset(self.strategy.investments_queryset(), self.dt, self.request)
        
        
        
    def io(self):
        if hasattr(self, "_io") is False:
            r=[]
            for io in self.iom:
                investment_url=self.request.build_absolute_uri(reverse('investments-detail', args=(io.investment.id, )))
                for o in io.io:
                    o["investments"]=investment_url
                    r.append(o)
            self._io=r
        return self._io
        
    def io_current(self):
        if hasattr(self, "_io_current") is False:
            r=[]
            for io in self.iom:
                investment_url=self.request.build_absolute_uri(reverse('investments-detail', args=(io.investment.id, )))
                for o in io.io_current:
                    o["investments"]=investment_url
                    r.append(o)
            self._io_current= r
        return self._io_current
        
    def io_historical(self):
        if hasattr(self, "_io_historical") is False:
            r=[]
            for io in self.iom:
                investment_url=self.request.build_absolute_uri(reverse('investments-detail', args=(io.investment.id, )))
                for o in io.io_historical:
                    if self.strategy.dt_from<=o["dt_end"] and o["dt_end"]<=self.strategy.dt_to_for_comparations():
                        o["investments"]=investment_url
                        r.append(o)
            self._io_historical=r
        return self._io_historical
        
    def current_invested_user(self):
        return self.iom.current_invested_user()
        
    def current_gains_net_user(self):
        return self.iom.current_gains_net_user()
        
    def historical_gains_net_user(self):
        r=0
        for o in self.io_historical():
            r=r + o["gains_net_user"]
        return r   
        
        
    def json(self):
        from moneymoney.models import Products, StrategiesTypes
        
        r={}
        r["strategy"]={
            "id": self.strategy.id,  
            "url": self.request.build_absolute_uri(reverse('strategies-detail', args=(self.strategy.pk, ))), 
            "name":self.strategy.name, 
            "dt_from": self.strategy.dt_from, 
            "dt_to": self.strategy.dt_to, 
            "investments":self.strategy.investments_urls(self.request), 
            "type": self.strategy.type, 
            "comment": self.strategy.comment, 
            "additional1": self.strategy.additional1, 
            "additional2": self.strategy.additional2, 
            "additional3": self.strategy.additional3, 
            "additional4": self.strategy.additional4, 
            "additional5": self.strategy.additional5, 
            "additional6": self.strategy.additional6, 
            "additional7": self.strategy.additional7, 
            "additional8": self.strategy.additional8, 
            "additional9": self.strategy.additional9, 
            "additional10": self.strategy.additional10, 
        }
        if self.strategy.type in (StrategiesTypes.Ranges, ):
            product=Products.objects.get(pk=self.strategy.additional1)
            r["product"]={
                "name": product.name, 
                "currency": product.currency, 
                "url": self.request.build_absolute_uri(reverse('products-detail', args=(product.id, ))), 
                "leverage_multiplier": product.leverages.multiplier, 
                "leverage_real_multiplier": product.real_leveraged_multiplier(), 
                "last": product.basic_results()["last"], 
                "decimals": product.decimals, 
            }
        r["io"]=self.io()
        r["io_current"]=self.io_current()
        r["io_historical"]=self.io_historical()
        r["temporaltable"]=self.temporaltable
        return r
        
class StrategyIOManager:
    def __init__(self, request):
        pass
