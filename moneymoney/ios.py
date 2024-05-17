from datetime import date, datetime
from decimal import Decimal
from json import dumps
from logging import debug, error
from moneymoney import models
from pydicts.percentage import Percentage, percentage_between
from pydicts.myjsonencoder import MyJSONEncoderDecimalsAsFloat
from pydicts import lod
from django.utils.translation import gettext_lazy as _


class IOSModes:
    sumtotals=3 #Shows only sumtotals
    totals_sumtotals=2 #Shows totals and sumtotals
    ios_totals_sumtotals=1 #Shows io,totals and sumtotals
    

class IOSTypes:
    from_qs=1
    from_qs_merging_io_current=2

def NoZ(v):
    """
        Returns a boolean if v is None or Zero
    """
    if v is None or v==0:
        return True
    return False

class IOS:
    """
        Class to operate with Assets.pl_investment_operations result
        La idea es generar una clase IOS usando funciones estáticas en classmethods( from_qs...)
        Estas classmethods devuelven objetos IOS
        
        Es decir se encapsula todo
        
        
        Si necesita añadir algún valor, se puede añadir a los diccionarios y luego hacer un response con ios.t() o lo que sea
    """
    def __init__(self, t):
        self._t=t

    @staticmethod
    def __ioc_percentage_annual_investment(d, ioc):
        """
        Public method ioc is a io_current dictionary
        """
        basic_results=d["data"]["basic_results"]
        if ioc["datetime"].year==date.today().year:
            lastyear=ioc["price_investment"] #Product value, self.money_price(type) not needed.
        else:
            lastyear=basic_results["lastyear"]
        if basic_results["lastyear"] is None or lastyear is None:
            return Percentage()

        if ioc["shares"]>0:
            return Percentage(basic_results["last"]-Decimal(lastyear), lastyear)
        else:
            return Percentage(-(basic_results["last"]-Decimal(lastyear)), lastyear)
            
    @staticmethod
    def __ioc_percentage_annual_user(d, ioc):
        """
        Public method ioc is a io_current dictionary
            o['investment2account']=o['currency_conversion']
        """
        basic_results=d["data"]["basic_results"]
        if ioc["datetime"].year==date.today().year:
            lastyear=ioc["price_user"] 
            if lastyear is None:
                return Percentage()
        else:
            if basic_results["lastyear"] is None:
                return Percentage()
            lastyear=basic_results["lastyear"]*ioc["investment2account"]*ioc["account2user"]

        last=basic_results["last"]*ioc["investment2account"]*ioc["account2user"]

        if ioc["shares"]>0:
            return Percentage(last-Decimal(lastyear), lastyear)
        else:
            return Percentage(-(last-Decimal(lastyear)), lastyear)

    def ioc_percentage_sellingpoint(self, ioc, selling_price):
        if selling_price is None or selling_price==0:
            return Percentage()
        return percentage_between(self.basic_results(ioc["investments_id"])["last"], selling_price)

    def total_io_current_percentage_sellingpoint(self, id, selling_price):
        if selling_price is None or selling_price==0:
            return Percentage()
        return percentage_between(self.d_basic_results(id)["last"], selling_price)
        
    @staticmethod
    def __ioc_days(ioc):
        days=(date.today()-ioc["datetime"].date()).days
        if days==0:
            return 1
        return days
    @staticmethod
    def __ioh_years(ioh):
        return round(Decimal((ioh["dt_end"]-ioh["dt_start"]).days/365), 2)
    
    def mode(self):
        return self._t["mode"]
        
    def entries(self):
        return self._t["entries"]
        
    def qs_investments(self):
        return models.Investments.objects.filter(id__in = self.entries()).select_related("accounts")
        
    def d(self, id_):
        return self._t[str(id_)]
        
    def t(self):
        return self._t
        
    def type(self):
        return self._t["type"]
        
    def d_data(self, id_):
        return self._t[str(id_)]["data"]

    def d_basic_results(self, id_):
        return self._t[str(id_)]["data"]["basic_results"]

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

    def sum_total_io_current_zerorisk_user(self):
        """
            Returns a decimal with zerorisk 
        """
        if IOSModes.sumtotals==self.mode():
            error( _("You need total mode to calculate sum_total_io_current_zerorisk_user"))
            return
        
        r=Decimal(0)
        for investments_id in self.entries():
            if self.d_data(investments_id)["variable_percentage"]==0:
                r=r+self.d_total_io_current(investments_id)["balance_user"]
        return r

    def investment(self, id_):
        return models.Investments.objects.get(pk=id_)
        
    def dumps(self):
        return dumps(self._t,  indent=4,  cls=MyJSONEncoderDecimalsAsFloat )
        
    def print_dumps(self):
        print(self.dumps())
        
    def print(self):
        print("Printing IOS")
        print(f" - type: {self.type()}")
        print(f" - Entries: {self.entries()}")
        
    def print_d(self, id):
        print(f"*** IO {id} ***")
        lod.lod_print(self.d(id)["io"])
        print(f"*** IO CURRENT {id} ***")
        lod.lod_print(self.d(id)["io_current"])
        print(f"*** IO HISTORICAL {id} ***")
        lod.lod_print(self.d(id)["io_historical"])
        print(f"*** TOTAL IO {id} ***")
        lod.lod_print([self.d_total_io(id), ])
        print(f"*** TOTAL IO CURRENT {id} ***")
        lod.lod_print([self.d_total_io_current(id), ])
        print(f"*** TOTAL IO HISTORICAL {id} ***")
        lod.lod_print([self.d_total_io_historical(id), ])
        
        
    def io_historical_sum_between_dt(self, dt_from, dt_to,  key, productstypes_id=None):
        r=0
        for investments_id in self.entries():
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
        for investments_id in self.entries():
            for o in self.d_io(investments_id):
                if dt_from<=o["datetime"] and o["datetime"]<=dt_to:
                    r=r - o[key]
        return r
        
    def io_current_addition_current_year_gains(self):
        """
            Calculates current_year_gains of all entries and adds them to d_io_current
            Returns a Decimal with the gains of this investment operation
                - If io is newer than last year datetime. Returns gains from bought datetime
                - If not returns gains from last year datetime
            
        """
        sum_total_investment=Decimal(0)
        sum_total_account=Decimal(0)
        sum_total_user=Decimal(0)
        for entry in self.entries():
            for o in self.d_io_current(entry):
                if o["datetime"]<=self.d_basic_results(entry)["lastyear_datetime"]: #Bought before lastyear
                    o["current_year_gains_investment"]=o["shares"]*(self.d_basic_results(entry)["last"]-self.d_basic_results(entry)["lastyear"])
                else:
                    o["current_year_gains_investment"]=o["shares"]*(self.d_basic_results(entry)["last"]-o["price_investment"])
                o["current_year_gains_account"]=o["current_year_gains_investment"]*o["investment2account"]
                o["current_year_gains_user"]=o["current_year_gains_account"]*o["account2user"]
        
            self.d_total_io_current(entry)["current_year_gains_investment"]=lod.lod_sum(self.d_io_current(entry), "current_year_gains_investment")
            self.d_total_io_current(entry)["current_year_gains_account"]=lod.lod_sum(self.d_io_current(entry), "current_year_gains_account")
            self.d_total_io_current(entry)["current_year_gains_user"]=lod.lod_sum(self.d_io_current(entry), "current_year_gains_user")
            
            sum_total_investment+=self.d_total_io_current(entry)["current_year_gains_investment"]
            sum_total_account+=self.d_total_io_current(entry)["current_year_gains_account"]
            sum_total_user+=self.d_total_io_current(entry)["current_year_gains_user"]
        
        self.sum_total_io_current()["current_year_gains_investment"]=sum_total_investment
        self.sum_total_io_current()["current_year_gains_account"]=sum_total_account
        self.sum_total_io_current()["current_year_gains_user"]=sum_total_user
            
                

    def io_current_highest_price(self):
        """
            Returns highest io operation price of all io operations
        """
        
        r=0
        for investments_id in self.entries():
            for o in self.d_io_current(investments_id):
                if o["price_investment"]>r:
                    r=o["price_investment"]
        return r
    def io_current_lowest_price(self):
        """
            Returns highest io operation price of all io operations
        """
        
        r=10000000
        for investments_id in self.entries():
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

    @classmethod
    def from_qs(cls, dt,  local_currency,  qs_investments,  mode, simulation=[]):
        """
            simulation is a list of dictionary of ios if you want to simulate
            
                {'id': 3, 'operationstypes_id': 4, 'investments_id': 2, 'shares': Decimal('1000.000000'), 'taxes': Decimal('0.00'), 'commission': Decimal('0.00'), 'price': Decimal('10.000000'), 'datetime': datetime.datetime(2023, 7, 23, 6, 4, 4, 934773, tzinfo=datetime.timezone.utc), 'comment': '', 'currency_conversion': Decimal('1.0000000000')}
        """
