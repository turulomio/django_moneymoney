from base64 import b64encode
from datetime import datetime, timedelta
from decimal import Decimal
from django.core.serializers.json import DjangoJSONEncoder 


def cast_dict(iter_value, decimal_fields, datetime_fields):
    """
        Iterates a dict or list to cast decimals and dtaware in json.loads using objeck_hook
    """
    def cast(k, v):
        if k in decimal_fields and v.__class__==str:
            return Decimal(v)
        if k in datetime_fields and v.__class__==str:
            return postgres_datetime_string_2_dtaware(v)
        return v
    #####
    if isinstance(iter_value, dict):
        for k, v in iter_value.items():
            if isinstance(v, dict):
                iter_value[k]=cast_dict(v, decimal_fields, datetime_fields)
            elif isinstance(iter_value, list):
                for i in v:
                    i=cast_dict(v, decimal_fields, datetime_fields)
            else:
                iter_value[k]=cast(k, v)
    elif isinstance(iter_value, list):
        for i in v:
            i=cast_dict(i, decimal_fields, datetime_fields)
    return iter_value


def loads_hooks_tb(o):
    """
        Function to json.object_hook for total_balance
    """
    return cast_dict(o,  ["accounts_user",'investments_user', 'total_user', 'investments_invested_user'], ["datetime", ])

def loads_hooks_io(o):
    """
        Function to json.object_hook for investment_operations
    """
    return cast_dict(o,  [
        "account2user",
        "account2user_start",
        "account2user_end",
        "accounts_user",
        "account2user_at_datetime",
        "average_price_investment",
        "balance_futures_account",
        "balance_futures_investment",
        "balance_futures_user",
        "balance_account",
        "balance_investment",
        "balance_user",
        "commission",
        "commission_account",
        "commissions_account",
        "commissions_investment",
        "commissions_user",
        "currency_conversion",
        "gains_gross_account",
        "gains_gross_investment",
        "gains_gross_user", 
        "gains_net_account",
        "gains_net_investment",
        "gains_net_user",
        "gross_account",
        "gross_investment",
        "gross_end_account",
        "gross_end_investment",
        "gross_end_user",
        "gross_start_account",
        "gross_start_investment",
        "gross_start_user",
        "gross_user",
        "invested_account",
        "invested_investment",
        'invested_user',
        "investment2account", 
        "investment2account_at_datetime",
        "investment2account_start",
        "investment2account_end",
        'investments_user', 
        "multiplier",
        "net_account",
        "net_investment",
        "net_user",
        "price",
        "price_account",
        "price_end_investment",
        "price_investment",
        "price_start_investment",
        "price_user",
        "shares", 
        "taxes",
        "taxes_account",
        "taxes_investment",
        "taxes_user",
        'total_user', 
        'investments_invested_user'
    ], [
        "datetime", 
        "dt_end", 
        "dt_start", 
        "dt"
    ])


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

        t[investments_id]=calculate_io_finish(t, d, mode)

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
def postgres_datetime_string_2_dtaware(s):
    if s is None:
        return None
    arrPlus=s.split("+")
    zone=arrPlus[1]
    
    arrPunto=arrPlus[0].split(".")
    if len(arrPunto)==2:
        naive=arrPunto[0]
        micro=str(arrPunto[1])
    else:
        naive=arrPunto[0]
        micro='0'
    micro=int(micro+ '0'*(6-len(micro)))
    dt=datetime.strptime( naive+"+"+zone+":00", "%Y-%m-%d %H:%M:%S%z" )
    dt=dt+timedelta(microseconds=micro)
    return dt

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

def calculate_io_finish(t, d, mode):
    def lf(from_, to_, dt):
        return t["lazy_factors"][(from_, to_, dt)]
        
    def lq(products_id, dt):
        return t["lazy_quotes"][(products_id, dt)]
        
    
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
