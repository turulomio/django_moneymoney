from moneymoney.reusing.tabulator import TabulatorFromListDict, TabulatorFromQuerySet
from django.utils.translation import ugettext_lazy as _



def table_InvestmentsOperationsCurrent_Homogeneus_UserCurrency(ld_ioc, local_zone, name="table_ioc_homogeneus_usercurrency"):      
    currency=ld_ioc[0]["currency_user"]
    r=TabulatorFromListDict(name)
    r.setDestinyUrl(None)
    r.setLocalZone(local_zone)
    r.setListDict(ld_ioc)
    r.setFields("id","datetime", "name","operationstypes",  "shares", "price_user", "invested_user", "balance_user", "gains_gross_user", "percentage_annual", "percentage_apr", "percentage_total")
    r.setHeaders("Id", _("Date and time"), _("Name"),  _("Operation type"),  _("Shares"), _("Price"), _("Invested"), _("Current balance"), _("Gross gains"), _("% year"), _("% APR"), _("% Total"))
    r.setTypes("int","datetime", "str", "str",  "Decimal", currency, currency, currency, currency, "percentage", "percentage", "percentage")
    r.setBottomCalc(None, None, None, None, "sum", None,  "sum", "sum", "sum", None, None, None)
    r.showLastRecord(False)
    return r.render()
class TabulatorAccounts(TabulatorFromListDict):
    def __init__(self, name, destiny_url, listdict, local_currency):
        TabulatorFromListDict.__init__(self, name)
        self.setDestinyUrl(destiny_url)
        self.setListDict(listdict)
        self.setFields("id","name", "active", "number", "balance", "balance_user")
        self.setHeaders("Id", _("Name"), _("Active"), _("Number"), _("Balance"), _("Local curr. B."))
        self.setTypes("int","str", "bool", "str", "str", local_currency)
        self.setBottomCalc(None, "sum", None, "sum", "sum", "sum", None, None, None)


class TabulatorProductQuotesMonthPercentages(TabulatorFromListDict):
    def __init__(self, name, destiny_url, listdict):
        TabulatorFromListDict.__init__(self, name)
        self.setDestinyUrl(destiny_url)
        self.setListDict(listdict)
        self.setFields("year", "1","2","3", "4","5","6", "7","8","9", "10","11","12","13" )
        self.setHeaders(_("Year"), _("January"),  _("February"), _("March"), _("April"), _("May"), _("June"), _("July"), _("August"), _("September"), _("October"), _("November"), _("December"), _("Total"))
        self.setTypes("str", *["percentage"]*13)

class TabulatorProductQuotesMonthQuotes(TabulatorFromListDict):
    def __init__(self, name, destiny_url, listdict, currency):
        TabulatorFromListDict.__init__(self, name)
        self.setDestinyUrl(destiny_url)
        self.setListDict(listdict)
        self.setFields("year", "1","2","3", "4","5","6", "7","8","9", "10","11","12" )
        self.setHeaders(_("Year"), _("January"),  _("February"), _("March"), _("April"), _("May"), _("June"), _("July"), _("August"), _("September"), _("October"), _("November"), _("December"))
        self.setTypes("str", *[currency]*12)

class TabulatorAccountOperations(TabulatorFromListDict):
    def __init__(self, name, destiny_url, listdict, currency,  local_zone):
        TabulatorFromListDict.__init__(self, name)
        self.setDestinyUrl(destiny_url)
        self.setListDict(listdict)
#        self.setLayout("fitColumns")
        self.setLocalZone(local_zone)
        self.setFields("id","datetime", "concepts","amount", "balance","comment")
        self.setHeaders("Id", _("Date and time"), _("Concept"), _("Amount"),_("Balance"),  _("Comment"))
        self.setTypes("int","datetime", "str", currency, currency,  "str")
        self.setBottomCalc(None,  None, None, "sum", None, None)

class TabulatorBanks(TabulatorFromListDict):
    def __init__(self, name, destiny_url, listdict, local_currency):
        TabulatorFromListDict.__init__(self, name)
        self.setDestinyUrl(destiny_url)
        self.setListDict(listdict)
        self.setFields("id","name", "active", "accounts_balance", "investments_balance", "total_balance")
        self.setHeaders("Id", _("Name"), _("Active"), _("Accounts balance"), _("Investments balance"), _("Total balance"))
        self.setTypes("int","str", "bool", local_currency,  local_currency, local_currency)
        self.setBottomCalc(None,  None, None, "sum", "sum", "sum")

class TabulatorConcepts(TabulatorFromQuerySet):
    def __init__(self, name, destiny_url, queryset):
        TabulatorFromQuerySet.__init__(self, name)
        self.setDestinyUrl(destiny_url)
        self.setQuerySet(queryset)
        self.setCallByNames("id", "name", "operationstypes", "editable")
        self.setHeaders(_("Id"), _("Name"), _("Operation type"), _("Editable"))
        self.setTypes("int", "str", "str", "bool")
        self.generate_listdict()


class TabulatorInvestmentsPairsInvestCalculator(TabulatorFromListDict):
    def __init__(self, name, destiny_url, listdict, local_currency, local_zone):
        TabulatorFromListDict.__init__(self, name)
        self.setDestinyUrl(destiny_url)
        self.setListDict(listdict)    
        self.setFields("name", "last_datetime","last","invested", "current", "new",   "new_plus_current", "shares")
        self.setHeaders(_("Investment name"), _("Last quote update"),  _("Last quote"), _("Invested"), _("Current balance"),   _("New inversion"), _("Current + new"), _("Shares to invest"))
        self.setTypes("str", "datetime", "Decimal", local_currency, local_currency,local_currency,local_currency,"Decimal")
        self.setBottomCalc(None, None, None,  "sum", "sum",  "sum", "sum", None)

