from datetime import date
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from moneymoney.reusing.libmanagers import ObjectManager, DatetimeValueManager
from moneymoney import models, investment_operations
from moneymoney.reusing.percentage import Percentage

class ProductRange():
    def __init__(self, request,  id=None,  product=None,  value=None, percentage_down=None,  percentage_up=None, totalized_operations=True, decimals=2):
        self.request=request
        self.id=id
        self.product=product
        self.value=value
        self.percentage_down=percentage_down
        self.percentage_up=percentage_up
        self.totalized_operations=totalized_operations
        self.decimals=decimals
        self.recomendation_invest=False
        self.recomendation_reinvest=False
        
    def __repr__(self):
        return "({}, {}]".format(
            round(self.range_lowest_value(),  self.decimals), 
            round(self.range_highest_value(), self.decimals), 
        )
    
    ## Returns the value rounded to the number of decimals
    def value_rounded(self):
        return round(self.value, self.decimals)
        
    ## Return th value of the range highest value.. Points + percentage/2
    def range_highest_value(self):
        points_to_next_high= self.value/(1-self.percentage_down.value)-self.value
        return self.value+points_to_next_high/2

    ## Return th value of the range highest value.. Points + percentage/2
    def range_lowest_value(self):
        points_to_next_low=self.value-self.value*(1-self.percentage_down.value)
        return self.value-points_to_next_low/2
        
    ## @return Boolean if it's inside the range
    def isInside(self, value):
        if value<self.range_highest_value() and value>=self.range_lowest_value():
            return True
        else:
            return False

        
    ## Search for investments in self.mem.data and 
    def getInvestmentsOperationsInsideJson(self, plio):
        r=[]
        if self.totalized_operations is True:
            for investment in plio.qs_investments():
                if self.isInside(plio.d_total_io_current(investment.id)["average_price_investment"]) is True:
                    r.append({
                        "url":self.request.build_absolute_uri(reverse('investments-detail', args=(investment.pk, ))), 
                        "id": investment.pk, 
                        "name": investment.fullName(), 
                        "invested": plio.d_total_io_current(investment.id)["invested_user"], 
                        "currency": investment.products.currency, 
                        "active": investment.active, 
                        "selling_price": investment.selling_price, 
                        "daily_adjustment": investment.daily_adjustment, 
                        "selling_expiration": investment.selling_expiration, 
                        "products": self.request.build_absolute_uri(reverse('products-detail', args=(investment.products.pk, ))), 
                        "accounts": self.request.build_absolute_uri(reverse('accounts-detail', args=(investment.accounts.pk, ))), 
                    })
        else: #Shows all investments operations in each range
            for investment in plio.qs_investments():
                for op in plio.d_io_current(investment.id):
                    if self.isInside(op["price_investment"]) is True:
                        r.append({
                            "url":self.request.build_absolute_uri(reverse('investments-detail', args=(investment.pk, ))), 
                            "id": investment.pk, 
                            "name": investment.fullName(), 
                            "invested": op[ 'invested_user'], 
                            "currency": investment.products.currency, 
                            "active": investment.active, 
                            "selling_price": investment.selling_price, 
                            "daily_adjustment": investment.daily_adjustment, 
                            "selling_expiration": investment.selling_expiration, 
                            "products": self.request.build_absolute_uri(reverse('products-detail', args=(investment.products.pk, ))), 
                            "accounts": self.request.build_absolute_uri(reverse('accounts-detail', args=(investment.accounts.pk, ))), 
                        })

        return r
        
    ## Search for orders in self.mem.data and 
    def getOrdersInsideJson(self, orders): 
        r=[]
        for o in orders:
            if o.investments.products.id==self.product.id and self.isInside(o.price)==True:
                r.append({
                    "name": o.investments.fullName(), 
                    "amount": o.currency_amount().amount, 
                })
        return r

## @param is a queryset of investments
## @param additional_ranges. Number ranges to show over and down calculated limits

