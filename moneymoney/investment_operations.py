from datetime import date, datetime
from decimal import Decimal
from json import dumps
from moneymoney import models
from moneymoney.reusing.percentage import Percentage, percentage_between
from pydicts import lod
from base64 import b64encode
from django.core.serializers.json import DjangoJSONEncoder 

class MyDjangoJSONEncoder(DjangoJSONEncoder):    
    #Converts from dict to json text
    def default(self, o):
        if o.__class__.__name__=="Decimal":
            return str(o)
        if o.__class__.__name__=="bytes":
            return b64encode(o).decode("UTF-8")
        if o.__class__.__name__=="Percentage":
            return o.value
        if o.__class__.__name__=="Currency":
            return o.amount
        return DjangoJSONEncoder.default(self,o)


class PlInvestmentOperations():
    """
        Class to operate with Assets.pl_investment_operations result
    """
    def __init__(self, t):
        self._t=t
    
    @classmethod
    def from_qs(cls, dt,  local_currency,  qs_investments,  mode):
        ids=list(qs_investments.values_list('pk',flat=True))
        return cls.from_ids(dt, local_currency, ids, mode)

    @classmethod
    def from_ids(cls,  dt,  local_currency,  list_ids,  mode):
        
        s=datetime.now()
        lod_investments=PlInvestmentOperations.qs_investments_to_lod(models.Investments.objects.filter(id__in=list_ids), local_currency)
        lod_=models.Investmentsoperations.objects.filter(investments__id__in=list_ids, datetime__lte=dt).order_by("datetime").values()
        
        t=calculate_ios_lazy(dt, lod_investments,  lod_,  local_currency)
        t["lazy_quotes"], t["lazy_factors"]=get_quotes_and_factors(t["lazy_quotes"], t["lazy_factors"])
        t=calculate_ios_finish(t, mode)
        print("LAZY", datetime.now()-s)
        return cls(t)


    @classmethod
    def from_all(cls,  dt,  local_currency,  mode):
        return cls.from_qs(dt, local_currency, models.Investments.objects.all(), mode)
        
    @staticmethod
    def qs_investments_to_lod(qs, currency_user):
        """
            Converts a qs to a lod investments used in moneymoney_pl
        """
        r=[]
        for i in qs:
            r.append({
                "products_id": i.products.id, 
                "investments_id": str(i.id), 
                "multiplier": i.products.leverages.multiplier, 
                "currency_account": i.accounts.currency, 
                "currency_product": i.products.currency, 
                "currency_user": currency_user, 
                "productstypes_id": i.products.productstypes.id, 
            })
        return r

    @staticmethod
    def list_unsaved_io_to_lod(list_):
        """
            Converts a list of unsaved investmentsoperations to a lod_ios used in moneymoney_pl
        """
        r=[]
        for i, io in enumerate(list_):
            r.append({
                "id":-i, 
                "operationstypes_id": io.operationstypes.id, 
                "investments_id": str(i.investments.id), 
                "shares": io.shares, 
                "taxes": io.taxes, 
                "commission": io.commission, 
                "price": io.price, 
                "datetime": io.datetime, 
                "comment": io.comment, 
                "currency_conversion":io.currency_conversion
            })
        return r
        
    @staticmethod
    def qs_investments_to_lod_ios(qs):
        """
            Converts a list of unsaved investmentsoperations to a lod_ios used in moneymoney_pl
        """
        r=[]
        ids=tuple(qs.values_list('pk',flat=True))
        for i, io in enumerate(models.Investmentsoperations.objects.filter(investments_id__in=ids).order_by("datetime")):
            r.append({
                "id":-i, 
                "operationstypes_id": io.operationstypes.id, 
                "investments_id": str(io.investments.id), 
                "shares": io.shares, 
                "taxes": io.taxes, 
                "commission": io.commission, 
                "price": io.price, 
                "datetime": io.datetime, 
                "comment": io.comment, 
                "currency_conversion":io.currency_conversion
            })
        return r

    @classmethod
    def plio_id_from_virtual_investments_simulation(cls, dt,  local_currency,  lod_investment_data, lod_ios_to_simulate, mode):
        """
        Devuelve un plio_Id, solo se debe pasar una inversión
        
        investments_id canbe virtual  coordinated with data and ios_to_simulate
        lod_ios_to_simulate must load all io and simulation ios
        
        Lod_investments_data
        [{'products_id': -81742, 'invesments_id': '445', 'multiplier': Decimal('2'), 'currency_account': 'EUR', 'currency_product': 'EUR', 'productstypes_id': 4}]

        Class method lod_simulated_ios must have
            r.append({
                "id":-i, 
                "operationstypes_id": io.operationstypes.id, 
                "shares": io.shares, 
                "taxes": io.taxes, 
                "commission": io.commission, 
                "price": io.price, 
                "datetime": io.datetime, 
                "currency_conversion":io.currency_conversion
                 "investments_id": virtual_investments_id, 
            })
        """
        lod_ios_to_simulate= sorted(lod_ios_to_simulate,  key=lambda item: item['datetime'])
        t=calculate_ios_lazy(dt, lod_investment_data, lod_ios_to_simulate, local_currency)
        cls.external_query_factors_quotes(t)
        t=calculate_ios_finish(t, mode)
        return cls(t).d(lod_investment_data[0]["investments_id"])
        
        
    @classmethod
    def plio_id_from_strategy(cls, dt,  local_currency,  strategy):
        """
            Returns a plio_id adding all io, io_current,io_historical of all investments (plio) and returning only one plio. Only adds, do not calculate
        """
        
        plio=cls.from_ids(dt, local_currency, strategy.investments_ids(), 1)
        
        r={}
        r["data"]={}
        r["data"]["products_id"]="HETEROGENEOUS"
        r["data"]["investments_id"]=strategy.investments_ids()
        r["data"]["multiplier"]="HETEROGENEOUS"
        r["data"]["currency_product"]="HETEROGENEOUS"
        r["data"]["productstypes_id"]="HETEROGENEOUS"
        r["data"]["currency_user"]=local_currency
        
        r["io"]=[]
        for plio_id in plio.list_investments_id():
            for o in plio.d_io(plio_id):
                if strategy.dt_from<=o["datetime"] and o["datetime"]<=strategy.dt_to_for_comparations():
                    r["io"].append(o)
        r["io"]= sorted(r["io"],  key=lambda item: item['datetime'])

        r["io_current"]=[]
        for plio_id in plio.list_investments_id():
            for o in plio.d_io_current(plio_id):
                if strategy.dt_from<=o["datetime"] and o["datetime"]<=strategy.dt_to_for_comparations():
                    r["io_current"].append(o)
        r["io_current"]= sorted(r["io_current"],  key=lambda item: item['datetime'])
                
        r["total_io_current"]={}
        r["total_io_current"]["balance_user"]=lod.lod_sum(r["io_current"], "balance_user")
        r["total_io_current"]["balance_investment"]="HETEROGENEOUS"
        r["total_io_current"]["balance_futures_user"]=lod.lod_sum(r["io_current"], "balance_futures_user")
        r["total_io_current"]["gains_gross_user"]=lod.lod_sum(r["io_current"], "gains_gross_user")
        r["total_io_current"]["gains_net_user"]=lod.lod_sum(r["io_current"], "gains_net_user")
        r["total_io_current"]["shares"]=lod.lod_sum(r["io_current"], "shares")
        r["total_io_current"]["invested_user"]=lod.lod_sum(r["io_current"], "invested_user")
        r["total_io_current"]["invested_investment"]="HETEROGENEOUS"
        
        r["io_historical"]=[]
        for plio_id in plio.list_investments_id():
            for o in plio.d_io_historical(plio_id):
                if strategy.dt_from<=o["dt_end"] and o["dt_end"]<=strategy.dt_to_for_comparations():
                    r["io_historical"].append(o)
        r["io_historical"]= sorted(r["io_historical"],  key=lambda item: item['dt_end'])

        r["total_io_historical"]={}
        r["total_io_historical"]["gains_net_user"]=lod.lod_sum(r["total_io_historical"], "gains_net_user")
        return r

        
    @classmethod
    def from_merging_io_current(cls, dt,  local_currency,  qs_investments, mode):
        """
            Return a plio merging in same virtual (negative) id all investments in qs with same product
            only io_current and io_historical
        """
        def get_investments_id(product):
            """
                Function Returns a list of integers with all investments_id of a product in plio
            """
            r=[]
            for id in plio.list_investments_id():
                if product.id==plio.d_data(id)["products_id"]:
                    r.append(int(id))
            return r
        
        
        ###############
        plio=cls.from_qs(dt, local_currency, qs_investments, mode)
        products_ids=list(models.Investments.objects.filter(active=True).values_list("products__id",  flat=True).distinct())
        t_merged={}
        for product in models.Products.objects.filter(id__in=products_ids):
            t_merged[str(product.id)]={}
            t_merged[str(product.id)]["data"]={}
            t_merged[str(product.id)]["data"]["products_id"]=product.id
            t_merged[str(product.id)]["data"]["investments_id"]=get_investments_id(product)
            t_merged[str(product.id)]["data"]["multiplier"]=product.leverages.multiplier
            t_merged[str(product.id)]["data"]["currency_product"]=product.currency
            t_merged[str(product.id)]["data"]["productstypes_id"]=product.productstypes.id
            t_merged[str(product.id)]["data"]["currency_user"]=local_currency
            
            t_merged[str(product.id)]["io_current"]=[]
            for plio_id in plio.list_investments_id():
                if plio.d_data(plio_id)["products_id"]==product.id:
                    for o in plio.d_io_current(plio_id):
                        t_merged[str(product.id)]["io_current"].append(o)
            t_merged[str(product.id)]["io_current"]= sorted(t_merged[str(product.id)]["io_current"],  key=lambda item: item['datetime'])
            
            average_price_investment=0
            
            t_merged[str(product.id)]["total_io_current"]={}
            t_merged[str(product.id)]["total_io_current"]["balance_user"]=lod.lod_sum(t_merged[str(product.id)]["io_current"], "balance_user")
            t_merged[str(product.id)]["total_io_current"]["balance_investment"]=lod.lod_sum(t_merged[str(product.id)]["io_current"], "balance_investment")
            t_merged[str(product.id)]["total_io_current"]["balance_futures_user"]=lod.lod_sum(t_merged[str(product.id)]["io_current"], "balance_futures_user")
            t_merged[str(product.id)]["total_io_current"]["gains_gross_user"]=lod.lod_sum(t_merged[str(product.id)]["io_current"], "gains_gross_user")
            t_merged[str(product.id)]["total_io_current"]["gains_net_user"]=lod.lod_sum(t_merged[str(product.id)]["io_current"], "gains_net_user")
            t_merged[str(product.id)]["total_io_current"]["shares"]=lod.lod_sum(t_merged[str(product.id)]["io_current"], "shares")
            t_merged[str(product.id)]["total_io_current"]["invested_user"]=lod.lod_sum(t_merged[str(product.id)]["io_current"], "invested_user")
            t_merged[str(product.id)]["total_io_current"]["invested_investment"]=lod.lod_sum(t_merged[str(product.id)]["io_current"], "invested_investment")
            t_merged[str(product.id)]["total_io_current"]["balance_user"]=average_price_investment
            
            t_merged[str(product.id)]["io_historical"]=[]
            for plio_id in plio.list_investments_id():
                if plio.d_data(plio_id)["products_id"]==product.id:
                    for o in plio.d_io_historical(plio_id):
                        t_merged[str(product.id)]["io_historical"].append(o)
            t_merged[str(product.id)]["io_historical"]= sorted(t_merged[str(product.id)]["io_historical"],  key=lambda item: item['dt_end'])

            t_merged[str(product.id)]["total_io_historical"]={}
            t_merged[str(product.id)]["total_io_historical"]["gains_net_user"]=lod.lod_sum(t_merged[str(product.id)]["total_io_historical"], "gains_net_user")
            #t_merged[str(product.id)]["total_io_historical"]["commission_account"]=lod.lod_sum(t_merged[str(product.id)]["total_io_historical"], "commission_account")

        return cls(t_merged)
        
    def basic_results(self, id):
        """
        Public method Id is investments id
        """
        if not "basic_results" in self._t:
            self._t["basic_results"]={}
            
        products_id=str(self.d_data(str(id))["products_id"])
        if not products_id in self._t["basic_results"]:
            self._t["basic_results"][products_id]=models.Products.basic_results_from_products_id(products_id)
        return self._t["basic_results"][products_id]
        
    def ioc_percentage_annual_user(self, ioc):
        """
        Public method ioc is a io_current dictionary
        """
        if ioc["datetime"].year==date.today().year:
            lastyear=ioc["price_user"] #Product value, self.money_price(type) not needed.
        else:
            lastyear=self.basic_results(ioc["investments_id"])["lastyear"]
        if self.basic_results(ioc["investments_id"])["lastyear"] is None or lastyear is None:
            return Percentage()

        if ioc["shares"]>0:
            return Percentage(self.basic_results(ioc["investments_id"])["last"]-Decimal(lastyear), lastyear)
        else:
            return Percentage(-(self.basic_results(ioc["investments_id"])["last"]-Decimal(lastyear)), lastyear)

    def ioc_percentage_sellingpoint(self, ioc, selling_price):
        if selling_price is None or selling_price==0:
            return Percentage()
        return percentage_between(self.basic_results(ioc["investments_id"])["last"], selling_price)

    def total_io_current_percentage_total_user(self, id):
        if self.d_total_io_current(id)["invested_user"] is None:#initiating xulpymoney
            return Percentage()
        return Percentage(self.d_total_io_current(id)['gains_gross_user'], self.d_total_io_current(id)["invested_user"])
        
    def total_io_current_percentage_sellingpoint(self, id, selling_price):
        if selling_price is None or selling_price==0:
            return Percentage()
        return percentage_between(self.basic_results(id)["last"], selling_price)
        
    def ioc_days(self, ioc):
            return (date.today()-ioc["datetime"].date()).days
    def ioh_years(self, ioh):
        return round(Decimal((ioh["dt_end"]-ioh["dt_start"]).days/365), 2)

    def ioc_percentage_apr_user(self, ioc):
            dias=self.ioc_days(ioc)
            if dias==0:
                dias=1
            return Percentage(self.ioc_percentage_total_user(ioc)*365,  dias)

    def ioc_percentage_total_user(self, ioc):
        """
            Returns total porcentage of an current investment operation dictionary
        """
        if ioc["invested_user"] is None:#initiating xulpymoney
            return Percentage()
        return Percentage(ioc['gains_gross_user'], ioc["invested_user"])
        
    def mode(self):
        return self._t["mode"]
        
    def list_investments_id(self):
        r=[]
        for key in self.keys():
            if key not in t_keys_not_investment():
                r.append(key)
        return r
        
    def qs_investments(self):
        return models.Investments.objects.filter(id__in = self.list_investments_id()).select_related("accounts")
        
    def d(self, id_):
        return self._t[str(id_)]
        
    def t(self):
        return self._t
        
    def keys(self):
        return list(self._t.keys())
    def d_data(self, id_):
        return self._t[str(id_)]["data"]
    def d_io(self, id_):
        return self._t[str(id_)]["io"]
    def d_io_current(self, id_):
        return self._t[str(id_)]["io_current"]
    def d_io_historical(self, id_):
        return self._t[str(id_)]["io_historical"]
    def d_total_io(self, id_):
        return self._t[str(id_)]["total_io"]
    def d_total_io_current(self, id_):
        return self._t[str(id_)]["total_io_current"]
    def d_total_io_historical(self, id_):
        return self._t[str(id_)]["total_io_historical"]
    def sum_total_io_current(self):
        return self._t["sum_total_io_current"]
    def sum_total_io_historical(self):
        return self._t["sum_total_io_historical"]
        
    def investment(self, id_):
        return models.Investments.objects.get(pk=id_)
        
    def dumps(self):
        return dumps(self._t,  indent=4,  cls=MyDjangoJSONEncoder )
        
    def print_dumps(self):
        print(self.dumps())
        
    def print_d(self, id):
        print(self.keys())
        lod.lod_print(self.d(id)["io"])
        lod.lod_print(self.d(id)["io_current"])
        lod.lod_print(self.d(id)["io_historical"])
        lod.lod_print([self.d_total_io(id), ])
        lod.lod_print([self.d_total_io_current(id), ])
        lod.lod_print([self.d_total_io_historical(id), ])
        
        
    def io_historical_sum_between_dt(self, dt_from, dt_to,  key, productstypes_id=None):
        r=0
        for investments_id in self.list_investments_id():
            for ioh in self.d_io_historical(investments_id):
                if dt_from <= ioh["dt_end"] and ioh["dt_end"]<=dt_to:
                    if productstypes_id is None:
                        r=r+ioh[key]
                    else:
                        if int(self.d_data(investments_id)["productstypes_id"])==int(productstypes_id):
                            r=r+ioh[key]
        return r

    def io_sum_between_dt(self, dt_from, dt_to, key):
        r=0
        for investments_id in self.list_investments_id():
            for o in self.d_io(investments_id):
                if dt_from<=o["datetime"] and o["datetime"]<=dt_to:
                    r=r - o[key]
        return r

    def io_current_highest_price(self):
        """
        Public method Returns highest io operation price of all io operations
        """
        
        r=0
        for investments_id in self.list_investments_id():
            for o in self.d_io_current(investments_id):
                if o["price_investment"]>r:
                    r=o["price_investment"]
        return r
    def io_current_lowest_price(self):
        """
        Public method Returns highest io operation price of all io operations
        """
        
        r=10000000
        for investments_id in self.list_investments_id():
            for o in self.d_io_current(investments_id):
                if o["price_investment"]<r:
                    r=o["price_investment"]
        return r

    def  io_current_last_operation_excluding_additions(self, id):
        """
            Returns last investment operation excluding additions
        """
        for o in reversed(self.d_io_current(id)):
            if o["operationstypes_id"]!=6:# Shares Additions
                return o
        return None