#        s=datetime.now()
        qs_investments=qs_investments.select_related("products", "products__leverages", "products__productstypes", "accounts")
        lod_investments=IOS.__qs_investments_to_lod(qs_investments, local_currency)
        lod_=models.Investmentsoperations.objects.filter(investments__in=qs_investments, datetime__lte=dt).order_by("datetime").values()
#        print(list(lod_))
#        print(simulation)
        lod_=list(lod_)+simulation
        
        t=IOS.__calculate_ios_lazy(dt, lod_investments,  lod_,  local_currency)
        
        t["r_lazy_quotes"]=IOS.__get_all_quotes(t)
        
        t=IOS.__calculate_ios_finish(t, mode)
        t["type"]=IOSTypes.from_qs

        #Set entries name
        if mode in [IOSModes.ios_totals_sumtotals, IOSModes.totals_sumtotals]:
            for investment in qs_investments:
                t[str(investment.id)]["data"]["name"]=investment.fullName()
#        print("IOS FROM QS", datetime.now()-s)
        return cls(t)

    @classmethod
    def from_ids(cls,  dt,  local_currency,  list_ids,  mode, simulation=[]):
        """
            Ids de inverstments
        """
        qs_investments=models.Investments.objects.filter(id__in=list_ids)
        return cls.from_qs(dt, local_currency, qs_investments, mode, simulation)


    @classmethod
    def from_all(cls,  dt,  local_currency,  mode, simulation=[]):
        return cls.from_qs(dt, local_currency, models.Investments.objects.all(), mode, simulation)
    
    @staticmethod
    def __qs_investments_to_lod(qs, currency_user):
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
                "variable_percentage": i.products.percentage, 
            })
        return r
