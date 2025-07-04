from datetime import date
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from moneymoney import models, ios,indicators
from pydicts.percentage import Percentage
import pandas as pd


## INTEGRATE IN PYDICTS

## Return find less or equal dv of a given datetime
## @param dt datetime
def lod_dtv_find_le(lod_dtv_, dt):
    for o in reversed(lod_dtv_):
        if o["datetime"]<=dt:
            return o
    return None

    

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

        

    def setInvestRecomendations(self, method, df):
        print("RECO", method, df)

        if method==0:#ProductRangeInvestRecomendation. None_:
            return False
        elif method==1:#ProductRangeInvestRecomendation.All:
            return True
        elif method==2:#ProductRangeInvestRecomendation.ThreeSMA:   
            return False   

            # for o in self.arr:
            #     number_sma_over_price=len(self.list_of_sma_over_price(date.today(), o.value, [10, 50, 200], dvm_smas,  "close"))
            #     if number_sma_over_price==3 and o.id % 4==0:
            #         o.recomendation_invest=True
            #     elif number_sma_over_price==2 and o.id %2==0:
            #         o.recomendation_invest=True
            #     elif number_sma_over_price<=1:
            #         o.recomendation_invest=True
        elif method==3: #ProductRangeInvestRecomendation.SMA100:            
            return False         
            # for o in self.arr:
            #     number_sma_over_price=len(self.list_of_sma_over_price(date.today(), o.value, [100, ], dvm_smas,  "close"))
            #     if number_sma_over_price==0:
            #         o.recomendation_invest=True
            #     else: #number_sma_over_price=1 and o.id%4!=0
            #         o.recomendation_invest=False
        elif method==4:#ProductRangeInvestRecomendation.StrictThreeSMA:            
            return False         
            
            # for o in self.arr:
            #     number_sma_over_price=len(self.list_of_sma_over_price(date.today(), o.value, [10, 50, 200], dvm_smas,  "close"))
            #     if number_sma_over_price==2 and o.id %2==0:
            #         o.recomendation_invest=True
            #     elif number_sma_over_price<=1:
            #         o.recomendation_invest=True
        elif method==5: #ProductRangeInvestRecomendation.SMA100 STRICT:        
            return False                  
           
            # for o in self.arr:
            #     number_sma_over_price=len(self.list_of_sma_over_price(date.today(), o.value, [100, ], dvm_smas,  "close"))
            #     if number_sma_over_price==0:
            #         o.recomendation_invest=True
            #     else:
            #         o.recomendation_invest=False
        elif method==6:#ProductRangeInvestRecomendation.Strict SMA 10 , 100:       
            return False              
           
            # for o in self.arr:
            #     number_sma_over_price=len(self.list_of_sma_over_price(date.today(), o.value, [10,  100], dvm_smas,  "close"))
            #     if number_sma_over_price<2:
            #         o.recomendation_invest=True
        elif method==8: #ProductRangeInvestRecomendation.SMA10 Entry below SMA10 aren't recommended      
            if df.empty:
                return False
            return df["close"].iloc[-1] >= df["SMA10"].iloc[-1]   

            
            # for o in self.arr:
            #     number_sma_over_price=len(self.list_of_sma_over_price(date.today(), o.value, [10, ], dvm_smas,  "close"))
            #     if number_sma_over_price==0:
            #         o.recomendation_invest=True
            #     else: #number_sma_over_price=1 and o.id%4!=0
            #         o.recomendation_invest=False
        elif method==9: #ProductRangeInvestRecomendation.SMA10 Entry below SMA10 aren't recommended            
            return False              

            
            # for o in self.arr:
            #     number_sma_over_price=len(self.list_of_sma_over_price(date.today(), o.value, [5, ], dvm_smas,  "close"))
            #     if number_sma_over_price==0:
            #         o.recomendation_invest=True
            #     else: #number_sma_over_price=1 and o.id%4!=0
            #         o.recomendation_invest=False
        elif method==10: #HMA 10           
            if df.empty:
                return False
            return df["close"].iloc[-1] >= df["HMA10"].iloc[-1]


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

class ProductRangeManager:
    def __init__(self, request, product, percentage_down, percentage_up, totalized_operations=True, decimals=2, qs_investments=[], additional_ranges=3, recomendation_methods=0):
        self.totalized_operations=totalized_operations
        self.request=request
        self.product=product
        self.qs_investments=qs_investments
        self.percentage_down=Percentage(percentage_down, 100)
        self.percentage_up=Percentage(percentage_up, 100)
        self.decimals=decimals
        self.method=recomendation_methods
        
        self.plio=ios.IOS.from_qs( timezone.now(), request.user.profile.currency, self.qs_investments,  1)

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
        if product.basic_results()["last"]> max_:
            max_=product.basic_results()["last"]
        if product.basic_results()["last"]< min_:
            min_=product.basic_results()["last"]
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
            current_index=self.getTmpIndexOfValue(self.product.basic_results()["last"])
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
            sma_value=lod_dtv_find_le(dvm_sma, dt)
            if sma_value is not None and  price<sma_value["value"]:
                r.append(smas[i])
        return r


    
    def recomendationmethods2indicators(self):
        if self.method in (0, 1):#ProductRangeInvestRecomendation. None_:
            return []
        elif self.method in (2, 4):#ProductRangeInvestRecomendation.ThreeSMA:      
            return [("SMA", 10), ("SMA",50), ("SMA", 200)]
        elif self.method in (3, 5): #ProductRangeInvestRecomendation.SMA100:        
            return [("SMA", 100), ]
        elif self.method==6:#ProductRangeInvestRecomendation.Strict SMA 10 , 100:      
            return  [("SMA", 10), ("SMA", 100)]
        elif self.method==8:#ProductRangeInvestRecomendation.SMA 10
            return [("SMA", 10),]
        elif self.method==9:#ProductRangeInvestRecomendation.SMA 5
            return [("SMA", 5)]
        elif self.method==10:#ProductRangeInvestRecomendation.SMA 5
            return  [("HMA", 10)]
        
    def append_indicators(self,df):
        """
            df is a panda Dataframe with ohcl and date keys
        """
        print(self.recomendationmethods2indicators())
        for indicator in self.recomendationmethods2indicators():
            if indicator[0]=="SMA":
                df=indicators.sma(df, indicator[1])
            elif indicator[0]=="HMA":
                df=indicators.hma(df, indicator[1])
        return df

            


    def json(self):
        r={}
        ld_ohcl=self.product.ohclDailyBeforeSplits()         
        df=pd.DataFrame(ld_ohcl)
        df=self.append_indicators(df)

        r["pr"]=[]
        for i, o in enumerate(self.arr):
            r["pr"].append({
                "value": round(float(o.value),  self.decimals), 
                "recomendation_invest": o.setInvestRecomendations(self.method,df),
                "investments_inside": o.getInvestmentsOperationsInsideJson(self.plio), 
                "orders_inside": o.getOrdersInsideJson(self.orders), 
                "current_in_range": o.isInside(self.product.basic_results()["last"]), 
                "limits": str(o)
            })
        r["product"]={
            "name": o.product.fullName(), 
            "last": o.product.basic_results()["last"], 
            "currency": o.product.currency, 
        }
        r["dataframe"]=df.to_dict('records')
        return r