def realmultiplier(pia):
    if pia["productstypes_id"] in (12, 13):
        return pia['multiplier'] 
    return 1

def have_same_sign(a, b):
    if (a>=0 and b>=0) or (a<0 and b<0):
       return True 
    return False

def set_sign_of_other_number (number, number_to_change):
    return abs(number_to_change) if number>=0 else -abs(number_to_change)

def operationstypes(shares):
    return 4 if shares>=0 else 5


## lod_investments query ivestments
## lod_ios query investmentsoperations of investments
def calculate_ios_lazy(datetime, lod_investments, lod_ios, currency_user):
    investments={}
    ios={}

    for row in lod_investments:
        investments[str(row["investments_id"])]=row
        ios[str(row["investments_id"])]=[]
    for row in lod_ios:
        ios[str(row["investments_id"])].append(row)

    ## Total calculated ios
    t={}
    t["lazy_quotes"]={}
    t["lazy_factors"]={}

    for investments_id, investment in investments.items():
        d=calculate_io_lazy(datetime, investment, ios[investments_id], currency_user)
        t["lazy_quotes"].update(d["lazy_quotes"])
        t["lazy_factors"].update(d["lazy_factors"])
        del d["lazy_quotes"]
        del d["lazy_factors"]
        t[str(investments_id)]=d
    return t