class ProductRangeManager(ObjectManager):
    def __init__(self, request, product, percentage_down, percentage_up, totalized_operations=True, decimals=2, qs_investments=[], additional_ranges=3):
        ObjectManager.__init__(self)
        self.totalized_operations=totalized_operations
        self.request=request
        self.product=product
        self.qs_investments=qs_investments
        self.percentage_down=Percentage(percentage_down, 100)
        self.percentage_up=Percentage(percentage_up, 100)
        self.decimals=decimals
        self.method=0
        
        self.plio=investment_operations.PlInvestmentOperations.from_qs( timezone.now(), request.user.profile.currency, self.qs_investments,  1)

        self.orders=models.Orders.objects.select_related("investments", "investments__accounts","investments__products","investments__products__leverages","investments__products__productstypes")\
            .filter(investments__in=self.qs_investments, executed=None)\
            .filter(Q(expiration__gte=date.today()) | Q(expiration__isnull=True))

        self.tmp=[]
        self.highest_range_value=10000000
        current_value=self.highest_range_value
        i=0
        range_lowest=0.000001
        while current_value>range_lowest:
            self.tmp.append(ProductRange(self.request,  i, self.product,current_value, self.percentage_down, percentage_up, self.totalized_operations))
            current_value=current_value*(1-self.percentage_down.value)
            i=i+1
        
        #Calculate max_ price and min_price. last price and orders is valorated too 
        max_=self.plio.io_current_highest_price()
        min_=self.plio.io_current_lowest_price()
        if product.quote_last().quote> max_:
            max_=product.quote_last().quote
        if product.quote_last().quote< min_:
            min_=product.quote_last().quote
        for o in self.orders:
            if o.investments.products.id==self.product.id:
                if o.price>max_:
                    max_=o.price
                if o.price<min_:
                    min_=o.price
        
        # Calculate array index and generates arr
        if max_ is not None and min_ is not None: #Investment with shares
            top_index= self.getTmpIndexOfValue(max_)-additional_ranges-1
            bottom_index= self.getTmpIndexOfValue(min_)+additional_ranges+1
        else: # No investment jet and shows ranges from product current price
            current_index=self.getTmpIndexOfValue(self.product.quote_last().quote)
            top_index=current_index-additional_ranges-1
            bottom_index=current_index+additional_ranges+1
        self.arr=self.tmp[top_index:bottom_index]

    def getTmpIndexOfValue(self, value):
        for index,  pr in enumerate(self.tmp):
            if pr.isInside(value) is True:
                return index
        return None

    ## @return LIst of range values of the manager
    def list_of_range_values(self):
        return self.list_of("value")


    ## Returns a list of sma from smas, which dt values are over price parameter
    ## @param dt. datetime
    ## @param price Decimal to compare
    ## @param smas List of integers with the period of the sma
    ## @param dvm_smas. List of DatetimeValueManager with the SMAS with integers are in smas
    ## @param attribute. Can be "open", "high", "close","low"
    ## @return int. With the number of standard sma (10, 50,200) that are over product current price
    def list_of_sma_over_price(self,  dt, price, smas=[10, 50, 200], dvm_smas=None, attribute="close"):
        if dvm_smas==None:#Used when I only neet to calculate one value
            dvm=self.DatetimeValueManager(attribute)
        
            #Calculate smas for all values in smas
            dvm_smas=[]#Temporal list to store sma to fast calculations
            for sma in smas:
                dvm_smas.append(dvm.sma(sma))
            
        # Compare dt sma with price and return a List with smas integers
        r=[]
        for i, dvm_sma in enumerate(dvm_smas):
            sma_value=dvm_sma.find_le(dt)
            if sma_value is not None and  price<sma_value.value:
                r.append(smas[i])
        return r


    
    def list_of_sma_of_current_method(self):
        if self.method in (0, 1):#ProductRangeInvestRecomendation. None_:
            return []
        elif self.method in (2, 4):#ProductRangeInvestRecomendation.ThreeSMA:      
            return [10, 50, 200]
        elif self.method in (3, 5): #ProductRangeInvestRecomendation.SMA100:           
            return [100, ]
        elif self.method==6:#ProductRangeInvestRecomendation.Strict SMA 10 , 100:      
            return [10,  100]

    ## Set investment recomendations to all ProductRange objects in array 
    def setInvestRecomendation(self, method):
        self.method=int(method)
        if self.method==0:#ProductRangeInvestRecomendation. None_:
            for o in self.arr:
                o.recomendation_invest=False
        elif self.method==1:#ProductRangeInvestRecomendation.All:
            for o in self.arr:
                o.recomendation_invest=True
        elif self.method==2:#ProductRangeInvestRecomendation.ThreeSMA:      
            list_ohcl=self.product.ohclDailyBeforeSplits()
            dvm=DatetimeValueManager()
            for d in list_ohcl:
                dvm.appendDV(d["date"], d["close"])
            dvm_smas=[]
            for sma in [10, 50, 200]:
                dvm_smas.append(dvm.sma(sma))
            
            for o in self.arr:
                number_sma_over_price=len(self.list_of_sma_over_price(date.today(), o.value, [10, 50, 200], dvm_smas,  "close"))
                if number_sma_over_price==3 and o.id % 4==0:
                    o.recomendation_invest=True
                elif number_sma_over_price==2 and o.id %2==0:
                    o.recomendation_invest=True
                elif number_sma_over_price<=1:
                    o.recomendation_invest=True
        elif self.method==3: #ProductRangeInvestRecomendation.SMA100:           
            list_ohcl=self.product.ohclDailyBeforeSplits()
            dvm=DatetimeValueManager()
            for d in list_ohcl:
                dvm.appendDV(d["date"], d["close"])
            dvm_smas=[]
            for sma in [100, ]:
                dvm_smas.append(dvm.sma(sma))
            
            for o in self.arr:
                number_sma_over_price=len(self.list_of_sma_over_price(date.today(), o.value, [100, ], dvm_smas,  "close"))
                if number_sma_over_price==0:
                    o.recomendation_invest=True
                elif number_sma_over_price==1 and o.id % 4==0:
                    o.recomendation_invest=True
                else: #number_sma_over_price=1 and o.id%4!=0
                    o.recomendation_invest=False
        elif self.method==4:#ProductRangeInvestRecomendation.StrictThreeSMA:      
            list_ohcl=self.product.ohclDailyBeforeSplits()
            dvm=DatetimeValueManager()
            for d in list_ohcl:
                dvm.appendDV(d["date"], d["close"])
            dvm_smas=[]
            for sma in [10, 50, 200]:
                dvm_smas.append(dvm.sma(sma))
            
            for o in self.arr:
                number_sma_over_price=len(self.list_of_sma_over_price(date.today(), o.value, [10, 50, 200], dvm_smas,  "close"))
                if number_sma_over_price==2 and o.id %2==0:
                    o.recomendation_invest=True
                elif number_sma_over_price<=1:
                    o.recomendation_invest=True
        elif self.method==5: #ProductRangeInvestRecomendation.SMA100 STRICT:           
            list_ohcl=self.product.ohclDailyBeforeSplits()
            dvm=DatetimeValueManager()
            for d in list_ohcl:
                dvm.appendDV(d["date"], d["close"])
            dvm_smas=[]
            for sma in [100, ]:
                dvm_smas.append(dvm.sma(sma))
            
            for o in self.arr:
                number_sma_over_price=len(self.list_of_sma_over_price(date.today(), o.value, [100, ], dvm_smas,  "close"))
                if number_sma_over_price==0:
                    o.recomendation_invest=True
                else:
                    o.recomendation_invest=False
        elif self.method==6:#ProductRangeInvestRecomendation.Strict SMA 10 , 100:      
            list_ohcl=self.product.ohclDailyBeforeSplits()
            dvm=DatetimeValueManager()
            for d in list_ohcl:
                dvm.appendDV(d["date"], d["close"])
            dvm_smas=[]
            for sma in [10,  100]:
                dvm_smas.append(dvm.sma(sma))
            
            for o in self.arr:
                number_sma_over_price=len(self.list_of_sma_over_price(date.today(), o.value, [10,  100], dvm_smas,  "close"))
                if number_sma_over_price<2:
                    o.recomendation_invest=True

    def json(self):
        r={}
        ohcl=[]
        ld_ohcl=self.product.ohclDailyBeforeSplits()         
        dvm=DatetimeValueManager()
        for d in ld_ohcl:
            ohcl.append((d["date"], d["close"]))
            dvm.appendDV(d["date"], d["close"])
        
        #Series for variable smas
        smas=[]
        for sma_ in self.list_of_sma_of_current_method():   
            
            sma={"name": f"SMA{sma_}", "data":[]}
            for o in dvm.sma(sma_):
                sma["data"].append((o.datetime, o.value))
                
            smas.append(sma)

        d=[]
        for i, o in enumerate(self.arr):
            d.append({
                "value": round(float(o.value),  self.decimals), 
                "recomendation_invest": o.recomendation_invest, 
                "investments_inside": o.getInvestmentsOperationsInsideJson(self.plio), 
                "orders_inside": o.getOrdersInsideJson(self.orders), 
                "current_in_range": o.isInside(self.product.quote_last().quote), 
                "limits": str(o)
            })
            
        r["pr"]=d
        r["product"]={
            "name": o.product.fullName(), 
            "last": o.product.quote_last().quote, 
            "currency": o.product.currency, 
        }
        r["ohcl"]=ohcl
        r["smas"]=smas
        return r
