from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from math import ceil
from money.reusing.connection_dj import cursor_one_row, cursor_rows_as_dict
from money.reusing.currency import Currency
from money.reusing.decorators import deprecated
from money.reusing.datetime_functions import string2dtnaive, dtaware
from money.reusing.listdict_functions import listdict_sum, listdict2json, listdict_print_first
from money.reusing.percentage import Percentage, percentage_between
from money.tables import TabulatorFromListDict

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

    def age(self):
            return (date.today()-self.d["datetime"].date()).days

    def percentage_apr_investment(self):
            dias=self.age()
            if dias==0:
                dias=1
            return Percentage(self.percentage_total_investment()*365,  dias)


    def percentage_total_investment(self):
        if self.d["invested_investment"] is None:#initiating xulpymoney
            return Percentage()
        return Percentage(self.d['gains_gross_investment'], self.d["invested_investment"])
        
    def percentage_sellingpoint(self):
        if self.investment.selling_price is None or self.investment.selling_price==0:
            return Percentage()
        return percentage_between(self.investment.products.basic_results()["last"], self.investment.selling_price)

## Manage output of  investment_operations
class InvestmentsOperations:
    def __init__(self, request, investment,  str_ld_io, str_ld_io_current, str_ld_io_historical, name="IO"):
        self.request=request
        self.investment=investment
        self.name=name
        self.io=eval(str_ld_io)
        for o in self.io:
            o["datetime"]=postgres_datetime_string_2_dtaware(o["datetime"])
            
        self.io_current=eval(str_ld_io_current)
        for o in self.io_current:
            o["datetime"]=postgres_datetime_string_2_dtaware(o["datetime"])
           
        self.io_historical=eval(str_ld_io_historical)
        for o in self.io_historical:
            o["dt_start"]=postgres_datetime_string_2_dtaware(o["dt_start"])
            o["dt_end"]=postgres_datetime_string_2_dtaware(o["dt_end"])
        
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
        currency=self.request.local_currency
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
        
    def o_commissions_account_between_dt(self, dt_from, dt_to):
        r=0
        for o in self.io:
            if dt_from<=o["datetime"] and o["datetime"]<=dt_to:
                r=r - o["commission_account"]
        return r
        
        
    def current_listdict_tabulator_homogeneus_investment(self, request):
        for ioc in self.io_current:
            o=IOC(self.investment, ioc)
            ioc["percentage_annual_investment"]=o.percentage_annual_investment()
            ioc["percentage_apr_investment"]=o.percentage_apr_investment()
            ioc["percentage_total_investment"]=o.percentage_total_investment()
            ioc["operationstypes"]=request.operationstypes[ioc["operationstypes_id"]]
        return self.io_current
        
                
    def current_tabulator_homogeneus_investment(self):
        r=TabulatorFromListDict(f"{self.name}_current_tabulator_homogeneus_investment")
        r.setDestinyUrl(None)
        r.setLocalZone(self.request.local_zone)
        r.setListDict(self.current_listdict_tabulator_homogeneus_investment(self.request))
        r.setFields("id","datetime", "operationstypes",  "shares", "price_investment", "invested_investment", "balance_investment", "gains_gross_investment", "percentage_annual_investment", "percentage_apr_investment", "percentage_total_investment")
        r.setHeaders("Id", _("Date and time"), _("Operation type"),  _("Shares"), _("Price"), _("Invested"), _("Current balance"), _("Gross gains"), _("% year"), _("% APR"), _("% Total"))
        r.setTypes("int","datetime", "str",  "Decimal", self.investment.products.currency, self.investment.products.currency, self.investment.products.currency,  self.investment.products.currency, "percentage", "percentage", "percentage")
        r.setBottomCalc(None, None, None, "sum", None, "sum", "sum", "sum", None, None, None)
        r.showLastRecord(False)
        
        r.setHTMLCodeAfterObjectCreation(f"""
    <p>{_("Current average price is {} in investment currency").format(self.current_average_price_investment())}</p>
""")
        return r        

    def current_tabulator_homogeneus_user(self):
        currency=self.request.local_currency
        r=TabulatorFromListDict(f"{self.name}_current_tabulator_homogeneus_user")
        r.setDestinyUrl(None)
        r.setLocalZone(self.request.local_zone)
        r.setListDict(self.current_listdict_tabulator_homogeneus_investment(self.request))
        r.setFields("id","datetime", "name","operationstypes",  "shares", "price_user", "invested_user", "balance_user", "gains_gross_user", "percentage_annual", "percentage_apr", "percentage_total")
        r.setHeaders("Id", _("Date and time"), _("Name"),  _("Operation type"),  _("Shares"), _("Price"), _("Invested"), _("Current balance"), _("Gross gains"), _("% year"), _("% APR"), _("% Total"))
        r.setTypes("int","datetime", "str", "str",  "Decimal", currency, currency, currency, currency, "percentage", "percentage", "percentage")
        r.setBottomCalc(None, None, None, None, "sum", None,  "sum", "sum", "sum", None, None, None)
        r.showLastRecord(False)
        r.setHTMLCodeAfterObjectCreation(f"""
    <p>{_("Current average price is {} in user currency").format(self.current_average_price_user())}</p>
""")
        return r


    def o_tabulator_homogeneus_investment(self):
        r=TabulatorFromListDict(f"{self.name}_o_tabulator_homogeneus_investment")
        r.setDestinyUrl("investmentoperation_update")
        r.setLocalZone(self.request.local_zone)
        r.setListDict(self.o_listdict_tabulator_homogeneus(self.request))
        r.setFields("id","datetime", "operationstypes","shares", "price", "gross_investment","commission", "taxes" , "net_investment","currency_conversion",  "comment")
        r.setHeaders("Id", _("Date and time"), _("Operation types"),  _("Shares"), _("Price"), _("Gross"), _("Commission"), _("Taxes"), _("Net"), _("Currency convertion"),  _("Comment"))
        r.setTypes("int","datetime", "str","Decimal", self.investment.products.currency, self.investment.products.currency, self.investment.products.currency, self.investment.accounts.currency,self.investment.accounts.currency,"Decimal6", "str")
        r.setBottomCalc(None, None, None, "sum", None, "sum","sum", "sum", "sum", None, None)
        r.showLastRecord(False)
        return r

    def historical_tabulator_homogeneus_user(self):
        c=self.request.local_currency
        r=TabulatorFromListDict(f"{self.name}_historical_tabulator_homogeneus_investment")
        r.setDestinyUrl(None)
        r.setLocalZone(self.request.local_zone)
        r.setListDict(self.historical_listdict_homogeneus(self.request))
        r.setFields("id","dt_end", "years","operationstypes","shares", "gross_start_user", "gross_end_user", "gains_gross_user", "commissions_user", "taxes_user", "gains_net_user")
        r.setHeaders("Id", _("Date and time"), _("Years"), _("Operation type"),  _("Shares"), _("Gross start"), _("Gross end"), _("Gross gains"), _("Commissions"), _("Taxes"), _("Net gains"))
        r.setTypes("int","datetime", "int",  "str", "Decimal", c, c, c, c, c, c)
        r.setBottomCalc(None, None, None,None, None, "sum", "sum", "sum", "sum", "sum", "sum")
        r.showLastRecord(False)
        return r
        
    @deprecated
    def historical_tabulator_homogeneus_investment(self):
        r=TabulatorFromListDict(f"{self.name}_historical_tabulator_homogeneus_user")
        r.setDestinyUrl(None)
        r.setLocalZone(self.request.local_zone)
        r.setListDict(self.historical_listdict_homogeneus(self.request))
        r.setFields("id","dt_end", "years","operationstypes","shares", "gross_start_investment", "gross_end_investment", "gains_gross_investment", "commissions_account", "taxes_account", "gains_net_investment")
        r.setHeaders("Id", _("Date and time"), _("Years"), _("Operation type"),  _("Shares"), _("Gross start"), _("Gross end"), _("Gross gains"), _("Commissions"), _("Taxes"), _("Net gains"))
        r.setTypes("int","datetime", "int",  "str", "Decimal", self.investment.products.currency, self.investment.products.currency, self.investment.products.currency, self.investment.products.currency, self.investment.products.currency, self.investment.products.currency)
        r.setBottomCalc(None, None, None,None, None, "sum", "sum", "sum", "sum", "sum", "sum")
        r.showLastRecord(False)
        return r

    def historical_listdict_homogeneus(self, request):
        for ioh in self.io_historical:
            ioh["operationstypes"]=request.operationstypes[ioh["operationstypes_id"]]
            ioh["years"]=0
        return self.io_historical

    ## Gets and investment operation from its listdict_io using an id
    ## @param id integer with the id of the investment operation
    def o_find_by_id(self,  id):
        for o in self.io:
            if o["id"]==id:
                return o


    ## ECHARTS
    def eChart(self, name="investment_view_chart"):
        if len(self.io)==0:
            return _("Insuficient data")
            
        from money.listdict import QsoDividendsHomogeneus
        from money.models import Dividends
        from django.utils import timezone
            
        qso_dividends=QsoDividendsHomogeneus(self.request,  Dividends.objects.all().filter(investments_id=self.investment.id).order_by('datetime'),  self.investment)

        #Gets investment important datetimes: operations, dividends, init and current time. For each datetime adds another at the beginning of the day, to get mountains in graph
        datetimes=set()
        datetimes.add(self.io[0]["datetime"]-timedelta(days=30))
        for op in self.io:
            datetimes.add(op["datetime"])
            datetimes.add(op["datetime"]-timedelta(seconds=1))
        for dividend in qso_dividends.qs:
            datetimes.add(dividend.datetime)
        datetimes.add(timezone.now())
        datetimes_list=list(datetimes)
        datetimes_list.sort()
        
        str_datetimes_list=[]
                
        invested=[]
        gains_dividends=[]
        balance=[]
        dividends=[]
        gains=[]
        
        for i, dt in enumerate(datetimes_list):
            str_datetimes_list.append(str(dt.date()))
            oper_dt=InvestmentsOperations_from_investment(self.request, self.investment, dt, self.request.local_currency)
            #Calculate dividends in datetime
            dividend_net=0
            for dividend in qso_dividends.qs:
                if dividend.datetime<=dt:
                    dividend_net=dividend_net+dividend.net
    
            #Append data of that datetime
            invested.append(float(oper_dt.current_invested_user()))
            balance.append(float(oper_dt.current_balance_futures_user()))
            gains_dividends.append(float(oper_dt.historical_gains_net_user()+dividend_net))
            dividends.append(float(dividend_net))
            gains.append(float(oper_dt.historical_gains_net_user()))
       
        #Chart
        return f"""
        <div id="{name}" style="width: 100%;height:80%;"></div>
        <script type="text/javascript">

            // based on prepared DOM, initialize echarts instance
            var myChart = echarts.init(document.getElementById('{name}'));

            // specify chart configuration item and data
            var option = {{
                legend: {{
                    data: ['{self.investment.name}', "{_("Invested")}", "{_("Balance")}", "{_("Gains and dividends")}",  "{_("Gains")}",  "{_("Dividends")}"],
                    inactiveColor: '#777',
                }},
                tooltip: {{
                    trigger: 'axis',
                    axisPointer: {{
                        animation: false,
                        type: 'cross',
                    }}
                }},
                xAxis: {{
                    type: 'category',
                    data: {str(str_datetimes_list)},
                    axisLine: {{ lineStyle: {{ color: '#8392A5' }} }}
                }},
                yAxis: {{
                    scale: true,
                    axisLine: {{ lineStyle: {{ color: '#8392A5' }} }},
                    splitLine: {{ show: false }}
                }},
                grid: {{
                    bottom: 80, 
                    left:80
                }},
                dataZoom: [{{
                    textStyle: {{
                        color: '#8392A5'
                    }},
                    handleIcon: 'path://M10.7,11.9v-1.3H9.3v1.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4v1.3h1.3v-1.3c4.9-0.3,8.8-4.4,8.8-9.4C19.5,16.3,15.6,12.2,10.7,11.9z M13.3,24.4H6.7V23h6.6V24.4z M13.3,19.6H6.7v-1.4h6.6V19.6z',
                    dataBackground: {{
                        areaStyle: {{
                            color: '#8392A5'
                        }},
                        lineStyle: {{
                            opacity: 0.8,
                            color: '#8392A5'
                        }}
                    }},
                    brushSelect: true
                }}, {{
                    type: 'inside'
                }}],
                series: [
                    {{
                        type: 'line',
                        name: '{_("Invested")}',
                        data: {str(invested)},
                    }},                
                    {{
                        type: 'line',
                        name: '{_("Balance")}',
                        data: {str(balance)},
                    }},             
                    {{
                        type: 'line',
                        name: '{_("Gains and dividends")}',
                        data: {str(gains_dividends)},
                    }},             
                    {{
                        type: 'line',
                        name: '{_("Gains")}',
                        data: {str(gains)},
                    }},             
                    {{
                        type: 'line',
                        name: '{_("Dividends")}',
                        data: {str(dividends)},
                    }},                
                ]
            }};
            // use configuration item and data specified to show chart
            myChart.setOption(option);
        </script>"""