def t_keys_not_investment():
    return ["lazy_quotes","lazy_factors", "sum_total_io_current", "sum_total_io_historical","mode","basic_results"]

def calculate_ios_finish(t, mode):
    t["mode"]=mode
    # Is a key too like ios
    t["sum_total_io_current"]={}
    t["sum_total_io_current"]["balance_user"]=0
    t["sum_total_io_current"]["balance_futures_user"]=0
    t["sum_total_io_current"]["gains_gross_user"]=0
    t["sum_total_io_current"]["gains_net_user"]=0
    t["sum_total_io_current"]["invested_user"]=0

    t["sum_total_io_historical"]={}
    t["sum_total_io_historical"]["commissions_account"]=0
    t["sum_total_io_historical"]["gains_net_user"]=0

    for investments_id, d in t.items():
        if investments_id in t_keys_not_investment():
            continue

        t[investments_id]=calculate_io_finish(d, t)

        t["sum_total_io_current"]["balance_user"]=t["sum_total_io_current"]["balance_user"]+t[investments_id]["total_io_current"]['balance_user']
        t["sum_total_io_current"]["balance_futures_user"]=t["sum_total_io_current"]["balance_futures_user"]+t[investments_id]["total_io_current"]['balance_futures_user']
        t["sum_total_io_current"]["gains_gross_user"]=t["sum_total_io_current"]["gains_gross_user"]+t[investments_id]["total_io_current"]['gains_gross_user']
        t["sum_total_io_current"]["gains_net_user"]=t["sum_total_io_current"]["gains_net_user"]+t[investments_id]["total_io_current"]['gains_net_user']
        t["sum_total_io_current"]["invested_user"]=t["sum_total_io_current"]["invested_user"]+t[investments_id]["total_io_current"]['invested_user']
        t["sum_total_io_historical"]["gains_net_user"]=t["sum_total_io_historical"]["gains_net_user"]+t[investments_id]["total_io_historical"]['gains_net_user']
        t["sum_total_io_historical"]["commissions_account"]=t["sum_total_io_historical"]["commissions_account"]+t[investments_id]["total_io_historical"]['commissions_account']

        if mode in (2,3):
            del t[investments_id]["io"]
            del t[investments_id]["io_current"]
            del t[investments_id]["io_historical"]
    
    if mode==3:
        return {"sum_total_io_current": t["sum_total_io_current"], "sum_total_io_historical": t["sum_total_io_historical"], "mode":t["mode"]}

    del t["lazy_factors"]
    del t["lazy_quotes"]
    return t