class TabulatorInvestmentsOperationsCurrentHeterogeneus(TabulatorFromListDict):
    def __init__(self, name, destiny_url, listdict, local_currency, local_zone):
        TabulatorFromListDict.__init__(self, name)
        self.setDestinyUrl(destiny_url)
        self.setLocalZone(local_zone)
        self.setListDict(listdict)
        self.setFields("id","datetime", "name",  "operationstypes",  "shares", "price_investment", "invested_investment", "balance_investment", "gains_gross_investment", "percentage_annual", "percentage_apr", "percentage_total")
        self.setHeaders("Id", _("Date and time"), _("Name"),  _("Operation type"),  _("Shares"), _("Price"), _("Invested"), _("Current balance"), _("Gross gains"), _("% year"), _("% APR"), _("% Total"))
        self.setTypes("int","datetime", "str", "str",  "Decimal", local_currency, local_currency, local_currency,  local_currency, "percentage", "percentage", "percentage")
        self.setBottomCalc(None, None,  None, None, None, None, "sum", "sum", "sum", None, None, None)
        self.showLastRecord(False)

class TabulatorProducts(TabulatorFromListDict):
    def __init__(self, name, destiny_url, listdict, local_currency, local_zone):
        TabulatorFromListDict.__init__(self, name)
        self.setDestinyUrl(destiny_url)
        self.setLocalZone(local_zone)
        self.setListDict(listdict)
        self.setFields("id",  "code","name", "isin", "last_datetime", "last", "percentage_day", "percentage_year",  "percentage_dps")
        self.setHeaders(_("Id"), _("Code"),  _("Name"), _("ISIN"), _("Last quote datetime"), _("Last quote"), _("% day"), _("% year"), _("% DPS"))
        self.setTypes("int", "int","str", "str", "str", "Decimal6", "percentage", "percentage", "percentage")
        self.setFilterHeaders(None,  *["input"]*8)



class TabulatorInvestmentsOperationsHistoricalHeterogeneus(TabulatorFromListDict):
    def __init__(self, name, destiny_url, listdict, local_currency, local_zone):
        print("deprecated use LdoInvestmentsOperationsHistoricalHeterogeneus")
        TabulatorFromListDict.__init__(self, name)
        self.setDestinyUrl(destiny_url)
        self.setLocalZone(local_zone)
        self.setListDict(listdict)
        self.setFields("id","dt_end", "years", "name", "operationstypes","shares", "gross_start_user", "gross_end_user", "gains_gross_user", "commissions_user", "taxes_user", "gains_net_user")
        self.setHeaders("Id", _("Date and time"), _("Years"),_("Investment"), _("Operation type"),  _("Shares"), _("Gross start"), _("Gross end"), _("Gross gains"), _("Commissions"), _("Taxes"), _("Net gains"))
        self.setTypes("int","datetime", "int", "str",   "str", "Decimal", local_currency, local_currency, local_currency, local_currency, local_currency, local_currency)
        self.setBottomCalc(None, None, None, None, None, None, "sum", "sum", "sum", "sum", "sum", "sum")

        
class TabulatorCreditCards(TabulatorFromListDict):
    def __init__(self, name, destiny_url, listdict, account):
        TabulatorFromListDict.__init__(self, name)
        self.setDestinyUrl(destiny_url)
        self.setListDict(listdict)
        self.setFields("id", "name", "number", "deferred", "maximumbalance", "balance")
        self.setHeaders(_("Id"), _("Name"), _("Number"), _("Deferred pay"), _("Maximum balance"), _("balance"))
        self.setTypes("int", "str", "str", "bool", account.currency, account.currency)  

class TabulatorReportConcepts(TabulatorFromListDict):
    def __init__(self, name, destiny_url, listdict, local_currency):
        TabulatorFromListDict.__init__(self, name)
        self.setDestinyUrl(destiny_url)
        self.setListDict(listdict)
        self.setFields("id", "name", "operationstypes","total","percentage_total",  "median")
        self.setHeaders(_("id"), _("Name"), _("Operation type"),  _("Total"), _("% total"),  _("Median"))
        self.setTypes("int","str", "str", local_currency, "percentage", local_currency)
        self.setBottomCalc(None, None, None,"sum", None, None)   
        self.setInitialOptions("""
    initialSort:[
    {column:"total", dir:"desc"}, //sort by this first
    ],""")        

class TabulatorOrders(TabulatorFromListDict):
    def __init__(self, name, destiny_url, listdict, local_currency):
        TabulatorFromListDict.__init__(self, name)
        self.setDestinyUrl(destiny_url)
        self.setListDict(listdict)
        self.setFields("id", "date", "expiration", "name", "currency","shares", "price", "amount", "percentage_from_price","executed")
        self.setHeaders(_("Id"), _("Date"),_("Expiration"), _("Investment"), _("Currency"),   _("Shares"), _("Price"), _("Amount"), _("% from price"), _("Executed"))
        self.setTypes("int", "str", "str", "str",  "str",   "Decimal", "Decimal", "Decimal", "percentage","str")
        self.setBottomCalc(None, None, None, None, None,None,None,"sum", None, None)        