def InvestmentsOperations_from_investment(request,  investment, dt, local_currency):
    row_io= cursor_one_row("select * from investment_operations(%s,%s,%s)", (investment.pk, dt, local_currency))
    r=InvestmentsOperations(request, investment,  row_io["io"], row_io['io_current'],  row_io['io_historical'])
    return r

## Set of InvestmentsOperations
class InvestmentsOperationsManager:
    def __init__(self, request):
        self.request=request
        self.list=[]

    def __iter__(self):
        return iter(self.list)

    def list_of_investments_ids(self):
        r=[]
        for iot in self.list:
            r.append(iot.investment.id)
        return r

    def append(self, o):
        self.list.append(o)
        
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
        from money.listdict import LdoInvestmentsOperationsHeterogeneus
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
        from money.listdict import LdoInvestmentsOperationsCurrentHeterogeneus
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
        from money.listdict import LdoInvestmentsOperationsHistoricalHeterogeneus
        r=LdoInvestmentsOperationsHistoricalHeterogeneus(self.request)
        for io in self.list:
            for o in io.io_historical:
                if dt_from<=o["dt_end"] and o["dt_end"]<=dt_to:
                    o["name"]=io.investment.fullName()
                    o["operationstypes"]=self.request.operationstypes[o["operationstypes_id"]]
                    r.append(o)
        r.order_by("dt_end")
        return r
        
    def o_commissions_account_between_dt(self, dt_from, dt_to):
        r=0
        for o in self.list:
                r=r + o.o_commissions_account_between_dt(dt_from, dt_to)
        return r