## lazy_factors id, dt, from, to
## lazy_quotes product, timestamp
def calculate_io_lazy(dt, data,  io_rows, currency_user):
    lazy_quotes={}
    lazy_factors={}
    data["currency_user"]=currency_user
    data["dt"]=dt
    data['real_leverages']= realmultiplier(data)
    
    lazy_quotes[(data['products_id'], dt)]=None
    lazy_factors[(data["currency_product"], data["currency_account"], dt)]=None

    ioh_id=0
    io=[]
    cur=[]
    hist=[]

    for row in io_rows:
        row["currency_account"]=data["currency_account"]
        row["currency_product"]=data["currency_product"]
        row["currency_user"]=data["currency_user"]
        lazy_factors[(data["currency_account"], data["currency_user"],row['datetime'])]=None
        io.append(row)
        if len(cur)==0 or have_same_sign(cur[0]["shares"], row["shares"]) is True:
            cur.append({
                "id":row["id"], 
                "investments_id":row["investments_id"], 
                "datetime":row["datetime"] , 
                "shares": row["shares"], 
                "price_investment": row["price"], 
                "operationstypes_id": row['operationstypes_id'], 
                "taxes_account":row["taxes"], 
                "commissions_account": row["commission"], 
                "investment2account": row["currency_conversion"], 
                "currency_account": data["currency_account"], 
                "currency_product": data["currency_product"], 
                "currency_user":currency_user, 
            }) 
        elif have_same_sign(cur[0]["shares"], row["shares"]) is False:
            rest=row["shares"]
            ciclos=0
            while rest!=0:
                ciclos=ciclos+1
                commissions=0
                taxes=0
                if ciclos==1:
                    commissions=row["commission"]+cur[0]["commissions_account"]
                    taxes=row["taxes"]+cur[0]["taxes_account"]

                if len(cur)>0:
                    if abs(cur[0]["shares"])>=abs(rest):
                        ioh_id=ioh_id+1
                        hist.append({
                            "shares":set_sign_of_other_number(row["shares"],rest),
                            "id":ioh_id, 
                            "investments_id": row["investments_id"], 
                            "dt_start":cur[0]["datetime"], 
                            "dt_end":row["datetime"], 
                            "operationstypes_id": operationstypes(rest), 
                            "commissions_account":commissions, 
                            "taxes_account":taxes, 
                            "price_start_investment":cur[0]["price_investment"], 
                            "price_end_investment":row["price"],
                            "investment2account_start": cur[0]["investment2account"] , 
                            "investment2account_end":row["currency_conversion"] , 
                            "currency_account": data["currency_account"], 
                            "currency_product": data["currency_product"], 
                            "currency_user":currency_user, 
                        })
                        if rest+cur[0]["shares"]!=0:
                            cur.insert(0, {
                                "id":cur[0]["id"], 
                                "investments_id":cur[0]["investments_id"], 
                                "datetime":cur[0]["datetime"] , 
                                "shares": rest+cur[0]["shares"], 
                                "price_investment": cur[0]["price_investment"], 
                                "operationstypes_id": cur[0]['operationstypes_id'], 
                                "taxes_account":cur[0]["taxes_account"], 
                                "commissions_account": cur[0]["commissions_account"], 
                                "investment2account": cur[0]["investment2account"], 
                                "currency_account": data["currency_account"], 
                                "currency_product": data["currency_product"], 
                                "currency_user":currency_user, 
                            }) 
                            cur.pop(1)
                        else:
                            cur.pop(0)
                        rest=0
                        break
                    else:
                        ioh_id=ioh_id+1
                        hist.append({
                            "shares":set_sign_of_other_number(row["shares"],cur[0]["shares"]),
                            "id":ioh_id, 
                            "investments_id": row["investments_id"], 
                            "dt_start":cur[0]["datetime"], 
                            "dt_end":row["datetime"], 
                            "operationstypes_id": operationstypes(row['shares']), 
                            "commissions_account":commissions, 
                            "taxes_account":taxes, 
                            "price_start_investment":cur[0]["price_investment"], 
                            "price_end_investment":row["price"],
                            "investment2account_start":cur[0]["investment2account"], 
                            "investment2account_end":row["currency_conversion"]  , 
                            "currency_account": data["currency_account"], 
                            "currency_product": data["currency_product"], 
                            "currency_user":currency_user, 
                        })

                        rest=rest+cur[0]["shares"]
                        rest=set_sign_of_other_number(row["shares"],rest)
                        cur.pop(0)
                else:
                    cur.insert(0, {
                        "id":row["id"], 
                        "investments_id":row["investments_id"], 
                        "datetime":row["datetime"] , 
                        "shares": rest, 
                        "price_investment": row["price"], 
                        "operationstypes_id": row['operationstypes_id'],
                        "taxes_account":row["taxes"], 
                        "commissions_account": row["commission"], 
                        "investment2account": row["currency_conversion"],
                        "currency_account": data["currency_account"], 
                        "currency_product": data["currency_product"], 
                        "currency_user":currency_user, 
                    }) 
                    break
                    
                    
        
        
                    
    return { "io": io, "io_current": cur,"io_historical":hist, "data":data, "lazy_quotes":lazy_quotes, "lazy_factors": lazy_factors}
    
    