#        
#    @staticmethod
#    def __qs_investments_to_lod_ios(qs):
#        """
#            Converts a list of unsaved investmentsoperations to a lod_ios used in moneymoney_pl
#        """
#        r=[]
#        ids=tuple(qs.values_list('pk',flat=True))
#        for i, io in enumerate(models.Investmentsoperations.objects.filter(investments_id__in=ids).order_by("datetime")):
#            r.append({
#                "id":-i, 
#                "operationstypes_id": io.operationstypes.id, 
#                "investments_id": str(io.investments.id), 
#                "shares": io.shares, 
#                "taxes": io.taxes, 
#                "commission": io.commission, 
#                "price": io.price, 
#                "datetime": io.datetime, 
#                "comment": io.comment, 
#                "currency_conversion":io.currency_conversion
#            })
#        return r

    @classmethod
    def from_qs_merging_io_current(cls, dt,  local_currency,  qs_investments, mode, simulation=[]):
        """
            Return a plio merging in same virtual (negative) id all investments in qs with same product
            only io_current and io_historical
            
            To simulate see test.py example
            
        """

        s=datetime.now()
        old_ios=cls.from_qs(dt, local_currency, qs_investments, IOSModes.ios_totals_sumtotals)#Must have ios, although result can be other mode
        
        # Sets a dictionary with key products_id and values all investments_id of this products to set at the end
        investments_id_in_each_product={}
        for inv in qs_investments:
            if inv.products_id in investments_id_in_each_product:
                investments_id_in_each_product[str(inv.products.id)].append(inv.id)
            else:#Not set yet
                investments_id_in_each_product[str(inv.products.id)]=[inv.id, ]
            
        
        # Preparing lod_data 
        products={}#Temp dictionary
        for investments_id in old_ios.entries():
            d=old_ios.d_data(investments_id)
            products[d["products_id"]]={
                "name": f"Merging product {d['products_id']}", 
                "products_id": d["products_id"], 
                "investments_id": d["products_id"], 
                "multiplier": d["multiplier"], 
                "currency_account": d["currency_account"], 
                "currency_product": d["currency_product"], 
                "currency_user": local_currency, 
                "productstypes_id": d["productstypes_id"], 
            }
                
        lod_data=lod.dod2lod(products)
        

        #preparing lod_investments
        
        lod_io=[]
        for investments_id in old_ios.entries():
            lod_io_current=old_ios.d_io_current(investments_id)
            data_investments_id=old_ios.d_data(investments_id)

            for o in lod_io_current:
                lod_io.append({
                    "id":o["id"], 
                    "operationstypes_id": o["operationstypes_id"], 
                    "investments_id": data_investments_id["products_id"], #Now is products_id
                    "shares": o["shares"], 
                    "taxes": o["taxes_investment"], 
                    "commission": o["commissions_investment"], 
                    "price": o["price_investment"], 
                    "datetime": o["datetime"], 
                    "comment": o["investments_id"], # I set the original investments_id before merge 
                    "currency_conversion": o["investment2account"], 
                })
        lod_io=lod.lod_order_by(lod_io, "datetime")