## Generate object from and ids list
def InvestmentsOperationsManager_from_investment_queryset(qs_investments, dt, request):
    ids=tuple(qs_investments.values_list('pk',flat=True))
    
    r=InvestmentsOperationsManager(request)
    if len(ids)>0:
        rows=cursor_rows_as_dict("id","select id, t.* from investments, investment_operations(investments.id, %s, %s ) as t where investments.id in %s;", (dt, request.local_currency, ids))
        for investment in qs_investments:  
            row=rows[investment.id]
            r.append(InvestmentsOperations(request, investment,  row["io"], row['io_current'],  row['io_historical']))
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
    def __init__(self, investment, str_d_io_total, str_d_io_current_total, str_d_io_historical_total):
        self.investment=investment
        self.io_total=eval(str_d_io_total)
        self.io_total_current=eval(str_d_io_current_total)
        self.io_total_historical=eval(str_d_io_historical_total)
                
    def current_last_day_diff(self):
            basic_quotes=self.investment.products.basic_results()
            try:
                return (basic_quotes['last']-basic_quotes['penultimate'])*self.io_total_current["shares"]*self.investment.products.real_leveraged_multiplier()
            except:
                return 0

def InvestmentsOperationsTotals_from_investment( investment, dt, local_currency):
    row_io= cursor_one_row("select * from investment_operations_totals(%s,%s,%s)", (investment.pk, dt, local_currency))
    r=InvestmentsOperationsTotals(investment,  row_io["io"], row_io['io_current'],  row_io['io_historical'])
    return r
        
