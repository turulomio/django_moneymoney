from datetime import date
from decimal import Decimal
from json import dumps
from django.urls import reverse
from django.utils import timezone
from xulpymoney.libmanagers import ObjectManager, DatetimeValueManager
from money.models import Investments, Orders
from money.reusing.listdict_functions import listdict2list
from money.reusing.percentage import Percentage
from money.investmentsoperations import InvestmentsOperationsManager_from_investment_queryset

class ProductRange():
    def __init__(self, request,  id=None,  product=None,  value=None, percentage_down=None,  percentage_up=None, only_first=True, only_account=None, decimals=2):
        self.request=request
        self.id=id
        self.product=product
        self.value=value
        self.percentage_down=percentage_down
        self.percentage_up=percentage_up
        self.only_first=only_first
        self.only_account=only_account
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
    def getInvestmentsOperationsInsideJson(self, iom):
        r=[]
        for io in iom.list:
            if self.only_account is not None:#If different account continues
                if io.investment.accounts.id != self.only_account.id:
                    continue
            
            for op in io.io_current:
                if self.only_first is True:#Only first when neccesary
                    if io.io_current.index(op)!=0:
                        continue
                if self.isInside(op["price_investment"])==True:
                    r.append({
                        "url": reverse('investment_view', args=(io.investment.id,)), 
                        "name": io.investment.fullName(), 
                        "invested": float(op[ 'invested_user']), 
                    })

        return r
        
    ## Search for orders in self.mem.data and 
    def getOrdersInsideJson(self, orders): 
        r=[]
        for o in orders:
            if self.only_account is not None:#If different account continues
                if o.investments.accounts.id != self.only_account.id:
                    continue
            if o.investments.products.id==self.product.id and self.isInside(o.price)==True:
                r.append({
                    "url": reverse('order_update',  args=(o.id, )), 
                    "name": o.investments.fullName(), 
                    "amount": float(o.currency_amount().amount), 
                })
        return r
      

class ProductRangeManager(ObjectManager):
    def __init__(self, request, product, percentage_down, percentage_up, only_first=True, only_account=None, decimals=2):
        ObjectManager.__init__(self)
        self.only_first=only_first
        self.only_account=only_account
        self.request=request
        self.product=product
        self.percentage_down=Percentage(percentage_down, 100)
        self.percentage_up=Percentage(percentage_up, 100)
        self.decimals=decimals
        self.method=0
        
        max_=self.product.highest_investment_operation_price()
        min_=self.product.lowest_investment_operation_price()
        
        
        if max_ is not None and min_ is not None: #Investment with shares
            range_highest=max_*Decimal(1+self.percentage_down.value*10)#5 times up value
            range_lowest=min_*Decimal(1-self.percentage_down.value*10)#5 times down value
        else: # No investment jet and shows ranges from product current price
            range_highest=self.product.basic_results()["last"]*Decimal(1+self.percentage_down.value*10)#5 times up value
            range_lowest=self.product.basic_results()["last"]*Decimal(1-self.percentage_down.value*10)#5 times down value

        if range_lowest<Decimal(0.001):#To avoid infinity loop
            range_lowest=Decimal(0.001)



        self.highest_range_value=10000000
        current_value=self.highest_range_value
        i=0
        while current_value>range_lowest:
            if current_value>=range_lowest and current_value<=range_highest:
                self.append(ProductRange(self.request,  i, self.product,current_value, self.percentage_down, percentage_up, self.only_first, self.only_account))
            current_value=current_value*(1-self.percentage_down.value)
            i=i+1

        self.qs_investments=Investments.objects.select_related("accounts").filter(active=True, products_id=self.product.id)
        self.iom=InvestmentsOperationsManager_from_investment_queryset(self.qs_investments, timezone.now(), self.request)
        
        self.orders=Orders.objects.select_related("investments").select_related("investments__accounts").select_related("investments__products").select_related("investments__products__leverages").select_related("investments__products__productstypes").filter(executed=None, expiration__gte=date.today())

        
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

    def listdict_json(self):
        r=[]
        for i, o in enumerate(self.arr):
            r.append({
                "value": round(float(o.value),  self.decimals), 
                "recomendation_invest": o.recomendation_invest, 
                "investments_inside": o.getInvestmentsOperationsInsideJson(self.iom), 
                "orders_inside": o.getOrdersInsideJson(self.orders), 
                "current_in_range": o.isInside(self.product.basic_results()["last"]), 
                "limits": str(o)
            })
        return dumps(r,  indent=4, sort_keys=True)

    ## ECHARTS
    def eChartVUE(self, name="chart_product_ranges"):            
        ld_ohcl=self.product.ohclDailyBeforeSplits()         
        dvm=DatetimeValueManager()
        for d in ld_ohcl:
            dvm.appendDV(d["date"], d["close"])
        
        #Series for variable smas
        sma_series=""
        sma_series_legend=""
        for sma in self.list_of_sma_of_current_method():   
            l=["None"]*sma
            for o in dvm.sma(sma):
                l.append(float(o.value))
            sma_series=sma_series+f"""{{
                        name: 'SMA{sma}',
                        type: 'line',
                        data: {str(l)},
                        smooth: true,
                        showSymbol: false,
                        lineStyle: {{
                            width: 1
                        }}
                    }},
    """   
            sma_series_legend=sma_series_legend+f"'SMA{sma}', "
        sma_series_legend=sma_series_legend[:-2]
        
        #Series for product ranges horizontal lines
        ranges_series=""
        for range_ in self:
            if range_.recomendation_invest is True:
                ranges_series=ranges_series+f"""
                    {{
                        type: 'line',
                        data: {str([float(range_.value)]*len(ld_ohcl))},
                        tooltip: {{
                            show: false
                        }}, 
                        showSymbol: false,
                        itemStyle: {{
                            color: 'rgba(255, 173, 177, 0.4)'
                        }}, 
                    }},
    """
       
        return f"""
        {{
                legend: {{
                    data: ['{self.product.name}', {sma_series_legend}],
                    inactiveColor: '#777',
                }},
                tooltip: {{
                    trigger: 'axis',
                    axisPointer: {{
                        animation: false,
                        type: 'cross',
                        lineStyle: {{
                            color: '#376df4',
                            width: 2,
                            opacity: 1
                        }}
                    }}
                }},
                xAxis: {{
                    type: 'category',
                    data: {str(listdict2list(ld_ohcl, "date", cast="str"))},
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
                        name: '{self.product.name}',
                        data: {str(listdict2list(ld_ohcl, "close", cast="float"))},
                    }},
                    {ranges_series}, 
                    {sma_series}, 
                ]
            }}
        """