#        print(lod_io)
#        print(simulation)
        lod_io=lod_io+simulation

        #Generating new_t
        t=IOS.__calculate_ios_lazy(dt, lod_data,  lod_io,  local_currency)

        #Now I have to add io_historical before merging 
        for investments_id in old_ios.entries():
            products_id=old_ios.d_data(investments_id)["products_id"]
            for old_ioh in old_ios.d_io_historical(investments_id):
                old_ioh["investments_id"]=products_id
                t[str(products_id)]["io_historical"].append(old_ioh)
                ##Añado factors y quotes
                t["lod_lazy_quotes"].append({"products_id":products_id, "datetime": old_ioh["dt_start"]})
                t["lod_lazy_quotes"].append({"products_id":products_id, "datetime": old_ioh["dt_end"]})
                if old_ioh["currency_product"]!=old_ioh["currency_account"]:
                    t["lod_lazy_quotes"].append(models.Quotes.get_quote_dictionary_for_currency_factor(old_ioh["dt_start"], old_ioh["currency_product"], old_ioh["currency_account"]))
                    t["lod_lazy_quotes"].append(models.Quotes.get_quote_dictionary_for_currency_factor(old_ioh["dt_end"], old_ioh["currency_product"], old_ioh["currency_account"]))
                if old_ioh["currency_account"]!=old_ioh["currency_user"]:
                    t["lod_lazy_quotes"].append(models.Quotes.get_quote_dictionary_for_currency_factor(old_ioh["dt_start"], old_ioh["currency_account"], old_ioh["currency_user"]))
                    t["lod_lazy_quotes"].append(models.Quotes.get_quote_dictionary_for_currency_factor(old_ioh["dt_end"], old_ioh["currency_account"], old_ioh["currency_user"]))
            t[str(products_id)]["io_historical"]=lod.lod_order_by(t[str(products_id)]["io_historical"], "dt_end")
            
        # I make ios_finish after to get old io_historical too in results
        t["r_lazy_quotes"]=IOS.__get_all_quotes(t)
        
        t=IOS.__calculate_ios_finish(t, mode)
        
        
        #Set entries name for product, iterating all investments. Redundant but simpler
        if mode in [IOSModes.ios_totals_sumtotals, IOSModes.totals_sumtotals]:
            for old_investment in qs_investments:
                t[str(old_investment.products.id)]["data"]["name"]=_("IOC merged investment of '{0}'").format( old_investment.products.fullName()) 
                t[str(old_investment.products.id)]["data"]["investments_id"]=investments_id_in_each_product[str(old_investment.products.id)]
                debug("IOS FROM QS MERGING ", datetime.now()-s)
        return cls(t)




    ## lazy_factors id, dt, from, to
    ## lazy_quotes product, timestamp
    @staticmethod
    def __calculate_io_lazy( dt, data,  io_rows, currency_user):
        lod_lazy_quotes=[]
        data["currency_user"]=currency_user
        data["dt"]=dt
        data['real_leverages']= IOS.__realmultiplier(data)
        
        lod_lazy_quotes.append({"datetime":dt, "products_id":data["products_id"]})
        if data["currency_product"]!=data["currency_account"]:
            lod_lazy_quotes.append(models.Quotes.get_quote_dictionary_for_currency_factor(dt, data["currency_product"], data["currency_account"]))

        ioh_id=0
        io=[]
        cur=[]
        hist=[]

        for row in io_rows:
            row["currency_account"]=data["currency_account"]
            row["currency_product"]=data["currency_product"]
            row["currency_user"]=data["currency_user"]
            if data["currency_account"]!=data["currency_user"]:
                lod_lazy_quotes.append(models.Quotes.get_quote_dictionary_for_currency_factor(row['datetime'], data["currency_account"], data["currency_user"]))
            io.append(row)
            if len(cur)==0 or IOS.__have_same_sign(cur[0]["shares"], row["shares"]) is True:
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
            elif IOS.__have_same_sign(cur[0]["shares"], row["shares"]) is False:
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
                                "shares":IOS.__set_sign_of_other_number(row["shares"],rest),
                                "id":ioh_id, 
                                "investments_id": row["investments_id"], 
                                "dt_start":cur[0]["datetime"], 
                                "dt_end":row["datetime"], 
                                "operationstypes_id": IOS.__operationstypes(rest), 
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
                                "shares":IOS.__set_sign_of_other_number(row["shares"],cur[0]["shares"]),
                                "id":ioh_id, 
                                "investments_id": row["investments_id"], 
                                "dt_start":cur[0]["datetime"], 
                                "dt_end":row["datetime"], 
                                "operationstypes_id": IOS.__operationstypes(row['shares']), 
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
                            rest=IOS.__set_sign_of_other_number(row["shares"],rest)
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
                        
                        
            
            
                        
        return { "io": io, "io_current": cur,"io_historical":hist, "data":data, "lod_lazy_quotes": lod_lazy_quotes}

    @staticmethod
    def __calculate_io_finish(d, r_lazy_quotes):
        """
            d es el resultado de __calculate_io_lazy
            dict_with_lf_and_lq puede ser en d o en t segun sea io o ios
        """
        def lf(from_, to_, dt):
            #Parece que el error es por mal from_, to_