def get_quotes_and_factors(lazy_quotes, lazy_factors):
    """
        d es el resultado de calculate_io_lazy
    """
    for lz in lazy_quotes.keys():
        products_id, datetime_=lz
        r=models.Quotes.get_quote(products_id, datetime_)
        if r is None:
            lazy_quotes[lz]=None
        else:
            lazy_quotes[lz]=r.quote
    for lf in lazy_factors.keys():
        from_, to_, datetime_=lf
        lazy_factors[lf]=models.Quotes.currency_factor(datetime_, from_,  to_)
    return lazy_quotes, lazy_factors



def calculate_io_finish(d, dict_with_lf_and_lq):
    """
        d es el resultado de calculate_io_lazy
        dict_with_lf_and_lq puede ser en d o en t segun sea io o ios
    """
    def lf(from_, to_, dt):
        return dict_with_lf_and_lq["lazy_factors"][(from_, to_, dt)]
        
    def lq(products_id, dt):
        return dict_with_lf_and_lq["lazy_quotes"][(products_id, dt)]
        
    
    data=d["data"]
    
    d["total_io"]={}

    for o in d["io"]:
        account2user=lf(data["currency_account"], data["currency_user"], o["datetime"])
        o['investment2account']=o['currency_conversion']
        o['commission_account']=o['commission']
        o['taxes_account']=o['taxes']
        o['gross_investment']=abs(o['shares']*o['price']*data['real_leverages'])
        o['gross_account']=o['gross_investment']*o['investment2account']
        o['gross_user']=o['gross_account']*account2user
        o['account2user']=account2user
        o['gross_user']=o['gross_account']*account2user
        if o['shares']>=0:
            o['net_account']=o['gross_account']+o['commission_account']+o['taxes_account']
        else:
            o['net_account']=o['gross_account']-o['commission_account']-o['taxes_account']
        o['net_user']=o['net_account']*account2user
        o['net_investment']=o['net_account']/o['investment2account']

    d["total_io_current"]={}
    d["total_io_current"]["balance_user"]=0
    d["total_io_current"]["balance_investment"]=0
    d["total_io_current"]["balance_futures_user"]=0
    d["total_io_current"]["gains_gross_user"]=0
    d["total_io_current"]["gains_net_user"]=0
    d["total_io_current"]["shares"]=0
    d["total_io_current"]["average_price_investment"]=0
    d["total_io_current"]["invested_user"]=0
    d["total_io_current"]["invested_investment"]=0
    sumaproducto=0

    for c in d["io_current"]:
        investment2account_at_datetime=lf(data["currency_product"], data["currency_account"], data["dt"] )
        account2user_at_datetime=lf(data["currency_account"], data["currency_user"], data["dt"])
        account2user=lf(data["currency_account"], data["currency_user"], c["datetime"])
        quote_at_datetime=lq(data["products_id"], data["dt"])
        c['investment2account_at_datetime']=investment2account_at_datetime
        c['account2user_at_datetime']=account2user_at_datetime
        c['account2user']=account2user
        c['price_account']=c['price_investment']*c['investment2account']
        c['price_user']=c['price_account']*account2user
        c['taxes_investment']=c['taxes_account']/c['investment2account']#taxes and commissions are in account currency buy we can guess them
        c['taxes_user']=c['taxes_account']*account2user
        c['commissions_investment']=c['commissions_account']/c['investment2account']
        c['commissions_user']=c['commissions_account']*account2user
        #Si son cfds o futuros el saldo es 0, ya que es un contrato y el saldo todavía está en la cuenta. Sin embargo cuento las perdidas
        c['balance_investment']=0 if d["data"]['productstypes_id'] in (12,13) else abs(c['shares'])*quote_at_datetime*data['real_leverages']
        c['balance_account']=c['balance_investment']*investment2account_at_datetime
        c['balance_user']=c['balance_account']*account2user_at_datetime
        #Aquí calculo con saldo y futuros y cfd
        if c['shares']>0:
            c['balance_futures_investment']=c['shares']*quote_at_datetime*data['real_leverages']
        else:
            diff=(quote_at_datetime-c['price_investment'])*abs(c['shares'])*data['real_leverages']
            init_balance=c['price_investment']*abs(c['shares'])*data['real_leverages']
            c['balance_futures_investment']=init_balance-diff
        c['balance_futures_account']=c['balance_futures_investment']*investment2account_at_datetime
        c['balance_futures_user']=c['balance_futures_account']*account2user_at_datetime
        c['invested_investment']=abs(c['shares']*c['price_investment']*data['real_leverages'])
        c['invested_account']=c['invested_investment']*c['investment2account']
        c['invested_user']=c['invested_account']*account2user
        c['gains_gross_investment']=(quote_at_datetime - c['price_investment'])*c['shares']*data['real_leverages']
        c['gains_gross_account']=(quote_at_datetime*investment2account_at_datetime - c['price_investment']*c['investment2account'])*c['shares']*data['real_leverages']
        c['gains_gross_user']=(quote_at_datetime*investment2account_at_datetime*account2user_at_datetime - c['price_investment']*c['investment2account']*account2user)*c['shares']*data['real_leverages']
        c['gains_net_investment']=c['gains_gross_investment'] -c['taxes_investment'] -c['commissions_investment']
        c['gains_net_account']=c['gains_gross_account']-c['taxes_account']-c['commissions_account'] 
        c['gains_net_user']=c['gains_gross_user']-c['taxes_user']-c['commissions_user']

        d["total_io_current"]["balance_user"]=d["total_io_current"]["balance_user"]+c['balance_user']
        d["total_io_current"]["balance_investment"]=d["total_io_current"]["balance_investment"]+c['balance_investment']
        d["total_io_current"]["balance_futures_user"]=d["total_io_current"]["balance_futures_user"]+c['balance_futures_user']
        d["total_io_current"]["gains_gross_user"]=d["total_io_current"]["gains_gross_user"]+c['gains_gross_user']
        d["total_io_current"]["gains_net_user"]=d["total_io_current"]["gains_net_user"]+c['gains_net_user']
        d["total_io_current"]["shares"]=d["total_io_current"]["shares"]+c['shares']
        d["total_io_current"]["invested_user"]=d["total_io_current"]["invested_user"]+c['invested_user']
        d["total_io_current"]["invested_investment"]=d["total_io_current"]["invested_investment"]+c['invested_investment']     
        sumaproducto=sumaproducto+c['shares']*c["price_investment"] 
    d["total_io_current"]["average_price_investment"]=sumaproducto/d["total_io_current"]["shares"] if d["total_io_current"]["shares"]>0 else 0

    d["total_io_historical"]={}
    d["total_io_historical"]["commissions_account"]=0
    d["total_io_historical"]["gains_net_user"]=0

    for h in d["io_historical"]:
        h['account2user_start']=lf(data["currency_account"], data["currency_user"], h["dt_start"] )
        h['account2user_end']=lf(data["currency_account"], data["currency_user"], h["dt_end"] )
        h['gross_start_investment']=0 if h['operationstypes_id'] in (9,10) else abs(h['shares']*h['price_start_investment']*data['real_leverages'])#Transfer shares 9, 10
        if h['operationstypes_id'] in (9,10):
            h['gross_end_investment']=0
        elif h['shares']<0:#Sell after bought
            h['gross_end_investment']=abs(h['shares'])*h['price_end_investment']*data['real_leverages']
        else:
            diff=(h['price_end_investment']-h['price_start_investment'])*abs(h['shares'])*data['real_leverages']
            init_balance=h['price_start_investment']*abs(h['shares'])*data['real_leverages']
            h['gross_end_investment']=init_balance-diff
        h['gains_gross_investment']=h['gross_end_investment']-h['gross_start_investment']
        h['gross_start_account']=h['gross_start_investment']*h['investment2account_start']
        h['gross_start_user']=h['gross_start_account']*h['account2user_start']
        h['gross_end_account']=h['gross_end_investment']*h['investment2account_end']
        h['gross_end_user']=h['gross_end_account']*h['account2user_end']
        h['gains_gross_account']=h['gross_end_account']-h['gross_start_account']
        h['gains_gross_user']=h['gross_end_user']-h['gross_start_user']

        h['taxes_investment']=h['taxes_account']/h['investment2account_end']#taxes and commissions are in account currency buy we can guess them
        h['taxes_user']=h['taxes_account']*h['account2user_end']
        h['commissions_investment']=h['commissions_account']/h['investment2account_end']
        h['commissions_user']=h['commissions_account']*h['account2user_end']
        h['gains_net_investment']=h['gains_gross_investment']-h['taxes_investment']-h['commissions_investment']
        h['gains_net_account']=h['gains_gross_account']-h['taxes_account']-h['commissions_account']
        h['gains_net_user']=h['gains_gross_user']-h['taxes_user']-h['commissions_user']

        d["total_io_historical"]["commissions_account"]=d["total_io_historical"]["commissions_account"]+h["commissions_account"]
        d["total_io_historical"]["gains_net_user"]=d["total_io_historical"]["gains_net_user"]+h["gains_net_user"]
    return d