## Manage several rows of investment_operation_totals in several rows (list)
class InvestmentsOperationsTotalsManager:
    def __init__(self, request):
        self.request=request
        self.list=[]
        
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
        
    def json_classes_by_pci(self):
        from money.models import Accounts
        accounts_balance=Accounts.accounts_balance_user_currency(Accounts.objects.filter(active=True), timezone.now())
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
        
        return listdict2json(ld)

    def json_classes_by_product(self):
        from money.models import Accounts
        accounts_balance=Accounts.accounts_balance_user_currency(Accounts.objects.filter(active=True), timezone.now())
        ld=[]
        for product in self.distinct_products():
            d={"name": product.fullName(), "balance": 0,  "invested": 0}
            for iot in self.list:
                if iot.investment.products==product:
                    d["balance"]=d["balance"]+iot.io_total_current["balance_user"]
                    d["invested"]=d["invested"]+iot.io_total_current["invested_user"]
            ld.append(d)
        ld.append({"name": "Accounts", "balance": accounts_balance,  "invested": accounts_balance})
        return listdict2json(ld)

    def json_classes_by_percentage(self):
        from money.models import Accounts
        accounts_balance=Accounts.accounts_balance_user_currency(Accounts.objects.filter(active=True), timezone.now())
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
        return listdict2json(ld)

    def json_classes_by_producttype(self):
        from money.models import Accounts, Productstypes
        accounts_balance=Accounts.accounts_balance_user_currency(Accounts.objects.filter(active=True), timezone.now())
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
        return listdict2json(ld)
        
    def json_classes_by_leverage(self):
        from money.models import Accounts, Leverages
        accounts_balance=Accounts.accounts_balance_user_currency(Accounts.objects.filter(active=True), timezone.now())
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
        return listdict2json(ld)

## Generate object from and ids list
def InvestmentsOperationsTotalsManager_from_investment_queryset(qs_investments, dt, request):
    ids=tuple(qs_investments.values_list('pk',flat=True))
    r=InvestmentsOperationsTotalsManager(request)
    if len(ids)>0:
        rows=cursor_rows_as_dict("id","select id, investment_operations_totals.* from investments, investment_operations_totals(investments.id, %s, %s ) as investment_operations_totals where investments.id in %s;", (dt, request.local_currency, ids))
        for investment in qs_investments:  
            row=rows[investment.id]
            r.append(InvestmentsOperationsTotals(investment,  row["io"], row['io_current'],  row['io_historical']))
    return r
    
def InvestmentsOperationsTotalsManager_from_all_investments(request, dt):
    from money.models import Investments
    qs=Investments.objects.all().select_related("products")
    return InvestmentsOperationsTotalsManager_from_investment_queryset(qs, dt, request)