#            try:
                return models.Quotes.get_currency_factor(dt,  from_, to_, r_lazy_quotes)
#            except:
#                print(dict_with_lf_and_lq["lazy_factors"])
#                print("No encontrado", (from_,  to_,  dt),  dt.__class__)
            
        def lq(products_id, dt):
            return r_lazy_quotes[products_id][dt]["quote"]
            
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
            c['percentage_total_investment'] = Percentage() if NoZ(c["invested_investment"]) else Percentage(c['gains_gross_investment'], c['invested_investment']) 
            c['percentage_apr_investment']=Percentage() if NoZ(c["percentage_total_investment"].value) else Percentage(c['percentage_total_investment'].value*365, IOS.__ioc_days(c))
            c['percentage_annual_investment']=IOS.__ioc_percentage_annual_investment(d, c)
            c['percentage_total_user'] = Percentage() if NoZ(c["invested_user"]) else Percentage(c['gains_gross_user'], c['invested_user']) 
            c['percentage_apr_user']=Percentage() if NoZ(c["percentage_total_user"].value) else Percentage(c['percentage_total_user'].value*365, IOS.__ioc_days(c))
            c['percentage_annual_user']=IOS.__ioc_percentage_annual_user(d, c)
            
            
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
        d['total_io_current']['percentage_total_user'] = Percentage() if NoZ(d['total_io_current']["invested_user"]) else Percentage(d['total_io_current']['gains_gross_user'], d['total_io_current']['invested_user']) 

        d["total_io_historical"]={}
        d["total_io_historical"]["commissions_account"]=0
        d["total_io_historical"]["gains_net_user"]=0

        for h in d["io_historical"]:
            h['years']=IOS.__ioh_years(h)
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







    @staticmethod
    def __realmultiplier(pia):
        if pia["productstypes_id"] in (12, 13):
            return pia['multiplier'] 
        return 1

    @staticmethod
    def __have_same_sign(a, b):
        if (a>=0 and b>=0) or (a<0 and b<0):
           return True 
        return False

    @staticmethod
    def __set_sign_of_other_number (number, number_to_change):
        return abs(number_to_change) if number>=0 else -abs(number_to_change)

    @staticmethod
    def __operationstypes(shares):
        return 4 if shares>=0 else 5

    @staticmethod
    def __get_all_quotes( t):       
        """
            Makes Three queries 2 for basic_results 1 for the rest. I thin It's not necesary to join in 2. They are different
        """
        products_ids=set()
        for entry in t["entries"]:
            products_ids.add(t[str(entry)]["data"]["products_id"])
        products_ids=list(products_ids)
        r_basic_results=models.Products.basic_results_from_list_of_products_id(products_ids)
        for entry in t["entries"]:
            t[entry]["data"]["basic_results"]=r_basic_results[int(t[entry]["data"]["products_id"])]
            
        return models.Quotes.get_quotes(t["lod_lazy_quotes"])

    ## lod_investments query ivestments
    ## lod_ios query investmentsoperations of investments
    @staticmethod
    def __calculate_ios_lazy( datetime, lod_investments, lod_ios, currency_user):
        investments={}
        ios={}

        for row in lod_investments:
            investments[str(row["investments_id"])]=row
            ios[str(row["investments_id"])]=[]
        for row in lod_ios:
            ios[str(row["investments_id"])].append(row)

        ## Total calculated ios
        t={}
        t["lod_lazy_quotes"]=[]
        t["entries"]=[] #All ids to enter in ios_id

        for investments_id, investment in investments.items():
            t["entries"].append(investments_id)
            d=IOS.__calculate_io_lazy(datetime, investment, ios[investments_id], currency_user)
            t["lod_lazy_quotes"]+=d["lod_lazy_quotes"]
            del d["lod_lazy_quotes"]
            t[str(investments_id)]=d
        
        return t


    @staticmethod
    def __calculate_ios_finish(t, mode):
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

        for investments_id in t["entries"]:
            t[investments_id]=IOS.__calculate_io_finish(t[investments_id], t["r_lazy_quotes"])

            t["sum_total_io_current"]["balance_user"]=t["sum_total_io_current"]["balance_user"]+t[investments_id]["total_io_current"]['balance_user']
            t["sum_total_io_current"]["balance_futures_user"]=t["sum_total_io_current"]["balance_futures_user"]+t[investments_id]["total_io_current"]['balance_futures_user']
            t["sum_total_io_current"]["gains_gross_user"]=t["sum_total_io_current"]["gains_gross_user"]+t[investments_id]["total_io_current"]['gains_gross_user']
            t["sum_total_io_current"]["gains_net_user"]=t["sum_total_io_current"]["gains_net_user"]+t[investments_id]["total_io_current"]['gains_net_user']
            t["sum_total_io_current"]["invested_user"]=t["sum_total_io_current"]["invested_user"]+t[investments_id]["total_io_current"]['invested_user']
            t["sum_total_io_historical"]["gains_net_user"]=t["sum_total_io_historical"]["gains_net_user"]+t[investments_id]["total_io_historical"]['gains_net_user']
            t["sum_total_io_historical"]["commissions_account"]=t["sum_total_io_historical"]["commissions_account"]+t[investments_id]["total_io_historical"]['commissions_account']

            if mode in (IOSModes.totals_sumtotals, IOSModes.sumtotals):
                del t[investments_id]["io"]
                del t[investments_id]["io_current"]
                del t[investments_id]["io_historical"]
        
        if mode==IOSModes.sumtotals:
            return {"sum_total_io_current": t["sum_total_io_current"], "sum_total_io_historical": t["sum_total_io_historical"], "mode":t["mode"]}

        del t["lod_lazy_quotes"]
        del t["r_lazy_quotes"]
        return t
        
    def distinct_products_id(self):
        """
            Returns all distinct data.products_id from al entries
        """
        products=set()#Son los ids del ios_
        for entry in self.entries():
            products.add(entry["data"]["products_id"])
        return list(products)
